"""
    python manage.py carica_regole

Carica le regole di partenza (indici/regole_iniziali.py). Una regola già presente
con lo stesso codice NON viene toccata: le modifiche del Configuratore restano.
"""
from django.core.management.base import BaseCommand

from indici import regole_iniziali
from indici.models import RegolaDiRischio


class Command(BaseCommand):
    help = "Carica le regole di rischio di partenza, senza toccare quelle già presenti."

    def handle(self, *args, **opzioni):
        nuove = 0
        for codice, descrizione, tipo, peso, prefissi, dipendenti, fatturato in regole_iniziali.REGOLE:
            _, creata = RegolaDiRischio.objects.get_or_create(codice=codice, defaults={
                "descrizione": descrizione, "tipo": tipo, "peso": peso, "prefissi_attivita": prefissi,
                "classi_dipendenti": dipendenti, "classi_fatturato": fatturato,
            })
            nuove += creata
        self.stdout.write(f"Regole nuove: {nuove} | in tutto: {RegolaDiRischio.objects.count()}")
