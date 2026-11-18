"""Explicit MongoDB persistence; transactions require a replica set (including Atlas)."""

from functools import lru_cache
from django.conf import settings
from pymongo import MongoClient


@lru_cache(maxsize=1)
def get_client():
    return MongoClient(
        settings.MONGODB_URI, serverSelectionTimeoutMS=5000, tz_aware=True, maxPoolSize=20
    )


def get_collection(name):
    return get_client()[settings.MONGODB_DATABASE][name]


def run_transaction(operation):
    with get_client().start_session() as session:
        return session.with_transaction(operation)


def ensure_indexes():
    definitions = {
        "users": [("email", {"unique": True})],
        "profiles": [("user_id", {"unique": True}), ("skills", {}), ("domain", {})],
        "connections": [("pair_key", {"unique": True})],
        "projects": [([("status", 1), ("created_at", -1)], {}), ("team_members", {})],
        "applications": [([("project_id", 1), ("user_id", 1)], {"unique": True})],
        "invitations": [([("project_id", 1), ("recipient_id", 1)], {"unique": True})],
        "conversations": [("pair_key", {"unique": True}), ("participants", {})],
        "messages": [
            ([("conversation_id", 1), ("_id", -1)], {}),
            (
                [("conversation_id", 1), ("sender_id", 1), ("client_id", 1)],
                {"unique": True, "partialFilterExpression": {"client_id": {"$exists": True}}},
            ),
        ],
        "events": [("starts_at", {}), ([("interest_tags", 1), ("starts_at", 1)], {}), ("organizer_id", {})],
        "feedback": [
            ([("project_id", 1), ("from_user_id", 1), ("to_user_id", 1)], {"unique": True})
        ],
        "auth_sessions": [("sid", {"unique": True}), ("expires_at", {"expireAfterSeconds": 0})],
        "websocket_tickets": [
            ("ticket_hash", {"unique": True}),
            ("expires_at", {"expireAfterSeconds": 0}),
        ],
        "interactions": [
            (
                [("user_id", 1), ("target_type", 1), ("target_id", 1), ("action", 1)],
                {"unique": True},
            )
        ],
    }
    for name, indexes in definitions.items():
        for keys, options in indexes:
            get_collection(name).create_index(keys, **options)
