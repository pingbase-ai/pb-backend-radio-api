from . import views
from django.urls import path

urlpatterns = [
    path("get_meeting", views.DyteMeetingView.as_view(), name="get_meeting_details"),
]
