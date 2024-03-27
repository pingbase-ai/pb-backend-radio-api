from django.urls import path, include

urlpatterns = [
    path(
        "slack/",
        include("integrations.slack.urls"),
    ),
    path("google/", include("integrations.google_oauth.urls")),
]
