from dataclasses import dataclass

from bson import ObjectId
from bson.errors import InvalidId
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.settings import api_settings

from .mongo import get_collection


@dataclass
class MongoPrincipal:
    id: str
    email: str
    is_active: bool = True

    @property
    def pk(self):
        return self.id

    @property
    def is_authenticated(self):
        return True


class MongoJWTAuthentication(JWTAuthentication):
    def get_user(self, validated_token):
        raw_user_id = validated_token.get(api_settings.USER_ID_CLAIM)
        try:
            user_document = get_collection("users").find_one(
                {"_id": ObjectId(raw_user_id), "is_active": True},
                {"email": 1},
            )
        except (InvalidId, TypeError):
            user_document = None
        if user_document is None:
            raise AuthenticationFailed("User not found or inactive.")
        return MongoPrincipal(str(user_document["_id"]), user_document["email"])