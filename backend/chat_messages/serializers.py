from rest_framework import serializers
from .models import Attachment, Message


class SendAttachmentSerializer(serializers.ModelSerializer):

    class Meta:
        model = Attachment
        fields = ["file", "attachment_type", "mime_type", "file_size"]
        read_only_fields = ["mime_type", "file_size"]

    def validate_file(self, value):
        # 1 GB calculated in bytes (1024 * 1024 * 1024)
        max_size = 1073741824

        if value.size > max_size:
            raise serializers.ValidationError("File size cannot exceed 1 GB.")
        return value


class SendMessageSerializer(serializers.ModelSerializer):
    attachments = SendAttachmentSerializer(many=True, read_only=True)
    files = serializers.ListField(
        child=serializers.FileField(), write_only=True, required=False
    )

    class Meta:
        model = Message
        fields = ["id", "text", "attachments", "files", "sender", "created_at"]

        # so Django knows NOT to ask the frontend for these
        read_only_fields = ["sender", "created_at"]


class EditMessageSerializer(serializers.ModelSerializer):
    model = Message
    fields = ["text"]
