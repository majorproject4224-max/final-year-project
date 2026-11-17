import re
from datetime import datetime, timezone
from bson import ObjectId
from bson.errors import InvalidId
from rest_framework.exceptions import NotFound, ValidationError


def now():
    return datetime.now(timezone.utc)


def object_id(value):
    try:
        return ObjectId(str(value))
    except (InvalidId, TypeError):
        raise NotFound("Record not found.")


def pair_key(left, right):
    return ":".join(sorted([str(left), str(right)]))


def page_args(request, maximum=50):
    try:
        page = max(1, int(request.query_params.get("page", 1)))
        size = max(1, min(maximum, int(request.query_params.get("page_size", 20))))
    except (ValueError, TypeError):
        raise ValidationError("Page and page_size must be integers.")
    return page, size


def page_result(collection, query, request, serialize, sort=None):
    page, size = page_args(request)
    rows = collection.find(query).sort(sort or [("_id", -1)]).skip((page - 1) * size).limit(size)
    return {
        "items": [serialize(item) for item in rows],
        "page": page,
        "page_size": size,
        "total": collection.count_documents(query),
    }


def search_regex(value):
    return {"$regex": re.escape(value.strip()[:100]), "$options": "i"}
