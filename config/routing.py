# config/routing.py
from django.urls import re_path
from game.consumers import MatchConsumer

websocket_urlpatterns = [
    # UUID estándar (8-4-4-4-12) en hex
    re_path(
        r"^ws/match/(?P<match_id>[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})/$",
        MatchConsumer.as_asgi(),
    ),
]
