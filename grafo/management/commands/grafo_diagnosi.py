"""
    python manage.py grafo_diagnosi 10276

Dice perché un'azienda ha, o non ha, rapporti nell'analisi di rete: per ogni file che
la riguarda segue il documento fino alla mappa e indica il punto in cui si ferma
(vedi grafo/dati_reali.py, diagnosi). L'azienda si indica con COE, partita IVA o nome.
"""
from django.core.management.base import BaseCommand, CommandError

from elaborazione import coda
from grafo import dati_reali


class Command(BaseCommand):
    help = "Spiega perché una società ha o non ha rapporti nella mappa e nella chat."

    def add_arguments(self, parser):
        parser.add_argument("azienda", nargs="+", help="COE, partita IVA o nome")

    def handle(self, *args, **opzioni):
        soggetto, messaggio = coda.trova_azienda(" ".join(opzioni["azienda"]))
        if soggetto is None:
            raise CommandError(messaggio)
        for riga in dati_reali.diagnosi(soggetto):
            self.stdout.write(riga)
