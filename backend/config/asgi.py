import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
from django.core.asgi import get_asgi_application
django_application = get_asgi_application()
from django.conf import settings
from django.urls import re_path
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import OriginValidator
from platform_api.messaging import ConversationConsumer

websocket_urlpatterns = [re_path(r"^ws/conversations/(?P<conversation_id>[0-9a-fA-F]{24})/$", ConversationConsumer.as_asgi())]
application = ProtocolTypeRouter({
    "http": django_application,
    "websocket": OriginValidator(URLRouter(websocket_urlpatterns), settings.WEBSOCKET_ALLOWED_ORIGINS),
})
