from django.core.management.base import BaseCommand

from grafo import interrogazione


class Command(BaseCommand):
    help = "Risponde a una domanda senza chat, con lo smistamento a parole chiave."

    def add_arguments(self, parser):
        parser.add_argument("domanda", nargs="+")

    def handle(self, *args, **opzioni):
        self.stdout.write(interrogazione.consulta(" ".join(opzioni["domanda"])))
