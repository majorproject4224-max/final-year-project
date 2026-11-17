import uuid
from datetime import datetime, timezone
from bson import ObjectId
from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from pymongo.errors import DuplicateKeyError
from rest_framework.exceptions import AuthenticationFailed, ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from .authentication import MongoPrincipal
from .common import now
from .mongo import get_collection
from .serializers import LoginSerializer, RegisterSerializer, PasswordChangeSerializer

class AuthThrottle(AnonRateThrottle):
    scope = "auth"

def tokens_for(user, sid):
    refresh = RefreshToken.for_user(MongoPrincipal(str(user["_id"]), user["email"]))
    refresh["sid"] = sid
    return refresh

def issue_tokens(user):
    sid = uuid.uuid4().hex
    refresh = tokens_for(user, sid)
    get_collection("auth_sessions").insert_one({
        "sid": sid, "user_id": user["_id"], "refresh_jti": refresh["jti"],
        "expires_at": datetime.fromtimestamp(refresh["exp"], timezone.utc), "created_at": now(),
    })
    return {"refresh": str(refresh), "access": str(refresh.access_token)}

def auth_response(user):
    return {"user": {"id": str(user["_id"]), "name": user["name"], "email": user["email"]}, "tokens": issue_tokens(user)}

class PublicAuthView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get_authenticate_header(self, request):
        return 'Bearer realm="api"'

    def get_throttles(self):
        return [AuthThrottle()] if settings.REST_FRAMEWORK.get("DEFAULT_THROTTLE_CLASSES") else []

class RegisterView(PublicAuthView):
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        values = serializer.validated_data
        user = {"name": values["name"], "email": values["email"], "password_hash": make_password(values["password"]), "is_active": True, "created_at": now()}
        try:
            user["_id"] = get_collection("users").insert_one(user).inserted_id
        except DuplicateKeyError:
            return Response({"detail": "An account with this email already exists."}, status=409)
        return Response(auth_response(user), status=201)

class LoginView(PublicAuthView):
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        values = serializer.validated_data
        user = get_collection("users").find_one({"email": values["email"], "is_active": True})
        if user is None or not check_password(values["password"], user["password_hash"]):
            # Perform a password hash even for unknown emails.
            if user is None:
                make_password(values["password"])
            raise AuthenticationFailed("Email or password is incorrect.")
        return Response(auth_response(user))

class RefreshView(PublicAuthView):
    def post(self, request):
        try:
            old = RefreshToken(request.data.get("refresh", ""))
            user_id = ObjectId(old["user_id"])
            sid = old["sid"]
        except (TokenError, KeyError, TypeError, ValueError):
            raise AuthenticationFailed("Invalid refresh token.")
        user = get_collection("users").find_one({"_id": user_id, "is_active": True})
        if user is None:
            raise AuthenticationFailed("Account unavailable.")
        new = tokens_for(user, sid)
        updated = get_collection("auth_sessions").update_one(
            {"sid": sid, "user_id": user_id, "refresh_jti": old["jti"], "expires_at": {"$gt": now()}},
            {"$set": {"refresh_jti": new["jti"], "expires_at": datetime.fromtimestamp(new["exp"], timezone.utc)}},
        )
        if not updated.modified_count:
            raise AuthenticationFailed("Session expired or refresh token already used.")
        return Response({"access": str(new.access_token), "refresh": str(new)})

class LogoutView(APIView):
    def post(self, request):
        get_collection("auth_sessions").delete_one({"sid": request.user.session_id, "user_id": ObjectId(request.user.id)})
        return Response({"detail": "Signed out."})

class AccountView(APIView):
    def get(self, request):
        user = get_collection("users").find_one({"_id": ObjectId(request.user.id)})
        return Response({"id": request.user.id, "name": user["name"], "email": user["email"]})

    def patch(self, request):
        serializer = PasswordChangeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user_id = ObjectId(request.user.id)
        user = get_collection("users").find_one({"_id": user_id})
        if not check_password(serializer.validated_data["current_password"], user["password_hash"]):
            raise ValidationError({"current_password": ["Current password is incorrect."]})
        get_collection("users").update_one({"_id": user_id}, {"$set": {"password_hash": make_password(serializer.validated_data["new_password"])}})
        get_collection("auth_sessions").delete_many({"user_id": user_id})
        return Response({"detail": "Password changed. Sign in again on all devices."})
