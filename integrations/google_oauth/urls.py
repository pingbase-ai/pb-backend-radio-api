from django.urls import path
from . import views


urlpatterns = [
    path("", views.GoogleCalendarViewInit.as_view(), name="google_permission"),
    path(
        "redirect", views.GoogleCalendarViewRedirect.as_view(), name="google_redirect"
    ),
    path("events", views.GoogleCalendarEventsView.as_view(), name="google_events"),
]
