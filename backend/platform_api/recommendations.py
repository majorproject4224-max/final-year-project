from bson import ObjectId
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView
from ml.features import explain_pair, explain_project, project_features
from .mongo import get_collection
from .people import profile_data
from .projects import project_data
from .common import object_id
from .services.projects import get_project, require_owner
from .services.recommendations import load_models, candidate_indices, probabilities, notice
import pandas as pd

def excluded_targets(user_id, kind):
    return [row["target_id"] for row in get_collection("interactions").find({"user_id": user_id, "target_type": kind, "action": "ignore"})]

def source_profile(user_id):
    return get_collection("profiles").find_one({"user_id": user_id})

class UserRecommendationsView(APIView):
    def get(self, request):
        actor = ObjectId(request.user.id)
        source = source_profile(actor)
        if not source:
            return Response({"items": [], "detail": "Add skills and interests to receive recommendations."})
        excluded = [actor] + excluded_targets(actor, "student")
        for connection in get_collection("connections").find({"$or": [{"requester_id": actor}, {"recipient_id": actor}]}):
            excluded.extend([connection["requester_id"], connection["recipient_id"]])
        active_ids = [u["_id"] for u in get_collection("users").find({"is_active": True, "_id": {"$nin": excluded}}, {"_id": 1})]
        candidates = list(get_collection("profiles").find({"user_id": {"$in": active_ids}}).sort("_id", 1).limit(2000))
        if not candidates:
            return Response({"items": [], "detail": "No new students to recommend yet. Browse Students to find existing connections."})
        indices, cluster = candidate_indices(source, candidates)
        candidates = [candidates[i] for i in indices]
        if not candidates:
            return Response({"items": [], "detail": "Your profile needs skills represented in the current model. You can still browse students."})
        scores = probabilities(source, candidates)
        result = [{**profile_data(c, request.user.id), "compatibility_score": round(float(score) * 100, 1), "explanations": explain_pair(source, c)} for c, score in zip(candidates, scores)]
        result.sort(key=lambda item: (-item["compatibility_score"], item["user_id"]))
        return Response({"items": result[:12], "model_notice": notice(), "candidate_cluster": cluster, "candidate_count": len(candidates)})

class ProjectRecommendationsView(APIView):
    def get(self, request):
        actor = ObjectId(request.user.id)
        source = source_profile(actor)
        if not source:
            return Response({"items": [], "detail": "Complete your profile to receive project recommendations."})
        candidates = list(get_collection("projects").find({"status": "Open", "team_members": {"$ne": actor}, "_id": {"$nin": excluded_targets(actor, "project")}, "$expr": {"$lt": [{"$size": "$team_members"}, "$team_size"]}}).sort("_id", 1).limit(2000))
        if not candidates:
            return Response({"items": [], "detail": "No projects are currently recruiting."})
        indices, cluster = candidate_indices(source, candidates, True)
        candidates = [candidates[i] for i in indices]
        if not candidates:
            return Response({"items": [], "detail": "No model-supported project matches yet. Browse all projects."})
        scores = probabilities(source, candidates, "projects")
        result = [{**project_data(c, actor), "compatibility_score": round(float(score) * 100, 1), "explanations": explain_project(source, c)} for c, score in zip(candidates, scores)]
        result.sort(key=lambda item: (-item["compatibility_score"], item["id"]))
        return Response({"items": result[:12], "model_notice": notice(), "ranking_method": "Random Forest student-project model", "candidate_cluster": cluster})

class ProjectTeammateRecommendationsView(APIView):
    def get(self, request, project_id):
        project = get_project(object_id(project_id))
        require_owner(project, ObjectId(request.user.id))
        if project["status"] != "Open" or len(project["team_members"]) >= project["team_size"]:
            return Response({"items": [], "detail": "This project is not recruiting."})
        active_ids = [u["_id"] for u in get_collection("users").find({"is_active": True, "_id": {"$nin": project["team_members"]}}, {"_id": 1})]
        candidates = list(get_collection("profiles").find({"user_id": {"$in": active_ids}}).sort("_id", 1).limit(2000))
        if not candidates:
            return Response({"items": [], "detail": "No eligible student profiles yet."})
        indices, _ = candidate_indices({"skills": project["required_skills"], "interests": project.get("required_interests", [])}, candidates)
        candidates = [candidates[i] for i in indices]
        if not candidates:
            return Response({"items": [], "detail": "No model-supported teammates yet. Browse Students."})
        bundle = load_models()
        vectors = [project_features(c, project) for c in candidates]
        scores = bundle["projects"].predict_proba(pd.DataFrame(vectors, columns=bundle["project_features"]))[:, list(bundle["projects"].classes_).index(1)]
        result = [{**profile_data(c, request.user.id), "compatibility_score": round(float(score) * 100, 1), "explanations": explain_project(c, project)} for c, score in zip(candidates, scores)]
        result.sort(key=lambda item: (-item["compatibility_score"], item["user_id"]))
        return Response({"items": result[:12], "model_notice": notice(), "ranking_method": "Random Forest student-project model; excludes existing members"})
