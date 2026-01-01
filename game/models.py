import uuid
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.conf import settings


class Rarity(models.TextChoices):
    COMMON = "common", "Common"
    RARE = "rare", "Rare"
    EPIC = "epic", "Epic"
    LEGENDARY = "legendary", "Legendary"


class TrapType(models.TextChoices):
    MINUS_UP = "MINUS_UP", "Minus Up"
    MINUS_DOWN = "MINUS_DOWN", "Minus Down"
    MINUS_LEFT = "MINUS_LEFT", "Minus Left"
    MINUS_RIGHT = "MINUS_RIGHT", "Minus Right"


class CardCharacter(models.Model):
    name = models.CharField(max_length=64)
    up = models.IntegerField()
    down = models.IntegerField()
    left = models.IntegerField()
    right = models.IntegerField()
    rarity = models.CharField(max_length=16, choices=Rarity.choices, default=Rarity.COMMON)
    image = models.ImageField(upload_to="cards/characters/", blank=True, null=True)

    def __str__(self):
        return f"{self.name} ({self.up}/{self.right}/{self.down}/{self.left})"


class CardTrap(models.Model):
    name = models.CharField(max_length=64)
    trap_type = models.CharField(max_length=32, choices=TrapType.choices)
    value = models.IntegerField(default=1)
    rarity = models.CharField(max_length=16, choices=Rarity.choices, default=Rarity.COMMON)
    image = models.ImageField(upload_to="cards/traps/", blank=True, null=True)

    def __str__(self):
        return f"{self.name} [{self.trap_type} -{self.value}]"


# ==========================
# Inventario por usuario
# ==========================
class UserCharacterCard(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="inv_char_cards")
    card = models.ForeignKey(CardCharacter, on_delete=models.CASCADE, related_name="owned_by")
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = ("user", "card")

    def __str__(self):
        return f"{self.user} owns {self.card} x{self.quantity}"


class UserTrapCard(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="inv_trap_cards")
    trap = models.ForeignKey(CardTrap, on_delete=models.CASCADE, related_name="owned_by")
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = ("user", "trap")

    def __str__(self):
        return f"{self.user} owns {self.trap} x{self.quantity}"


# ==========================
# Mazos (Decks)
# ==========================
class Deck(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="decks")
    name = models.CharField(max_length=64, default="Mi mazo")
    is_active = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Deck({self.user.username}:{self.name})"


class DeckCharacter(models.Model):
    deck = models.ForeignKey(Deck, on_delete=models.CASCADE, related_name="deck_characters")
    card = models.ForeignKey(CardCharacter, on_delete=models.CASCADE)

    class Meta:
        unique_together = ("deck", "card")


class DeckTrap(models.Model):
    deck = models.ForeignKey(Deck, on_delete=models.CASCADE, related_name="deck_traps")
    trap = models.ForeignKey(CardTrap, on_delete=models.CASCADE)

    class Meta:
        unique_together = ("deck", "trap")


# ==========================
# Match / queue
# ==========================
class MatchStatus(models.TextChoices):
    WAITING = "waiting", "Waiting"
    ACTIVE = "active", "Active"
    FINISHED = "finished", "Finished"


class Match(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    player1 = models.ForeignKey(User, on_delete=models.CASCADE, related_name="matches_p1")
    player2 = models.ForeignKey(User, on_delete=models.CASCADE, related_name="matches_p2")

    status = models.CharField(max_length=16, choices=MatchStatus.choices, default=MatchStatus.ACTIVE)

    # 1 o 2 (id del jugador actual)
    turn_player = models.IntegerField(default=1)

    # ✅ deadline de turno (timer 45s)
    turn_deadline = models.DateTimeField(null=True, blank=True)

    # JSON state: list[9] slots, each slot: {"char":..., "trap":...}
    board_state = models.JSONField(default=list)

    # Para “1 vez cada carta por match”
    used_char_p1 = models.JSONField(default=list)  # list[int] ids
    used_char_p2 = models.JSONField(default=list)
    used_trap_p1 = models.JSONField(default=list)
    used_trap_p2 = models.JSONField(default=list)

    # manos
    hand_p1 = models.JSONField(default=list, blank=True)  # personajes (ids)
    hand_p2 = models.JSONField(default=list, blank=True)

    hand_traps_p1 = models.JSONField(default=list, blank=True)
    hand_traps_p2 = models.JSONField(default=list, blank=True)

    winner = models.IntegerField(default=0)  # 0 tie/none, 1 player1, 2 player2
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Match {self.id} ({self.player1} vs {self.player2})"


class MatchMove(models.Model):
    match = models.ForeignKey(Match, on_delete=models.CASCADE, related_name="moves")
    player = models.IntegerField()  # 1 o 2
    move_type = models.CharField(max_length=16)  # PLAY_CHAR / PLACE_TRAP / TIMEOUT_FORFEIT
    payload = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)


class MatchQueue(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Queue({self.user.username})"
