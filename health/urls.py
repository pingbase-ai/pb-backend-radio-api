from django.urls import path
from . import views

from .views import HealthCheckView  # Import the HealthCheckView class

urlpatterns = [
    path(
        "ping", HealthCheckView.as_view(), name="health-check"
    ),  # Use HealthCheckView as the view argument
]
