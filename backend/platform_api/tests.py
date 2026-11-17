"""Real MongoDB/Redis integration tests; never run against a production database."""

import os
import uuid
from datetime import timedelta
from concurrent.futures import ThreadPoolExecutor
from unittest import skipUnless
from unittest.mock import patch
from asgiref.sync import async_to_sync
from bson import ObjectId
from channels.routing import URLRouter
from channels.security.websocket import OriginValidator
from channels.testing import WebsocketCommunicator
from django.conf import settings
from django.core.cache import cache
from django.test import SimpleTestCase, override_settings
from django.urls import re_path
from rest_framework.test import APIClient
from .common import now
from .mongo import get_client, get_collection, ensure_indexes
from .messaging import ConversationConsumer
from .services.projects import decide_membership, Conflict
from .services.recommendations import load_models

PROFILE = {
    "name": "Asha",
    "branch": "CSE",
    "academic_year": 3,
    "skills": ["Python", "ML", "SQL"],
    "interests": ["Research", "AI"],
    "domain": "AI / ML",
    "experience": "Intermediate",
    "preferred_project_type": "AI/ML Application",
    "availability_hours": 8,
}
PROJECT = {
    "title": "Campus research assistant",
    "description": "Build a research tool with student collaborators.",
    "required_skills": ["Python", "Machine Learning"],
    "required_interests": ["Research", "AI"],
    "domain": "AI / ML",
    "project_type": "AI/ML Application",
    "team_size": 3,
}


