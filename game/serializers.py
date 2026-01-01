from rest_framework import serializers
from .models import (
    CardCharacter, CardTrap, Match,
    UserCharacterCard, UserTrapCard,
    Deck, DeckCharacter, DeckTrap,
)


def _image_url_from_context(serializer: serializers.Serializer, url: str) -> str:
    """Devuelve URL absoluta si hay request en el context; si no, devuelve la url tal cual."""
    request = serializer.context.get("request") if hasattr(serializer, "context") else None
    if request is not None:
        try:
            return request.build_absolute_uri(url)
        except Exception:
            return url
    return url


class CardCharacterSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    class Meta:
        model = CardCharacter
        fields = ["id", "name", "up", "down", "left", "right", "rarity", "image"]

    def get_image(self, obj):
        if getattr(obj, "image", None):
            try:
                return _image_url_from_context(self, obj.image.url)
            except Exception:
                return None
        return None


class CardTrapSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    class Meta:
        model = CardTrap
        fields = ["id", "name", "trap_type", "value", "rarity", "image"]

    def get_image(self, obj):
        if getattr(obj, "image", None):
            try:
                return _image_url_from_context(self, obj.image.url)
            except Exception:
                return None
        return None


class MatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Match
        fields = ["id", "status", "turn_player", "winner", "created_at"]


class UserCharacterCardSerializer(serializers.ModelSerializer):
    card = CardCharacterSerializer()

    class Meta:
        model = UserCharacterCard
        fields = ["card", "quantity"]


class UserTrapCardSerializer(serializers.ModelSerializer):
    trap = CardTrapSerializer()

    class Meta:
        model = UserTrapCard
        fields = ["trap", "quantity"]


class DeckSerializer(serializers.ModelSerializer):
    characters = serializers.SerializerMethodField()
    traps = serializers.SerializerMethodField()

    class Meta:
        model = Deck
        fields = ["id", "name", "is_active", "characters", "traps"]

    def get_characters(self, obj):
        cards = [dc.card for dc in obj.deck_characters.select_related("card").all()]
        return CardCharacterSerializer(cards, many=True, context=self.context).data

    def get_traps(self, obj):
        traps = [dt.trap for dt in obj.deck_traps.select_related("trap").all()]
        return CardTrapSerializer(traps, many=True, context=self.context).data
