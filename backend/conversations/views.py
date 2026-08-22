from rest_framework.generics import (
    CreateAPIView,
    ListAPIView,
    RetrieveUpdateDestroyAPIView,
)
from rest_framework.views import APIView

from .serializers import (
    ConversationPrivateCreateSerializer,
    ConversationGroupCreateSerializer,
    ConversationListSerializer,
    ConversationGroupDetailSerializer,
    ConversationPrivateDetailSerializer,
    ConversationMemberDetailSerializer,
    TransferOwnershipSerializer,
)

from rest_framework.permissions import IsAuthenticated
from .permissions import (
    CanManageConversationMemberPermission,
    IsConversationMemberPermission,
    IsGroupOwnerOrAdminPermission,
    IsGroupOwnerPermission,
)

from .models import Conversation, ConversationMember

from rest_framework.response import Response
from rest_framework.status import (
    HTTP_201_CREATED,
    HTTP_406_NOT_ACCEPTABLE,
    HTTP_200_OK,
    HTTP_403_FORBIDDEN,
    HTTP_400_BAD_REQUEST,
)

from django.shortcuts import get_object_or_404

from django.utils import timezone
from django.db import transaction


class PrivateConversationCreateView(CreateAPIView):
    serializer_class = ConversationPrivateCreateSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        creator = self.request.user
        target_user = serializer.validated_data["username"]

        if creator == target_user:  # Prevent creating a chat with yourself
            return Response(
                {
                    "non_field_errors": [
                        "You cannot start a conversation with yourself."
                    ]
                },
                status=HTTP_400_BAD_REQUEST,
            )

        existing_convo = (
            Conversation.objects.filter(
                type=Conversation.Type.PRIVATE, members__user=creator
            )
            .filter(members__user=target_user)
            .first()
        )

        # Reopen existing conversation if found
        if existing_convo:
            existing_convo.deleted_at = None
            existing_convo.save()
            return Response(
                {"message": "Conversation reopened", "id": existing_convo.id},
                status=HTTP_200_OK,
            )

        conversation = Conversation.objects.create(type=Conversation.Type.PRIVATE)

        ConversationMember.objects.create(
            conversation=conversation,
            user=target_user,
            role=ConversationMember.Role.MEMBER,
        )
        ConversationMember.objects.create(
            conversation=conversation, user=creator, role=ConversationMember.Role.MEMBER
        )

        return Response({"message": "Conversation created"})


class GroupConversationCreateView(CreateAPIView):
    serializer_class = ConversationGroupCreateSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)

        users_data = serializer.validated_data["usernames"]
        valid_users = users_data["valid_users"]
        invalid_users = users_data["invalid_users"]

        owner = self.request.user
        title = serializer.validated_data["title"]

        conversation = Conversation.objects.create(
            title=title, type=Conversation.Type.GROUP
        )

        members_to_create = [
            ConversationMember(
                conversation=conversation,
                user=owner,
                role=ConversationMember.Role.OWNER,
            )
        ]

        for user in valid_users:
            members_to_create.append(
                ConversationMember(
                    conversation=conversation,
                    user=user,
                    role=ConversationMember.Role.MEMBER,
                )
            )

        ConversationMember.objects.bulk_create(members_to_create)

        response_data = {"message": "Group conversation created successfully."}
        if invalid_users:
            response_data["warning"] = (
                f"The following users do not exist and were skipped: {', '.join(invalid_users)}"
            )

        return Response(response_data, status=HTTP_201_CREATED)


class ConversationListView(ListAPIView):

    serializer_class = ConversationListSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Conversation.objects.filter(
            members__user=self.request.user,
            deleted_at__isnull=True,
            members__deleted_at__isnull=True,
        )


