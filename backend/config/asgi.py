"""
ASGI config for config project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from django.urls import re_path

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

django_application = get_asgi_application()
from platform_api.messaging import ConversationConsumer

websocket_urlpatterns = [
	re_path(r"^ws/conversations/(?P<conversation_id>[0-9a-fA-F]{24})/$", ConversationConsumer.as_asgi()),
]

application = ProtocolTypeRouter({
	"http": django_application,
	"websocket": URLRouter(websocket_urlpatterns),
})
