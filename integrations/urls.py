from django.urls import path, include

urlpatterns = [
    path(
        "slack/",
        include("integrations.slack.urls"),
    ),
    path("google/", include("integrations.google_oauth.urls")),
    path("outlook/", include("integrations.outlook.urls")),
    path("cal/", include("integrations.caldotcom.urls")),
]
