from django.urls import path
from . import views


urlpatterns = [
    path("", views.OutlookCalendarViewInit.as_view(), name="outlook_permission"),
    path(
        "redirect", views.OutlookCalendarViewRedirect.as_view(), name="google_redirect"
    ),
    # path("events", views.GoogleCalendarEventsView.as_view(), name="google_events"),
]
