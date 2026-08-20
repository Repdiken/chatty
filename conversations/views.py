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
)

from rest_framework.permissions import IsAuthenticated
from .permissions import IsGroupOwnerPermission

from .models import Conversation, ConversationMember

from rest_framework.response import Response
from rest_framework.status import (
    HTTP_201_CREATED,
    HTTP_406_NOT_ACCEPTABLE,
    HTTP_200_OK,
    HTTP_403_FORBIDDEN,
)

from django.shortcuts import get_object_or_404

from django.utils import timezone


class PrivateConversationCreateView(CreateAPIView):

    serializer_class = ConversationPrivateCreateSerializer

    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        creator = self.request.user
        user = serializer.validated_data["username"]
        conversation = Conversation.objects.create(type=Conversation.Type.PRIVATE)
        ConversationMember.objects.create(
            conversation=conversation, user=user, role=ConversationMember.Role.MEMBER
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

            conversation.title = serializer.validated_data["title"]
            conversation.description = serializer.validated_data["description"]
            conversation.profile_picture = serializer.validated_data["profile_picture"]
            conversation.save()

            return Response(
                {"message": "Successfully updated."},
                status=HTTP_200_OK,
            )

    def perform_destroy(self, instance):
        # Instead of instance.delete(), we soft delete it.
        instance.deleted_at = timezone.now()
        instance.save()


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
