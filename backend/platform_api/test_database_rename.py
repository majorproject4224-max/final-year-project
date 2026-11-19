"""Check the offline rename against disposable MongoDB namespaces only."""

import os
from unittest import skipUnless
from unittest.mock import patch
from uuid import uuid4
from bson import ObjectId
from django.test import SimpleTestCase, override_settings
from django.core.management.base import CommandError
from pymongo.database import Database
from pymongo.errors import OperationFailure
from .mongo import get_client
from .presentation_guard import require_presentation_database
from scripts.rename_database import move_database, snapshot


class PresentationGuardTests(SimpleTestCase):
    def test_application_requires_explicit_opt_in(self):
        with override_settings(DEBUG=True, MONGODB_DATABASE="connect_ai", PRESENTATION_DATA_ENABLED=False):
            with self.assertRaises(CommandError):
                require_presentation_database()
        with override_settings(DEBUG=True, MONGODB_DATABASE="connect_ai", PRESENTATION_DATA_ENABLED=True):
            require_presentation_database()

    def test_deployed_settings_always_reject_fictional_seeding(self):
        with override_settings(DEBUG=False, MONGODB_DATABASE="connect_ai_test", PRESENTATION_DATA_ENABLED=True):
            with self.assertRaises(CommandError):
                require_presentation_database()


@skipUnless(os.getenv("RUN_MONGO_TESTS") == "1", "Requires disposable MongoDB services.")
class DatabaseRenameTests(SimpleTestCase):
    def setUp(self):
        self.client = get_client()
        self.source = f"connect_ai_move_{uuid4().hex[:10]}_test"
        self.target = f"connect_ai_move_{uuid4().hex[:10]}_test"
        users = self.client[self.source].users
        user_id = ObjectId()
        users.insert_one({"_id": user_id, "email": "fixture@example.invalid", "password_hash": "unchanged-hash"})
        users.create_index("email", unique=True)
        self.client[self.source].z_messages.insert_one(
            {"sender_id": user_id, "content": "preserve", "attachment": b"\x00\xffbinary"}
        )
        self.before = snapshot(self.client[self.source])

    def tearDown(self):
        for name in (self.source, self.target):
            assert name.endswith("_test")
            self.client.drop_database(name)

    def test_preserves_bson_relationships_and_indexes(self):
        backups = []
        result = move_database(self.client, self.source, self.target, backups.append)
        self.assertEqual(backups, [self.before])
        self.assertEqual(result, self.before)
        self.assertFalse(self.client[self.source].list_collection_names())

    def test_existing_destination_is_never_overwritten(self):
        self.client[self.target].keep.insert_one({"value": "untouched"})
        with self.assertRaisesRegex(RuntimeError, "Destination"):
            move_database(self.client, self.source, self.target, lambda _: self.fail("Unexpected backup"))
        self.assertEqual(snapshot(self.client[self.source]), self.before)
        self.assertEqual(self.client[self.target].keep.find_one()["value"], "untouched")

    def test_failed_move_rolls_back_earlier_collections(self):
        original = Database.command

        def fail_one(database, command, *args, **kwargs):
            if command == "renameCollection" and args == (self.source + ".z_messages",):
                raise OperationFailure("Simulated interrupted move")
            return original(database, command, *args, **kwargs)

        with patch.object(Database, "command", fail_one):
            with self.assertRaises(OperationFailure):
                move_database(self.client, self.source, self.target, lambda _: None)
        self.assertEqual(snapshot(self.client[self.source]), self.before)
        self.assertFalse(self.client[self.target].list_collection_names())
