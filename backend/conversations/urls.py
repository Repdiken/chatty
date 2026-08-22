from django.urls import path
from .views import (
    PrivateConversationCreateView,
    GroupConversationCreateView,
    ConversationListView,
    ConversationDetailListView,
    ConversationMemberDetailAPIView,
    LeaveConversationAPIView,
)

urlpatterns = [
    path("conversations/create-private", PrivateConversationCreateView.as_view()),
    path("conversations/create-group", GroupConversationCreateView.as_view()),
    path("conversations", ConversationListView.as_view()),
    path("conversations/<int:conversation_id>", ConversationDetailListView.as_view()),
    path(
        "conversations/<int:conversation_id>/members/<int:member_id>",
        ConversationMemberDetailAPIView.as_view(),
    ),
    path(
        "conversations/<int:conversation_id>/leave", LeaveConversationAPIView.as_view()
    ),
]
