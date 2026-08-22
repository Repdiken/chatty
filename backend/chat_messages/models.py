from django.db import models
from conversations.models import Conversation
from users.models import User


class Message(models.Model):
    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE, related_name="messages"
    )

    sender = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="messages_sent"
    )

    text = models.TextField(blank=True)

    edited_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    deleted_at = models.DateTimeField(blank=True, null=True)


class Attachment(models.Model):

    class AttachmentType(models.TextChoices):
        IMAGE = "image", "Image"
        VIDEO = "video", "Video"
        AUDIO = "audio", "Audio"
        DOCUMENT = "document", "Document"

    message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        related_name="attachments",
    )

    file = models.FileField(upload_to="attachments/")

    attachment_type = models.CharField(
        max_length=8,
        choices=AttachmentType.choices,
    )

    mime_type = models.CharField(max_length=100)  # What kind of file is this?

    file_size = models.BigIntegerField()
