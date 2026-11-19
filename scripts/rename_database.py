"""Offline local-Codespace database rename with backup, verification and rollback."""

import argparse
import gzip
import hashlib
import json
from pathlib import Path
import re
import socket
import subprocess
from datetime import datetime, timezone
from uuid import uuid4

from bson import BSON, json_util
from dotenv import dotenv_values
from pymongo import MongoClient

ROOT = Path(__file__).resolve().parents[1]


def snapshot(database):
    """Compare full BSON contents, IDs, attachments, collection options and indexes."""
    result = {}
    for info in sorted(database.list_collections(), key=lambda value: value["name"]):
        if info["type"] != "collection" or info["name"].startswith("system."):
            raise RuntimeError("Only ordinary application collections can be moved.")
        collection = database[info["name"]]
        digest, count = hashlib.sha256(), 0
        for document in collection.find({}).sort("_id", 1):
            digest.update(BSON.encode(document))
            count += 1
        indexes = [
            {key: value for key, value in index.items() if key != "ns"}
            for index in collection.list_indexes()
        ]
        result[info["name"]] = {
            "count": count,
            "sha256": digest.hexdigest(),
            "indexes": sorted(indexes, key=lambda index: index["name"]),
            "options": info.get("options", {}),
        }
    return result


def move_database(client, source, target, backup):
    """Never merge/overwrite a target. Roll back namespace moves on any failure."""
    for name in (source, target):
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,62}", name) or name in {
            "admin", "config", "local"
        }:
            raise ValueError("Use distinct application database names only.")
    if source == target:
        raise ValueError("Source and destination must differ.")
    if client[target].list_collection_names():
        raise RuntimeError("Destination already contains collections; nothing was changed.")
    before = snapshot(client[source])
    if not before:
        raise RuntimeError("Source contains no application collections.")
    backup(before)
    # Backup must not race an application write or TTL expiry.
    if snapshot(client[source]) != before:
        raise RuntimeError("Source changed during backup. Stop writers and retry.")
    try:
        for name in before:
            client.admin.command(
                "renameCollection", f"{source}.{name}", to=f"{target}.{name}",
                dropTarget=False,
            )
        after = snapshot(client[target])
        if before != after or client[source].list_collection_names():
            raise RuntimeError("Content/index verification failed.")
        # Only remove the now-empty namespace; every record is already verified in target.
        client.drop_database(source)
        return after
    except Exception:
        remaining = set(client[source].list_collection_names())
        moved = set(client[target].list_collection_names())
        for name in reversed(list(before)):
            if name in moved and name not in remaining:
                client.admin.command(
                    "renameCollection", f"{target}.{name}", to=f"{source}.{name}",
                    dropTarget=False,
                )
        if snapshot(client[source]) != before:
            raise RuntimeError("Rollback needs manual recovery from the private backup.")
        if not client[target].list_collection_names():
            client.drop_database(target)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", default="connect_ai")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    env_path = ROOT / ".env"
    config = dotenv_values(env_path)
    source = config.get("MONGODB_DATABASE")
    uri = config.get("MONGODB_URI", "")
    # This maintenance tool intentionally only handles the project's local Docker service.
    if not re.match(r"^mongodb://(?:127\.0\.0\.1|localhost):27017(?:/|\?|$)", uri):
        raise RuntimeError("This tool is only for the existing local Codespace Docker database.")
    if not source:
        raise RuntimeError("MONGODB_DATABASE must be explicit in .env.")
    if source == args.target:
        print("The application already uses the requested database.")
        return
    with MongoClient(uri, serverSelectionTimeoutMS=5000) as client:
        before = snapshot(client[source])
        print(json.dumps({"source": source, "target": args.target,
                          "collections": {k: v["count"] for k, v in before.items()}}))
        if not args.apply:
            print("Preview only. Stop the application, then rerun with --apply.")
            return
        try:
            connection = socket.create_connection(("127.0.0.1", 8000), timeout=1)
        except ConnectionRefusedError:
            pass
        else:
            connection.close()
            raise RuntimeError("Stop the application on port 8000 before the rename.")
        directory = ROOT / ".presentation-private" / (
            "database-rename-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
            + "-" + uuid4().hex[:6]
        )
        directory.mkdir(parents=True, mode=0o700)
        directory.chmod(0o700)
        original = env_path.read_text()
        updated, changes = re.subn(
            r"(?m)^MONGODB_DATABASE\s*=.*$", f"MONGODB_DATABASE={args.target}", original
        )
        if changes != 1:
            raise RuntimeError("Expected exactly one database setting in .env.")
        for name, content in (("environment.backup", original), ("environment.updated", updated)):
            path = directory / name
            path.write_text(content)
            path.chmod(0o600)

        def backup(manifest):
            (directory / "before.json").write_text(json_util.dumps(manifest, indent=2))
            archive = directory / "database.archive.gz"
            with archive.open("xb") as stream, (directory / "backup.log").open("w") as log:
                archive.chmod(0o600)
                subprocess.run(
                    ["docker", "compose", "exec", "-T", "mongo", "mongodump",
                     "--db", source, "--archive", "--gzip"],
                    cwd=ROOT, stdout=stream, stderr=log, check=True,
                )
            with gzip.open(archive, "rb") as stream:
                while stream.read(1024 * 1024):
                    pass  # Validate the gzip stream including its checksum/trailer.

        verified = move_database(client, source, args.target, backup)
        try:
            (directory / "environment.updated").replace(env_path)
        except Exception:
            move_database(client, args.target, source, lambda _: None)
            raise
        report = {"source": source, "target": args.target, "verified": True,
                  "collections": verified, "backup": "database.archive.gz"}
        (directory / "verified.json").write_text(json_util.dumps(report, indent=2))
        # Keep previously saved read-only playgrounds pointed at the active database.
        for path in (ROOT / ".presentation-private").glob("*.mongodb.js"):
            text = path.read_text()
            path.write_text(text.replace(f"use('{source}')", f"use('{args.target}')"))
        print("Verified every record and index. Application database:", args.target)
        print("Private backup and verification:", directory.relative_to(ROOT))
        print("Restart the application and refresh the MongoDB Connections view.")


if __name__ == "__main__":
    main()
