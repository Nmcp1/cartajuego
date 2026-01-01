from django.contrib import admin
from .models import CardCharacter, CardTrap, Match, MatchMove

admin.site.register(CardCharacter)
admin.site.register(CardTrap)
admin.site.register(Match)
admin.site.register(MatchMove)