class ConversationDetailListView(RetrieveUpdateDestroyAPIView):

    def get_permissions(self):
        if self.request.method == "DELETE":
            permission_classes = [IsGroupOwnerPermission, IsAuthenticated]
        elif self.request.method in ["PUT", "PATCH"]:
            permission_classes = [IsAuthenticated, IsGroupOwnerOrAdminPermission]
        else:
            permission_classes = [IsAuthenticated]

        return [permission() for permission in permission_classes]

    lookup_url_kwarg = "conversation_id"

    def get_serializer_class(self):

        conversation = self.get_object()

        if conversation.type == "private":
            return ConversationPrivateDetailSerializer
        else:
            return ConversationGroupDetailSerializer

    def get_queryset(self):
        return Conversation.objects.filter(
            members__user=self.request.user,
            deleted_at__isnull=True,
            members__deleted_at__isnull=True,
        )

    def put(self, request, *args, **kwargs):

        conversation = self.get_object()

        if conversation.type == "private":
            return Response(
                {"message": "Can't change the details for a private chat."},
                status=HTTP_406_NOT_ACCEPTABLE,
            )
        else:
            serializer = self.get_serializer(
                conversation,
                data=request.data,
                partial=True,
                context={"request": request},
            )
            serializer.is_valid(raise_exception=True)

            # The endpoint accepts partial PUT/PATCH updates, so preserve any
            # group fields that were not included in the request.
            for field in ["title", "description", "profile_picture"]:
                if field in serializer.validated_data:
                    setattr(conversation, field, serializer.validated_data[field])
            conversation.save()

            return Response(
                {"message": "Successfully updated."},
                status=HTTP_200_OK,
            )

    def patch(self, request, *args, **kwargs):
        """Apply the same private-chat and group-role rules to PATCH."""
        return self.put(request, *args, **kwargs)

    def perform_destroy(self, instance):
        # Soft-delete the group and its memberships together so no member can
        # keep using a deleted group through another endpoint.
        deleted_at = timezone.now()
        with transaction.atomic():
            ConversationMember.objects.filter(
                conversation=instance, deleted_at__isnull=True
            ).update(deleted_at=deleted_at)
            instance.deleted_at = deleted_at
            instance.save(update_fields=["deleted_at"])


class LeaveConversationAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, conversation_id):
        # If the chat doesn't exist, OR if they aren't in it, this returns a 404
        member = get_object_or_404(
            ConversationMember,
            conversation_id=conversation_id,
            user=request.user,
            deleted_at__isnull=True,
        )

        if member.role == ConversationMember.Role.OWNER:
            return Response(
                {"error": "Owners cannot leave without transferring ownership."},
                status=HTTP_403_FORBIDDEN,
            )

        member.deleted_at = timezone.now()
        member.save()

        return Response(
            {"message": "You have left the conversation."}, status=HTTP_200_OK
        )


class ConversationMemberDetailAPIView(RetrieveUpdateDestroyAPIView):
    serializer_class = ConversationMemberDetailSerializer
    permission_classes = [IsAuthenticated, CanManageConversationMemberPermission]
    lookup_url_kwarg = "member_id"

    def get_queryset(self):
        return ConversationMember.objects.filter(
            conversation_id=self.kwargs["conversation_id"],
            conversation__deleted_at__isnull=True,
            deleted_at__isnull=True,
        )

    def perform_destroy(self, instance):
        instance.deleted_at = timezone.now()
        instance.save(update_fields=["deleted_at"])


class ConversationMemberListAPIView(ListAPIView):
    """List active members for a group the requesting user belongs to."""

    serializer_class = ConversationMemberDetailSerializer
    permission_classes = [IsAuthenticated, IsConversationMemberPermission]

    def get_queryset(self):
        return ConversationMember.objects.filter(
            conversation_id=self.kwargs["conversation_id"],
            conversation__type=Conversation.Type.GROUP,
            conversation__deleted_at__isnull=True,
            deleted_at__isnull=True,
        ).select_related("user")


class TransferConversationOwnershipAPIView(APIView):
    """Transfer a group's sole owner role to another active member."""

    permission_classes = [IsAuthenticated]

    def post(self, request, conversation_id):
        serializer = TransferOwnershipSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        target_user = serializer.validated_data["username"]

        with transaction.atomic():
            conversation = get_object_or_404(
                Conversation.objects.select_for_update(),
                id=conversation_id,
                type=Conversation.Type.GROUP,
                deleted_at__isnull=True,
            )
            current_owner = get_object_or_404(
                ConversationMember.objects.select_for_update(),
                conversation=conversation,
                user=request.user,
                role=ConversationMember.Role.OWNER,
                deleted_at__isnull=True,
            )
            new_owner = get_object_or_404(
                ConversationMember.objects.select_for_update(),
                conversation=conversation,
                user=target_user,
                deleted_at__isnull=True,
            )

            if new_owner == current_owner:
                return Response(
                    {"message": "You already own this group."},
                    status=HTTP_400_BAD_REQUEST,
                )

            # Demote first so the database's one-owner constraint is true at
            # every completed write, then promote the selected member.
            current_owner.role = ConversationMember.Role.MEMBER
            current_owner.save(update_fields=["role"])
            new_owner.role = ConversationMember.Role.OWNER
            new_owner.save(update_fields=["role"])

        return Response(
            {"message": "Ownership transferred successfully."},
            status=HTTP_200_OK,
        )
