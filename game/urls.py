from django.urls import path
from .views import *

urlpatterns = [
    path("cards/", CardsView.as_view(), name="cards"),
    path("matches/", MyMatchesView.as_view(), name="my_matches"),

    path("queue/join/", queue_join, name="queue_join"),
    path("queue/leave/", queue_leave, name="queue_leave"),
    path("queue/status/", queue_status, name="queue_status"),

    path("match/<uuid:match_id>/hand/", match_hand, name="match_hand"),

    path("inventory/", MyInventoryView.as_view(), name="my_inventory"),
    path("deck/", MyDeckView.as_view(), name="my_deck"),
    path("deck/set-active/", SetActiveDeckView.as_view(), name="set_active_deck"),
]
