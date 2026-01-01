from django.urls import path
from game.consumers import MatchConsumer

websocket_urlpatterns = [
    path("ws/match/<uuid:match_id>/", MatchConsumer.as_asgi()),
]
