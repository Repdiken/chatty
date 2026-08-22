from rest_framework import serializers
import phonenumbers
from .models import User, OTP
from django.contrib.auth.password_validation import validate_password
from django.utils import timezone


def normalize_phone_number(value):
    try:
        number = phonenumbers.parse(value, None)
    except phonenumbers.NumberParseException:
        raise serializers.ValidationError("Invalid phone number.")

    if not phonenumbers.is_valid_number(number):
        raise serializers.ValidationError("Invalid phone number.")

    return phonenumbers.format_number(
        number,
        phonenumbers.PhoneNumberFormat.E164,
    )


class RegisterSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=20)

    def validate_phone_number(self, value):
        return normalize_phone_number(value=value)


class LoginSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=20)
    otp = serializers.CharField(min_length=6, max_length=6)

    def validate_phone_number(self, value):
        return normalize_phone_number(value=value)

    def validate_otp(self, value):
        if not value.isdigit():
            raise serializers.ValidationError("OTP must contain only digits.")

        return value


class UserDetailSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = [
            "id",
            "profile_picture",
            "first_name",
            "last_name",
            "phone_number",
            "username",
            "bio",
        ]

        read_only_fields = ["phone_number", "username"]


class PhoneNumberChangeSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = ["phone_number"]

    def validate_phone_number(self, value):
        return normalize_phone_number(value=value)


class SetUsernameSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["username"]


class SetPasswordSerializer(serializers.Serializer):
    password = serializers.CharField(write_only=True)
    password_2 = serializers.CharField(write_only=True)

    def validate(self, attrs):
        if attrs["password"] != attrs["password_2"]:
            raise serializers.ValidationError({"password_2": "Passwords do not match."})

        # Django's built-in validator checks length, common passwords, etc.
        validate_password(attrs["password"])
        return attrs


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)
    new_password_2 = serializers.CharField(write_only=True)

    def validate_current_password(self, value):
        # Grab the user making the request
        user = self.context["request"].user

        # Verify the hash matches
        if not user.check_password(value):
            raise serializers.ValidationError("Incorrect current password.")
        return value

    def validate(self, attrs):
        if attrs["new_password"] != attrs["new_password_2"]:
            raise serializers.ValidationError(
                {"new_password_2": "New passwords do not match."}
            )

        validate_password(attrs["new_password"])
        return attrs


class CheckPasswordSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=20)
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        phone_number = attrs["phone_number"]
        password = attrs["password"]

        user = User.objects.filter(phone_number=phone_number).first()
        otp = OTP.objects.filter(phone_number=phone_number).first()

        if not user:
            raise serializers.ValidationError({"phone_number": "User does not exist."})

        if not otp:
            raise serializers.ValidationError(
                {"phone_number": "No active OTP session found."}
            )

        if not otp.is_verified:
            raise serializers.ValidationError(
                {"phone_number": "OTP is not verified yet."}
            )

        if not user.check_password(password):
            raise serializers.ValidationError({"password": "Incorrect password."})

        if otp.expires_at < timezone.now():
            otp.delete()
            raise serializers.ValidationError(
                {"phone_number": "This 2FA session has expired."}
            )

        attrs["user"] = user
        attrs["otp"] = otp
        return attrs


class Remove2FAPasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        user = self.context["request"].user
        current_password = attrs["current_password"]

        if user.two_factor_enabled == False:
            raise serializers.ValidationError(
                {"current_password": "You don't have an active 2FA."}
            )

        if not user.check_password(current_password):
            raise serializers.ValidationError(
                {"current_password": "Incorrect password."}
            )

        return attrs
