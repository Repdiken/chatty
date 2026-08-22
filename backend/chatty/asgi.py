"""
ASGI config for chatty project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/asgi/
"""

import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import chat_messages.routing

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "chatty.settings")

django_asgi_app = get_asgi_application()

application = ProtocolTypeRouter(
    {
        # Standard HTTP requests go to Django's standard ASGI application
        "http": django_asgi_app,
        # WebSocket requests go through authentication middleware and custom URL routing
        "websocket": AuthMiddlewareStack(
            URLRouter(chat_messages.routing.websocket_urlpatterns)
        ),
    }
)
