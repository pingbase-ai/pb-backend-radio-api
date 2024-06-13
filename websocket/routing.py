from django.urls import path, include
from websocket.live_sessions import consumers


websocket_urlpatterns = [
    path(
        "ws/session/enduser/<str:channel_type>/<str:org_id>/<str:enduser_id>/<str:session_id>/",
        consumers.EndUserConsumer.as_asgi(),
    ),
    path(
        "ws/session/client/<str:channel_type>/<str:org_id>/<str:enduser_id>/<str:session_id>/",
        consumers.ClientConsumer.as_asgi(),
    ),
]
