from . import views
from django.urls import path
from rest_framework_simplejwt.views import (
    TokenRefreshView,
)

urlpatterns = [
    path("", views.APIRootView.as_view(), name="api-main"),
    # being used
    path("signup/<slug:type>", views.SignUpView.as_view(), name="signup"),
    path(
        "invite_teamate/<slug:type>",
        views.InviteTeamateView.as_view(),
        name="invite_teamate",
    ),
    path("verify-email/", views.EmailVerificationView.as_view(), name="verify-email"),
    path(
        "resend-verification-email/",
        views.ResendVerificationEmailView.as_view(),
        name="resend-verification-email",
    ),
    path("login/", views.LoginView.as_view(), name="login"),
    path("refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path(
        "request-password-reset-email/",
        views.RequestPasswordResetEmailView.as_view(),
        name="request-password-reset-email",
    ),
    path(
        "password-reset/<uidb64>/<token>/",
        views.PasswordResetTokenValidationView.as_view(),
        name="password-reset-confirm",
    ),
    path("password-reset/", views.SetNewPasswordView.as_view(), name="password-reset"),
    path(
        "reset-password-adhoc/",
        views.ResetPasswordAdhocView.as_view(),
        name="reset-password-adhoc",
    ),
    path("logout/", views.LogoutView.as_view(), name="logout"),
    path(
        "onboarding/<slug:type>/",
        views.OnboardingView.as_view(),
        name="onboarding",
    ),
    path(
        "onboarding_data/<slug:type>/",
        views.OnboardingDataView.as_view(),
        name="onboarding_data",
    ),
    path(
        "profile/<slug:type>/",
        views.ProfileView.as_view(),
        name="profile",
    ),
    path(
        "end-users/<slug:search>/",
        views.EndUserList.as_view(),
        name="end-user-list",
    ),
    # not completely done
    path("register/", views.RegistrationView.as_view(), name="register"),
    path("register-team/", views.TeamRegistrationView.as_view(), name="register-team"),
    path("register-enduser/", views.CreateEndUserView.as_view(), name="create-enduser"),
    # path(
    #     "register-customer/",
    #     views.CustomerRegistrationView.as_view(),
    #     name="register-cusomter",
    # ),
    path("users/", views.UserList.as_view(), name="user-list"),
    path("users/<int:pk>/", views.UserDetail.as_view(), name="user-detail"),
]
