from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from ml.features import normalize_items, normalize_domain

DOMAINS = [
    "AI / ML",
    "Data Science",
    "Web Development",
    "Mobile Development",
    "Backend Development",
    "Cybersecurity",
    "Cloud / DevOps",
    "Other",
]
EXPERIENCE = ["Beginner", "Intermediate", "Advanced"]


class PasswordField(serializers.CharField):
    def __init__(self, **kwargs):
        super().__init__(
            min_length=8, max_length=128, write_only=True, trim_whitespace=False, **kwargs
        )

    def to_internal_value(self, data):
        value = super().to_internal_value(data)
        try:
            validate_password(value)
        except DjangoValidationError as error:
            raise serializers.ValidationError(error.messages)
        return value


class RegisterSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=80)
    email = serializers.EmailField(max_length=254)
    password = PasswordField()

    def validate_email(self, value):
        return value.strip().casefold()


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=254)
    password = serializers.CharField(max_length=128, write_only=True, trim_whitespace=False)

    def validate_email(self, value):
        return value.strip().casefold()


class NormalizedItemsField(serializers.ListField):
    def __init__(self, **kwargs):
        super().__init__(child=serializers.CharField(max_length=60), max_length=40, **kwargs)

    def to_internal_value(self, data):
        values = normalize_items(super().to_internal_value(data))
        if not values and not self.allow_empty:
            raise serializers.ValidationError("Add at least one item.")
        return values


class ProfileSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=80)
    branch = serializers.CharField(max_length=100)
    academic_year = serializers.IntegerField(min_value=1, max_value=4)
    skills = NormalizedItemsField(allow_empty=False)
    interests = NormalizedItemsField(allow_empty=False)
    domain = serializers.ChoiceField(choices=DOMAINS)
    experience = serializers.ChoiceField(choices=EXPERIENCE)
    preferred_project_type = serializers.CharField(max_length=80)
    projects_completed = serializers.IntegerField(min_value=0, max_value=100, default=0)
    availability_hours = serializers.IntegerField(min_value=1, max_value=40, default=8)
    bio = serializers.CharField(max_length=1000, allow_blank=True, default="")
    city = serializers.CharField(max_length=100, allow_blank=True, default="")
    phone = serializers.CharField(max_length=40, allow_blank=True, default="")
    github = serializers.URLField(allow_blank=True, default="")
    share_contact = serializers.BooleanField(default=False)


class ProjectSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=100)
    description = serializers.CharField(max_length=3000)
    required_skills = NormalizedItemsField(allow_empty=False)
    required_interests = NormalizedItemsField(default=list)
    domain = serializers.ChoiceField(choices=DOMAINS)
    project_type = serializers.CharField(max_length=80)
    team_size = serializers.IntegerField(min_value=2, max_value=10, default=4)
    required_experience = serializers.ChoiceField(choices=EXPERIENCE, default="Beginner")
    expected_hours = serializers.IntegerField(min_value=1, max_value=40, default=6)
    deadline = serializers.DateTimeField(required=False, allow_null=True)


class ApplicationDecisionSerializer(serializers.Serializer):
    application_id = serializers.CharField(max_length=24)
    decision = serializers.ChoiceField(choices=["Accepted", "Rejected"])


class EventSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=120)
    description = serializers.CharField(max_length=2000)
    location = serializers.CharField(max_length=160)
    starts_at = serializers.DateTimeField()


class FeedbackSerializer(serializers.Serializer):
    to_user_id = serializers.CharField(max_length=24)
    project_id = serializers.CharField(max_length=24)
    rating = serializers.IntegerField(min_value=1, max_value=5)
    comment = serializers.CharField(max_length=1000, allow_blank=True, default="")


class ConversationSerializer(serializers.Serializer):
    recipient_id = serializers.CharField(max_length=24)


class MessageSerializer(serializers.Serializer):
    content = serializers.CharField(max_length=4000, trim_whitespace=True, allow_blank=True, default="")
    client_id = serializers.UUIDField()
    attachments = serializers.ListField(
        child=serializers.FileField(), max_length=3, required=False, default=list
    )

    def validate(self, attrs):
        if not attrs["content"] and not attrs["attachments"]:
            raise serializers.ValidationError("Write a message or attach a file.")
        return attrs


class ConnectionRequestSerializer(serializers.Serializer):
    user_id = serializers.CharField(max_length=24)


class InteractionSerializer(serializers.Serializer):
    target_type = serializers.ChoiceField(choices=["student", "project"])
    target_id = serializers.CharField(max_length=24)
    action = serializers.ChoiceField(choices=["view", "ignore", "save", "unsave"])


class PasswordChangeSerializer(serializers.Serializer):
    current_password = serializers.CharField(max_length=128, trim_whitespace=False)
    new_password = PasswordField()
