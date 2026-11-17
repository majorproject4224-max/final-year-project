from django.core.management.base import BaseCommand, CommandError
from platform_api.common import pair_key
from platform_api.mongo import ensure_indexes, get_collection

class Command(BaseCommand):
    help = "Create MongoDB indexes and repair legacy pair identifiers without deleting records."

    def handle(self, *args, **options):
        for name in ("conversations", "connections"):
            collection = get_collection(name)
            seen = set()
            for row in collection.find({}):
                participants = row["participants"] if name == "conversations" else [row["requester_id"], row["recipient_id"]]
                key = pair_key(*participants)
                if key in seen:
                    raise CommandError(f"Duplicate pair in {name}; review before migration. No records deleted.")
                seen.add(key)
                collection.update_one({"_id": row["_id"]}, {"$set": {"pair_key": key}})
        conversations = get_collection("conversations")
        for name, index in conversations.index_information().items():
            if index.get("unique") and index["key"] == [("participants", 1)]:
                conversations.drop_index(name)
        ensure_indexes()
        self.stdout.write(self.style.SUCCESS("MongoDB indexes ready."))
