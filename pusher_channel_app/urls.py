from . import views
from django.urls import path

urlpatterns = [
    path(
        "get_app_details/", views.PusherChannelAppView.as_view(), name="get_app_details"
    ),
    path(
        "get_app_details_with_company_name/",
        views.PusherChannelAppCompanyView.as_view(),
        name="get_app_details_company",
    ),
    path(
        "webhook/",
        views.PusherChannelAppWebhookView.as_view(),
        name="webhook",
    ),
    path(
        "publish_client/",
        views.ClientPusherChannelAppPublishView.as_view(),
        name="publish",
    ),
    path(
        "publish_enduser/",
        views.EndUserPusherChannelPublishView.as_view(),
        name="publish",
    ),
    path("auth/", views.PusherAuth.as_view(), name="pusher_auth"),
    path("user-auth/", views.PusherUserAuth.as_view(), name="pusher_user_auth"),
    path("publish_event/", views.PusherEventPublish.as_view(), name="publish_event"),
    path(
        "client/send_message/", views.ClientSendMessage.as_view(), name="send_message"
    ),
]
