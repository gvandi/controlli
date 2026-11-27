"""
    python manage.py grafo_dati_reali

Prende dall'archivio la fotografia dei dati reali per l'analisi di rete: i soggetti
e i rapporti che risultano dai documenti confermati (vedi grafo/dati_reali.py).
Non calcola punteggi e non cambia ciò che la chat usa.
"""
from django.core.management.base import BaseCommand

from grafo import dati_reali


class Command(BaseCommand):
    help = "Registra la fotografia dei dati reali (società e rapporti dai documenti confermati)."

    def handle(self, *args, **opzioni):
        resoconto = dati_reali.fotografa()
        for motivo, quanti in sorted(resoconto["esclusi"].items()):
            self.stdout.write(f"Documenti confermati non usati, {motivo}: {quanti}")
        versione = resoconto["versione_dati"]
        if versione is None:
            self.stdout.write("Nessuna società con dati per periodo e nessun documento confermato utilizzabile: nessuna fotografia.")
            return
        stato = "nuova fotografia" if resoconto["nuova"] else "nessuna novità: resta la fotografia"
        self.stdout.write(
            f"{stato} dati n. {versione.numero}: {resoconto['soggetti']} società, {resoconto['relazioni']} relazioni."
        )
        self.stdout.write("Non ci sono ancora punteggi su questi dati: la chat continua a usare l'ultima esecuzione.")
