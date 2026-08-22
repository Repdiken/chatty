import pytest
from datetime import timedelta
from django.utils import timezone
from rest_framework.test import APIClient
from users.models import User, OTP
from freezegun import freeze_time

# Marks all tests in this file to allow database access
pytestmark = pytest.mark.django_db

@pytest.fixture
def client():
    # This forces every test to send raw JSON by default
    client = APIClient()
    client.defaults['HTTP_ACCEPT'] = 'application/json'
    client.defaults['CONTENT_TYPE'] = 'application/json'
    return client

# intercepts the generate_otp function whenever it is called during the test and forces it to always return "123456"
@pytest.fixture
def mock_otp(mocker):
    """Mocks the OTP generator so we always know the OTP is '123456' during tests."""
    return mocker.patch('users.services.generate_otp', return_value='123456')

@pytest.fixture
def test_user():
    """Creates a standard verified user."""
    user = User.objects.create(phone_number="+905540565213")
    user.set_unusable_password()
    user.save()
    return user

@pytest.fixture
def two_factor_user():
    """Creates a user with 2FA enabled and a known password."""
    user = User.objects.create(phone_number="+905325201370", two_factor_enabled=True)
    user.set_password("SecurePass123!")
    user.save()
    return user

# --- TESTS ---

class TestRegistrationAndLoginFlows:
    def test_existing_phone_number_cannot_register(self, client, test_user):
        """Check that if a phone number already exists, they cannot hit the register endpoint."""
        response = client.post("/auth/register/request-otp", {"phone_number": test_user.phone_number})
        assert response.status_code == 400
        assert "already exists" in response.data["message"]

    def test_otp_generation_two_minute_cooldown(self, client):
        """Check that a user cannot receive a new OTP until 2 minutes have passed."""
        phone = "+905340585483"
        
        # 1st Request - Success
        response = client.post("/auth/register/request-otp", {"phone_number": phone})
        assert response.status_code == 200

        # 2nd Request immediately - Fails
        response = client.post("/auth/register/request-otp", {"phone_number": phone})
        assert response.status_code == 403

        # 3rd Request after 2 minutes - Success
        with freeze_time(timezone.now() + timedelta(minutes=2, seconds=1)):
            response = client.post("/auth/register/request-otp", {"phone_number": phone})
            assert response.status_code == 200

    def test_otp_lockout_after_three_incorrect_attempts(self, client, mock_otp):
        """Check that if the OTP is used incorrectly 3 times, they are locked out."""
        phone = "+905540565213"
        client.post("/auth/register/request-otp", {"phone_number": phone})

        # Fail 1
        res1 = client.post("/auth/register/verify", {"phone_number": phone, "otp": "000000"})
        assert res1.status_code == 400

        # Fail 2
        res2 = client.post("/auth/register/verify", {"phone_number": phone, "otp": "000000"})
        assert res2.status_code == 400

        # Fail 3 - Triggers lockout
        res3 = client.post("/auth/register/verify", {"phone_number": phone, "otp": "000000"})
        assert res3.status_code == 403
        assert "30 minutes" in res3.data["message"]

        # Fail 4 - Blocked entirely
        res4 = client.post("/auth/register/verify", {"phone_number": phone, "otp": "123456"}) # Even with correct OTP
        assert res4.status_code == 403

    def test_spamming_requests_blocked_by_custom_logic(self, client):
        """Check that a user can't send thousands of requests (custom rate limiting verification)."""
        phone = "+905540565213"
        # Hit request-otp 5 times rapidly
        responses = [client.post("/auth/register/request-otp", {"phone_number": phone}) for _ in range(5)]
        
        assert responses[0].status_code == 200 # First succeeds
        for res in responses[1:]:
            assert res.status_code == 403 # The rest are blocked by the 2-minute timer

    def test_verification_fails_without_active_otp(self, client):
        """Check that when a user doesn't have an active OTP, they get an error for verification."""
        response = client.post("/auth/register/verify", {"phone_number": "+905540565213", "otp": "123456"})
        assert response.status_code == 404

    def test_expired_otp_cannot_be_verified(self, client, mock_otp):
        """Check that the user cannot verify an expired OTP."""
        phone = "+905540565213"
        client.post("/auth/register/request-otp", {"phone_number": phone})

        # Fast-forward 4 minutes (past the 3-minute expiration)
        with freeze_time(timezone.now() + timedelta(minutes=4)):
            response = client.post("/auth/register/verify", {"phone_number": phone, "otp": "123456"})
            assert response.status_code == 400
            assert "expired" in response.data["message"]

    def test_otp_remains_verified_for_2fa_enabled_user(self, client, mock_otp, two_factor_user):
        """Check that the OTP won't get removed after verification for a user who has 2FA enabled."""
        client.post("/auth/login/request-otp", {"phone_number": two_factor_user.phone_number})
        
        response = client.post("/auth/login/verify", {"phone_number": two_factor_user.phone_number, "otp": "123456"}, format="json")
        print(response.data)
        assert response.status_code == 200
        
        otp_record = OTP.objects.get(phone_number=two_factor_user.phone_number)
        assert otp_record.is_verified is True # It stayed in DB and updated state

    def test_otp_deleted_after_standard_login(self, client, mock_otp, test_user):
        """Check that the OTP expires (is removed) after verifying and receiving Token (No 2FA)."""
        client.post("/auth/login/request-otp", {"phone_number": test_user.phone_number})
        
        response = client.post("/auth/login/verify", {"phone_number": test_user.phone_number, "otp": "123456"})
        assert response.status_code == 200
        assert "access" in response.data
        
        assert not OTP.objects.filter(phone_number=test_user.phone_number).exists()

    def test_otp_deleted_after_full_2fa_login(self, client, mock_otp, two_factor_user):
        """Check that the OTP expires after verifying the 2FA password and receiving a Token."""
        # 1. Generate & Verify OTP
        client.post("/auth/login/request-otp", {"phone_number": two_factor_user.phone_number})
        client.post("/auth/login/verify", {"phone_number": two_factor_user.phone_number, "otp": "123456"})
        
        # 2. Complete 2FA
        response = client.post("/auth/login/2fa", {
            "phone_number": two_factor_user.phone_number, 
            "password": "SecurePass123!"
        })
        
        assert response.status_code == 200
        assert "access" in response.data
        assert not OTP.objects.filter(phone_number=two_factor_user.phone_number).exists() # Deleted

    def test_locked_user_cannot_generate_otp_until_30_minutes(self, client, mock_otp):
        """Check that a user cannot generate OTP when locked, but can after 30 mins."""
        phone = "+905540565213"
        client.post("/auth/register/request-otp", {"phone_number": phone})

        # Fail 3 times to trigger lockout
        for _ in range(3):
            client.post("/auth/register/verify", {"phone_number": phone, "otp": "000000"})
        
        # Attempt to request new OTP while locked
        res_locked = client.post("/auth/register/request-otp", {"phone_number": phone})
        assert res_locked.status_code == 403

        # Fast forward 31 minutes
        with freeze_time(timezone.now() + timedelta(minutes=31)):
            res_unlocked = client.post("/auth/register/request-otp", {"phone_number": phone})
            assert res_unlocked.status_code == 200

    def test_cannot_verify_2fa_without_active_otp(self, client, two_factor_user):
        """Check that the user can't verify their 2FA password if they don't have an active OTP."""
        response = client.post("/auth/login/2fa", {
            "phone_number": two_factor_user.phone_number, 
            "password": "SecurePass123!"
        })
        assert response.status_code == 400
        assert "No active OTP" in str(response.data)

    def test_2fa_rejected_if_otp_not_verified(self, client, mock_otp, two_factor_user):
        """Attempt to hit LoginCheckPasswordAPIView without first verifying the OTP."""
        client.post("/auth/login/request-otp", {"phone_number": two_factor_user.phone_number})
        
        # Hit 2FA before hitting /auth/login/verify
        response = client.post("/auth/login/2fa", {
            "phone_number": two_factor_user.phone_number, 
            "password": "SecurePass123!"
        })
        
        assert response.status_code == 400
        assert "OTP is not verified" in str(response.data)

    def test_2fa_rejected_if_otp_expired(self, client, mock_otp, two_factor_user):
        """Check that the user cannot complete 2FA if they take too long after verifying the OTP."""
        # 1. Use the login endpoints!
        client.post("/auth/login/request-otp", {"phone_number": two_factor_user.phone_number}, format="json")
        client.post("/auth/login/verify", {"phone_number": two_factor_user.phone_number, "otp": "123456"}, format="json")

        # 2. Fast forward 5 minutes
        with freeze_time(timezone.now() + timedelta(minutes=5)):
            
            # 3. Use the raw password, not the hash, and add the leading slash
            response = client.post("/auth/login/2fa", {
                "phone_number": two_factor_user.phone_number,
                "password": "SecurePass123!" 
            }, format="json")

            assert response.status_code == 400
            assert "expired" in str(response.data)

