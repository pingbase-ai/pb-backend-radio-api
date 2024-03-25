from django.urls import path, include

urlpatterns = [
    path(
        "slack",
        include("integrations.slack.urls"),
    ),
]
