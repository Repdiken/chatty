from rest_framework.permissions import BasePermission

from .models import Conversation


class IsConversationMemberPermission(BasePermission):
    def has_permission(self, request, view):

        conversation_id = view.kwargs.get("conversation_id")

        return Conversation.objects.filter(
            id=conversation_id, members__user=request.user
        ).exists()
