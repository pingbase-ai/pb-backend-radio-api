from . import views
from django.urls import path

urlpatterns = [
    path("get_meeting", views.DyteMeetingView.as_view(), name="get_meeting_details"),
    path("get_auth_token", views.DyteAuthTokenView.as_view(), name="get_auth_token"),
    path(
        "get_auth_token_public",
        views.DytePublicAuthTokenView.as_view(),
        name="get_public_auth_token",
    ),
    path("webhook", views.DyteWebhookView.as_view(), name="webhook"),
]
