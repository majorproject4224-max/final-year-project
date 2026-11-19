"""Activity permissions, inclusive profiles, matching and atomic capacity on disposable MongoDB."""

import os
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from unittest import skipUnless
from unittest.mock import patch
from bson import ObjectId
from django.test import SimpleTestCase
from rest_framework.test import APIClient
from . import tests as platform_tests
from .common import now
from .mongo import get_collection


@skipUnless(os.getenv("RUN_MONGO_TESTS") == "1", "Requires disposable MongoDB/Redis test services.")
class ActivityTests(SimpleTestCase):
    setUp = platform_tests.PlatformTests.setUp
    register = platform_tests.PlatformTests.register
    as_user = platform_tests.PlatformTests.as_user

    def activity(self, owner, **changes):
        self.as_user(owner)
        response = self.client.post(
            "/api/events/",
            {
                "title": "Community garden",
                "description": "Plant and care for trees. Beginners welcome.",
                "location": "Community park",
                "city": "Delhi",
                "category": "Volunteer drive",
                "interest_tags": [" Gardening ", "GARDENING", "Environmental conservation"],
                "participant_limit": 2,
                "starts_at": (now() + timedelta(days=3)).isoformat(),
                **changes,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        return response.data

    def test_individual_profile_and_organizer_permissions(self):
        owner, member = self.register("Owner"), self.register("Member")
        self.as_user(owner)
        response = self.client.put(
            "/api/profiles/me/", {"name": "Individual", "languages": [], "databases": [], "frameworks": [], "platforms": [], "community_interests": ["Gardening"]}, format="json"
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertNotIn("academic_year", response.data)
        self.assertEqual(response.data["skills"], [])
        activity = self.activity(owner)
        self.assertEqual(activity["organizer_name"], "Individual")
        self.assertEqual(activity["organization_name"], "")
        self.assertEqual(activity["interest_tags"], ["environmental conservation", "gardening"])
        endpoint = f"/api/events/{activity['id']}/"
        self.as_user(member)
        self.assertEqual(self.client.post(endpoint + "attendance/").status_code, 200)
        self.assertEqual(self.client.get(endpoint + "participants/").status_code, 403)
        self.assertEqual(
            self.client.patch(endpoint, {"title": "Hacked"}, format="json").status_code, 403
        )
        self.assertEqual(self.client.delete(endpoint).status_code, 403)
        self.assertNotIn("attendee_ids", self.client.get(endpoint).data)
        self.as_user(owner)
        people = self.client.get(endpoint + "participants/").data["items"]
        self.assertEqual(people, [{"user_id": member["id"], "name": "Member"}])
        self.assertEqual(
            self.client.patch(
                endpoint, {"organization_name": "Gardening club"}, format="json"
            ).status_code,
            200,
        )
        self.assertEqual(self.client.get("/api/events/?scope=organizing").data["total"], 1)
        self.client.credentials()
        self.assertEqual(self.client.get(endpoint).status_code, 401)
        self.as_user(owner)
        self.assertEqual(self.client.delete(endpoint).status_code, 204)

    def test_capacity_is_atomic_idempotent_and_released_when_leaving(self):
        owner = self.register("Owner")
        first, second = self.register("First"), self.register("Second")
        activity = self.activity(owner, participant_limit=1)
        endpoint = f"/api/events/{activity['id']}/attendance/"

        def join(user):
            client = APIClient()
            client.credentials(HTTP_AUTHORIZATION="Bearer " + self.tokens[user["id"]]["access"])
            return client.post(endpoint).status_code

        with ThreadPoolExecutor(max_workers=2) as pool:
            statuses = list(pool.map(join, [first, second]))
        self.assertEqual(sorted(statuses), [200, 409])
        winner, other = (first, second) if statuses[0] == 200 else (second, first)
        self.assertEqual(join(winner), 200)
        document = get_collection("events").find_one({"_id": ObjectId(activity["id"])})
        self.assertEqual(len(document["attendee_ids"]), 1)
        self.as_user(winner)
        self.assertEqual(self.client.delete(endpoint).status_code, 204)
        self.assertEqual(join(other), 200)
        self.as_user(owner)
        detail = f"/api/events/{activity['id']}/"
        self.assertEqual(
            self.client.patch(detail, {"participant_limit": 2}, format="json").status_code, 200
        )
        self.assertEqual(join(winner), 200)
        self.assertEqual(
            self.client.patch(detail, {"participant_limit": 1}, format="json").status_code, 409
        )

    def test_shared_interests_location_exclusions_and_no_ml_dependency(self):
        owner, member = self.register("Owner"), self.register("Member")
        local = self.activity(owner)
        remote = self.activity(owner, city="Mumbai")
        online = self.activity(owner, mode="Online", city="")
        unrelated = self.activity(owner, interest_tags=["Photography"])
        full = self.activity(owner, participant_limit=1)
        get_collection("events").update_one(
            {"_id": ObjectId(full["id"])}, {"$set": {"attendee_ids": [ObjectId(owner["id"])]}}
        )
        expired = self.activity(owner)
        get_collection("events").update_one(
            {"_id": ObjectId(expired["id"])}, {"$set": {"starts_at": now() - timedelta(days=1)}}
        )
        own = self.activity(member)
        self.as_user(member)
        response = self.client.put(
            "/api/profiles/me/",
            {
                "name": "Member",
                "community_interests": ["GARDENING"],
                "city": " delhi ",
                "activity_location_preference": "local",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        with patch(
            "platform_api.services.recommendations.load_models",
            side_effect=AssertionError("Activity matching must not load ML"),
        ):
            result = self.client.get("/api/recommendations/activities/")
        self.assertEqual(result.status_code, 200, result.data)
        self.assertEqual({r["id"] for r in result.data["items"]}, {local["id"], online["id"]})
        self.assertEqual(result.data["matching_method"], "shared_interests")
        self.assertNotIn("compatibility_score", result.data["items"][0])
        self.assertEqual(result.data["items"][0]["shared_interests"], ["gardening"])
        self.assertIn("Matches your interests: gardening", result.data["items"][0]["reasons"])
        for hidden in (remote, unrelated, full, expired, own):
            self.assertNotIn(hidden["id"], {r["id"] for r in result.data["items"]})
        self.client.post(f"/api/events/{local['id']}/attendance/")
        self.assertEqual(
            [r["id"] for r in self.client.get("/api/recommendations/activities/").data["items"]],
            [online["id"]],
        )
        self.assertEqual(self.client.get("/api/events/?scope=joined").data["total"], 1)
        self.client.put(
            "/api/profiles/me/",
            {"name": "Member", "community_interests": ["gardening"], "activity_location_preference": "any"},
            format="json",
        )
        self.assertIn(
            remote["id"],
            {r["id"] for r in self.client.get("/api/recommendations/activities/").data["items"]},
        )

    def test_validation_legacy_events_and_cold_start(self):
        owner = self.register("Owner")
        activity = self.activity(owner)
        endpoint = f"/api/events/{activity['id']}/"
        for invalid in (
            {"participant_limit": 0},
            {"participant_limit": 501},
            {"interest_tags": []},
            {"category": "Unknown"},
            {"starts_at": (now() - timedelta(days=1)).isoformat()},
        ):
            self.assertEqual(self.client.patch(endpoint, invalid, format="json").status_code, 400)
        self.assertEqual(
            self.client.put(
                "/api/profiles/me/",
                {
                    "name": "Owner",
                    "community_interests": ["gardening"],
                    "activity_location_preference": "local",
                },
                format="json",
            ).status_code,
            400,
        )
        get_collection("profiles").delete_one({"user_id": ObjectId(owner["id"])})
        result = self.client.get("/api/recommendations/activities/")
        self.assertEqual(result.data["items"], [])
        self.assertIn("interests", result.data["detail"])
        get_collection("events").update_one(
            {"_id": ObjectId(activity["id"])},
            {
                "$unset": {
                    key: ""
                    for key in ("participant_limit", "interest_tags", "category", "city", "mode")
                }
            },
        )
        result = self.client.get(endpoint)
        self.assertEqual(result.data["participant_limit"], 500)
        self.assertEqual(result.data["category"], "Other")
        self.assertEqual(self.client.post(endpoint + "attendance/").status_code, 200)
        get_collection("events").update_one(
            {"_id": ObjectId(activity["id"])}, {"$set": {"starts_at": now() - timedelta(days=1)}}
        )
        self.assertEqual(self.client.post(endpoint + "attendance/").status_code, 409)
        self.assertEqual(
            self.client.patch(endpoint, {"title": "Past"}, format="json").status_code, 409
        )
        self.assertEqual(self.client.get("/api/events/?category=Unknown").status_code, 400)
