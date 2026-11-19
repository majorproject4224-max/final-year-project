"""Community activities and transparent interest matching, independent of the ML models."""

from bson import ObjectId
from pymongo import ReturnDocument
from rest_framework.exceptions import APIException, NotFound, PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView
from ml.features import normalize_items, normalize_text
from .common import now, object_id, page_result, search_regex
from .mongo import get_collection
from .serializers import EventSerializer, EVENT_CATEGORIES


class ActivityConflict(APIException):
    status_code = 409
    default_detail = (
        "This activity is full or has already started. Refresh to see its latest details."
    )


def attendee_count_expression():
    return {"$size": {"$ifNull": ["$attendee_ids", []]}}


def available_space_expression():
    return {"$lt": [attendee_count_expression(), {"$ifNull": ["$participant_limit", 500]}]}


def event_data(event, viewer):
    organizer = get_collection("users").find_one({"_id": event["organizer_id"]}, {"name": 1})
    count = len(event.get("attendee_ids", []))
    limit = event.get("participant_limit", 500)
    return {
        "id": str(event["_id"]),
        **{key: event[key] for key in ("title", "description", "location", "starts_at")},
        "category": event.get("category", "Other"),
        "interest_tags": event.get("interest_tags", []),
        "city": event.get("city", ""),
        "mode": event.get("mode", "In person"),
        "organization_name": event.get("organization_name", ""),
        "organizer_id": str(event["organizer_id"]),
        "organizer_name": organizer["name"] if organizer else "Unavailable account",
        "attendee_count": count,
        "participant_limit": limit,
        "spots_remaining": max(0, limit - count),
        "is_attending": viewer in event.get("attendee_ids", []),
        "has_started": event["starts_at"] <= now(),
    }


def get_event(event_id):
    event = get_collection("events").find_one({"_id": object_id(event_id)})
    if event is None:
        raise NotFound("Activity not found.")
    return event


def require_organizer(event, user_id):
    if event["organizer_id"] != ObjectId(user_id):
        raise PermissionDenied("Only the organizer can manage this activity.")


class EventsView(APIView):
    def get(self, request):
        viewer = ObjectId(request.user.id)
        query = {"starts_at": {"$gt": now()}}
        category = request.query_params.get("category")
        if category:
            if category not in EVENT_CATEGORIES:
                raise ValidationError("Choose a valid activity category.")
            query["category"] = category
        if request.query_params.get("q"):
            term = search_regex(request.query_params["q"])
            query["$or"] = [
                {field: term} for field in ("title", "description", "interest_tags", "city")
            ]
        scope = request.query_params.get("scope", "all")
        if scope == "organizing":
            query["organizer_id"] = viewer
            query.pop("starts_at")
        elif scope == "joined":
            query["attendee_ids"] = viewer
        elif scope != "all":
            raise ValidationError("Choose all, organizing or joined activities.")
        return Response(
            page_result(
                get_collection("events"),
                query,
                request,
                lambda e: event_data(e, viewer),
                [("starts_at", 1), ("_id", 1)],
            )
        )

    def post(self, request):
        serializer = EventSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        event = {
            **serializer.validated_data,
            "organizer_id": ObjectId(request.user.id),
            "attendee_ids": [],
            "created_at": now(),
        }
        event["_id"] = get_collection("events").insert_one(event).inserted_id
        return Response(event_data(event, ObjectId(request.user.id)), status=201)


class EventDetailView(APIView):
    def get(self, request, event_id):
        return Response(event_data(get_event(event_id), ObjectId(request.user.id)))

    def patch(self, request, event_id):
        event = get_event(event_id)
        require_organizer(event, request.user.id)
        serializer = EventSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        values = serializer.validated_data
        query = {
            "_id": event["_id"],
            "organizer_id": event["organizer_id"],
            "starts_at": {"$gt": now()},
        }
        if "participant_limit" in values:
            # The same-document predicate also prevents shrinking below concurrent sign-ups.
            query["$expr"] = {"$lte": [attendee_count_expression(), values["participant_limit"]]}
        updated = get_collection("events").find_one_and_update(
            query, {"$set": {**values, "updated_at": now()}}, return_document=ReturnDocument.AFTER
        )
        if updated is None:
            raise ActivityConflict(
                "The activity has started, or the limit is below its current participant count."
            )
        return Response(event_data(updated, ObjectId(request.user.id)))

    def delete(self, request, event_id):
        event = get_event(event_id)
        require_organizer(event, request.user.id)
        get_collection("events").delete_one(
            {"_id": event["_id"], "organizer_id": event["organizer_id"]}
        )
        return Response(status=204)


