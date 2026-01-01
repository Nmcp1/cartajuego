from typing import Dict, Any, List, Optional, Tuple
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .models import (
    Match,
    CardCharacter,
    CardTrap,
    MatchMove,
    MatchStatus,
    TrapType,
)

TURN_SECONDS = 45

DIRS = {
    "up": (-3, "down"),
    "down": (3, "up"),
    "left": (-1, "right"),
    "right": (1, "left"),
}

NEIGHBORS = {
    0: ["right", "down"],
    1: ["left", "right", "down"],
    2: ["left", "down"],
    3: ["up", "right", "down"],
    4: ["up", "left", "right", "down"],
    5: ["up", "left", "down"],
    6: ["up", "right"],
    7: ["up", "left", "right"],
    8: ["up", "left"],
}


def _empty_board() -> List[Dict[str, Any]]:
    return [{"char": None, "trap": None} for _ in range(9)]


def _get_used_lists(match: Match, player: int):
    if player == 1:
        return match.used_char_p1, match.used_trap_p1
    return match.used_char_p2, match.used_trap_p2


def _set_used_lists(match: Match, player: int, used_chars, used_traps):
    if player == 1:
        match.used_char_p1 = used_chars
        match.used_trap_p1 = used_traps
    else:
        match.used_char_p2 = used_chars
        match.used_trap_p2 = used_traps


def _switch_turn(match: Match):
    match.turn_player = 2 if match.turn_player == 1 else 1


def _reset_turn_deadline(match: Match):
    match.turn_deadline = timezone.now() + timezone.timedelta(seconds=TURN_SECONDS)


def _count_owner(board: List[Dict[str, Any]]) -> Tuple[int, int]:
    p1 = 0
    p2 = 0
    for s in board:
        if s["char"] is None:
            continue
        owner = s["char"]["owner"]
        if owner == 1:
            p1 += 1
        elif owner == 2:
            p2 += 1
    return p1, p2


def _is_full(board: List[Dict[str, Any]]) -> bool:
    return all(s["char"] is not None for s in board)


def _apply_trap_to_stats(trap: Dict[str, Any], stats: Dict[str, int]) -> Dict[str, int]:
    ttype = trap["type"]
    val = int(trap.get("value", 1))

    new_stats = dict(stats)
    if ttype == TrapType.MINUS_UP:
        new_stats["up"] = max(0, new_stats["up"] - val)
    elif ttype == TrapType.MINUS_DOWN:
        new_stats["down"] = max(0, new_stats["down"] - val)
    elif ttype == TrapType.MINUS_LEFT:
        new_stats["left"] = max(0, new_stats["left"] - val)
    elif ttype == TrapType.MINUS_RIGHT:
        new_stats["right"] = max(0, new_stats["right"] - val)
    return new_stats


def _resolve_captures(board: List[Dict[str, Any]], pos: int) -> None:
    placed = board[pos]["char"]
    if placed is None:
        return

    for direction in NEIGHBORS[pos]:
        delta, opposite = DIRS[direction]
        npos = pos + delta

        if direction == "left" and pos % 3 == 0:
            continue
        if direction == "right" and pos % 3 == 2:
            continue

        neighbor = board[npos]["char"]
        if neighbor is None:
            continue

        if neighbor["owner"] == placed["owner"]:
            continue

        my_val = placed[direction]
        their_val = neighbor[opposite]
        if my_val > their_val:
            neighbor["owner"] = placed["owner"]


def _finish_if_needed(match: Match):
    if not _is_full(match.board_state):
        return

    p1, p2 = _count_owner(match.board_state)
    match.status = MatchStatus.FINISHED
    if p1 > p2:
        match.winner = 1
    elif p2 > p1:
        match.winner = 2
    else:
        match.winner = 0


def _media_url(path: Optional[str]) -> Optional[str]:
    if not path:
        return None
    if path.startswith("http://") or path.startswith("https://"):
        return path
    if path.startswith(settings.MEDIA_URL):
        return path
    return settings.MEDIA_URL + path.lstrip("/")


@transaction.atomic
def ensure_match_initialized(match: Match):
    changed = False

    if not match.board_state or len(match.board_state) != 9:
        match.board_state = _empty_board()
        match.turn_player = 1
        match.status = MatchStatus.ACTIVE
        changed = True

    # ✅ si no hay deadline, se inicia
    if match.status == MatchStatus.ACTIVE and not match.turn_deadline:
        _reset_turn_deadline(match)
        changed = True

    if changed:
        match.save()


@transaction.atomic
def timeout_forfeit_if_needed(match: Match) -> bool:
    """
    Si se pasó el tiempo del turno y el match sigue activo:
    pierde el jugador que debía jugar (turn_player),
    gana el otro.
    Retorna True si se aplicó forfeit.
    """
    ensure_match_initialized(match)

    if match.status != MatchStatus.ACTIVE:
        return False

    if not match.turn_deadline:
        _reset_turn_deadline(match)
        match.save()
        return False

    if timezone.now() <= match.turn_deadline:
        return False

    loser = match.turn_player
    winner = 2 if loser == 1 else 1

    match.status = MatchStatus.FINISHED
    match.winner = winner

    MatchMove.objects.create(
        match=match,
        player=loser,
        move_type="TIMEOUT_FORFEIT",
        payload={"loser": loser, "winner": winner},
    )

    match.save()
    return True


