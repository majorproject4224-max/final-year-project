from django.apps import AppConfig


class PlatformApiConfig(AppConfig):
    name = "platform_api"
    default_auto_field = "django_mongodb_backend.fields.ObjectIdAutoField"