from django.contrib.auth.apps import AuthConfig
from django.contrib.contenttypes.apps import ContentTypesConfig


class MongoAuthConfig(AuthConfig):
    default_auto_field = "django_mongodb_backend.fields.ObjectIdAutoField"

    def ready(self):
        super().ready()
        from django.db.models.signals import post_migrate

        post_migrate.disconnect(
            dispatch_uid="django.contrib.auth.management.create_permissions"
        )


class MongoContentTypesConfig(ContentTypesConfig):
    default_auto_field = "django_mongodb_backend.fields.ObjectIdAutoField"