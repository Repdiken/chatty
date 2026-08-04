from rest_framework import status
from rest_framework.response import Response
from rest_framework.generics import RetrieveUpdateAPIView, CreateAPIView
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from .models import User
from .services import request_otp, verify_otp, OTPError
from .serializers import (
    LoginSerializer,
    RegisterSerializer,
    UserDetailSerializer,
    PhoneNumberChangeSerializer,
    SetUsernameSerializer,
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
            user = User.objects.create(
                phone_number=phone_number,
            )
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
            token = CustomTokenObtainPairSerializer.get_token(user)
            return Response(
                {
                    "access": str(token.access_token),
                    "refresh": str(token),
                },
                status=status.HTTP_200_OK,
            )
        except OTPError as e:
            return Response({"message": e.message}, status=e.status_code)


class CompleteProfieAPIView(RetrieveUpdateAPIView):
    permission_classes = [AllowAny]
    serializer_class = UserDetailSerializer

    def get_object(self):
        return self.request.user


class PhoneNumberChangeGetOTPAPIVIEW(RetrieveUpdateAPIView):
    permission_classes = [AllowAny]
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
