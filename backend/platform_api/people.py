from bson import ObjectId
from pymongo.errors import DuplicateKeyError
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.views import APIView
from .common import now, object_id, pair_key, page_result, search_regex
from .mongo import get_collection
from .resume import extract_resume
from .serializers import ProfileSerializer, ConnectionRequestSerializer

def profile_data(profile, viewer=None):
    user = get_collection("users").find_one({"_id": profile["user_id"], "is_active": True}, {"name": 1})
    result = {key: value for key, value in profile.items() if key not in {"_id", "user_id", "phone", "share_contact"}}
    result.update({"id": str(profile["_id"]), "user_id": str(profile["user_id"]), "name": user["name"] if user else "Unavailable account"})
    own = viewer and str(profile["user_id"]) == str(viewer)
    result["connection"] = None
    if viewer and not own:
        connection = get_collection("connections").find_one({"pair_key": pair_key(viewer, profile["user_id"])})
        if connection and connection["status"] != "Rejected":
            result["connection"] = {"id": str(connection["_id"]), "status": connection["status"], "direction": "sent" if str(connection["requester_id"]) == str(viewer) else "received"}
    if own:
        result.update({"phone": profile.get("phone", ""), "share_contact": profile.get("share_contact", False)})
    elif viewer and profile.get("share_contact") and are_connected(ObjectId(viewer), profile["user_id"]):
        result["phone"] = profile.get("phone", "")
    return result

def are_connected(left, right):
    return get_collection("connections").find_one({"pair_key": pair_key(left, right), "status": "Accepted"}) is not None

class ProfileView(APIView):
    def get(self, request):
        profile = get_collection("profiles").find_one({"user_id": ObjectId(request.user.id)})
        if profile is None:
            return Response({"code": "profile_incomplete", "detail": "Complete your profile to receive recommendations."}, status=404)
        return Response(profile_data(profile, request.user.id))

    def put(self, request):
        serializer = ProfileSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        values = dict(serializer.validated_data)
        name = values.pop("name")
        user_id = ObjectId(request.user.id)
        get_collection("users").update_one({"_id": user_id}, {"$set": {"name": name}})
        get_collection("profiles").update_one(
            {"user_id": user_id},
            {"$set": {**values, "updated_at": now()}, "$setOnInsert": {"user_id": user_id, "created_at": now()}}, upsert=True,
        )
        return self.get(request)

class ResumeSuggestionsView(APIView):
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        upload = request.FILES.get("resume")
        if upload is None:
            raise ValidationError("Choose a PDF or DOCX resume.")
        try:
            suggestions = extract_resume(upload)
        except ValueError as error:
            raise ValidationError(str(error))
        return Response({"suggestions": suggestions, "requires_review": True})

class StudentsView(APIView):
    def get(self, request):
        active_ids = list(get_collection("users").find({"is_active": True}, {"_id": 1}))
        query = {"user_id": {"$in": [u["_id"] for u in active_ids], "$ne": ObjectId(request.user.id)}}
        if request.query_params.get("q"):
            term = search_regex(request.query_params["q"])
            matches = get_collection("users").find({"name": term}, {"_id": 1})
            query["$or"] = [{"skills": term}, {"interests": term}, {"domain": term}, {"user_id": {"$in": [u["_id"] for u in matches]}}]
        if request.query_params.get("domain"):
            query["domain"] = request.query_params["domain"]
        return Response(page_result(get_collection("profiles"), query, request, lambda p: profile_data(p, request.user.id)))

class StudentDetailView(APIView):
    def get(self, request, user_id):
        target = object_id(user_id)
        if not get_collection("users").find_one({"_id": target, "is_active": True}):
            raise NotFound("Student not found.")
        profile = get_collection("profiles").find_one({"user_id": target})
        if profile is None:
            raise NotFound("This student has not completed their profile.")
        return Response(profile_data(profile, request.user.id))

class ConnectionsView(APIView):
    def get(self, request):
        user_id = ObjectId(request.user.id)
        def serialize(row):
            other = row["recipient_id"] if row["requester_id"] == user_id else row["requester_id"]
            user = get_collection("users").find_one({"_id": other})
            return {"id": str(row["_id"]), "user_id": str(other), "name": user["name"] if user else "Unavailable account", "status": row["status"], "direction": "sent" if row["requester_id"] == user_id else "received"}
        return Response(page_result(get_collection("connections"), {"$or": [{"requester_id": user_id}, {"recipient_id": user_id}]}, request, serialize))

    def post(self, request):
        serializer = ConnectionRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        target = object_id(serializer.validated_data["user_id"])
        user_id = ObjectId(request.user.id)
        if target == user_id:
            raise ValidationError("Choose another student.")
        if not get_collection("users").find_one({"_id": target, "is_active": True}):
            raise NotFound("Student not found.")
        row = {"pair_key": pair_key(user_id, target), "requester_id": user_id, "recipient_id": target, "status": "Pending", "created_at": now()}
        try:
            identifier = get_collection("connections").insert_one(row).inserted_id
        except DuplicateKeyError:
            return Response({"detail": "A request or connection already exists."}, status=409)
        return Response({"id": str(identifier), "status": "Pending"}, status=201)

class ConnectionDetailView(APIView):
    def patch(self, request, connection_id):
        action = request.data.get("action", "accept")
        if action not in {"accept", "reject"}:
            raise ValidationError("Choose accept or reject.")
        query = {"_id": object_id(connection_id), "recipient_id": ObjectId(request.user.id), "status": "Pending"}
        if action == "reject":
            changed = get_collection("connections").delete_one(query).deleted_count
        else:
            changed = get_collection("connections").update_one(query, {"$set": {"status": "Accepted", "responded_at": now()}}).modified_count
        if not changed:
            raise NotFound("Pending request not found.")
        return Response({"status": "Accepted" if action == "accept" else "Rejected"})

    def delete(self, request, connection_id):
        user_id = ObjectId(request.user.id)
        result = get_collection("connections").delete_one({"_id": object_id(connection_id), "$or": [{"requester_id": user_id}, {"recipient_id": user_id}]})
        if not result.deleted_count:
            raise NotFound("Connection not found.")
        return Response(status=204)
