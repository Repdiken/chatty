from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator


class User(AbstractUser):
    profile_picture = models.ImageField(upload_to="pfp", blank=True, null=True)
    phone_number = models.CharField(max_length=20, unique=True)
    bio = models.TextField(blank=True)

    username_validator = RegexValidator(
        regex=r"^[a-zA-Z0-9_]{3,30}$",
        message="Username must be 3-30 characters and contain only letters, numbers, and underscores.",
    )

    username = models.CharField(
        max_length=30,
        unique=True,
        validators=[username_validator],
        blank=True,
        null=True,
    )

    two_factor_enabled = models.BooleanField(default=False)

    token_version = models.PositiveIntegerField(default=0)

    is_online = models.BooleanField(default=False)
    last_seen_at = models.DateTimeField(null=True, blank=True)

    deleted_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.username or f"User {self.pk}"


class OTP(models.Model):
    phone_number = models.CharField(max_length=20, unique=True)

    code_hash = models.CharField(max_length=255)

    attempts = models.PositiveSmallIntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)

    last_sent_at = models.DateTimeField(null=True, blank=True)

    expires_at = models.DateTimeField()

    created_at = models.DateTimeField(auto_now_add=True)

    is_verified = models.BooleanField(default=False)
