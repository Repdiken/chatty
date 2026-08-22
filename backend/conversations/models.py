from django.db import models
from users.models import User


class Conversation(models.Model):

    class Type(models.TextChoices):
        PRIVATE = "private", "Private"
        GROUP = "group", "Group"

    type = models.CharField(max_length=8, choices=Type.choices)

    title = models.CharField(max_length=55, blank=True)
    description = models.TextField(blank=True)
    profile_picture = models.ImageField(
        upload_to="conversation_pictures/",
        blank=True,
        null=True,
    )

    deleted_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title or str(self.id)


class ConversationMember(models.Model):
    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE, related_name="members"
    )

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="conversations"
    )

    class Role(models.TextChoices):
        OWNER = "owner", "Owner"
        ADMIN = "admin", "Admin"
        MEMBER = "member", "Member"

    role = models.CharField(
        max_length=7,
        choices=Role.choices,
    )

    joined_at = models.DateTimeField(auto_now_add=True)

    deleted_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        unique_together = ("conversation", "user")
        constraints = [
            models.UniqueConstraint(
                fields=["conversation"],
                condition=models.Q(role="owner"),
                name="one_owner_per_conversation",
            )
        ]

    def __str__(self):
        return f"{self.user} in {self.conversation}"
