from django.core.management.base import BaseCommand

from elaborazione.catalogo_iniziale import VOCI
from elaborazione.models import VoceCatalogo


class Command(BaseCommand):
    help = "Carica le prime voci del catalogo delle entità. Ripetibile: non modifica le voci già presenti."

    def handle(self, *args, **opzioni):
        nuove = 0
        for ordine, (codice, descrizione, tipo, ha_periodo, multipla, cambia, sinonimi) in enumerate(VOCI, start=1):
            _, creata = VoceCatalogo.objects.get_or_create(
                codice=codice,
                defaults={
                    "descrizione": descrizione, "tipo_valore": tipo, "ha_periodo": ha_periodo, "multipla": multipla,
                    "cambia_nel_tempo": cambia, "sinonimi": "\n".join(sinonimi), "ordine": ordine * 10,
                },
            )
            nuove += creata
        self.stdout.write(f"Catalogo delle entità: {nuove} voci aggiunte, {len(VOCI) - nuove} già presenti.")
