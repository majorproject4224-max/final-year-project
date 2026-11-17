import logging
from pymongo.errors import PyMongoError, DuplicateKeyError
from rest_framework.response import Response
from rest_framework.views import exception_handler

def api_exception_handler(exc, context):
    if isinstance(exc, DuplicateKeyError):
        return Response({"detail": "This record already exists.", "code": "duplicate"}, status=409)
    if isinstance(exc, PyMongoError):
        logging.getLogger(__name__).exception("MongoDB request failed")
        return Response({"detail": "The database is temporarily unavailable. Please retry.", "code": "database_unavailable"}, status=503)
    response = exception_handler(exc, context)
    if response is not None and isinstance(response.data, dict):
        response.data.setdefault("code", getattr(exc, "default_code", "request_failed"))
    return response
