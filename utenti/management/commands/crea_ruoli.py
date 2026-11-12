from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand

from utenti.ruoli import DIRITTI


class Command(BaseCommand):
    help = (
        "Crea i ruoli dell'applicazione e assegna i diritti definiti in utenti/ruoli.py. "
        "Si può rieseguire: aggiunge i diritti mancanti e non toglie quelli assegnati a mano."
    )

    def handle(self, *args, **options):
        for nome_ruolo, regole in DIRITTI.items():
            gruppo, creato = Group.objects.get_or_create(name=nome_ruolo)
            aggiunti = 0
            for app, modello, azioni in regole:
                permessi = Permission.objects.filter(content_type__app_label=app)
                if modello is not None:
                    permessi = permessi.filter(content_type__model=modello)
                for permesso in permessi:
                    azione = permesso.codename.split("_", 1)[0]
                    if azione in azioni and not gruppo.permissions.filter(pk=permesso.pk).exists():
                        gruppo.permissions.add(permesso)
                        aggiunti += 1
            stato = "creato" if creato else "già presente"
            self.stdout.write(f"{nome_ruolo}: {stato}, {aggiunti} diritti aggiunti")
