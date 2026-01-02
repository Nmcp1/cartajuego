from django.contrib import admin
from django.utils.html import format_html
from django.db import models
from django.forms import Textarea

from .models import (
    CardCharacter,
    CardTrap,
    UserCharacterCard,
    UserTrapCard,
    Deck,
    DeckCharacter,
    DeckTrap,
    Match,
    MatchMove,
    MatchQueue,
)


# ==========================
# Helpers
# ==========================
def _img_preview(url: str, size: int = 56):
    if not url:
        return "—"
    return format_html(
        '<img src="{}" style="width:{}px;height:{}px;object-fit:cover;border-radius:10px;border:1px solid #2a3556;" />',
        url, size, size
    )


# ==========================
# Cards
# ==========================
@admin.register(CardCharacter)
class CardCharacterAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "rarity", "up", "right", "down", "left", "preview")
    list_filter = ("rarity",)
    search_fields = ("name",)
    ordering = ("name",)
    list_per_page = 50

    fields = (
        "name",
        "rarity",
        ("up", "right", "down", "left"),
        "image_url",
        "image",
        "preview",
    )
    readonly_fields = ("preview",)

    def preview(self, obj):
        # Prioridad: image_url, si no, image.url
        url = obj.image_url or (obj.image.url if obj.image else "")
        return _img_preview(url, 72)
    preview.short_description = "Preview"


@admin.register(CardTrap)
class CardTrapAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "rarity", "trap_type", "value", "preview")
    list_filter = ("rarity", "trap_type")
    search_fields = ("name",)
    ordering = ("name",)
    list_per_page = 50

    fields = (
        "name",
        "rarity",
        ("trap_type", "value"),
        "image_url",
        "image",
        "preview",
    )
    readonly_fields = ("preview",)

    def preview(self, obj):
        url = obj.image_url or (obj.image.url if obj.image else "")
        return _img_preview(url, 72)
    preview.short_description = "Preview"


# ==========================
# Inventarios
# ==========================
@admin.register(UserCharacterCard)
class UserCharacterCardAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "card", "quantity")
    list_filter = ("user", "card__rarity")
    search_fields = ("user__username", "card__name")
    raw_id_fields = ("user", "card")
    ordering = ("user", "card")


@admin.register(UserTrapCard)
class UserTrapCardAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "trap", "quantity")
    list_filter = ("user", "trap__rarity", "trap__trap_type")
    search_fields = ("user__username", "trap__name")
    raw_id_fields = ("user", "trap")
    ordering = ("user", "trap")


# ==========================
# Decks
# ==========================
class DeckCharacterInline(admin.TabularInline):
    model = DeckCharacter
    extra = 0
    raw_id_fields = ("card",)


class DeckTrapInline(admin.TabularInline):
    model = DeckTrap
    extra = 0
    raw_id_fields = ("trap",)


@admin.register(Deck)
class DeckAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "name", "is_active", "created_at")
    list_filter = ("is_active", "created_at")
    search_fields = ("user__username", "name")
    raw_id_fields = ("user",)
    ordering = ("-created_at",)
    inlines = [DeckCharacterInline, DeckTrapInline]


@admin.register(DeckCharacter)
class DeckCharacterAdmin(admin.ModelAdmin):
    list_display = ("id", "deck", "card")
    search_fields = ("deck__name", "deck__user__username", "card__name")
    raw_id_fields = ("deck", "card")


@admin.register(DeckTrap)
class DeckTrapAdmin(admin.ModelAdmin):
    list_display = ("id", "deck", "trap")
    search_fields = ("deck__name", "deck__user__username", "trap__name")
    raw_id_fields = ("deck", "trap")


# ==========================
# Match / Queue
# ==========================
@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = ("id", "status", "player1", "player2", "turn_player", "winner", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("id", "player1__username", "player2__username")
    raw_id_fields = ("player1", "player2")
    ordering = ("-created_at",)

    # JSONFields grandes: mejor en textarea
    formfield_overrides = {
        models.JSONField: {"widget": Textarea(attrs={"rows": 6, "cols": 90})},
    }


@admin.register(MatchMove)
class MatchMoveAdmin(admin.ModelAdmin):
    list_display = ("id", "match", "player", "move_type", "created_at")
    list_filter = ("move_type", "created_at")
    search_fields = ("match__id",)
    raw_id_fields = ("match",)
    ordering = ("-created_at",)

    formfield_overrides = {
        models.JSONField: {"widget": Textarea(attrs={"rows": 6, "cols": 90})},
    }


@admin.register(MatchQueue)
class MatchQueueAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "created_at")
    list_filter = ("created_at",)
    search_fields = ("user__username",)
    raw_id_fields = ("user",)
    ordering = ("-created_at",)
