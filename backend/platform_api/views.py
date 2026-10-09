from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

import joblib
import pandas as pd
from bson import ObjectId
from bson.errors import InvalidId
from django.contrib.auth.hashers import check_password, make_password
from pymongo.errors import DuplicateKeyError, PyMongoError
from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .authentication import MongoPrincipal
from .matching import explain_pair, pair_features, profile_text
from .mongo import get_collection
from .resume import extract_resume
from .serializers import (
    ApplicationDecisionSerializer,
    ConnectionRequestSerializer,
    ConversationSerializer,
    EventSerializer,
    FeedbackSerializer,
    LoginSerializer,
    MessageSerializer,
    ProfileSerializer,
    ProjectSerializer,
    RegisterSerializer,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def issue_tokens(user_document):
    principal = MongoPrincipal(str(user_document["_id"]), user_document["email"])
    refresh = RefreshToken.for_user(principal)
    return {"refresh": str(refresh), "access": str(refresh.access_token)}


def public_profile(document):
    result = {key: value for key, value in document.items() if key not in {"_id", "user_id"}}
    result["id"] = str(document["_id"])
    return result


class RegisterView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        values = serializer.validated_data
        users = get_collection("users")
        try:
            users.create_index("email", unique=True)
            user_id = users.insert_one({
                "name": values["name"],
                "email": values["email"],
                "password_hash": make_password(values["password"]),
                "is_active": True,
                "created_at": datetime.now(timezone.utc),
            }).inserted_id
        except DuplicateKeyError:
            return Response({"email": ["An account with this email already exists."]}, status=status.HTTP_409_CONFLICT)
        user = users.find_one({"_id": user_id}, {"password_hash": 0})
        return Response({"user": {"id": str(user_id), "name": user["name"], "email": user["email"]}, "tokens": issue_tokens(user)}, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        values = serializer.validated_data
        user = get_collection("users").find_one({"email": values["email"], "is_active": True})
        if user is None or not check_password(values["password"], user["password_hash"]):
            return Response({"detail": "Email or password is incorrect."}, status=status.HTTP_401_UNAUTHORIZED)
        return Response({"user": {"id": str(user["_id"]), "name": user["name"], "email": user["email"]}, "tokens": issue_tokens(user)})


class ProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        document = get_collection("profiles").find_one({"user_id": ObjectId(request.user.id)})
        if document is None:
            user = get_collection("users").find_one({"_id": ObjectId(request.user.id)}, {"name": 1})
            return Response({"detail": "Complete your profile to continue.", "code": "profile_incomplete", "name": user["name"]}, status=status.HTTP_404_NOT_FOUND)
        result = public_profile(document)
        user = get_collection("users").find_one({"_id": ObjectId(request.user.id)}, {"name": 1})
        result["name"] = user["name"]
        result["user_id"] = request.user.id
        return Response(result)

    def put(self, request):
        serializer = ProfileSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        profiles = get_collection("profiles")
        profiles.create_index("user_id", unique=True)
        user_id = ObjectId(request.user.id)
        now = datetime.now(timezone.utc)
        profile_values = serializer.validated_data.copy()
        name = profile_values.pop("name")
        get_collection("users").update_one({"_id": user_id}, {"$set": {"name": name}})
        profiles.update_one(
            {"user_id": user_id},
            {"$set": {**profile_values, "updated_at": now}, "$setOnInsert": {"user_id": user_id, "created_at": now}},
            upsert=True,
        )
        document = profiles.find_one({"user_id": user_id})
        result = public_profile(document)
        result["name"] = name
        result["user_id"] = request.user.id
        return Response(result)


class ResumeSuggestionsView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        upload = request.FILES.get("resume")
        if upload is None:
            return Response({"resume": ["Choose a PDF or DOCX file."]}, status=status.HTTP_400_BAD_REQUEST)
        try:
            suggestions = extract_resume(upload)
        except ValueError as error:
            return Response({"resume": [str(error)]}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"suggestions": suggestions, "requires_review": True})


class ProjectsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        documents = get_collection("projects").find({"status": "Open"}).sort("created_at", -1).limit(100)
        return Response([{
            "id": str(project["_id"]),
            "owner_id": str(project["owner_id"]),
            "title": project["title"],
            "description": project["description"],
            "required_skills": project["required_skills"],
            "domain": project["domain"],
            "project_type": project["project_type"],
            "team_size": project["team_size"],
            "team_member_count": len(project.get("team_members", [])),
            "status": project["status"],
        } for project in documents])

    def post(self, request):
        serializer = ProjectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        project = {
            **serializer.validated_data,
            "owner_id": ObjectId(request.user.id),
            "team_members": [ObjectId(request.user.id)],
            "status": "Open",
            "created_at": datetime.now(timezone.utc),
        }
        inserted_id = get_collection("projects").insert_one(project).inserted_id
        return Response({"id": str(inserted_id), **serializer.validated_data, "status": "Open"}, status=status.HTTP_201_CREATED)


class ProjectApplicationView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, project_id):
        project_object_id = resolve_object_id(project_id)
        if project_object_id is None:
            return Response({"detail": "Project not found."}, status=status.HTTP_404_NOT_FOUND)
        project = get_collection("projects").find_one({"_id": project_object_id})
        if project is None:
            return Response({"detail": "Project not found."}, status=status.HTTP_404_NOT_FOUND)
        if project["owner_id"] != ObjectId(request.user.id):
            return Response({"detail": "Only the project owner can review applications."}, status=status.HTTP_403_FORBIDDEN)
        applications = list(
            get_collection("applications")
            .find({"project_id": project_object_id})
            .sort("created_at", -1)
        )
        applicant_ids = [application["user_id"] for application in applications]
        names = {
            user["_id"]: user["name"]
            for user in get_collection("users").find(
                {"_id": {"$in": applicant_ids}}, {"name": 1}
            )
        }
        return Response([
            {
                "id": str(application["_id"]),
                "user_id": str(application["user_id"]),
                "name": names.get(application["user_id"], "Student"),
                "status": application["status"],
                "created_at": application["created_at"],
            }
            for application in applications
        ])

    def patch(self, request, project_id):
        serializer = ApplicationDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        project_object_id = resolve_object_id(project_id)
        application_object_id = resolve_object_id(serializer.validated_data["application_id"])
        if project_object_id is None or application_object_id is None:
            return Response({"detail": "Project application not found."}, status=status.HTTP_404_NOT_FOUND)
        projects = get_collection("projects")
        project = projects.find_one({"_id": project_object_id})
        if project is None:
            return Response({"detail": "Project not found."}, status=status.HTTP_404_NOT_FOUND)
        if project["owner_id"] != ObjectId(request.user.id):
            return Response({"detail": "Only the project owner can review applications."}, status=status.HTTP_403_FORBIDDEN)
        applications = get_collection("applications")
        application = applications.find_one({
            "_id": application_object_id,
            "project_id": project_object_id,
            "status": "Pending",
        })
        if application is None:
            return Response({"detail": "Pending application not found."}, status=status.HTTP_404_NOT_FOUND)
        decision = serializer.validated_data["decision"]
        if decision == "Accepted":
            member_update = projects.update_one({
                "_id": project_object_id,
                "status": "Open",
                "team_members": {"$ne": application["user_id"]},
                "$expr": {
                    "$lt": [
                        {"$size": {"$ifNull": ["$team_members", []]}},
                        "$team_size",
                    ]
                },
            }, {"$addToSet": {"team_members": application["user_id"]}})
            if not member_update.modified_count:
                return Response({"detail": "The project team is full or this student already joined."}, status=status.HTTP_409_CONFLICT)
        applications.update_one(
            {"_id": application_object_id, "status": "Pending"},
            {"$set": {"status": decision, "reviewed_at": datetime.now(timezone.utc)}},
        )
        return Response({"application_id": str(application_object_id), "status": decision})

    def post(self, request, project_id):
        try:
            project_object_id = ObjectId(project_id)
        except (InvalidId, TypeError):
            return Response({"detail": "Project not found."}, status=status.HTTP_404_NOT_FOUND)
        projects = get_collection("projects")
        project = projects.find_one({"_id": project_object_id, "status": "Open"})
        if project is None:
            return Response({"detail": "Project not found or no longer open."}, status=status.HTTP_404_NOT_FOUND)
        if project["owner_id"] == ObjectId(request.user.id):
            return Response({"detail": "Project owners cannot apply to their own project."}, status=status.HTTP_400_BAD_REQUEST)
        if ObjectId(request.user.id) in project.get("team_members", []):
            return Response({"detail": "You are already on this project team."}, status=status.HTTP_409_CONFLICT)
        applications = get_collection("applications")
        applications.create_index([("project_id", 1), ("user_id", 1)], unique=True)
        try:
            applications.insert_one({
                "project_id": project_object_id,
                "user_id": ObjectId(request.user.id),
                "status": "Pending",
                "created_at": datetime.now(timezone.utc),
            })
        except DuplicateKeyError:
            return Response({"detail": "You have already applied to this project."}, status=status.HTTP_409_CONFLICT)
        return Response({"status": "Pending"}, status=status.HTTP_201_CREATED)


