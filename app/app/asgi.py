import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "app.settings")

from django.core.asgi import get_asgi_application

# This initializes Django and loads apps
django_asgi_app = get_asgi_application()

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator, OriginValidator
from django.conf import settings

from .ws_jwt_auth import CookieJWTAuthMiddlewareStack

websocket_urlpatterns = []

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": AllowedHostsOriginValidator(
            OriginValidator(
                CookieJWTAuthMiddlewareStack(URLRouter(websocket_urlpatterns)),
                getattr(settings, "WS_ALLOWED_ORIGINS", []),
            )
        ),
    }
)
