"""
    python manage.py importa_anagrafica percorso/del/file.csv [--fonte "Camera di Commercio 2025"]

Importa l'anagrafica per periodo da un file CSV (formato in indici/importazione.py;
un esempio con dati inventati è in indici/esempio_anagrafica.csv).
"""
import pathlib

from django.core.management.base import BaseCommand, CommandError

from indici import importazione


class Command(BaseCommand):
    help = "Importa da un file CSV attività, dipendenti e fatturato delle società, per periodo."

    def add_arguments(self, parser):
        parser.add_argument("percorso")
        parser.add_argument("--fonte", default="", help="Da dove viene il file (resta scritto su ogni riga)")

    def handle(self, *args, **opzioni):
        percorso = pathlib.Path(opzioni["percorso"])
        try:
            testo = percorso.read_text(encoding="utf-8-sig")
        except (OSError, UnicodeDecodeError) as errore:
            raise CommandError(f"Il file non si legge (deve essere testo UTF-8): {errore}")
        try:
            resoconto = importazione.importa(testo, opzioni["fonte"] or percorso.name)
        except importazione.RigaNonValida as problema:
            raise CommandError(str(problema))
        self.stdout.write(
            f"Righe nuove: {resoconto['create']} | aggiornate: {resoconto['aggiornate']} | "
            f"rifiutate: {len(resoconto['rifiutate'])}"
        )
        for numero, motivo in resoconto["rifiutate"]:
            self.stdout.write(f"  riga {numero}: {motivo}")