@lru_cache(maxsize=1)
def load_compatibility_model():
    return joblib.load(PROJECT_ROOT / "ml/models/random_forest_compatibility.joblib")


@lru_cache(maxsize=1)
def load_student_cluster_model():
    return joblib.load(PROJECT_ROOT / "ml/models/student_clusters.joblib")


class UserRecommendationsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profiles = get_collection("profiles")
        source = profiles.find_one({"user_id": ObjectId(request.user.id)})
        if source is None:
            return Response({"items": [], "detail": "Complete your profile to receive recommendations."})
        candidates = list(profiles.find({"user_id": {"$ne": ObjectId(request.user.id)}}).limit(500))
        if not candidates:
            return Response({"items": [], "detail": "There are no other complete student profiles yet."})

        cluster_bundle = load_student_cluster_model()
        source_cluster = int(cluster_bundle["model"].predict(
            cluster_bundle["vectorizer"].transform([profile_text(source)])
        )[0])
        candidate_clusters = cluster_bundle["model"].predict(
            cluster_bundle["vectorizer"].transform([profile_text(candidate) for candidate in candidates])
        )
        clustered_candidates = [
            candidate for candidate, cluster in zip(candidates, candidate_clusters)
            if int(cluster) == source_cluster
        ]
        if clustered_candidates:
            candidates = clustered_candidates

        bundle = load_compatibility_model()
        features = bundle["features"]
        vectors = [pair_features(source, candidate) for candidate in candidates]
        probabilities = bundle["model"].predict_proba(pd.DataFrame(vectors, columns=features))
        compatible_column = list(bundle["model"].classes_).index(1)
        user_ids = [candidate["user_id"] for candidate in candidates]
        users = get_collection("users")
        user_names = {
            str(user["_id"]): user["name"]
            for user in users.find({"_id": {"$in": user_ids}}, {"name": 1})
        }
        items = []
        for candidate, vector, probability in zip(candidates, vectors, probabilities):
            items.append({
                "user_id": str(candidate["user_id"]),
                "name": user_names.get(str(candidate["user_id"]), "Student"),
                "branch": candidate["branch"],
                "academic_year": candidate["academic_year"],
                "skills": candidate["skills"],
                "interests": candidate["interests"],
                "domain": candidate["domain"],
                "compatibility_score": round(float(probability[compatible_column]) * 100, 1),
                "explanations": explain_pair(source, candidate),
            })
        items.sort(key=lambda item: item["compatibility_score"], reverse=True)
        return Response({
            "items": items[:8],
            "model": "random_forest_compatibility",
            "candidate_cluster": source_cluster,
            "clustered_candidate_count": len(candidates),
            "model_notice": "Prototype estimates trained on synthetic labels; not validated real-student outcomes.",
        })


