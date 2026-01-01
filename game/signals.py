import random
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model

from .models import CardCharacter, CardTrap, Rarity, UserCharacterCard, UserTrapCard, Deck, DeckCharacter, DeckTrap

User = get_user_model()


def _add_char(user, card_id, qty=1):
    obj, created = UserCharacterCard.objects.get_or_create(user=user, card_id=card_id, defaults={"quantity": qty})
    if not created:
        obj.quantity += qty
        obj.save(update_fields=["quantity"])


def _add_trap(user, trap_id, qty=1):
    obj, created = UserTrapCard.objects.get_or_create(user=user, trap_id=trap_id, defaults={"quantity": qty})
    if not created:
        obj.quantity += qty
        obj.save(update_fields=["quantity"])


@receiver(post_save, sender=User)
def give_starter_cards(sender, instance, created, **kwargs):
    """
    Al registrarse:
    - 5 personajes COMMON aleatorios (sin repetir si hay suficientes)
    - (Recomendado) 3 trampas COMMON aleatorias
    - crea un deck activo y mete esas cartas adentro
    """
    if not created:
        return

    user = instance

    # Evitar dar starter a superusers/staff si no quieres
    # (puedes comentar esto si te da igual)
    if getattr(user, "is_staff", False) or getattr(user, "is_superuser", False):
        return

    common_chars = list(CardCharacter.objects.filter(rarity=Rarity.COMMON).values_list("id", flat=True))
    if common_chars:
        if len(common_chars) >= 5:
            picked_chars = random.sample(common_chars, 5)
        else:
            picked_chars = common_chars[:]  # menos de 5 existentes
            random.shuffle(picked_chars)

        for cid in picked_chars:
            _add_char(user, cid, qty=1)

    # ✅ recomendado para que sea jugable desde el inicio
    common_traps = list(CardTrap.objects.filter(rarity=Rarity.COMMON).values_list("id", flat=True))
    picked_traps = []
    if common_traps:
        if len(common_traps) >= 3:
            picked_traps = random.sample(common_traps, 3)
        else:
            picked_traps = common_traps[:]
            random.shuffle(picked_traps)

        for tid in picked_traps:
            _add_trap(user, tid, qty=1)

    # Crear deck activo y poner las starter adentro (solo si no existe aún)
    deck = Deck.objects.filter(user=user, is_active=True).first()
    if not deck:
        Deck.objects.filter(user=user).update(is_active=False)
        deck = Deck.objects.create(user=user, name="Mi mazo", is_active=True)

    # Meter cartas (sin duplicar)
    for cid in (picked_chars or []):
        DeckCharacter.objects.get_or_create(deck=deck, card_id=cid)

    for tid in (picked_traps or []):
        DeckTrap.objects.get_or_create(deck=deck, trap_id=tid)
