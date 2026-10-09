import io
from datetime import datetime, timedelta, timezone
from asgiref.sync import async_to_sync
import mongomock
from bson import ObjectId
from docx import Document
from channels.routing import URLRouter
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase
from django.urls import re_path
from pymongo.errors import ServerSelectionTimeoutError
from rest_framework.test import APIClient
from unittest.mock import patch
from channels.testing import WebsocketCommunicator

from .messaging import ConversationConsumer


PROFILE = {
    "name": "Asha Student",
    "branch": "Computer Science and Engineering",
    "academic_year": 3,
    "skills": ["Python", "ML", "SQL"],
    "interests": ["Research", "AI"],
    "domain": "AI / ML",
    "experience": "Intermediate",
    "preferred_project_type": "AI/ML Application",
    "city": "Pune",
}


class PlatformApiTests(SimpleTestCase):
    def setUp(self):
        self.mongo_client = mongomock.MongoClient()
        self.mongo_patch = patch("platform_api.mongo.get_client", return_value=self.mongo_client)
        self.mongo_patch.start()
        self.addCleanup(self.mongo_patch.stop)
        self.client = APIClient()
        self.access_tokens = {}

    def register(self, name, email):
        response = self.client.post("/api/auth/register/", {
            "name": name,
            "email": email,
            "password": "a-strong-password",
        }, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['tokens']['access']}")
        self.access_tokens[email] = response.data["tokens"]["access"]
        return response.data["user"]

    def test_registration_login_profile_project_application_and_recommendation(self):
        first_user = self.register("Asha Student", "asha@example.edu")
        response = self.client.put("/api/profiles/me/", PROFILE, format="json")
        self.assertEqual(response.status_code, 200, response.data)

        response = self.client.post("/api/projects/", {
            "title": "Campus Research Assistant",
            "description": "Build a research assistant for student teams.",
            "required_skills": ["Python", "NLP"],
            "domain": "AI / ML",
            "project_type": "AI/ML Application",
        }, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        project_id = response.data["id"]

        self.client.credentials()
        second_user = self.register("Rahul Student", "rahul@example.edu")
        self.client.put("/api/profiles/me/", {**PROFILE, "name": "Rahul Student", "skills": ["python", "Machine Learning"]}, format="json")

        response = self.client.get("/api/recommendations/users/")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["items"][0]["name"], "Asha Student")
        self.assertGreaterEqual(response.data["items"][0]["compatibility_score"], 0)
        self.assertIn("model_notice", response.data)

        response = self.client.post(f"/api/projects/{project_id}/applications/", {}, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        response = self.client.post(f"/api/projects/{project_id}/applications/", {}, format="json")
        self.assertEqual(response.status_code, 409, response.data)

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access_tokens['asha@example.edu']}")
        response = self.client.get(f"/api/projects/{project_id}/applications/")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data[0]["name"], "Rahul Student")
        application_id = response.data[0]["id"]
        response = self.client.patch(f"/api/projects/{project_id}/applications/", {
            "application_id": application_id,
            "decision": "Accepted",
        }, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        project = self.mongo_client.connect_ai.projects.find_one({"_id": ObjectId(project_id)})
        self.assertIn(ObjectId(second_user["id"]), project["team_members"])

        self.client.credentials()
        response = self.client.post("/api/auth/login/", {
            "email": "rahul@example.edu",
            "password": "a-strong-password",
        }, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["user"]["id"], second_user["id"])

    def test_invalid_profile_is_rejected_and_protected_route_requires_token(self):
        response = self.client.get("/api/profiles/me/")
        self.assertEqual(response.status_code, 401)

        self.register("Asha Student", "asha@example.edu")
        response = self.client.put("/api/profiles/me/", {**PROFILE, "academic_year": 7}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_mongodb_unavailable_returns_json_service_unavailable(self):
        with patch("platform_api.views.get_collection") as get_collection_mock:
            get_collection_mock.return_value.find_one.side_effect = ServerSelectionTimeoutError(
                "127.0.0.1:27017 connection refused"
            )
            response = self.client.post("/api/auth/login/", {
                "email": "student@example.edu",
                "password": "a-strong-password",
            }, format="json")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.data["code"], "database_unavailable")
        self.assertIn("Start MongoDB", response.data["detail"])

    def test_resume_suggestions_are_reviewable_and_do_not_guess_missing_domain(self):
        self.register("Asha Student", "asha@example.edu")
        document = Document()
        document.add_paragraph("Resume Applicant")
        document.add_paragraph("Branch: Computer Science and Engineering")
        document.add_paragraph("Year: 2")
        document.add_paragraph("Skills: Communication, Leadership, Teamwork")
        buffer = io.BytesIO()
        document.save(buffer)
        upload = SimpleUploadedFile(
            "resume.docx",
            buffer.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )

        response = self.client.post("/api/profiles/resume-suggestions/", {"resume": upload}, format="multipart")

        self.assertEqual(response.status_code, 200, response.data)
        self.assertTrue(response.data["requires_review"])
        self.assertEqual(response.data["suggestions"]["branch"], "Computer Science And Engineering")
        self.assertEqual(response.data["suggestions"]["academic_year"], "2")
        self.assertEqual(response.data["suggestions"]["skills"], [])
        self.assertEqual(response.data["suggestions"]["domain"], "")

    def test_conversation_history_read_state_and_websocket_ticket(self):
        first_user = self.register("Asha Student", "asha@example.edu")
        self.client.credentials()
        second_user = self.register("Rahul Student", "rahul@example.edu")

        response = self.client.post("/api/conversations/", {"recipient_id": first_user["id"]}, format="json")
        self.assertEqual(response.status_code, 403, response.data)

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access_tokens['asha@example.edu']}")
        response = self.client.post("/api/connections/", {"user_id": second_user["id"]}, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        connection_id = response.data["id"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access_tokens['rahul@example.edu']}")
        response = self.client.patch(f"/api/connections/{connection_id}/")
        self.assertEqual(response.status_code, 200, response.data)

        response = self.client.post("/api/conversations/", {"recipient_id": first_user["id"]}, format="json")
        self.assertIn(response.status_code, (200, 201), response.data)
        conversation_id = response.data["id"]
        response = self.client.post(
            f"/api/conversations/{conversation_id}/messages/",
            {"content": "Would you like to collaborate?"},
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["sender_id"], second_user["id"])
        response = self.client.get(f"/api/conversations/{conversation_id}/messages/")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["sender_id"], second_user["id"])

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access_tokens['asha@example.edu']}")
        response = self.client.get(f"/api/conversations/{conversation_id}/messages/")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data[0]["sender_id"], second_user["id"])
        response = self.client.post(
            f"/api/conversations/{conversation_id}/messages/",
            {"content": "Yes, let's collaborate."},
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["sender_id"], first_user["id"])
        response = self.client.patch(f"/api/conversations/{conversation_id}/messages/")
        self.assertEqual(response.status_code, 200, response.data)
        response = self.client.post(f"/api/conversations/{conversation_id}/websocket-ticket/")
        self.assertEqual(response.status_code, 200, response.data)
        ticket = response.data["ticket"]

        async def exercise_socket():
            communicator = WebsocketCommunicator(
                URLRouter([re_path(r"^ws/conversations/(?P<conversation_id>[0-9a-fA-F]{24})/$", ConversationConsumer.as_asgi())]),
                f"/ws/conversations/{conversation_id}/?ticket={ticket}",
            )
            connected, _ = await communicator.connect()
            self.assertTrue(connected)
            await communicator.send_json_to({"content": "Live message"})
            sent = await communicator.receive_json_from()
            broadcast = await communicator.receive_json_from()
            self.assertEqual(sent["type"], "sent")
            self.assertEqual(broadcast["type"], "message")
            self.assertEqual(broadcast["message"]["content"], "Live message")
            self.assertEqual(broadcast["message"]["sender_id"], first_user["id"])
            await communicator.disconnect()

        async_to_sync(exercise_socket)()

        async def reject_reused_ticket():
            communicator = WebsocketCommunicator(
                URLRouter([re_path(r"^ws/conversations/(?P<conversation_id>[0-9a-fA-F]{24})/$", ConversationConsumer.as_asgi())]),
                f"/ws/conversations/{conversation_id}/?ticket={ticket}",
            )
            connected, _ = await communicator.connect()
            self.assertFalse(connected)

        async_to_sync(reject_reused_ticket)()
        self.assertEqual(second_user["email"], "rahul@example.edu")

    def test_connections_projects_events_and_feedback(self):
        first_user = self.register("Asha Student", "asha@example.edu")
        self.client.put("/api/profiles/me/", PROFILE, format="json")
        self.client.credentials()
        second_user = self.register("Rahul Student", "rahul@example.edu")
        self.client.put("/api/profiles/me/", {**PROFILE, "name": "Rahul Student"}, format="json")
        response = self.client.post("/api/projects/", {
            "title": "Campus Research Assistant",
            "description": "Build an assistant for research teams.",
            "required_skills": ["Python", "NLP"],
            "domain": "AI / ML",
            "project_type": "AI/ML Application",
        }, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        project_id = response.data["id"]

        response = self.client.get(f"/api/projects/{project_id}/teammates/")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["items"][0]["name"], "Asha Student")
        self.assertIn("required_skill_coverage", response.data["items"][0])

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access_tokens['asha@example.edu']}")
        response = self.client.get("/api/projects/recommendations/")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["items"][0]["title"], "Campus Research Assistant")
        self.assertEqual(response.data["items"][0]["explanations"][0]["items"], ["python"])
        self.assertIn("not a trained project classifier", response.data["ranking_method"])

        response = self.client.post("/api/connections/", {"user_id": second_user["id"]}, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        connection_id = response.data["id"]
        response = self.client.post("/api/connections/", {"user_id": second_user["id"]}, format="json")
        self.assertEqual(response.status_code, 409)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access_tokens['rahul@example.edu']}")
        response = self.client.patch(f"/api/connections/{connection_id}/")
        self.assertEqual(response.status_code, 200, response.data)
        response = self.client.get("/api/connections/")
        self.assertEqual(response.data[0]["status"], "Accepted")

        starts_at = (datetime.now(timezone.utc) + timedelta(days=4)).isoformat()
        response = self.client.post("/api/events/", {
            "title": "Project Showcase",
            "description": "Student teams share current work.",
            "location": "Engineering Hall",
            "starts_at": starts_at,
        }, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        event_id = response.data["id"]
        response = self.client.post(f"/api/events/{event_id}/attendance/", {}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        response = self.client.get("/api/events/")
        self.assertEqual(response.data[0]["attendee_count"], 1)

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access_tokens['asha@example.edu']}")
        response = self.client.post("/api/feedback/", {
            "to_user_id": second_user["id"],
            "rating": 5,
            "comment": "Clear communication during the project.",
        }, format="json")
        self.assertEqual(response.status_code, 201, response.data)