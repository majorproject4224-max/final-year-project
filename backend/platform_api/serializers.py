from rest_framework import serializers

from .matching import normalize_items


class RegisterSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=80, trim_whitespace=True)
    email = serializers.EmailField(max_length=254)
    password = serializers.CharField(min_length=8, write_only=True, trim_whitespace=False)

    def validate_email(self, value):
        return value.strip().casefold()


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=254)
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate_email(self, value):
        return value.strip().casefold()


class ProfileSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=80)
    branch = serializers.CharField(max_length=100)
    academic_year = serializers.IntegerField(min_value=1, max_value=4)
    skills = serializers.ListField(child=serializers.CharField(max_length=60), min_length=1, max_length=40)
    interests = serializers.ListField(child=serializers.CharField(max_length=60), min_length=1, max_length=40)
    domain = serializers.ChoiceField(choices=["AI / ML", "Data Science", "Web Development", "Mobile Development", "Backend Development", "Cybersecurity"])
    experience = serializers.ChoiceField(choices=["Beginner", "Intermediate", "Advanced"])
    preferred_project_type = serializers.CharField(max_length=80)
    city = serializers.CharField(max_length=100)
    phone = serializers.CharField(max_length=40, required=False, allow_blank=True, default="")
    github = serializers.URLField(required=False, allow_blank=True, default="")
    share_contact = serializers.BooleanField(required=False, default=False)

    def validate_skills(self, values):
        normalized = normalize_items(values)
        if not normalized:
            raise serializers.ValidationError("Add at least one skill.")
        return normalized

    def validate_interests(self, values):
        normalized = normalize_items(values)
        if not normalized:
            raise serializers.ValidationError("Add at least one interest.")
        return normalized


class ProjectSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=100)
    description = serializers.CharField(max_length=2000)
    required_skills = serializers.ListField(child=serializers.CharField(max_length=60), min_length=1, max_length=40)
    domain = serializers.ChoiceField(choices=["AI / ML", "Data Science", "Web Development", "Mobile Development", "Backend Development", "Cybersecurity"])
    project_type = serializers.CharField(max_length=80)
    team_size = serializers.IntegerField(min_value=2, max_value=10, default=4)

    def validate_required_skills(self, values):
        normalized = normalize_items(values)
        if not normalized:
            raise serializers.ValidationError("Add at least one required skill.")
        return normalized


class ApplicationDecisionSerializer(serializers.Serializer):
    application_id = serializers.CharField(max_length=24)
    decision = serializers.ChoiceField(choices=["Accepted", "Rejected"])


class ConnectionRequestSerializer(serializers.Serializer):
    user_id = serializers.CharField(max_length=24)


class EventSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=120)
    description = serializers.CharField(max_length=2000)
    location = serializers.CharField(max_length=160)
    starts_at = serializers.DateTimeField()


class FeedbackSerializer(serializers.Serializer):
    to_user_id = serializers.CharField(max_length=24)
    project_id = serializers.CharField(max_length=24, required=False, allow_blank=True, default="")
    rating = serializers.IntegerField(min_value=1, max_value=5)
    comment = serializers.CharField(max_length=1000, required=False, allow_blank=True, default="")


class ConversationSerializer(serializers.Serializer):
    recipient_id = serializers.CharField(max_length=24)


class MessageSerializer(serializers.Serializer):
    content = serializers.CharField(max_length=4000, trim_whitespace=True)