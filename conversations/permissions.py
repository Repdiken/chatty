from rest_framework.permissions import BasePermission

from .models import Conversation, ConversationMember


class IsConversationMemberPermission(BasePermission):
    def has_permission(self, request, view):

        conversation_id = view.kwargs.get("conversation_id")

        return Conversation.objects.filter(
            id=conversation_id, members__user=request.user
        ).exists()


class IsGroupOwnerPermission(BasePermission):
    """
    Allows access only if the requesting user is the OWNER of the group.
    Only applies to DELETE actions.
    """

    def has_object_permission(self, request, view, obj):
        # If they are just reading (GET) or updating (PUT/PATCH), let them pass!
        if request.method != "DELETE":
            return True

        # If they are trying to DELETE, enforce the Owner rule:
        return ConversationMember.objects.filter(
            conversation=obj, user=request.user, role=ConversationMember.Role.OWNER
        ).exists()
