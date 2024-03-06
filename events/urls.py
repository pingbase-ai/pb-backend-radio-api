from . import views
from django.urls import path

urlpatterns = [
    path("create_event/", views.EventCreateAPIView.as_view(), name="create_an_event"),
]
