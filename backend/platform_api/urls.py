from django.urls import path
from .accounts import RegisterView, LoginView, RefreshView, LogoutView, AccountView
from .people import (
    ProfileView,
    ResumeSuggestionsView,
    StudentsView,
    StudentDetailView,
    ConnectionsView,
    ConnectionDetailView,
)
from .projects import (
    ProjectsView,
    ProjectDetailView,
    ProjectApplicationView,
    ProjectMembersView,
    InvitationsView,
    InvitationDetailView,
)
from .community import (
    EventsView,
    EventDetailView,
    EventAttendanceView,
    FeedbackView,
    InteractionsView,
)
from .messaging import ConversationsView, ConversationMessagesView, MessageAttachmentView, WebSocketTicketView
from .recommendations import (
    UserRecommendationsView,
    ProjectRecommendationsView,
    ProjectTeammateRecommendationsView,
)

urlpatterns = [
    path("auth/register/", RegisterView.as_view()),
    path("auth/login/", LoginView.as_view()),
    path("auth/token/refresh/", RefreshView.as_view()),
    path("auth/logout/", LogoutView.as_view()),
    path("auth/me/", AccountView.as_view()),
    path("profiles/me/", ProfileView.as_view()),
    path("profiles/resume-suggestions/", ResumeSuggestionsView.as_view()),
    path("students/", StudentsView.as_view()),
    path("students/<str:user_id>/", StudentDetailView.as_view()),
    path("connections/", ConnectionsView.as_view()),
    path("connections/<str:connection_id>/", ConnectionDetailView.as_view()),
    path("projects/", ProjectsView.as_view()),
    path("projects/recommendations/", ProjectRecommendationsView.as_view()),
    path("projects/<str:project_id>/", ProjectDetailView.as_view()),
    path("projects/<str:project_id>/applications/", ProjectApplicationView.as_view()),
    path("projects/<str:project_id>/members/<str:user_id>/", ProjectMembersView.as_view()),
    path("projects/<str:project_id>/teammates/", ProjectTeammateRecommendationsView.as_view()),
    path("invitations/", InvitationsView.as_view()),
    path("invitations/<str:invitation_id>/", InvitationDetailView.as_view()),
    path("events/", EventsView.as_view()),
    path("events/<str:event_id>/", EventDetailView.as_view()),
    path("events/<str:event_id>/attendance/", EventAttendanceView.as_view()),
    path("feedback/", FeedbackView.as_view()),
    path("interactions/", InteractionsView.as_view()),
    path("conversations/", ConversationsView.as_view()),
    path("conversations/<str:conversation_id>/messages/", ConversationMessagesView.as_view()),
    path(
        "conversations/<str:conversation_id>/messages/<str:message_id>/attachments/<str:attachment_id>/",
        MessageAttachmentView.as_view(),
    ),
    path("conversations/<str:conversation_id>/websocket-ticket/", WebSocketTicketView.as_view()),
    path("recommendations/users/", UserRecommendationsView.as_view()),
    path("recommendations/projects/", ProjectRecommendationsView.as_view()),
    path(
        "recommendations/teammates/<str:project_id>/", ProjectTeammateRecommendationsView.as_view()
    ),
]
