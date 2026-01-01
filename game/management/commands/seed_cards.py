from django.core.management.base import BaseCommand
from game.models import CardCharacter, CardTrap, TrapType

class Command(BaseCommand):
    help = "Crea cartas de ejemplo"

    def handle(self, *args, **options):
        CardCharacter.objects.all().delete()
        CardTrap.objects.all().delete()

        chars = [
            ("Soldado", 2, 3, 1, 4),
            ("Mago", 4, 1, 2, 3),
            ("Tanque", 1, 5, 4, 1),
            ("Asesino", 5, 1, 1, 5),
            ("Rey", 1, 10, 1, 1),
        ]
        for name, up, down, left, right in chars:
            CardCharacter.objects.create(name=name, up=up, down=down, left=left, right=right)

        traps = [
            ("Trampa -UP", TrapType.MINUS_UP, 1),
            ("Trampa -DOWN", TrapType.MINUS_DOWN, 1),
            ("Trampa -LEFT", TrapType.MINUS_LEFT, 1),
            ("Trampa -RIGHT", TrapType.MINUS_RIGHT, 1),
        ]
        for name, t, v in traps:
            CardTrap.objects.create(name=name, trap_type=t, value=v)

        self.stdout.write(self.style.SUCCESS("✅ Cartas seed creadas"))
