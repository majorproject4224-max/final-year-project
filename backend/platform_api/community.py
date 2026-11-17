from bson import ObjectId
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView
from .common import now, object_id, page_result
from .mongo import get_collection
from .serializers import EventSerializer, FeedbackSerializer, InteractionSerializer

def event_data(event, viewer):
    return {"id": str(event["_id"]), "title": event["title"], "description": event["description"], "location": event["location"], "starts_at": event["starts_at"], "organizer_id": str(event["organizer_id"]), "attendee_count": len(event.get("attendee_ids", [])), "is_attending": viewer in event.get("attendee_ids", [])}

class EventsView(APIView):
    def get(self, request):
        viewer = ObjectId(request.user.id)
        return Response(page_result(get_collection("events"), {"starts_at": {"$gte": now()}}, request, lambda e: event_data(e, viewer), [("starts_at", 1)]))

    def post(self, request):
        serializer = EventSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if serializer.validated_data["starts_at"] <= now():
            raise ValidationError("Choose a future date and time.")
        event = {**serializer.validated_data, "organizer_id": ObjectId(request.user.id), "attendee_ids": [], "created_at": now()}
        event["_id"] = get_collection("events").insert_one(event).inserted_id
        return Response(event_data(event, ObjectId(request.user.id)), status=201)

class EventDetailView(APIView):
    def delete(self, request, event_id):
        result = get_collection("events").delete_one({"_id": object_id(event_id), "organizer_id": ObjectId(request.user.id)})
        if not result.deleted_count:
            raise NotFound("Event not found or you are not its organizer.")
        return Response(status=204)

class EventAttendanceView(APIView):
    def post(self, request, event_id):
        result = get_collection("events").update_one({"_id": object_id(event_id), "starts_at": {"$gt": now()}}, {"$addToSet": {"attendee_ids": ObjectId(request.user.id)}})
        if not result.matched_count:
            raise NotFound("Upcoming event not found.")
        return Response({"status": "attending"})

    def delete(self, request, event_id):
        get_collection("events").update_one({"_id": object_id(event_id)}, {"$pull": {"attendee_ids": ObjectId(request.user.id)}})
        return Response(status=204)

class FeedbackView(APIView):
    def post(self, request):
        serializer = FeedbackSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        values = serializer.validated_data
        actor, recipient, project_id = ObjectId(request.user.id), object_id(values["to_user_id"]), object_id(values["project_id"])
        if actor == recipient:
            raise ValidationError("You cannot review yourself.")
        project = get_collection("projects").find_one({"_id": project_id, "status": "Completed"})
        if not project or actor not in project["team_members"] or recipient not in project["team_members"]:
            raise PermissionDenied("Feedback requires a completed project shared by both students.")
        get_collection("feedback").update_one(
            {"project_id": project_id, "from_user_id": actor, "to_user_id": recipient},
            {"$set": {"rating": values["rating"], "comment": values["comment"], "updated_at": now(), "source": "verified_project_feedback"}, "$setOnInsert": {"created_at": now()}},
            upsert=True,
        )
        return Response({"detail": "Feedback saved. It is not automatically used to retrain models."}, status=201)

class InteractionsView(APIView):
    def post(self, request):
        serializer = InteractionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        values = serializer.validated_data
        target = object_id(values["target_id"])
        collection = "users" if values["target_type"] == "student" else "projects"
        if not get_collection(collection).find_one({"_id": target}):
            raise NotFound("Recommendation target not found.")
        query = {"user_id": ObjectId(request.user.id), "target_type": values["target_type"], "target_id": target, "action": "save" if values["action"] == "unsave" else values["action"]}
        if values["action"] == "unsave":
            get_collection("interactions").delete_one(query)
        else:
            get_collection("interactions").update_one(query, {"$set": {"updated_at": now()}, "$setOnInsert": {"created_at": now()}}, upsert=True)
        return Response({"status": "recorded"})

    def get(self, request):
        rows = get_collection("interactions").find({"user_id": ObjectId(request.user.id), "action": "save"}).sort("updated_at", -1).limit(100)
        return Response({"items": [{"target_type": r["target_type"], "target_id": str(r["target_id"])} for r in rows]})
