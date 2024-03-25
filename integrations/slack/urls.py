from django.urls import path
from . import views

urlpatterns = [
    path(
        "",
        views.SlackIntegrationAPIView.as_view(),
        name="slack_integration",
    )
]
