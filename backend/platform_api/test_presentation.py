"""Presentation preparation uses real ML artifacts and a disposable MongoDB replica set."""

import gzip
import os
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import skipUnless
from unittest.mock import patch
from bson import ObjectId, json_util
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase, override_settings
from . import tests as platform_tests
from .common import now, pair_key
from .mongo import get_collection, get_client
from .presentation_data import SOURCE, fixture_id


@skipUnless(os.getenv("RUN_MONGO_TESTS") == "1", "Requires disposable MongoDB/Redis test services.")
@override_settings(DEBUG=True)
class PresentationTests(SimpleTestCase):
    setUp = platform_tests.PlatformTests.setUp
    register = platform_tests.PlatformTests.register
    as_user = platform_tests.PlatformTests.as_user
    project = platform_tests.PlatformTests.project

    def tearDown(self):
        if not settings.MONGODB_DATABASE.endswith("_test"):
            raise RuntimeError("Refusing to clear a non-test database.")
        get_client().drop_database(settings.MONGODB_DATABASE)

    def prepare(self, **options):
        output = StringIO()
        with patch.dict(os.environ, {"PRESENTATION_PASSWORD": "Presentation-tests-only-4224!"}):
            call_command("prepare_presentation", stdout=output, **options)
        self.assertNotIn("Presentation-tests-only-4224!", output.getvalue())
        return output.getvalue()

    def test_replacement_preserves_personal_data_and_measured_matches(self):
        personal, old = self.register("Personal"), self.register("Legacy")
        old_id, personal_id = ObjectId(old["id"]), ObjectId(personal["id"])
        get_collection("users").update_one(
            {"_id": old_id},
            {"$set": {"email": "demo1@example.invalid", "data_source": "synthetic_demo"}},
        )
        old_project = ObjectId(self.project(old))
        personal_project = ObjectId(self.project(personal))
        get_collection("projects").update_one(
            {"_id": personal_project}, {"$addToSet": {"team_members": old_id}}
        )
        pair = pair_key(old_id, personal_id)
        get_collection("connections").insert_one(
            {
                "pair_key": pair,
                "requester_id": old_id,
                "recipient_id": personal_id,
                "status": "Accepted",
            }
        )
        conversation = (
            get_collection("conversations")
            .insert_one(
                {"pair_key": pair, "participants": [old_id, personal_id], "updated_at": now()}
            )
            .inserted_id
        )
        get_collection("messages").insert_one(
            {
                "conversation_id": conversation,
                "sender_id": old_id,
                "content": "Old presentation",
                "attachments": [{"size": 3, "data": b"abc"}],
            }
        )
        get_collection("storage_usage").insert_one({"_id": "chat_attachments", "bytes": 8})
        with TemporaryDirectory() as directory, override_settings(PROJECT_ROOT=Path(directory)):
            preview = self.prepare()
            self.assertIn("Preview only", preview)
            self.assertEqual(get_collection("users").count_documents({}), 2)
            self.assertFalse((Path(directory) / ".presentation-private").exists())
            self.prepare(apply=True, replace_legacy_records=True)
            self.assertIsNone(get_collection("users").find_one({"_id": old_id}))
            self.assertIsNone(get_collection("projects").find_one({"_id": old_project}))
            self.assertIsNotNone(get_collection("users").find_one({"_id": personal_id}))
            self.assertEqual(
                get_collection("projects").find_one({"_id": personal_project})["team_members"],
                [personal_id],
            )
            self.assertIsNone(get_collection("conversations").find_one({"_id": conversation}))
            self.assertEqual(
                get_collection("storage_usage").find_one({"_id": "chat_attachments"})["bytes"], 5
            )
            self.assertEqual(get_collection("users").count_documents({"data_source": SOURCE}), 5)
            self.assertEqual(get_collection("projects").count_documents({"data_source": SOURCE}), 5)
            self.assertEqual(get_collection("events").count_documents({"data_source": SOURCE}), 2)
            backups = list(
                (Path(directory) / ".presentation-private").glob("legacy-backup-*.json.gz")
            )
            self.assertEqual(len(backups), 1)
            with gzip.open(backups[0], "rt") as stream:
                backup = json_util.loads(stream.read())
            self.assertEqual(backup["collections"]["users"][0]["_id"], old_id)
            self.assertEqual(backup["collections"]["messages"][0]["attachments"][0]["data"], b"abc")
            old_hash = get_collection("users").find_one({"_id": fixture_id("aarav")})[
                "password_hash"
            ]
            self.prepare(apply=True, replace_legacy_records=True)
            self.assertEqual(
                get_collection("users").find_one({"_id": fixture_id("aarav")})["password_hash"],
                old_hash,
            )
            self.assertEqual(
                len(list((Path(directory) / ".presentation-private").glob("credentials-*.txt"))), 1
            )
        self.client.credentials()
        login = self.client.post(
            "/api/auth/login/",
            {"email": "aarav@connect.example", "password": "Presentation-tests-only-4224!"},
            format="json",
        )
        self.assertEqual(login.status_code, 200, login.data)
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + login.data["tokens"]["access"])
        people = self.client.get("/api/recommendations/users/").data["items"]
        self.assertIn(str(fixture_id("rohan")), {row["user_id"] for row in people})
        self.assertNotIn(str(fixture_id("priya")), {row["user_id"] for row in people})
        projects = self.client.get("/api/recommendations/projects/").data["items"]
        self.assertIn(str(fixture_id("study-buddy")), {row["id"] for row in projects})
        self.assertEqual(
            self.client.get("/api/connections/").data["items"][0]["status"], "Accepted"
        )
        self.assertEqual(
            self.client.get("/api/conversations/").data["items"][0]["participant_name"],
            "Priya Verma",
        )
        self.assertIn(
            str(fixture_id("plantation")),
            {
                row["id"]
                for row in self.client.get("/api/recommendations/activities/").data["items"]
            },
        )

    def test_unmarked_accounts_and_conflicting_identities_are_not_removed(self):
        personal = self.register("Personal")
        get_collection("users").update_one(
            {"_id": ObjectId(personal["id"])}, {"$set": {"email": "demo77@example.invalid"}}
        )
        with TemporaryDirectory() as directory, override_settings(PROJECT_ROOT=Path(directory)):
            self.prepare(apply=True, replace_legacy_records=True)
            self.assertIsNotNone(
                get_collection("users").find_one({"_id": ObjectId(personal["id"])})
            )
            get_collection("users").update_one(
                {"_id": fixture_id("aarav")}, {"$unset": {"data_source": ""}}
            )
            with self.assertRaises(CommandError):
                self.prepare(apply=True, replace_legacy_records=True)

    def test_production_guard(self):
        with override_settings(MONGODB_DATABASE="connect_ai_production"):
            with self.assertRaises(CommandError):
                self.prepare(apply=True, replace_legacy_records=True)
