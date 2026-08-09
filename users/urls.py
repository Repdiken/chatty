from django.urls import path
from .views import (
    RegisterGetOTPAPIView,
    RegisterCreateAccountGetTokenAPIView,
    LoginGetOTPAPIView,
    LoginGetTokenAPIView,
    CompleteProfieAPIView,
    PhoneNumberChangeGetOTPAPIVIEW,
    PhoneNumberChangeGetTokenAPIVIEW,
    SetUsernameAPIView,
    SetPasswordAPIView,
    LoginCheckPasswordAPIView,
)

urlpatterns = [
    path("auth/register/request-otp", RegisterGetOTPAPIView.as_view()),
    path("auth/register/verify", RegisterCreateAccountGetTokenAPIView.as_view()),
    path("auth/login/request-otp", LoginGetOTPAPIView.as_view()),
    path("auth/login/verify", LoginGetTokenAPIView.as_view()),
    path("auth/login/2fa", LoginCheckPasswordAPIView.as_view()),
    path("users/me/about/", CompleteProfieAPIView.as_view()),
    path(
        "users/me/about/phone-number-change", PhoneNumberChangeGetOTPAPIVIEW.as_view()
    ),
    path(
        "users/me/about/phone-number-change/verify",
        PhoneNumberChangeGetTokenAPIVIEW.as_view(),
    ),
    path("users/me/about/username-change", SetUsernameAPIView.as_view()),
    path("users/me/security/2fa", SetPasswordAPIView.as_view()),
]
