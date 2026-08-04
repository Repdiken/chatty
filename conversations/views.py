from rest_framework.generics import CreateAPIView, ListAPIView
from .serializers import (
    ConversationPrivateCreateSerializer,
    ConversationGroupCreateSerializer,
    ConversationListSerializer,
)
from rest_framework.permissions import IsAuthenticated
from .models import Conversation, ConversationMember
from users.models import User
from rest_framework.response import Response
from rest_framework.status import HTTP_201_CREATED


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

        return Response({"message: Conversation created"})


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

    permission_classes = [IsAuthenticated]
    serializer_class = ConversationListSerializer

    def get_queryset(self):
        return Conversation.objects.filter(members__user=self.request.user)