@skipUnless(
    os.getenv("RUN_MONGO_TESTS") == "1",
    "Set RUN_MONGO_TESTS=1 with a disposable replica-set database ending in _test.",
)
class PlatformTests(SimpleTestCase):
    def setUp(self):
        if not settings.MONGODB_DATABASE.endswith("_test"):
            raise RuntimeError("Refusing to reset a database whose name does not end in _test.")
        get_client().drop_database(settings.MONGODB_DATABASE)
        ensure_indexes()
        cache.clear()
        self.client = APIClient()
        self.tokens = {}

    def register(self, name):
        self.client.credentials()
        response = self.client.post(
            "/api/auth/register/",
            {
                "name": name,
                "email": f"{name.lower()}@example.edu",
                "password": "Learning-project-4224!",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        user = response.data["user"]
        self.tokens[user["id"]] = response.data["tokens"]
        self.as_user(user)
        profile = self.client.put("/api/profiles/me/", {**PROFILE, "name": name}, format="json")
        self.assertEqual(profile.status_code, 200, profile.data)
        return user

    def as_user(self, user):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.tokens[user['id']]['access']}")

    def project(self, owner, **changes):
        self.as_user(owner)
        response = self.client.post("/api/projects/", {**PROJECT, **changes}, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        return response.data["id"]

    def connect(self, left, right):
        self.as_user(left)
        response = self.client.post("/api/connections/", {"user_id": right["id"]}, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        self.as_user(right)
        response2 = self.client.patch(
            f"/api/connections/{response.data['id']}/", {"action": "accept"}, format="json"
        )
        self.assertEqual(response2.status_code, 200, response2.data)
        return response.data["id"]

    def test_authentication_rotation_logout_validation_and_search(self):
        user = self.register("Asha")
        self.client.credentials()
        refresh = self.tokens[user["id"]]["refresh"]
        response = self.client.post("/api/auth/token/refresh/", {"refresh": refresh}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(
            self.client.post(
                "/api/auth/token/refresh/", {"refresh": refresh}, format="json"
            ).status_code,
            401,
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")
        self.assertEqual(self.client.post("/api/auth/logout/").status_code, 200)
        self.assertEqual(self.client.get("/api/auth/me/").status_code, 401)
        self.assertEqual(
            self.client.post(
                "/api/auth/register/",
                {"name": "Invalid", "email": "invalid@example.edu", "password": "12345678"},
                format="json",
            ).status_code,
            400,
        )
        second = self.register("Rahul")
        self.assertEqual(self.client.get("/api/students/?q=machine").data["total"], 1)
        response = self.client.put(
            "/api/profiles/me/", {**PROFILE, "academic_year": 9}, format="json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.client.get("/api/students/not-an-id/").status_code, 404)

    def test_applications_permissions_capacity_and_feedback(self):
        owner, applicant, outsider = (
            self.register("Owner"),
            self.register("Applicant"),
            self.register("Outsider"),
        )
        project_id = self.project(owner, team_size=2)
        self.as_user(applicant)
        response = self.client.post(f"/api/projects/{project_id}/applications/", {}, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        application_id = response.data["id"]
        self.assertEqual(
            self.client.get(f"/api/projects/{project_id}/applications/").status_code, 403
        )
        self.as_user(owner)
        result = self.client.patch(
            f"/api/projects/{project_id}/applications/",
            {"application_id": application_id, "decision": "Accepted"},
            format="json",
        )
        self.assertEqual(result.status_code, 200, result.data)
        self.as_user(outsider)
        self.assertEqual(
            self.client.post(
                f"/api/projects/{project_id}/applications/", {}, format="json"
            ).status_code,
            409,
        )
        self.assertEqual(
            self.client.patch(
                f"/api/projects/{project_id}/", {"title": "Hijacked"}, format="json"
            ).status_code,
            403,
        )
        self.as_user(applicant)
        payload = {
            "project_id": project_id,
            "to_user_id": owner["id"],
            "rating": 5,
            "comment": "Helpful teammate",
        }
        self.assertEqual(
            self.client.post("/api/feedback/", payload, format="json").status_code, 403
        )
        self.as_user(owner)
        for state in ("In Progress", "Completed"):
            self.assertEqual(
                self.client.patch(
                    f"/api/projects/{project_id}/", {"status": state}, format="json"
                ).status_code,
                200,
            )
        self.as_user(applicant)
        self.assertEqual(
            self.client.post("/api/feedback/", payload, format="json").status_code, 201
        )
        self.assertEqual(
            self.client.delete(
                f"/api/projects/{project_id}/members/{applicant['id']}/"
            ).status_code,
            409,
        )

    def test_concurrent_applications_cannot_overfill_team(self):
        owner, first, second = (
            self.register("Owner"),
            self.register("First"),
            self.register("Second"),
        )
        identifier = self.project(owner, team_size=2)
        applications = []
        for user in (first, second):
            self.as_user(user)
            applications.append(
                self.client.post(
                    f"/api/projects/{identifier}/applications/", {}, format="json"
                ).data["id"]
            )

        def accept(application):
            try:
                decide_membership(
                    ObjectId(identifier), ObjectId(application), ObjectId(owner["id"]), "Accepted"
                )
                return True
            except Conflict:
                return False

        with ThreadPoolExecutor(max_workers=2) as pool:
            accepted = list(pool.map(accept, applications))
        self.assertEqual(sum(accepted), 1)
        project = get_collection("projects").find_one({"_id": ObjectId(identifier)})
        self.assertEqual(len(project["team_members"]), 2)
        self.assertEqual(get_collection("applications").count_documents({"status": "Accepted"}), 1)

    def test_invitations_events_and_recommendations(self):
        owner, student, other = (
            self.register("Owner"),
            self.register("Student"),
            self.register("Other"),
        )
        identifier = self.project(owner)
        response = self.client.post(
            "/api/invitations/",
            {"project_id": identifier, "recipient_id": student["id"]},
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        invitation = response.data["id"]
        self.as_user(other)
        self.assertEqual(
            self.client.patch(
                f"/api/invitations/{invitation}/", {"decision": "Accepted"}, format="json"
            ).status_code,
            403,
        )
        self.as_user(student)
        self.assertEqual(
            self.client.patch(
                f"/api/invitations/{invitation}/", {"decision": "Accepted"}, format="json"
            ).status_code,
            200,
        )
        self.as_user(other)
        for url in ("/api/recommendations/users/", "/api/recommendations/projects/"):
            matches = self.client.get(url)
            self.assertEqual(matches.status_code, 200, matches.data)
            self.assertTrue(matches.data["items"], matches.data)
            self.assertIn("synthetic", matches.data["model_notice"])
        self.as_user(owner)
        matches = self.client.get(f"/api/projects/{identifier}/teammates/")
        self.assertEqual(matches.status_code, 200, matches.data)
        self.assertNotIn(student["id"], [p["user_id"] for p in matches.data["items"]])
        event = self.client.post(
            "/api/events/",
            {
                "title": "Showcase",
                "description": "Demo day",
                "location": "Campus",
                "starts_at": (now() + timedelta(days=5)).isoformat(),
            },
            format="json",
        )
        self.assertEqual(event.status_code, 201, event.data)
        endpoint = f"/api/events/{event.data['id']}/attendance/"
        self.client.post(endpoint)
        self.client.post(endpoint)
        self.assertEqual(self.client.get("/api/events/").data["items"][0]["attendee_count"], 1)
        self.client.delete(endpoint)
        self.assertEqual(self.client.get("/api/events/").data["items"][0]["attendee_count"], 0)

    def test_multiple_chat_partners_idempotence_read_receipts_and_permissions(self):
        left, right, third = self.register("Asha"), self.register("Rahul"), self.register("Priya")
        connection_id = self.connect(left, right)
        self.connect(left, third)
        self.as_user(left)
        first = self.client.post(
            "/api/conversations/", {"recipient_id": right["id"]}, format="json"
        )
        second = self.client.post(
            "/api/conversations/", {"recipient_id": third["id"]}, format="json"
        )
        self.assertEqual(first.status_code, 201, first.data)
        self.assertEqual(second.status_code, 201, second.data)
        identifier = first.data["id"]
        endpoint = f"/api/conversations/{identifier}/messages/"
        message = {"content": "Hello Rahul", "client_id": str(uuid.uuid4())}
        sent = self.client.post(endpoint, message, format="json")
        self.assertEqual(sent.status_code, 201, sent.data)
        repeated = self.client.post(endpoint, message, format="json")
        self.assertEqual(sent.data["id"], repeated.data["id"])
        self.assertEqual(get_collection("messages").count_documents({}), 1)
        self.as_user(third)
        self.assertEqual(self.client.get(endpoint).status_code, 404)
        self.as_user(right)
        self.assertEqual(
            self.client.patch(endpoint, {"through": sent.data["id"]}, format="json").status_code,
            200,
        )
        self.as_user(left)
        history = self.client.get(endpoint).data["items"]
        self.assertIn(right["id"], history[0]["read_by"])
        ticket = self.client.post(f"/api/conversations/{identifier}/websocket-ticket/").data[
            "ticket"
        ]
        self.client.delete(f"/api/connections/{connection_id}/")
        self.assertIsNone(ConversationConsumer.consume_ticket(ticket, identifier))
        self.assertEqual(
            self.client.post(
                endpoint, {"content": "Blocked", "client_id": str(uuid.uuid4())}, format="json"
            ).status_code,
            404,
        )

    def test_websocket_origin_tickets_delivery_and_reuse(self):
        left, right = self.register("Asha"), self.register("Rahul")
        self.connect(left, right)
        self.as_user(left)
        identifier = self.client.post(
            "/api/conversations/", {"recipient_id": right["id"]}, format="json"
        ).data["id"]
        ticket = self.client.post(f"/api/conversations/{identifier}/websocket-ticket/").data[
            "ticket"
        ]
        app = OriginValidator(
            URLRouter(
                [
                    re_path(
                        r"^ws/conversations/(?P<conversation_id>[0-9a-fA-F]{24})/$",
                        ConversationConsumer.as_asgi(),
                    )
                ]
            ),
            ["http://localhost:5173"],
        )

        async def exercise():
            address = f"/ws/conversations/{identifier}/?ticket={ticket}"
            denied = WebsocketCommunicator(
                app, address, headers=[(b"origin", b"https://evil.example")]
            )
            self.assertFalse((await denied.connect())[0])
            socket = WebsocketCommunicator(
                app, address, headers=[(b"origin", b"http://localhost:5173")]
            )
            self.assertTrue((await socket.connect())[0])
            await socket.send_json_to({"content": "Live message", "client_id": str(uuid.uuid4())})
            events = [
                await socket.receive_json_from(timeout=5),
                await socket.receive_json_from(timeout=5),
            ]
            self.assertEqual({e["type"] for e in events}, {"sent", "message"})
            await socket.disconnect()
            reused = WebsocketCommunicator(
                app, address, headers=[(b"origin", b"http://localhost:5173")]
            )
            self.assertFalse((await reused.connect())[0])

        async_to_sync(exercise)()

    def test_profile_privacy_validation_password_change_and_missing_models(self):
        owner, viewer = self.register("Owner"), self.register("Viewer")
        self.as_user(owner)
        self.client.put(
            "/api/profiles/me/",
            {**PROFILE, "phone": "private-number", "share_contact": True},
            format="json",
        )
        self.as_user(viewer)
        endpoint = f"/api/students/{owner['id']}/"
        self.assertNotIn("phone", self.client.get(endpoint).data)
        self.assertNotIn("email", self.client.get(endpoint).data)
        self.connect(owner, viewer)
        self.as_user(viewer)
        self.assertEqual(self.client.get(endpoint).data["phone"], "private-number")
        self.assertEqual(self.client.get("/api/students/?page=invalid").status_code, 400)
        self.assertEqual(self.client.post("/api/invitations/", [], format="json").status_code, 400)
        self.assertEqual(
            self.client.patch(
                "/api/auth/me/",
                {"current_password": "wrong", "new_password": "Changed-credentials-4224!"},
                format="json",
            ).status_code,
            400,
        )
        self.assertEqual(
            self.client.patch(
                "/api/auth/me/",
                {
                    "current_password": "Learning-project-4224!",
                    "new_password": "Changed-credentials-4224!",
                },
                format="json",
            ).status_code,
            200,
        )
        self.assertEqual(self.client.get("/api/auth/me/").status_code, 401)
        self.assertEqual(
            self.client.post(
                "/api/auth/token/refresh/",
                {"refresh": self.tokens[viewer["id"]]["refresh"]},
                format="json",
            ).status_code,
            401,
        )
        candidate = self.register("Candidate")
        self.as_user(owner)
        load_models.cache_clear()
        try:
            with override_settings(ML_MODEL_PATH="/missing/model.joblib"):
                response = self.client.get("/api/recommendations/users/")
                self.assertEqual(response.status_code, 503)
                self.assertEqual(response.data["code"], "models_unavailable")
        finally:
            load_models.cache_clear()

    def test_cold_start_duplicate_accounts_and_no_training_during_inference(self):
        owner, student = self.register("Owner"), self.register("Student")
        self.client.credentials()
        self.assertEqual(self.client.get("/api/students/").status_code, 401)
        duplicate = self.client.post(
            "/api/auth/register/",
            {
                "name": "Duplicate",
                "email": "STUDENT@example.edu",
                "password": "Learning-project-4224!",
            },
            format="json",
        )
        self.assertEqual(duplicate.status_code, 409)
        self.as_user(student)
        with patch(
            "sklearn.ensemble.RandomForestClassifier.fit",
            side_effect=AssertionError("Requests must not train"),
        ):
            result = self.client.get("/api/recommendations/users/")
            self.assertEqual(result.status_code, 200)
            scores = [item["compatibility_score"] for item in result.data["items"]]
            self.assertEqual(scores, sorted(scores, reverse=True))
        with patch("platform_api.recommendations.probabilities", return_value=[0.1]):
            self.assertEqual(self.client.get("/api/recommendations/users/").data["items"], [])
        get_collection("profiles").delete_one({"user_id": ObjectId(student["id"])})
        result = self.client.get("/api/recommendations/users/")
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.data["items"], [])
        self.assertIn("skills", result.data["detail"])
