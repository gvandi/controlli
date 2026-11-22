from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from grafo import sessioni


class Command(BaseCommand):
    help = "Crea un token personale (ripiego all'accesso OAuth) per il servizio MCP: mostrato una sola volta."

    def add_arguments(self, parser):
        parser.add_argument("utente", help="Nome utente dell'applicativo.")
        parser.add_argument("--etichetta", default="", help="Promemoria: per esempio il computer su cui verrà usato.")

    def handle(self, *args, **opzioni):
        utente = get_user_model().objects.filter(username=opzioni["utente"]).first()
        if utente is None:
            raise CommandError(f"Utente '{opzioni['utente']}' non trovato.")
        if not utente.has_perm("grafo.usa_chat"):
            self.stderr.write(
                "Attenzione: l'utente non ha il diritto 'usa_chat' (ruolo Analista): il token verrà rifiutato "
                "finché non gli viene assegnato."
            )
        _, in_chiaro = sessioni.crea_token(utente, opzioni["etichetta"])
        self.stdout.write(in_chiaro)
