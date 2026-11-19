"""Preserve existing accounts; update only marked fictional presentation profiles."""
from pathlib import Path
from datetime import datetime, timezone
from bson import json_util
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from platform_api.mongo import get_collection
from platform_api.presentation_data import SOURCE, build_fixtures, fixture_id
from ml.survey import PROFILE_FIELDS


class Command(BaseCommand):
    help = "Preview/upgrade the five fictional UI profiles to the real survey field schema. Not training data."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true")

    def handle(self, *args, **options):
        if not settings.DEBUG or not settings.MONGODB_DATABASE.endswith(("_demo", "_test")):
            raise CommandError("Only explicitly named development/demo databases are supported.")
        people, _, _ = build_fixtures()
        updates, backup = [], []
        for person in people:
            user = get_collection("users").find_one({"_id": fixture_id(person["key"]), "data_source": SOURCE})
            if not user:
                continue
            profile = get_collection("profiles").find_one({"user_id": user["_id"]})
            if profile and profile.get("profile_schema_version") != 3:
                backup.append(profile)
                values = {key: person["profile"][key] for key in PROFILE_FIELDS}
                values.update({"community_interests": profile.get("interests", person["profile"]["community_interests"]), "profile_schema_version": 3})
                updates.append((profile["_id"], values))
        self.stdout.write(f"Fictional profiles eligible: {len(updates)}. Real accounts, passwords, connections and messages are unchanged.")
        if options["apply"] and updates:
            directory = settings.PROJECT_ROOT / ".presentation-private"
            directory.mkdir(exist_ok=True)
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
            path = directory / f"pre-survey-profiles-{stamp}.json"
            path.write_text(json_util.dumps(backup), encoding="utf-8")
            for identifier, values in updates:
                get_collection("profiles").update_one({"_id": identifier}, {"$set": values})
            self.stdout.write(self.style.SUCCESS("Saved a private backup and upgraded the fictional profiles."))
