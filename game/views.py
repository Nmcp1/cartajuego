from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_http_methods

from .models import (
    CardCharacter, CardTrap, Match, MatchQueue, MatchStatus,
    UserCharacterCard, UserTrapCard,
    Deck, DeckCharacter, DeckTrap,
)
from .serializers import (
    CardCharacterSerializer, CardTrapSerializer, MatchSerializer,
    UserCharacterCardSerializer, UserTrapCardSerializer, DeckSerializer,
)
from .services_matchmaking import create_match_with_random_hands


class CardsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        chars = CardCharacterSerializer(CardCharacter.objects.all(), many=True, context={"request": request}).data
        traps = CardTrapSerializer(CardTrap.objects.all(), many=True, context={"request": request}).data
        return Response({"characters": chars, "traps": traps})


class MyMatchesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = Match.objects.filter(player1=request.user) | Match.objects.filter(player2=request.user)
        qs = qs.order_by("-created_at")[:20]
        return Response(MatchSerializer(qs, many=True).data)


@login_required
@transaction.atomic
def queue_join(request):
    MatchQueue.objects.get_or_create(user=request.user)

    other = (
        MatchQueue.objects
        .select_for_update()
        .exclude(user=request.user)
        .order_by("created_at")
        .first()
    )
    if other:
        MatchQueue.objects.filter(user__in=[request.user, other.user]).delete()
        match = create_match_with_random_hands(other.user, request.user)
        return JsonResponse({"status": "MATCH_FOUND", "match_id": str(match.id)})

    return JsonResponse({"status": "QUEUED"})


@login_required
def queue_leave(request):
    MatchQueue.objects.filter(user=request.user).delete()
    return JsonResponse({"status": "LEFT"})


@login_required
def queue_status(request):
    m = (
        Match.objects
        .filter(Q(player1=request.user) | Q(player2=request.user))
        .exclude(status=MatchStatus.FINISHED)
        .order_by("-id")
        .first()
    )

    if m:
        return JsonResponse({"status": "MATCH_FOUND", "match_id": str(m.id)})

    in_queue = MatchQueue.objects.filter(user=request.user).exists()
    return JsonResponse({"status": "QUEUED" if in_queue else "IDLE"})


@login_required
def match_hand(request, match_id):
    match = get_object_or_404(Match, id=match_id)

    if request.user == match.player1:
        char_ids = match.hand_p1 or []
        trap_ids = match.hand_traps_p1 or []
        used_chars = match.used_char_p1 or []
        used_traps = match.used_trap_p1 or []
    elif request.user == match.player2:
        char_ids = match.hand_p2 or []
        trap_ids = match.hand_traps_p2 or []
        used_chars = match.used_char_p2 or []
        used_traps = match.used_trap_p2 or []
    else:
        return JsonResponse({"detail": "Forbidden"}, status=403)

    char_qs = CardCharacter.objects.filter(id__in=char_ids)
    char_data = CardCharacterSerializer(char_qs, many=True, context={"request": request}).data
    by_id_char = {c["id"]: c for c in char_data}
    ordered_chars = [by_id_char[i] for i in char_ids if i in by_id_char]

    trap_qs = CardTrap.objects.filter(id__in=trap_ids)
    trap_data = CardTrapSerializer(trap_qs, many=True, context={"request": request}).data
    by_id_trap = {t["id"]: t for t in trap_data}
    ordered_traps = [by_id_trap[i] for i in trap_ids if i in by_id_trap]

    return JsonResponse({
        "characters": ordered_chars,
        "traps": ordered_traps,
        "used_chars": used_chars,
        "used_traps": used_traps,
    })


# ==========================
# NUEVO: Inventario
# ==========================
class MyInventoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        chars = UserCharacterCard.objects.filter(user=request.user).select_related("card")
        traps = UserTrapCard.objects.filter(user=request.user).select_related("trap")

        return Response({
            "characters": UserCharacterCardSerializer(chars, many=True, context={"request": request}).data,
            "traps": UserTrapCardSerializer(traps, many=True, context={"request": request}).data,
        })


# ==========================
# NUEVO: Deck (mazo)
# ==========================
def _get_or_create_active_deck(user):
    deck = Deck.objects.filter(user=user, is_active=True).first()
    if deck:
        return deck
    return Deck.objects.create(user=user, name="Mi mazo", is_active=True)


class MyDeckView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        deck = _get_or_create_active_deck(request.user)
        return Response(DeckSerializer(deck, context={"request": request}).data)

    @transaction.atomic
    def post(self, request):
        """
        Body esperado:
        {
          "name": "Mi mazo",
          "character_ids": [1,2,3],
          "trap_ids": [5,6]
        }
        Solo permite meter cartas que tengas en inventario.
        """
        deck = _get_or_create_active_deck(request.user)

        name = request.data.get("name")
        if isinstance(name, str) and name.strip():
            deck.name = name.strip()
            deck.save()

        character_ids = request.data.get("character_ids") or []
        trap_ids = request.data.get("trap_ids") or []

        # validar inventario
        owned_char_ids = set(
            UserCharacterCard.objects.filter(user=request.user, quantity__gt=0).values_list("card_id", flat=True)
        )
        owned_trap_ids = set(
            UserTrapCard.objects.filter(user=request.user, quantity__gt=0).values_list("trap_id", flat=True)
        )

        filtered_char_ids = [int(x) for x in character_ids if int(x) in owned_char_ids]
        filtered_trap_ids = [int(x) for x in trap_ids if int(x) in owned_trap_ids]

        # replace completo del deck (sin duplicar)
        DeckCharacter.objects.filter(deck=deck).delete()
        DeckTrap.objects.filter(deck=deck).delete()

        DeckCharacter.objects.bulk_create(
            [DeckCharacter(deck=deck, card_id=cid) for cid in dict.fromkeys(filtered_char_ids)]
        )
        DeckTrap.objects.bulk_create(
            [DeckTrap(deck=deck, trap_id=tid) for tid in dict.fromkeys(filtered_trap_ids)]
        )

        deck.refresh_from_db()
        return Response(DeckSerializer(deck, context={"request": request}).data)


class SetActiveDeckView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        """
        Body:
        { "deck_id": 123 }
        """
        deck_id = request.data.get("deck_id")
        deck = get_object_or_404(Deck, id=deck_id, user=request.user)

        Deck.objects.filter(user=request.user).update(is_active=False)
        deck.is_active = True
        deck.save()

        return Response({"status": "OK", "active_deck_id": deck.id})

@login_required
def deck_builder_page(request):
    return render(request, "deck_builder.html")
