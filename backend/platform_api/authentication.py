from dataclasses import dataclass
from bson import ObjectId
from bson.errors import InvalidId
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication
from .common import now
from .mongo import get_collection

@dataclass
class MongoPrincipal:
    id: str
    email: str
    session_id: str = ""
    is_active: bool = True

    @property
    def pk(self):
        return self.id

    @property
    def is_authenticated(self):
        return True

def session_is_active(user_id, sid):
    return (
        get_collection("users").find_one({"_id": user_id, "is_active": True}, {"_id": 1}) is not None
        and get_collection("auth_sessions").find_one(
            {"user_id": user_id, "sid": sid, "expires_at": {"$gt": now()}}, {"_id": 1}
        ) is not None
    )

class MongoJWTAuthentication(JWTAuthentication):
    def get_user(self, validated_token):
        try:
            user_id = ObjectId(validated_token.get("user_id"))
        except (InvalidId, TypeError):
            raise AuthenticationFailed("Invalid account.")
        sid = validated_token.get("sid", "")
        user = get_collection("users").find_one({"_id": user_id, "is_active": True})
        if user is None or not session_is_active(user_id, sid):
            raise AuthenticationFailed("Session expired. Please sign in again.")
        return MongoPrincipal(str(user_id), user["email"], sid)
