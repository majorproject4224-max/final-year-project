from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    LoginView,
    ConnectionDetailView,
    ConnectionsView,
    EventAttendanceView,
    EventsView,
    FeedbackView,
    ProfileView,
    ProjectApplicationView,
    ProjectsView,
    RegisterView,
    ResumeSuggestionsView,
    ProjectRecommendationsView,
    ProjectTeammateRecommendationsView,
    UserRecommendationsView,
)
from .messaging import (
    ConversationMessagesView,
    ConversationsView,
    WebSocketTicketView,
)

urlpatterns = [
    path("auth/register/", RegisterView.as_view(), name="register"),
    path("auth/login/", LoginView.as_view(), name="login"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("profiles/me/", ProfileView.as_view(), name="profile"),
    path("profiles/resume-suggestions/", ResumeSuggestionsView.as_view(), name="resume_suggestions"),
    path("projects/", ProjectsView.as_view(), name="projects"),
    path("projects/<str:project_id>/applications/", ProjectApplicationView.as_view(), name="project_application"),
    path("projects/recommendations/", ProjectRecommendationsView.as_view(), name="project_recommendations"),
    path("projects/<str:project_id>/teammates/", ProjectTeammateRecommendationsView.as_view(), name="project_teammates"),
    path("recommendations/users/", UserRecommendationsView.as_view(), name="user_recommendations"),
    path("connections/", ConnectionsView.as_view(), name="connections"),
    path("connections/<str:connection_id>/", ConnectionDetailView.as_view(), name="connection_detail"),
    path("events/", EventsView.as_view(), name="events"),
    path("events/<str:event_id>/attendance/", EventAttendanceView.as_view(), name="event_attendance"),
    path("feedback/", FeedbackView.as_view(), name="feedback"),
    path("conversations/", ConversationsView.as_view(), name="conversations"),
    path("conversations/<str:conversation_id>/messages/", ConversationMessagesView.as_view(), name="conversation_messages"),
    path("conversations/<str:conversation_id>/websocket-ticket/", WebSocketTicketView.as_view(), name="websocket_ticket"),
]