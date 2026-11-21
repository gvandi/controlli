from django.core.management.base import BaseCommand

from grafo import contratto, interrogazione


class Command(BaseCommand):
    help = "Mostra versioni del codice, schema dell'archivio ed esecuzioni presenti."

    def handle(self, *args, **opzioni):
        self.stdout.write(f"Codice (progetto): {contratto.VERSIONE_CODICE}")
        self.stdout.write(f"Calcolo: {contratto.VERSIONE_CALCOLO} (i lettori accettano {contratto.CALCOLO_ACCETTATO})")
        self.stdout.write(f"Schema prodotto dalle migrazioni del codice: {contratto.VERSIONE_SCHEMA} "
                          f"(i lettori richiedono {contratto.SCHEMA_RICHIESTO})")
        try:
            in_uso = interrogazione.apri()
        except contratto.ArchivioIncompatibile as errore:
            in_uso = None
            self.stdout.write(f"Archivio NON utilizzabile: {errore}")
        try:
            esecuzioni = interrogazione.esecuzioni_disponibili()
        except Exception:
            esecuzioni = []
        self.stdout.write(f"Esecuzioni presenti: {len(esecuzioni)}")
        for e in esecuzioni:
            etichetta = f"calcolo {e['versione_calcolo']} / dati {e['numero_dati']}"
            segno = "  <-- in uso" if etichetta == in_uso else ""
            self.stdout.write(f"  - {etichetta} | calcolata il {e['calcolata_il']} | codice {e['versione_codice']}{segno}")
