import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack

# 1) Primero inicializa Django (carga apps)
django_asgi_app = get_asgi_application()

# 2) Recién después importa routing (que importa consumers)
import config.routing

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": AuthMiddlewareStack(
            URLRouter(config.routing.websocket_urlpatterns)
        ),
    }
)
