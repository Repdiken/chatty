from django.urls import path
from .views import (
    PrivateConversationCreateView,
    GroupConversationCreateView,
    ConversationListView,
)

urlpatterns = [
    path("conversations/create-private", PrivateConversationCreateView.as_view()),
    path("conversations/create-group", GroupConversationCreateView.as_view()),
    path("conversations", ConversationListView.as_view()),
]
