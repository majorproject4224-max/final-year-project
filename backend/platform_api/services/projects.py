"""Team decisions are atomic across the project and its application/invitation."""

from pymongo import ReturnDocument
from rest_framework.exceptions import APIException, NotFound, PermissionDenied, ValidationError
from platform_api.common import now
from platform_api.mongo import get_collection, run_transaction


class Conflict(APIException):
    status_code = 409
    default_detail = "This record changed. Refresh and try again."


def get_project(project_id, session=None):
    project = get_collection("projects").find_one({"_id": project_id}, session=session)
    if project is None:
        raise NotFound("Project not found.")
    return project


def require_owner(project, user_id):
    if project["owner_id"] != user_id:
        raise PermissionDenied("Only the project owner can perform this action.")


def decide_membership(project_id, decision_id, actor_id, decision, kind="applications"):
    def operation(session):
        project = get_project(project_id, session)
        decisions = get_collection(kind)
        record = decisions.find_one({"_id": decision_id, "project_id": project_id}, session=session)
        if record is None:
            raise NotFound("Request not found.")
        if kind == "applications":
            require_owner(project, actor_id)
            applicant = record["user_id"]
        else:
            applicant = record["recipient_id"]
            if applicant != actor_id:
                raise PermissionDenied("Only the invited student can respond.")
        if record["status"] != "Pending":
            raise Conflict("This request has already been reviewed.")
        if decision == "Accepted":
            updated = get_collection("projects").update_one(
                {
                    "_id": project_id,
                    "status": "Open",
                    "team_members": {"$ne": applicant},
                    "$expr": {"$lt": [{"$size": "$team_members"}, "$team_size"]},
                },
                {"$addToSet": {"team_members": applicant}, "$set": {"updated_at": now()}},
                session=session,
            )
            if not updated.modified_count:
                raise Conflict("The team is full, closed, or the student is already a member.")
        decisions.update_one(
            {"_id": decision_id},
            {"$set": {"status": decision, "reviewed_at": now()}},
            session=session,
        )
        # An invitation and application can refer to the same student. Keep both views consistent.
        if decision == "Accepted":
            other = "invitations" if kind == "applications" else "applications"
            user_field = "recipient_id" if other == "invitations" else "user_id"
            get_collection(other).update_many(
                {"project_id": project_id, user_field: applicant, "status": "Pending"},
                {"$set": {"status": "Accepted", "reviewed_at": now()}},
                session=session,
            )
        return {"status": decision}

    return run_transaction(operation)
