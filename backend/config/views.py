from django.conf import settings
from django.shortcuts import redirect
from pymongo.errors import PyMongoError
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from platform_api.mongo import get_client


def app_root(request):
    return redirect(settings.FRONTEND_URL)


class HealthView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({"status": "ok", "service": "connect-ai-api"})


class ReadinessView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        try:
            get_client().admin.command("ping")
        except PyMongoError:
            return Response(
                {
                    "status": "not_ready",
                    "database": "unavailable",
                    "code": "database_unavailable",
                    "detail": "MongoDB is unavailable. Start MongoDB or check MONGODB_URI.",
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response({"status": "ready", "database": "available"})