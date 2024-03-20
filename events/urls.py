from . import views
from django.urls import path

urlpatterns = [
    path("create_event/", views.EventCreateAPIView.as_view(), name="create_an_event"),
    path("list_events/", views.EventListAPIView.as_view(), name="list_events"),
    path(
        "list_events_public/",
        views.EventListPublicAPIView.as_view(),
        name="list_events_public",
    ),
]
