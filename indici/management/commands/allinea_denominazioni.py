"""
    python manage.py allinea_denominazioni

Rimette in ordine i nomi delle aziende già presenti: prevale il nome dell'anagrafica
ufficiale (file CSV), poi quello confermato in un documento; un segnaposto come
"non rilevata" viene tolto. Vedi indici/allineamento.py. Si può rilanciare.
"""
from django.core.management.base import BaseCommand

from indici import allineamento


class Command(BaseCommand):
    help = "Riallinea le denominazioni delle aziende: anagrafica ufficiale, poi documenti confermati."

    def handle(self, *args, **opzioni):
        cambiati = allineamento.esegui()
        for soggetto, prima, dopo in cambiati:
            self.stdout.write(f"  soggetto {soggetto.pk}: «{prima or '(vuota)'}» -> «{dopo or '(vuota)'}»")
        self.stdout.write(f"Denominazioni cambiate: {len(cambiati)}")