def resolve_object_id(value):
    try:
        return ObjectId(value)
    except (InvalidId, TypeError):
        return None


class ConnectionsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user_id = ObjectId(request.user.id)
        relationships = list(get_collection("connections").find({
            "$or": [{"requester_id": user_id}, {"recipient_id": user_id}],
        }).sort("created_at", -1).limit(200))
        other_ids = set()
        for relation in relationships:
            other_id = relation["recipient_id"] if relation["requester_id"] == user_id else relation["requester_id"]
            other_ids.add(other_id)
        users = {user["_id"]: user for user in get_collection("users").find(
            {"_id": {"$in": list(other_ids)}}, {"name": 1, "email": 1}
        )}
        return Response([{
            "id": str(relation["_id"]),
            "user_id": str(relation["recipient_id"] if relation["requester_id"] == user_id else relation["requester_id"]),
            "name": users.get(relation["recipient_id"] if relation["requester_id"] == user_id else relation["requester_id"], {}).get("name", "Student"),
            "status": relation["status"],
            "direction": "sent" if relation["requester_id"] == user_id else "received",
        } for relation in relationships])

    def post(self, request):
        serializer = ConnectionRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        recipient_id = resolve_object_id(serializer.validated_data["user_id"])
        requester_id = ObjectId(request.user.id)
        if recipient_id is None or recipient_id == requester_id:
            return Response({"detail": "Choose another valid student."}, status=status.HTTP_400_BAD_REQUEST)
        if get_collection("users").find_one({"_id": recipient_id, "is_active": True}, {"_id": 1}) is None:
            return Response({"detail": "Student not found."}, status=status.HTTP_404_NOT_FOUND)
        connections = get_collection("connections")
        connections.create_index([("requester_id", 1), ("recipient_id", 1)], unique=True)
        existing = connections.find_one({"$or": [
            {"requester_id": requester_id, "recipient_id": recipient_id},
            {"requester_id": recipient_id, "recipient_id": requester_id},
        ]})
        if existing:
            return Response({"detail": "A connection request or connection already exists."}, status=status.HTTP_409_CONFLICT)
        inserted = connections.insert_one({
            "requester_id": requester_id,
            "recipient_id": recipient_id,
            "status": "Pending",
            "created_at": datetime.now(timezone.utc),
        })
        return Response({"id": str(inserted.inserted_id), "status": "Pending"}, status=status.HTTP_201_CREATED)


class ConnectionDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, connection_id):
        connection_object_id = resolve_object_id(connection_id)
        if connection_object_id is None:
            return Response({"detail": "Connection request not found."}, status=status.HTTP_404_NOT_FOUND)
        result = get_collection("connections").update_one(
            {"_id": connection_object_id, "recipient_id": ObjectId(request.user.id), "status": "Pending"},
            {"$set": {"status": "Accepted", "responded_at": datetime.now(timezone.utc)}},
        )
        if not result.modified_count:
            return Response({"detail": "Pending request not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response({"id": connection_id, "status": "Accepted"})


class EventsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        now = datetime.now(timezone.utc)
        events = get_collection("events").find({"starts_at": {"$gte": now}}).sort("starts_at", 1).limit(100)
        return Response([{
            "id": str(event["_id"]), "title": event["title"], "description": event["description"],
            "location": event["location"], "starts_at": event["starts_at"],
            "attendee_count": event.get("attendee_count", 0),
        } for event in events])

    def post(self, request):
        serializer = EventSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        values = serializer.validated_data
        if values["starts_at"] <= datetime.now(timezone.utc):
            return Response({"starts_at": ["Choose a future date and time."]}, status=status.HTTP_400_BAD_REQUEST)
        document = {
            **values, "organizer_id": ObjectId(request.user.id),
            "attendee_ids": [], "attendee_count": 0, "created_at": datetime.now(timezone.utc),
        }
        inserted_id = get_collection("events").insert_one(document).inserted_id
        return Response({"id": str(inserted_id), **values, "attendee_count": 0}, status=status.HTTP_201_CREATED)


class EventAttendanceView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, event_id):
        event_object_id = resolve_object_id(event_id)
        if event_object_id is None:
            return Response({"detail": "Event not found."}, status=status.HTTP_404_NOT_FOUND)
        result = get_collection("events").update_one(
            {"_id": event_object_id, "starts_at": {"$gte": datetime.now(timezone.utc)}},
            [{"$set": {
                "attendee_ids": {"$setUnion": [{"$ifNull": ["$attendee_ids", []]}, [ObjectId(request.user.id)]]},
                "attendee_count": {"$size": {"$setUnion": [{"$ifNull": ["$attendee_ids", []]}, [ObjectId(request.user.id)]]}},
            }}],
        )
        if not result.matched_count:
            return Response({"detail": "Upcoming event not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response({"event_id": event_id, "status": "attending"})


class FeedbackView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = FeedbackSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        values = serializer.validated_data
        to_user_id = resolve_object_id(values["to_user_id"])
        from_user_id = ObjectId(request.user.id)
        if to_user_id is None or to_user_id == from_user_id:
            return Response({"to_user_id": ["Choose another valid student."]}, status=status.HTTP_400_BAD_REQUEST)
        if get_collection("users").find_one({"_id": to_user_id}, {"_id": 1}) is None:
            return Response({"detail": "Student not found."}, status=status.HTTP_404_NOT_FOUND)
        project_id = resolve_object_id(values["project_id"]) if values["project_id"] else None
        if values["project_id"] and project_id is None:
            return Response({"project_id": ["Choose a valid project."]}, status=status.HTTP_400_BAD_REQUEST)
        get_collection("feedback").insert_one({
            "from_user_id": from_user_id, "to_user_id": to_user_id, "project_id": project_id,
            "rating": values["rating"], "comment": values["comment"],
            "created_at": datetime.now(timezone.utc),
        })
        return Response({"status": "recorded"}, status=status.HTTP_201_CREATED)


class ProjectRecommendationsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile = get_collection("profiles").find_one({"user_id": ObjectId(request.user.id)})
        if profile is None:
            return Response({"items": [], "detail": "Complete your profile to receive project recommendations."})
        profile_skills = set(profile["skills"])
        profile_interests = set(profile["interests"])
        projects = get_collection("projects").find({"status": "Open", "owner_id": {"$ne": ObjectId(request.user.id)}}).limit(200)
        items = []
        for project in projects:
            required = set(project["required_skills"])
            matched = sorted(profile_skills & required)
            interest_matches = sorted(profile_interests & set(project.get("preferred_interests", [])))
            skill_coverage = len(matched) / len(required) if required else 0.0
            same_domain = profile["domain"] == project["domain"]
            score = 100 * (0.75 * skill_coverage + 0.25 * float(same_domain))
            explanations = []
            if matched:
                explanations.append({"feature": "required_skills_matched", "items": matched})
            if interest_matches:
                explanations.append({"feature": "preferred_interests_matched", "items": interest_matches})
            if same_domain:
                explanations.append({"feature": "same_domain", "value": project["domain"]})
            items.append({
                "id": str(project["_id"]), "title": project["title"], "description": project["description"],
                "required_skills": project["required_skills"], "domain": project["domain"],
                "project_type": project["project_type"], "compatibility_score": round(score, 1),
                "explanations": explanations,
            })
        items.sort(key=lambda item: item["compatibility_score"], reverse=True)
        return Response({
            "items": items[:8],
            "ranking_method": "profile-to-requirements coverage; not a trained project classifier",
        })


class ProjectTeammateRecommendationsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, project_id):
        project_object_id = resolve_object_id(project_id)
        if project_object_id is None:
            return Response({"detail": "Project not found."}, status=status.HTTP_404_NOT_FOUND)
        project = get_collection("projects").find_one({"_id": project_object_id, "status": "Open"})
        if project is None:
            return Response({"items": [], "detail": "Open project not found."}, status=status.HTTP_404_NOT_FOUND)
        profiles = get_collection("profiles")
        owner_profile = profiles.find_one({"user_id": project["owner_id"]})
        if owner_profile is None:
            return Response({"items": [], "detail": "The project owner needs a complete profile before teammate matching."})
        candidates = list(profiles.find({"user_id": {"$ne": project["owner_id"]}}).limit(500))
        if not candidates:
            return Response({"items": [], "detail": "There are no other complete student profiles yet."})

        cluster_bundle = load_student_cluster_model()
        vectorizer = cluster_bundle["vectorizer"]
        cluster_model = cluster_bundle["model"]
        owner_cluster = int(cluster_model.predict(vectorizer.transform([profile_text(owner_profile)]))[0])
        candidate_clusters = cluster_model.predict(vectorizer.transform([profile_text(item) for item in candidates]))
        in_group = [
            item for item, cluster in zip(candidates, candidate_clusters)
            if int(cluster) == owner_cluster
        ]
        if in_group:
            candidates = in_group

        bundle = load_compatibility_model()
        feature_names = bundle["features"]
        vectors = [pair_features(owner_profile, candidate) for candidate in candidates]
        probabilities = bundle["model"].predict_proba(pd.DataFrame(vectors, columns=feature_names))
        compatible_column = list(bundle["model"].classes_).index(1)
        user_ids = [candidate["user_id"] for candidate in candidates]
        names = {
            user["_id"]: user["name"]
            for user in get_collection("users").find({"_id": {"$in": user_ids}}, {"name": 1})
        }
        required_skills = set(project["required_skills"])
        results = []
        for candidate, probability in zip(candidates, probabilities):
            matched_skills = sorted(required_skills & set(candidate["skills"]))
            coverage = len(matched_skills) / len(required_skills) if required_skills else 0.0
            rf_score = float(probability[compatible_column])
            ranking_score = 0.7 * rf_score + 0.3 * coverage
            results.append({
                "user_id": str(candidate["user_id"]),
                "name": names.get(candidate["user_id"], "Student"),
                "branch": candidate["branch"],
                "academic_year": candidate["academic_year"],
                "skills": candidate["skills"],
                "compatibility_score": round(rf_score * 100, 1),
                "required_skill_coverage": round(coverage * 100, 1),
                "ranking_score": round(ranking_score * 100, 1),
                "explanations": ([{"feature": "required_skills_matched", "items": matched_skills}] if matched_skills else []),
            })
        results.sort(key=lambda item: item["ranking_score"], reverse=True)
        return Response({
            "project_id": project_id,
            "items": results[:10],
            "ranking_method": "0.7 Random Forest user compatibility + 0.3 required-skill coverage; synthetic-label model",
        })