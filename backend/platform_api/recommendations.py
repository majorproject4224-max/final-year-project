"""Discovery endpoints. Social success is never inferred from survey preferences."""
import json
from bson import ObjectId
from django.conf import settings
from rest_framework.response import Response
from rest_framework.views import APIView
from ml.discovery import recommend_people, project_match
from .mongo import get_collection
from .people import profile_data
from .projects import project_data
from .common import object_id
from .services.projects import get_project, require_owner
from .services.recommendations import load_models, notice

PROJECT_NOTICE = "Ranked by observed technology coverage. There is no real project-outcome training dataset, so this score is not an ML success prediction."


def excluded_targets(user_id, kind):
    return [r["target_id"] for r in get_collection("interactions").find({"user_id": user_id, "target_type": kind, "action": "ignore"})]


def source_profile(user_id):
    return get_collection("profiles").find_one({"user_id": user_id})


def eligible_profiles(excluded):
    ids = [u["_id"] for u in get_collection("users").find({"is_active": True, "_id": {"$nin": excluded}}, {"_id": 1})]
    return list(get_collection("profiles").find({"user_id": {"$in": ids}}).sort("_id", 1).limit(2000))


class UserRecommendationsView(APIView):
    def get(self, request):
        actor = ObjectId(request.user.id)
        source = source_profile(actor)
        if not source:
            return Response({"items": [], "detail": "Add technologies you use and want to use in My profile."})
        excluded = [actor] + excluded_targets(actor, "student")
        for connection in get_collection("connections").find({"$or": [{"requester_id": actor}, {"recipient_id": actor}]}):
            excluded.extend([connection["requester_id"], connection["recipient_id"]])
        candidates = eligible_profiles(excluded)
        ranked, details = recommend_people(load_models(), source, candidates)
        items = []
        for ranking in ranked:
            candidate = candidates[ranking.pop("candidate_index")]
            items.append({**profile_data(candidate, request.user.id), **ranking})
        return Response({"items": items, **details, "model_notice": notice(), "candidate_count": len(candidates), "ranking_method": "K-Means + survey preference Random Forest + profile comparisons"})


class ProjectRecommendationsView(APIView):
    def get(self, request):
        actor = ObjectId(request.user.id)
        source = source_profile(actor)
        if not source:
            return Response({"items": [], "detail": "Complete your technology profile to receive project suggestions."})
        candidates = get_collection("projects").find({"status": "Open", "team_members": {"$ne": actor}, "_id": {"$nin": excluded_targets(actor, "project")}, "$expr": {"$lt": [{"$size": "$team_members"}, "$team_size"]}}).sort("_id", 1).limit(2000)
        items = []
        for project in candidates:
            match = project_match(source, project)
            if match["match_score"] > 0:
                items.append({**project_data(project, actor), **match})
        items.sort(key=lambda row: (-row["match_score"], row["id"]))
        return Response({"items": items[:12], "model_notice": PROJECT_NOTICE, "ranking_method": "Observed technology coverage", "detail": "No matching open projects yet. Browse all projects." if not items else ""})


class ProjectTeammateRecommendationsView(APIView):
    def get(self, request, project_id):
        project = get_project(object_id(project_id))
        require_owner(project, ObjectId(request.user.id))
        if project["status"] != "Open" or len(project["team_members"]) >= project["team_size"]:
            return Response({"items": [], "detail": "This project is not recruiting."})
        items = []
        for profile in eligible_profiles(project["team_members"]):
            match = project_match(profile, project)
            if match["match_score"] > 0:
                items.append({**profile_data(profile, request.user.id), **match})
        items.sort(key=lambda row: (-row["match_score"], row["user_id"]))
        return Response({"items": items[:12], "model_notice": PROJECT_NOTICE, "ranking_method": "Observed technology coverage", "detail": "No matching teammate profiles yet." if not items else ""})


class RecommendationEvidenceView(APIView):
    def get(self, request):
        path = settings.PROJECT_ROOT / "ml/evaluation/survey2024/metrics.json"
        if not path.exists():
            return Response({"detail": "The real-data experiment has not been published yet."}, status=503)
        report = json.loads(path.read_text(encoding="utf-8"))
        return Response({key: report[key] for key in ["metadata", "audit", "splits", "target_labels", "selected_parameters", "clustering", "test", "baselines", "learning_curve", "natural_missingness_evaluation", "artificial_masking_stress_test", "limitations"]})