@transaction.atomic
def play_character(match: Match, player: int, card_id: int, pos: int) -> Match:
    ensure_match_initialized(match)

    # ✅ antes de jugar, revisar timeout
    timeout_forfeit_if_needed(match)
    if match.status != MatchStatus.ACTIVE:
        raise ValueError("Match no está activo.")

    if player != match.turn_player:
        raise ValueError("No es tu turno.")
    if pos < 0 or pos > 8:
        raise ValueError("Posición inválida.")
    if match.board_state[pos]["char"] is not None:
        raise ValueError("Esa casilla ya tiene personaje.")

    used_chars, used_traps = _get_used_lists(match, player)
    if card_id in used_chars:
        raise ValueError("Ya usaste esa carta de personaje en esta partida.")

    card = CardCharacter.objects.get(id=card_id)

    base_stats = {"up": card.up, "down": card.down, "left": card.left, "right": card.right}

    trap = match.board_state[pos]["trap"]
    if trap and trap.get("armed") and trap.get("owner") != player:
        base_stats = _apply_trap_to_stats(trap, base_stats)
        trap["armed"] = False
        trap["triggered_by"] = player
        trap["revealed"] = True

    match.board_state[pos]["char"] = {
        "card_id": card.id,
        "name": card.name,
        "owner": player,
        "up": base_stats["up"],
        "down": base_stats["down"],
        "left": base_stats["left"],
        "right": base_stats["right"],
        "image": (card.image.url if getattr(card, "image", None) else None),
        "rarity": card.rarity,
    }

    _resolve_captures(match.board_state, pos)

    used_chars.append(card_id)
    _set_used_lists(match, player, used_chars, used_traps)

    MatchMove.objects.create(
        match=match,
        player=player,
        move_type="PLAY_CHAR",
        payload={"card_id": card_id, "pos": pos},
    )

    _finish_if_needed(match)
    if match.status == MatchStatus.ACTIVE:
        _switch_turn(match)
        # ✅ resetea timer cada turno
        _reset_turn_deadline(match)

    match.save()
    return match


@transaction.atomic
def place_trap(match: Match, player: int, trap_id: int, pos: int) -> Match:
    ensure_match_initialized(match)

    timeout_forfeit_if_needed(match)
    if match.status != MatchStatus.ACTIVE:
        raise ValueError("Match no está activo.")

    # regla actual: trampa solo si NO es tu turno
    if player == match.turn_player:
        raise ValueError("Primero debes jugar personaje (trampa va al final del turno).")

    if pos < 0 or pos > 8:
        raise ValueError("Posición inválida.")
    if match.board_state[pos]["trap"] is not None:
        raise ValueError("Esa casilla ya tiene una trampa.")

    used_chars, used_traps = _get_used_lists(match, player)
    if trap_id in used_traps:
        raise ValueError("Ya usaste esa trampa en esta partida.")

    trap_card = CardTrap.objects.get(id=trap_id)

    match.board_state[pos]["trap"] = {
        "trap_id": trap_card.id,
        "name": trap_card.name,
        "type": trap_card.trap_type,
        "value": trap_card.value,
        "owner": player,
        "armed": True,
        "revealed": False,
        "rarity": trap_card.rarity,
        "image": (trap_card.image.url if getattr(trap_card, "image", None) else None),
    }

    used_traps.append(trap_id)
    _set_used_lists(match, player, used_chars, used_traps)

    MatchMove.objects.create(
        match=match,
        player=player,
        move_type="PLACE_TRAP",
        payload={"trap_id": trap_id, "pos": pos},
    )

    match.save()
    return match


def serialize_match_for_viewer(match: Match, viewer_player: int) -> Dict[str, Any]:
    board = []

    for slot in match.board_state:
        char = slot.get("char")
        if char and char.get("image"):
            char["image"] = _media_url(char["image"])

        trap = slot.get("trap")
        masked_trap = None

        if trap:
            if trap.get("owner") == viewer_player:
                masked_trap = trap
            else:
                if trap.get("revealed") or (not trap.get("armed")):
                    masked_trap = trap
                else:
                    masked_trap = {"present": True}

            if masked_trap and masked_trap.get("image"):
                masked_trap["image"] = _media_url(masked_trap["image"])

        board.append({"char": char, "trap": masked_trap})

    p1_count, p2_count = _count_owner(match.board_state)

    used_chars, used_traps = _get_used_lists(match, viewer_player)

    # seconds left server-side
    seconds_left = None
    if match.turn_deadline and match.status == MatchStatus.ACTIVE:
        delta = (match.turn_deadline - timezone.now()).total_seconds()
        seconds_left = max(0, int(delta))

    return {
        "match_id": str(match.id),
        "status": match.status,
        "turn_player": match.turn_player,
        "winner": match.winner,
        "turn_deadline": match.turn_deadline.isoformat() if match.turn_deadline else None,
        "seconds_left": seconds_left,
        "counts": {"p1": p1_count, "p2": p2_count},
        "board": board,
        "players": {
            "p1": {"id": match.player1.id, "username": match.player1.username},
            "p2": {"id": match.player2.id, "username": match.player2.username},
        },
        "used_chars": used_chars or [],
        "used_traps": used_traps or [],
    }
