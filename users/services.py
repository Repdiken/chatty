import secrets
from datetime import timedelta

from django.contrib.auth.hashers import make_password, check_password
from django.utils import timezone

from .models import OTP, User


class OTPError(Exception):
    """Custom exception for OTP validation errors to pass messages and status codes to the view."""

    def __init__(self, message, status_code):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


def generate_otp() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def hash_otp(otp: str) -> str:
    return make_password(otp)


def request_otp(phone_number: str, is_login: bool = False) -> str:
    """
    Handles the logic for generating and requesting an OTP.
    """
    now = timezone.now()
    user_exists = User.objects.filter(phone_number=phone_number).exists()

    # Pre-checks based on whether this is a login or registration attempt
    if is_login and not user_exists:
        raise OTPError("No account found with this phone number.", 404)
    if not is_login and user_exists:
        raise OTPError("An account with this phone number already exists.", 400)

    current_otp = OTP.objects.filter(phone_number=phone_number).first()

    # Check if an OTP was generated recently or not
    if current_otp and current_otp.last_sent_at:
        if now < current_otp.last_sent_at + timedelta(minutes=2):
            raise OTPError(
                "An OTP was generated recently. Use that or wait a bit before asking for a new one.",
                403,
            )

    # Handle lockout state
    if current_otp and current_otp.locked_until:
        if current_otp.locked_until > now:
            raise OTPError("Too many attempts! Try again later.", 403)
        else:
            current_otp.locked_until = None
            current_otp.attempts = 0
            current_otp.save()

    otp = generate_otp()

    # Preserve attempts if not locked out, or reset if fresh request
    OTP.objects.update_or_create(
        phone_number=phone_number,
        defaults={
            "code_hash": hash_otp(otp),
            "expires_at": now + timedelta(minutes=3),
            "last_sent_at": now,
        },
    )

    return otp


def verify_otp(phone_number: str, otp: str) -> bool:
    """
    Verifies the OTP for a given phone number.
    Handles expirations, validations, and lockout penalties.
    """
    now = timezone.now()
    current_otp = OTP.objects.filter(phone_number=phone_number).first()

    if current_otp is None:
        raise OTPError("No OTP found for this phone number.", 404)

    # Check lockout duration
    if current_otp.locked_until:
        if current_otp.locked_until > now:
            raise OTPError("Too many attempts! Try again later.", 403)
        else:
            current_otp.locked_until = None
            current_otp.attempts = 0
            current_otp.save()

    if current_otp.expires_at < now:
        current_otp.delete()
        raise OTPError(f"The OTP for {phone_number} has expired.", 400)

    if check_password(otp, current_otp.code_hash):
        user = User.objects.filter(phone_number=phone_number).first()

        # If the user exists and has 2FA enabled, keep the OTP for the next step
        if user and user.two_factor_enabled:
            current_otp.is_verified = True
            current_otp.save()
        else:
            # Otherwise (registration or standard login), clean it up
            current_otp.delete()

        return True

    # Penalty for wrong OTP
    current_otp.attempts += 1
    if current_otp.attempts >= 3:
        current_otp.locked_until = now + timedelta(minutes=30)
        current_otp.save()
        raise OTPError("Too many attempts! Try again in 30 minutes.", 403)

    current_otp.save()
    raise OTPError("Invalid OTP.", 400)
