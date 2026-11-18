from bson import ObjectId
from pymongo.errors import DuplicateKeyError
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView
from .common import now, object_id, page_result, search_regex
from .mongo import get_collection, run_transaction
from .serializers import ProjectSerializer, ApplicationDecisionSerializer
from .services.projects import get_project, require_owner, decide_membership, Conflict


def project_data(project, viewer=None, details=False):
    owner = get_collection("users").find_one({"_id": project["owner_id"]}, {"name": 1})
    keys = [
        "title",
        "description",
        "required_skills",
        "required_interests",
        "domain",
        "project_type",
        "team_size",
        "status",
        "required_experience",
        "expected_hours",
        "deadline",
        "created_at",
    ]
    result = {key: project.get(key) for key in keys}
    result.update(
        {
            "id": str(project["_id"]),
            "owner_id": str(project["owner_id"]),
            "owner_name": owner["name"] if owner else "Member",
            "team_member_count": len(project["team_members"]),
            "is_member": viewer in project["team_members"],
        }
    )
    if details:
        users = get_collection("users").find({"_id": {"$in": project["team_members"]}}, {"name": 1})
        result["members"] = [{"id": str(user["_id"]), "name": user["name"]} for user in users]
        if viewer:
            application = get_collection("applications").find_one(
                {"project_id": project["_id"], "user_id": viewer}
            )
            result["application_status"] = application["status"] if application else None
    return result


class ProjectsView(APIView):
    def get(self, request):
        user_id = ObjectId(request.user.id)
        query = (
            {"team_members": user_id}
            if request.query_params.get("mine") == "1"
            else {"status": request.query_params.get("status", "Open")}
        )
        if request.query_params.get("q"):
            term = search_regex(request.query_params["q"])
            query["$or"] = [{"title": term}, {"required_skills": term}, {"domain": term}]
        return Response(
            page_result(
                get_collection("projects"), query, request, lambda p: project_data(p, user_id)
            )
        )

    def post(self, request):
        serializer = ProjectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        values = serializer.validated_data
        if values.get("deadline") and values["deadline"] <= now():
            raise ValidationError("Choose a future deadline.")
        user_id = ObjectId(request.user.id)
        project = {
            **values,
            "owner_id": user_id,
            "team_members": [user_id],
            "status": "Open",
            "created_at": now(),
            "updated_at": now(),
        }
        project["_id"] = get_collection("projects").insert_one(project).inserted_id
        return Response(project_data(project, user_id, True), status=201)


class ProjectDetailView(APIView):
    def get(self, request, project_id):
        return Response(
            project_data(get_project(object_id(project_id)), ObjectId(request.user.id), True)
        )

    def patch(self, request, project_id):
        project_id = object_id(project_id)
        actor = ObjectId(request.user.id)
        requested_status = request.data.get("status")
        payload = {key: value for key, value in request.data.items() if key != "status"}
        serializer = ProjectSerializer(data=payload, partial=True)
        serializer.is_valid(raise_exception=True)
        values = dict(serializer.validated_data)
        if values.get("deadline") and values["deadline"] <= now():
            raise ValidationError("Choose a future deadline.")

        def operation(session):
            project = get_project(project_id, session)
            require_owner(project, actor)
            if project["status"] in {"Completed", "Cancelled"}:
                raise Conflict("Completed or cancelled projects cannot be edited.")
            if values.get("team_size", project["team_size"]) < len(project["team_members"]):
                raise ValidationError("Team size cannot be smaller than the current team.")
            transitions = {
                "Open": {"In Progress", "Cancelled"},
                "In Progress": {"Open", "Completed", "Cancelled"},
            }
            if requested_status and requested_status != project["status"]:
                if requested_status not in transitions[project["status"]]:
                    raise ValidationError("Invalid project status transition.")
                values["status"] = requested_status
                if requested_status in {"Completed", "Cancelled"}:
                    for name in ("applications", "invitations"):
                        get_collection(name).update_many(
                            {"project_id": project_id, "status": "Pending"},
                            {"$set": {"status": "Cancelled", "reviewed_at": now()}},
                            session=session,
                        )
            get_collection("projects").update_one(
                {"_id": project_id}, {"$set": {**values, "updated_at": now()}}, session=session
            )

        run_transaction(operation)
        return self.get(request, str(project_id))