class TestInputValidationAndSecurity:
    @pytest.mark.parametrize("bad_phone", ["abc", "+123", "+120255501999999999", "555-5555"])
    def test_invalid_phone_numbers_rejected(self, client, bad_phone):
        """Check that requests with letters, missing country codes, or impossible lengths are rejected."""
        response = client.post("/auth/register/request-otp", {"phone_number": bad_phone})
        assert response.status_code == 400
        assert "Invalid phone number" in str(response.data)

    def test_unregistered_phone_rejected_on_login(self, client):
        """Check that hitting LoginGetOTPAPIView with an unregistered phone number throws 404."""
        response = client.post("/auth/login/request-otp", {"phone_number": "+905350000000"})
        assert response.status_code == 404

    @pytest.mark.parametrize("bad_username", ["space name", "user@name", "hi", "this_username_is_way_too_long_for_the_regex"])
    def test_set_username_validation(self, client, test_user, bad_username):
        """Check that SetUsernameAPIView rejects spaces, special characters, and wrong lengths."""
        client.force_authenticate(user=test_user)
        response = client.put("/users/me/about/username-change", {"username": bad_username})
        
        assert response.status_code == 400
        assert "username" in response.data

    def test_token_invalidation_after_password_change(self, client, test_user):
        """Test logging in, changing the password, and then trying to use the old token."""
        # 1. VIP Pass granted to change the password easily
        client.force_authenticate(user=test_user)
        
        res_pw = client.put("/users/me/security/2fa", {
            "password": "NewStrongPassword123!",
            "password_2": "NewStrongPassword123!"
        })
        assert res_pw.status_code == 200
        
        # 2. Simulate the old token
        from users.jwt import CustomTokenObtainPairSerializer
        test_user.token_version = 0  
        old_token = CustomTokenObtainPairSerializer.get_token(test_user).access_token
        
        # 3. CRITICAL FIX: Revoke the VIP pass so DRF is forced to evaluate the token!
        client.force_authenticate(user=None)
        
        # 4. Try to access protected endpoint with the old token
        client.credentials(HTTP_AUTHORIZATION=f'JWT {old_token}')
        res_protected = client.get("/users/me/about/")
        
        # Now CustomJWTAuthentication will actually run, see the version mismatch, and reject it!
        assert res_protected.status_code == 401
        assert "no longer valid" in str(res_protected.data)

    def test_password_mismatch_validation(self, client, test_user):
        """Check that submitting different values for password and password_2 correctly triggers an error."""
        client.force_authenticate(user=test_user)
        
        response = client.put("/users/me/security/2fa", {
            "password": "Password123!",
            "password_2": "Password456!"
        })
        
        assert response.status_code == 400
        assert "Passwords do not match" in str(response.data)

    def test_remove_password(self, client, two_factor_user):
        """Test successfully removing 2FA with the correct password."""
        
        client.force_authenticate(user=two_factor_user)

        response = client.put("/users/me/security/2fa/remove", {
            "current_password": "SecurePass123!" 
        }, format="json")

        assert response.status_code == 200
        assert "disabled successfully" in str(response.data)
        
        assert "access" in response.data
        assert "refresh" in response.data

    def test_remove_2fa_fails_with_incorrect_password(self, client, two_factor_user):
        """Check that providing the wrong password blocks the removal of 2FA."""
        client.force_authenticate(user=two_factor_user)

        response = client.put("/users/me/security/2fa/remove", {
            "current_password": "TotallyWrongPassword99!" 
        }, format="json")

        assert response.status_code == 400
        assert "Incorrect password" in str(response.data)


    def test_remove_2fa_fails_if_already_disabled(self, client, test_user):
        """Check that a user without 2FA cannot hit the remove endpoint."""

        client.force_authenticate(user=test_user)

        response = client.put("/users/me/security/2fa/remove", {
            "current_password": "DoesNotMatter123!" 
        }, format="json")

        assert response.status_code == 400
        assert "active 2FA" in str(response.data)


