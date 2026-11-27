"""
    python manage.py calcola_indici

Aggiorna la fotografia dei dati reali e calcola l'indice di rischio a regole
(indici/calcolo.py). Da quel momento la chat usa i dati reali.
"""
from django.core.management.base import BaseCommand

from grafo import contratto
from indici import calcolo


class Command(BaseCommand):
    help = "Calcola l'indice di rischio a regole sui dati reali e lo registra come esecuzione dell'analisi di rete."

    def handle(self, *args, **opzioni):
        resoconto = calcolo.esegui()
        if resoconto["esecuzione"] is None:
            self.stdout.write(
                "Nessun dato reale: importare l'anagrafica (importa_anagrafica) o confermare almeno un documento."
            )
            return
        if not resoconto["regole"]:
            self.stdout.write("Attenzione: nessuna regola attiva (python manage.py carica_regole, oppure dall'amministrazione).")
        self.stdout.write(
            f"Calcolo {contratto.VERSIONE_CALCOLO_REGOLE} / dati n. {resoconto['versione_dati'].numero}: "
            f"{resoconto['aziende']} società, {resoconto['segnalate']} sopra soglia, "
            f"{resoconto['senza_dati']} senza dati per periodo, {resoconto['regole']} regole attive."
        )
