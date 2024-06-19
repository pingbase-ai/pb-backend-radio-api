"""
ASGI config for master_mind project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/asgi/
"""

import os

from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application
from channels.auth import AuthMiddlewareStack
from channels.security.websocket import AllowedHostsOriginValidator

import websocket.routing
from websocket.middleware import TokenAuthMiddlewareStack

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "master_mind.settings")

application = ProtocolTypeRouter(
    {
        "http": get_asgi_application(),
        "websocket": AllowedHostsOriginValidator(
            TokenAuthMiddlewareStack(URLRouter(websocket.routing.websocket_urlpatterns))
        ),
    }
)
