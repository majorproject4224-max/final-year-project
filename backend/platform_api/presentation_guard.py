"""Require explicit permission before adding fictional records to an application DB."""

from django.conf import settings
from django.core.management.base import CommandError


def require_presentation_database():
    if not settings.DEBUG or not (
        settings.MONGODB_DATABASE.endswith("_test")
        or settings.PRESENTATION_DATA_ENABLED
    ):
        raise CommandError(
            "Fictional presentation data requires DEBUG and either a disposable _test "
            "database or explicit PRESENTATION_DATA_ENABLED=1."
        )
