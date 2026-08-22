from .serializers import SendMessageSerializer
from rest_framework.generics import ListCreateAPIView
from rest_framework.permissions import IsAuthenticated
from .models import Message, Attachment
from conversations.models import Conversation, ConversationMember
from django.shortcuts import get_object_or_404
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from rest_framework.response import Response
from rest_framework.status import HTTP_404_NOT_FOUND


class ListCreateMessageAPIView(ListCreateAPIView):
    serializer_class = SendMessageSerializer
    permission_classes = [IsAuthenticated]

    parser_classes = [MultiPartParser, FormParser, JSONParser]
    lookup_url_kwarg = "conversation_id"

    def get_queryset(self):
        conversation_id = self.kwargs.get("conversation_id")

        # Only return messages if the user is an active member
        is_member = ConversationMember.objects.filter(
            conversation_id=conversation_id,
            user=self.request.user,
            deleted_at__isnull=True,
        ).exists()

        if not is_member:
            return Response(
                {
                    "Error": "No conversation found",
                },
                status=HTTP_404_NOT_FOUND,
            )

        return Message.objects.filter(conversation_id=conversation_id).order_by(
            "created_at"
        )

    def perform_create(self, serializer):
        conversation_id = self.kwargs.get("conversation_id")

        # Verify they are an active member before allowing them to post
        member = get_object_or_404(
            ConversationMember,
            conversation_id=conversation_id,
            user=self.request.user,
            deleted_at__isnull=True,
        )

        message = serializer.save(
            sender=self.request.user, conversation_id=conversation_id
        )

        # Handle File Uploads (Optimized with bulk_create)
        uploaded_files = self.request.FILES.getlist("files")
        attachments_to_create = []

        for file in uploaded_files:
            mime_type = file.content_type
            attachment_type = Attachment.AttachmentType.DOCUMENT

            if mime_type.startswith("image/"):
                attachment_type = Attachment.AttachmentType.IMAGE
            elif mime_type.startswith("video/"):
                attachment_type = Attachment.AttachmentType.VIDEO
            elif mime_type.startswith("audio/"):
                attachment_type = Attachment.AttachmentType.AUDIO

            attachments_to_create.append(
                Attachment(
                    message=message,
                    file=file,
                    attachment_type=attachment_type,
                    mime_type=mime_type,
                    file_size=file.size,
                )
            )

        if attachments_to_create:
            Attachment.objects.bulk_create(attachments_to_create)

        # Revive the chat for anyone who soft-deleted it
        ConversationMember.objects.filter(
            conversation_id=conversation_id, deleted_at__isnull=False
        ).update(deleted_at=None)

        # Broadcast to WebSockets
        message_data = self.get_serializer(message).data
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"chat_{conversation_id}",
            {
                "type": "chat_message",
                "message": message_data,
            },
        )
