import random
from django.db import transaction

from .models import (
    Match, MatchStatus,
    Deck, DeckCharacter, DeckTrap,
)


def _pick_k_from_ids(ids, k: int):
    ids = list(ids)
    if not ids:
        return []
    if len(ids) <= k:
        random.shuffle(ids)
        return ids
    return random.sample(ids, k)


def _get_or_create_active_deck(user):
    deck = Deck.objects.filter(user=user, is_active=True).first()
    if deck:
        return deck
    # si no hay activo, crea uno y lo deja activo
    deck = Deck.objects.create(user=user, name="Mi mazo", is_active=True)
    return deck


def _deck_ids(deck: Deck):
    char_ids = list(deck.deck_characters.values_list("card_id", flat=True))
    trap_ids = list(deck.deck_traps.values_list("trap_id", flat=True))
    return char_ids, trap_ids


@transaction.atomic
def create_match_with_random_hands(user1, user2) -> Match:
    """
    user1 -> P1, user2 -> P2
    """
    d1 = _get_or_create_active_deck(user1)
    d2 = _get_or_create_active_deck(user2)

    d1_char_ids, d1_trap_ids = _deck_ids(d1)
    d2_char_ids, d2_trap_ids = _deck_ids(d2)

    match = Match.objects.create(
        player1=user1,
        player2=user2,
        status=MatchStatus.ACTIVE,
        turn_player=1,
        board_state=[],  # engine.ensure_match_initialized lo normaliza
        used_char_p1=[],
        used_char_p2=[],
        used_trap_p1=[],
        used_trap_p2=[],
        hand_p1=_pick_k_from_ids(d1_char_ids, 5),
        hand_p2=_pick_k_from_ids(d2_char_ids, 5),
        hand_traps_p1=_pick_k_from_ids(d1_trap_ids, 3),
        hand_traps_p2=_pick_k_from_ids(d2_trap_ids, 3),
    )

    return match
