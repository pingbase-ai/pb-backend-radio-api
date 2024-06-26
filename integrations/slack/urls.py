from django.urls import path
from . import views

urlpatterns = [
    path(
        "",
        views.SlackIntegrationAPIView.as_view(),
        name="slack_integration",
    ),
    path("get_status", views.SlackAuthUrlAPIView.as_view(), name="slack_auth_url"),
]
