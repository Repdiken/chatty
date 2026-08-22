from rest_framework.permissions import BasePermission

from .models import Conversation, ConversationMember


class IsConversationMemberPermission(BasePermission):
    """Allow only active members to access an active group conversation."""

    def has_permission(self, request, view):
        conversation_id = view.kwargs.get("conversation_id")

        return Conversation.objects.filter(
            id=conversation_id,
            type=Conversation.Type.GROUP,
            deleted_at__isnull=True,
            members__user=request.user,
            members__deleted_at__isnull=True,
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


class IsGroupOwnerOrAdminPermission(BasePermission):
    """Allow active group owners and admins to manage group details."""

    def has_object_permission(self, request, view, obj):
        # Private conversations are rejected by the view with its explicit
        # 406 response.  Let the request reach that branch rather than
        # returning a misleading permission error first.
        if obj.type != Conversation.Type.GROUP:
            return True

        return (
            ConversationMember.objects.filter(
                conversation=obj,
                user=request.user,
                deleted_at__isnull=True,
                role__in=[
                    ConversationMember.Role.OWNER,
                    ConversationMember.Role.ADMIN,
                ],
            ).exists()
        )


class CanManageConversationMemberPermission(BasePermission):
    """Apply the group's owner/admin hierarchy to member management."""

    message = "You do not have permission to manage this conversation member."

    def has_object_permission(self, request, view, obj):
        conversation = obj.conversation
        actor = ConversationMember.objects.filter(
            conversation=conversation, user=request.user, deleted_at__isnull=True
        ).first()

        if (
            conversation.type != Conversation.Type.GROUP
            or actor is None
            or actor.role not in [
                ConversationMember.Role.OWNER,
                ConversationMember.Role.ADMIN,
            ]
            or obj.deleted_at is not None
        ):
            return False

        # No one can remove or change the owner's membership through this endpoint.
        if obj.role == ConversationMember.Role.OWNER:
            return False

        if request.method == "DELETE":
            # Admins may remove regular members, but not other admins.
            return actor.role == ConversationMember.Role.OWNER or obj.role == ConversationMember.Role.MEMBER

        if request.method in ["PUT", "PATCH"]:
            # Only the owner can promote/demote members.  In particular, an
            # admin can never grant the admin role.
            return actor.role == ConversationMember.Role.OWNER

        return True