class EventAttendanceView(APIView):
    def post(self, request, event_id):
        viewer = ObjectId(request.user.id)
        # Atomic capacity check and add-to-set: retries are idempotent, simultaneous joins cannot overbook.
        query = {
            "_id": object_id(event_id),
            "starts_at": {"$gt": now()},
            "$or": [{"attendee_ids": viewer}, {"$expr": available_space_expression()}],
        }
        result = get_collection("events").update_one(query, {"$addToSet": {"attendee_ids": viewer}})
        if not result.matched_count:
            get_event(event_id)
            raise ActivityConflict()
        return Response({"status": "attending"})

    def delete(self, request, event_id):
        get_collection("events").update_one(
            {"_id": object_id(event_id)}, {"$pull": {"attendee_ids": ObjectId(request.user.id)}}
        )
        return Response(status=204)


class EventParticipantsView(APIView):
    def get(self, request, event_id):
        event = get_event(event_id)
        require_organizer(event, request.user.id)
        return Response(
            page_result(
                get_collection("users"),
                {"_id": {"$in": event.get("attendee_ids", [])}},
                request,
                lambda u: {"user_id": str(u["_id"]), "name": u["name"]},
                [("name", 1), ("_id", 1)],
            )
        )


class ActivityRecommendationsView(APIView):
    def get(self, request):
        viewer = ObjectId(request.user.id)
        profile = get_collection("profiles").find_one({"user_id": viewer}) or {}
        interests = set(normalize_items(profile.get("community_interests", profile.get("interests", []))))
        response = {
            "items": [],
            "matching_method": "shared_interests",
            "notice": "Suggested from your interests and location preference. No ML match score is used.",
        }
        if not interests:
            return Response(
                {**response, "detail": "Add your interests to discover activities for you."}
            )
        query = {
            "starts_at": {"$gt": now()},
            "organizer_id": {"$ne": viewer},
            "attendee_ids": {"$ne": viewer},
            "interest_tags": {"$in": sorted(interests)},
            "$expr": available_space_expression(),
        }
        city = normalize_text(profile.get("city", ""))
        if profile.get("activity_location_preference") == "local":
            if not city:
                return Response({**response, "detail": "Add your city to see nearby activities."})
            # Exact city equality, ignoring case and surrounding whitespace. No inferred distance.
            query["$or"] = [
                {"mode": "Online"},
                {
                    "$expr": {
                        "$eq": [
                            {"$toLower": {"$trim": {"input": {"$ifNull": ["$city", ""]}}}},
                            city,
                        ]
                    }
                },
            ]
        ranked = []
        for event in (
            get_collection("events").find(query).sort([("starts_at", 1), ("_id", 1)]).limit(500)
        ):
            shared = sorted(interests & set(normalize_items(event.get("interest_tags", []))))
            if not shared:
                continue
            same_city = bool(city and city == normalize_text(event.get("city", "")))
            reasons = ["Matches your interests: " + ", ".join(shared)]
            if event.get("mode") == "Online":
                reasons.append("Online activity")
            elif same_city:
                reasons.append("In your city: " + profile["city"])
            ranked.append(
                (
                    (-len(shared), -int(same_city), event["starts_at"], str(event["_id"])),
                    event,
                    shared,
                    reasons,
                )
            )
        ranked.sort(key=lambda item: item[0])
        response["items"] = [
            {**event_data(event, viewer), "shared_interests": shared, "reasons": reasons}
            for _, event, shared, reasons in ranked[:6]
        ]
        response["detail"] = (
            "No matching activities yet. Browse all events or update your interests."
        )
        return Response(response)
