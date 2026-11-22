from django.core.management.base import BaseCommand

from elaborazione import coda


class Command(BaseCommand):
    help = (
        "Elabora i file ricevuti: testo, entità, collegamento alle aziende. Da avviare di notte "
        "con un limite di tempo; i file non presi restano in attesa per la volta successiva."
    )

    def add_arguments(self, parser):
        parser.add_argument("--minuti", type=int, default=None, help="Tempo massimo di lavoro. Vuoto: finché ci sono file.")
        parser.add_argument("--massimo", type=int, default=None, help="Numero massimo di file da prendere.")

    def handle(self, *args, **opzioni):
        resoconto = coda.esegui(minuti=opzioni["minuti"], massimo=opzioni["massimo"])
        if resoconto["sbloccati"]:
            self.stdout.write(f"Ripresi dopo un'interruzione: {resoconto['sbloccati']}")
        self.stdout.write(
            f"Elaborati: {resoconto[coda.ELABORATO]} | da rivedere: {resoconto[coda.DA_RIVEDERE]} | "
            f"errori: {resoconto[coda.ERRORE]} | saltati: {resoconto[coda.SALTATO]} | "
            f"ancora in attesa: {resoconto['in attesa']}"
        )
        for motivo, numero in resoconto["motivi"].items():
            self.stdout.write(f"  saltati ({numero}): {motivo}")
