"""Prepare curated presentation records in a development DB; preview by default."""

import gzip
import os
import secrets
from pathlib import Path
from uuid import uuid4
from bson import json_util
from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.contrib.auth.password_validation import validate_password
from django.core.management.base import BaseCommand, CommandError
from platform_api.common import now, pair_key
from platform_api.mongo import get_collection, ensure_indexes, run_transaction
from platform_api.presentation_data import SOURCE, build_fixtures, fixture_id
from platform_api.services.recommendations import load_models
from ml.discovery import recommend_people, project_match


LEGACY_USERS = {"data_source": "synthetic_demo", "email": {"$regex": r"^demo\d+@example\.invalid$"}}


def cleanup_plan(session=None):
    legacy = [
        u["_id"] for u in get_collection("users").find(LEGACY_USERS, {"_id": 1}, session=session)
    ]
    projects = [
        r["_id"]
        for r in get_collection("projects").find(
            {"owner_id": {"$in": legacy}}, {"_id": 1}, session=session
        )
    ]
    events = [
        r["_id"]
        for r in get_collection("events").find(
            {"organizer_id": {"$in": legacy}}, {"_id": 1}, session=session
        )
    ]
    conversations = [
        r["_id"]
        for r in get_collection("conversations").find(
            {"participants": {"$in": legacy}}, {"_id": 1}, session=session
        )
    ]
    delete = {
        "users": {"_id": {"$in": legacy}},
        "profiles": {"user_id": {"$in": legacy}},
        "projects": {"_id": {"$in": projects}},
        "events": {"_id": {"$in": events}},
        "connections": {
            "$or": [{"requester_id": {"$in": legacy}}, {"recipient_id": {"$in": legacy}}]
        },
        "conversations": {"_id": {"$in": conversations}},
        "messages": {
            "$or": [{"conversation_id": {"$in": conversations}}, {"sender_id": {"$in": legacy}}]
        },
        "applications": {"$or": [{"project_id": {"$in": projects}}, {"user_id": {"$in": legacy}}]},
        "invitations": {
            "$or": [
                {"project_id": {"$in": projects}},
                {"recipient_id": {"$in": legacy}},
                {"sender_id": {"$in": legacy}},
            ]
        },
        "feedback": {
            "$or": [
                {"project_id": {"$in": projects}},
                {"from_user_id": {"$in": legacy}},
                {"to_user_id": {"$in": legacy}},
            ]
        },
        "interactions": {
            "$or": [
                {"user_id": {"$in": legacy}},
                {"target_id": {"$in": legacy + projects + events}},
            ]
        },
        "auth_sessions": {"user_id": {"$in": legacy}},
        "websocket_tickets": {
            "$or": [{"user_id": {"$in": legacy}}, {"conversation_id": {"$in": conversations}}]
        },
    }
    detach = {
        "projects": (
            {"owner_id": {"$nin": legacy}, "team_members": {"$in": legacy}},
            {"$pull": {"team_members": {"$in": legacy}}},
        ),
        "events": (
            {"organizer_id": {"$nin": legacy}, "attendee_ids": {"$in": legacy}},
            {"$pull": {"attendee_ids": {"$in": legacy}}},
        ),
    }
    return legacy, delete, detach


def check_matches(people, projects):
    profiles = {p["key"]: p["profile"] for p in people}
    scores = {}
    for target in ("priya", "rohan"):
        ranked, _ = recommend_people(load_models(), profiles["aarav"], [profiles[target]])
        scores[target] = ranked[0]["match_score"] if ranked else None
    study = next(p["values"] for p in projects if p["key"] == "study-buddy")
    scores["study-buddy"] = project_match(profiles["aarav"], study)["match_score"]
    return scores


