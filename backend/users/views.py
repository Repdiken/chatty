from rest_framework import status
from rest_framework.response import Response
from rest_framework.generics import (
    RetrieveUpdateAPIView,
    CreateAPIView,
    UpdateAPIView,
)
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from .models import User, OTP
from .services import request_otp, verify_otp, OTPError
from .serializers import (
    LoginSerializer,
    RegisterSerializer,
    UserDetailSerializer,
    PhoneNumberChangeSerializer,
    SetUsernameSerializer,
    SetPasswordSerializer,
    ChangePasswordSerializer,
    CheckPasswordSerializer,
    Remove2FAPasswordSerializer,
)

from .jwt import CustomTokenObtainPairSerializer


class RegisterGetOTPAPIView(CreateAPIView):
    permission_classes = [AllowAny]
    serializer_class = RegisterSerializer

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        phone_number = serializer.validated_data["phone_number"]

        try:
            otp = request_otp(phone_number, is_login=False)
            return Response(
                {"message": f"The OTP for {phone_number} is {otp}"},
                status=status.HTTP_200_OK,
            )
        except OTPError as e:
            return Response({"message": e.message}, status=e.status_code)


class RegisterCreateAccountGetTokenAPIView(CreateAPIView):
    permission_classes = [AllowAny]
    serializer_class = LoginSerializer

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        phone_number = serializer.validated_data["phone_number"]
        otp = serializer.validated_data["otp"]

        if User.objects.filter(phone_number=phone_number).exists():
            return Response(
                {"message": "User already exists."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            verify_otp(phone_number, otp)
            user = User.objects.create(phone_number=phone_number)
            user.set_unusable_password()
            user.save()
            token = CustomTokenObtainPairSerializer.get_token(user)
            token["token_version"] = user.token_version
            return Response(
                {
                    "access": str(token.access_token),
                    "refresh": str(token),
                },
                status=status.HTTP_200_OK,
            )
        except OTPError as e:
            return Response({"message": e.message}, status=e.status_code)


class LoginGetOTPAPIView(CreateAPIView):
    permission_classes = [AllowAny]
    serializer_class = RegisterSerializer

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        phone_number = serializer.validated_data["phone_number"]

        try:
            otp = request_otp(phone_number, is_login=True)
            return Response(
                {"message": f"The OTP for {phone_number} is {otp}"},
                status=status.HTTP_200_OK,
            )
        except OTPError as e:
            return Response({"message": e.message}, status=e.status_code)


class LoginGetTokenAPIView(CreateAPIView):
    permission_classes = [AllowAny]
    serializer_class = LoginSerializer

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        phone_number = serializer.validated_data["phone_number"]
        otp = serializer.validated_data["otp"]

        if not User.objects.filter(phone_number=phone_number).exists():
            return Response(
                {"message": "No account found with this phone number."},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            verify_otp(phone_number, otp)
            user = User.objects.get(phone_number=phone_number)
            if user.two_factor_enabled == False:
                token = CustomTokenObtainPairSerializer.get_token(user)
                return Response(
                    {
                        "access": str(token.access_token),
                        "refresh": str(token),
                    },
                    status=status.HTTP_200_OK,
                )
            else:
                return Response({"message": "OTP verified."}, status=status.HTTP_200_OK)
        except OTPError as e:
            return Response({"message": e.message}, status=e.status_code)


class LoginCheckPasswordAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = CheckPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data["user"]
        otp = serializer.validated_data["otp"]

        otp.delete()

        token = CustomTokenObtainPairSerializer.get_token(user)

        return Response(
            {
                "access": str(token.access_token),
                "refresh": str(token),
            },
            status=status.HTTP_200_OK,
        )


class CompleteProfieAPIView(RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserDetailSerializer

    def get_object(self):
        return self.request.user


class PhoneNumberChangeGetOTPAPIVIEW(RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PhoneNumberChangeSerializer

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        phone_number = self.request.data["phone_number"]

        try:
            otp = request_otp(phone_number, is_login=False)
            return Response(
                {"message": f"The OTP for {phone_number} is {otp}"},
                status=status.HTTP_200_OK,
            )
        except OTPError as e:
            return Response({"message": e.message}, status=e.status_code)


class PhoneNumberChangeGetTokenAPIVIEW(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        phone_number = serializer.validated_data["phone_number"]
        otp = serializer.validated_data["otp"]
        user = request.user

        if User.objects.filter(phone_number=phone_number).exists():
            return Response(
                {"message": "An account with this phone number already exists."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            verify_otp(phone_number, otp)

            user.phone_number = phone_number
            user.token_version += 1
            user.save()

            token = CustomTokenObtainPairSerializer.get_token(user)
            token["token_version"] = user.token_version
            return Response(
                {
                    "access": str(token.access_token),
                    "refresh": str(token),
                },
                status=status.HTTP_200_OK,
            )
        except OTPError as e:
            return Response({"message": e.message}, status=e.status_code)


class SetUsernameAPIView(RetrieveUpdateAPIView):

    serializer_class = SetUsernameSerializer

    def get_object(self):
        return self.request.user


class SetPasswordAPIView(UpdateAPIView):
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user

    def get_serializer_class(self):
        # Choose the serializer based on if they already have a password
        if self.request.user.has_usable_password():
            return ChangePasswordSerializer
        return SetPasswordSerializer

    def update(self, request, *args, **kwargs):
        user = self.get_object()
        # You need to pass the request into the context whenever your serializer
        # needs to make decisions based on the current user or the server state
        # self.get_serializer() automatically calls get_serializer_class()
        # & it automatically passes context={'request': request}
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Apply the correct password field based on their state
        if user.has_usable_password():
            user.set_password(serializer.validated_data["new_password"])
        else:
            user.set_password(serializer.validated_data["password"])

        # Invalidate old tokens
        user.token_version += 1
        user.two_factor_enabled = True
        user.save()

        token = CustomTokenObtainPairSerializer.get_token(user)

        return Response(
            {
                "message": "Password updated successfully.",
                "access": str(token.access_token),
                "refresh": str(token),
            },
            status=status.HTTP_200_OK,
        )


class Remove2FAPasswordAPIView(UpdateAPIView):
    serializer_class = Remove2FAPasswordSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        user = self.get_object()

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user.two_factor_enabled = False
        user.set_unusable_password()
        user.token_version += 1
        user.save()

        token = CustomTokenObtainPairSerializer.get_token(user)
        return Response(
            {
                "message": "2FA disabled successfully.",
                "access": str(token.access_token),
                "refresh": str(token),
            },
            status=status.HTTP_200_OK,
        )
