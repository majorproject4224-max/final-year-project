from pymongo.errors import PyMongoError
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler


def api_exception_handler(exc, context):
    if isinstance(exc, PyMongoError):
        return Response(
            {
                "code": "database_unavailable",
                "detail": "MongoDB is unavailable. Start MongoDB or check MONGODB_URI, then retry.",
            },
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    return exception_handler(exc, context)