"""Opt-in fictional fixtures for a disposable local/Codespaces database."""
import os
from datetime import timedelta
from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.contrib.auth.password_validation import validate_password
from django.core.management.base import BaseCommand, CommandError
from ml.data import clean_profiles, load_table, STUDENT_COLUMNS, PROJECT_COLUMNS
from platform_api.common import now
from platform_api.mongo import get_collection, ensure_indexes

class Command(BaseCommand):
    help = "Seed 21 clearly fictional students and 12 projects in a _demo or _test database."

    def add_arguments(self, parser):
        parser.add_argument("--password-env", default="DEMO_PASSWORD")

    def handle(self, *args, **options):
        if not settings.DEBUG or not settings.MONGODB_DATABASE.endswith(("_demo", "_test")):
            raise CommandError("Demo seeding requires DJANGO_DEBUG=1 and a database name ending in _demo or _test.")
        password = os.getenv(options["password_env"], "")
        if not password:
            raise CommandError("Set DEMO_PASSWORD privately before seeding. No default demo password is shipped.")
        validate_password(password)
        ensure_indexes()
        users = clean_profiles(load_table(settings.PROJECT_ROOT / "dataset/students.csv", STUDENT_COLUMNS))[:21]
        projects = clean_profiles(load_table(settings.PROJECT_ROOT / "dataset/projects.csv", PROJECT_COLUMNS), True)[:12]
        identifiers = []
        for index, profile in enumerate(users):
            email = f"demo{index + 1}@example.invalid"
            account = get_collection("users").find_one({"email": email})
            if not account:
                identifier = get_collection("users").insert_one({"name": f"Demo Student {index + 1:03}", "email": email, "password_hash": make_password(password), "is_active": True, "created_at": now(), "data_source": "synthetic_demo"}).inserted_id
            else:
                identifier = account["_id"]
            identifiers.append(identifier)
            values = {k: v for k, v in profile.items() if k not in {"user_id", "student_name"}}
            values.update({"bio": "Fictional student for demonstration. This is not a real person.", "city": "Demo campus", "phone": "", "github": "", "share_contact": False})
            get_collection("profiles").update_one({"user_id": identifier}, {"$setOnInsert": {**values, "user_id": identifier, "created_at": now(), "updated_at": now()}}, upsert=True)
        for index, project in enumerate(projects):
            owner = identifiers[index % len(identifiers)]
            values = {k: v for k, v in project.items() if k != "project_id"}
            values.update({"description": "Fictional development project: work together on " + project["title"].split(" — ")[0].lower() + ".", "owner_id": owner, "team_members": [owner], "status": "Open", "created_at": now(), "updated_at": now(), "deadline": now() + timedelta(days=60)})
            get_collection("projects").update_one({"demo_key": project["project_id"]}, {"$setOnInsert": values}, upsert=True)
        self.stdout.write(self.style.SUCCESS("Fictional demo records are ready. Sign in as demo1@example.invalid with your chosen password. Existing passwords were not changed."))