def preflight(people, projects, activities, session=None):
    for person in people:
        row = get_collection("users").find_one(
            {"$or": [{"email": person["email"]}, {"_id": fixture_id(person["key"])}]},
            session=session,
        )
        if row and (
            row.get("data_source") != SOURCE
            or row["_id"] != fixture_id(person["key"])
            or row["email"] != person["email"]
        ):
            raise CommandError(
                "A presentation identity conflicts with an existing account. Nothing was overwritten."
            )
    for name, fixtures in (("projects", projects), ("events", activities)):
        for item in fixtures:
            row = get_collection(name).find_one({"_id": fixture_id(item["key"])}, session=session)
            if row and row.get("data_source") != SOURCE:
                raise CommandError(
                    "A fixture identifier conflicts with an existing record. Nothing was overwritten."
                )


class Command(BaseCommand):
    help = (
        "Preview or apply five fictional presentation accounts, five projects and two activities."
    )

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true")
        parser.add_argument("--replace-legacy-demo", action="store_true")
        parser.add_argument("--password-env", default="PRESENTATION_PASSWORD")

    def handle(self, *args, **options):
        if not settings.DEBUG or not settings.MONGODB_DATABASE.endswith(("_demo", "_test")):
            raise CommandError(
                "Presentation preparation requires DEBUG and a database ending in _demo or _test."
            )
        people, projects, activities = build_fixtures()
        scores = check_matches(people, projects)
        preflight(people, projects, activities)
        _, delete, detach = cleanup_plan()
        counts = {
            name: get_collection(name).count_documents(query) for name, query in delete.items()
        }
        self.stdout.write("Database: " + settings.MONGODB_DATABASE)
        self.stdout.write(
            "Old seeded records identified: " + str({k: v for k, v in counts.items() if v})
        )
        self.stdout.write(
            "Plan: 5 fictional Indian-name accounts, 5 projects, 2 activities; Aarav and Priya connected; Rohan available for a new connection."
        )
        self.stdout.write(
            "Measured discovery scores for fictional UI profiles (not success probabilities): " + str(scores)
        )
        if not options["apply"]:
            self.stdout.write(
                "Preview only. Use --apply --replace-legacy-demo to replace the identified legacy demo records."
            )
            return
        ensure_indexes()
        private = Path(settings.PROJECT_ROOT) / ".presentation-private"
        private.mkdir(mode=0o700, parents=True, exist_ok=True)
        private.chmod(0o700)
        password = os.getenv(options["password_env"]) or "Connect-" + secrets.token_urlsafe(12)
        validate_password(password)
        password_hash = make_password(password)
        credential_path = private / (
            "credentials-" + now().strftime("%Y%m%d-%H%M%S") + "-" + uuid4().hex[:6] + ".txt"
        )
        # Write privately before the transaction so successful account creation never loses its password.
        with credential_path.open("x", encoding="utf-8") as stream:
            credential_path.chmod(0o600)
            stream.write("New presentation accounts only (existing passwords are never reset).\n")
            stream.write("\n".join(p["profile"]["name"] + ": " + p["email"] for p in people))
            stream.write("\nPassword: " + password + "\n")

        def operation(session):
            preflight(people, projects, activities, session)
            legacy, deletion, detachment = cleanup_plan(session)
            backup_path = None
            if legacy and options["replace_legacy_demo"]:
                snapshot = {}
                for name, query in deletion.items():
                    queries = [query]
                    if name in detachment:
                        queries.append(detachment[name][0])
                    snapshot[name] = list(
                        get_collection(name).find({"$or": queries}, session=session)
                    )
                snapshot["storage_usage"] = list(
                    get_collection("storage_usage").find(
                        {"_id": "chat_attachments"}, session=session
                    )
                )
                backup_path = private / (
                    "legacy-backup-"
                    + now().strftime("%Y%m%d-%H%M%S")
                    + "-"
                    + uuid4().hex[:8]
                    + ".json.gz"
                )
                # BSON JSON retains IDs, timestamps and binary attachments for manual restoration.
                with backup_path.open("xb") as raw:
                    backup_path.chmod(0o600)
                    with gzip.GzipFile(fileobj=raw, mode="wb") as compressed:
                        compressed.write(
                            json_util.dumps(
                                {
                                    "database": settings.MONGODB_DATABASE,
                                    "created_at": now(),
                                    "collections": snapshot,
                                }
                            ).encode()
                        )
                removed_bytes = sum(
                    a.get("size", 0) for m in snapshot["messages"] for a in m.get("attachments", [])
                )
                for name, query in deletion.items():
                    get_collection(name).delete_many(query, session=session)
                for name, (query, change) in detachment.items():
                    get_collection(name).update_many(query, change, session=session)
                if removed_bytes:
                    get_collection("storage_usage").update_one(
                        {"_id": "chat_attachments"},
                        [
                            {
                                "$set": {
                                    "bytes": {
                                        "$max": [
                                            0,
                                            {
                                                "$subtract": [
                                                    {"$ifNull": ["$bytes", 0]},
                                                    removed_bytes,
                                                ]
                                            },
                                        ]
                                    }
                                }
                            }
                        ],
                        session=session,
                    )
            created = []
            timestamp = now()
            for person in people:
                identifier = fixture_id(person["key"])
                result = get_collection("users").update_one(
                    {"_id": identifier},
                    {
                        "$setOnInsert": {
                            "name": person["profile"]["name"],
                            "email": person["email"],
                            "password_hash": password_hash,
                            "is_active": True,
                            "created_at": timestamp,
                            "data_source": SOURCE,
                        }
                    },
                    upsert=True,
                    session=session,
                )
                if result.upserted_id:
                    created.append(person["email"])
                profile = {k: v for k, v in person["profile"].items() if k != "name"}
                get_collection("profiles").update_one(
                    {"user_id": identifier},
                    {
                        "$setOnInsert": {
                            **profile,
                            "user_id": identifier,
                            "data_source": SOURCE,
                            "created_at": timestamp,
                            "updated_at": timestamp,
                        }
                    },
                    upsert=True,
                    session=session,
                )
            for item in projects:
                owner = fixture_id(item["owner"])
                get_collection("projects").update_one(
                    {"_id": fixture_id(item["key"])},
                    {
                        "$setOnInsert": {
                            **item["values"],
                            "owner_id": owner,
                            "team_members": [owner],
                            "status": "Open",
                            "data_source": SOURCE,
                            "created_at": timestamp,
                            "updated_at": timestamp,
                        }
                    },
                    upsert=True,
                    session=session,
                )
            for item in activities:
                get_collection("events").update_one(
                    {"_id": fixture_id(item["key"])},
                    {
                        "$setOnInsert": {
                            **item["values"],
                            "organizer_id": fixture_id(item["owner"]),
                            "attendee_ids": [],
                            "data_source": SOURCE,
                            "created_at": timestamp,
                        }
                    },
                    upsert=True,
                    session=session,
                )
            aarav, priya = fixture_id("aarav"), fixture_id("priya")
            key = pair_key(aarav, priya)
            get_collection("connections").update_one(
                {"pair_key": key},
                {
                    "$setOnInsert": {
                        "requester_id": aarav,
                        "recipient_id": priya,
                        "status": "Accepted",
                        "data_source": SOURCE,
                        "created_at": timestamp,
                        "responded_at": timestamp,
                    }
                },
                upsert=True,
                session=session,
            )
            get_collection("conversations").update_one(
                {"pair_key": key},
                {
                    "$setOnInsert": {
                        "participants": sorted([aarav, priya], key=str),
                        "created_at": timestamp,
                        "updated_at": timestamp,
                        "last_message": "",
                        "data_source": SOURCE,
                    }
                },
                upsert=True,
                session=session,
            )
            return created, backup_path

        try:
            created, backup = run_transaction(operation)
        except Exception:
            credential_path.unlink(missing_ok=True)
            raise
        if not created:
            credential_path.unlink()
            self.stdout.write(
                "Existing presentation accounts retained; passwords and edited records were not reset."
            )
        else:
            self.stdout.write("Created: " + ", ".join(created))
            self.stdout.write("Private login details: " + str(credential_path))
        if backup:
            self.stdout.write("Private backup of replaced records: " + str(backup))
        self.stdout.write(
            self.style.SUCCESS(
                "Presentation records ready. Training datasets and model artifacts were not modified."
            )
        )
