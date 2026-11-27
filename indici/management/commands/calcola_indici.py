"""
    python manage.py calcola_indici [--solo-verificati]

Aggiorna la fotografia dei dati reali e calcola l'indice di rischio a regole
(indici/calcolo.py). Da quel momento la chat usa i dati reali.
"""
from django.core.management.base import BaseCommand

from elaborazione import ammissione
from grafo import contratto
from indici import calcolo


class Command(BaseCommand):
    help = "Calcola l'indice di rischio a regole sui dati reali e lo registra come esecuzione dell'analisi di rete."

    def add_arguments(self, parser):
        parser.add_argument(
            "--solo-verificati", action="store_true",
            help="Usa solo i documenti confermati da una persona, qualunque sia l'impostazione CALCOLO_AMMETTE.",
        )

    def handle(self, *args, **opzioni):
        criteri = ammissione.SOLO_VERIFICATI if opzioni["solo_verificati"] else None
        resoconto = calcolo.esegui(criteri=criteri)
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
        self.stdout.write(
            f"Rapporti fra società: {resoconto['relazioni']}, di cui non verificati: {resoconto['non_verificate']} "
            f"({ammissione.descrivi(resoconto['criteri'], solo_documenti=True)}; si cambia con --solo-verificati)."
        )