class ProjectApplicationView(APIView):
    def get(self, request, project_id):
        project_id = object_id(project_id)
        require_owner(get_project(project_id), ObjectId(request.user.id))

        def serialize(item):
            user = get_collection("users").find_one({"_id": item["user_id"]})
            return {
                "id": str(item["_id"]),
                "user_id": str(item["user_id"]),
                "name": user["name"] if user else "Member",
                "status": item["status"],
                "created_at": item["created_at"],
            }

        return Response(
            page_result(
                get_collection("applications"), {"project_id": project_id}, request, serialize
            )
        )

    def post(self, request, project_id):
        project_id, user_id = object_id(project_id), ObjectId(request.user.id)

        def operation(session):
            project = get_project(project_id, session)
            if project["status"] != "Open" or len(project["team_members"]) >= project["team_size"]:
                raise Conflict("This project is not accepting applications.")
            if user_id in project["team_members"]:
                raise ValidationError("You are already a team member.")
            # Touch the project so a concurrent closing/status transition conflicts and retries.
            get_collection("projects").update_one(
                {"_id": project_id}, {"$set": {"updated_at": now()}}, session=session
            )
            return (
                get_collection("applications")
                .insert_one(
                    {
                        "project_id": project_id,
                        "user_id": user_id,
                        "status": "Pending",
                        "created_at": now(),
                    },
                    session=session,
                )
                .inserted_id
            )

        try:
            inserted = run_transaction(operation)
        except DuplicateKeyError:
            raise Conflict("You already applied to this project.")
        return Response({"id": str(inserted), "status": "Pending"}, status=201)

    def patch(self, request, project_id):
        serializer = ApplicationDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        values = serializer.validated_data
        result = decide_membership(
            object_id(project_id),
            object_id(values["application_id"]),
            ObjectId(request.user.id),
            values["decision"],
        )
        return Response(result)

    def delete(self, request, project_id):
        changed = get_collection("applications").delete_one(
            {
                "project_id": object_id(project_id),
                "user_id": ObjectId(request.user.id),
                "status": "Pending",
            }
        )
        if not changed.deleted_count:
            raise NotFound("Pending application not found.")
        return Response(status=204)


class ProjectMembersView(APIView):
    def delete(self, request, project_id, user_id):
        project_id, target, actor = (
            object_id(project_id),
            object_id(user_id),
            ObjectId(request.user.id),
        )

        def operation(session):
            project = get_project(project_id, session)
            if actor != target:
                require_owner(project, actor)
            if target == project["owner_id"]:
                raise ValidationError("The project owner cannot leave the team.")
            if project["status"] in {"Completed", "Cancelled"}:
                raise Conflict("Membership history is retained after a project ends.")
            if target not in project["team_members"]:
                raise NotFound("Team member not found.")
            get_collection("projects").update_one(
                {"_id": project_id},
                {"$pull": {"team_members": target}, "$set": {"updated_at": now()}},
                session=session,
            )
            for name, field in (("applications", "user_id"), ("invitations", "recipient_id")):
                get_collection(name).update_many(
                    {"project_id": project_id, field: target, "status": "Accepted"},
                    {"$set": {"status": "Left"}},
                    session=session,
                )

        run_transaction(operation)
        return Response(status=204)


class InvitationsView(APIView):
    def get(self, request):
        actor = ObjectId(request.user.id)
        query = {"$or": [{"recipient_id": actor}, {"sender_id": actor}]}

        def serialize(item):
            project = get_collection("projects").find_one({"_id": item["project_id"]})
            recipient = get_collection("users").find_one({"_id": item["recipient_id"]})
            return {
                "id": str(item["_id"]),
                "project_id": str(item["project_id"]),
                "project_title": project["title"] if project else "Unavailable project",
                "recipient_name": recipient["name"] if recipient else "Member",
                "status": item["status"],
                "direction": "received" if item["recipient_id"] == actor else "sent",
            }

        return Response(page_result(get_collection("invitations"), query, request, serialize))

    def post(self, request):
        project_id, recipient = (
            object_id(request.data.get("project_id")),
            object_id(request.data.get("recipient_id")),
        )
        actor = ObjectId(request.user.id)

        def operation(session):
            project = get_project(project_id, session)
            require_owner(project, actor)
            if project["status"] != "Open" or len(project["team_members"]) >= project["team_size"]:
                raise Conflict("The project is not recruiting.")
            if recipient in project["team_members"]:
                raise ValidationError("This person is already a member.")
            if not get_collection("users").find_one(
                {"_id": recipient, "is_active": True}, session=session
            ):
                raise NotFound("Person not found.")
            get_collection("projects").update_one(
                {"_id": project_id}, {"$set": {"updated_at": now()}}, session=session
            )
            return (
                get_collection("invitations")
                .insert_one(
                    {
                        "project_id": project_id,
                        "recipient_id": recipient,
                        "sender_id": actor,
                        "status": "Pending",
                        "created_at": now(),
                    },
                    session=session,
                )
                .inserted_id
            )

        try:
            identifier = run_transaction(operation)
        except DuplicateKeyError:
            raise Conflict("An invitation already exists for this person and project.")
        return Response({"id": str(identifier), "status": "Pending"}, status=201)


class InvitationDetailView(APIView):
    def patch(self, request, invitation_id):
        decision = request.data.get("decision")
        if decision not in {"Accepted", "Rejected"}:
            raise ValidationError("Choose Accepted or Rejected.")
        identifier = object_id(invitation_id)
        record = get_collection("invitations").find_one({"_id": identifier})
        if not record:
            raise NotFound("Invitation not found.")
        return Response(
            decide_membership(
                record["project_id"], identifier, ObjectId(request.user.id), decision, "invitations"
            )
        )

    def delete(self, request, invitation_id):
        result = get_collection("invitations").update_one(
            {
                "_id": object_id(invitation_id),
                "sender_id": ObjectId(request.user.id),
                "status": "Pending",
            },
            {"$set": {"status": "Cancelled", "reviewed_at": now()}},
        )
        if not result.modified_count:
            raise NotFound("Pending invitation not found.")
        return Response(status=204)
