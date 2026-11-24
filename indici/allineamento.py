"""
RIALLINEAMENTO DELLE DENOMINAZIONI (DECISIONI.md, n. 93).

Rimette in ordine i nomi dei soggetti già presenti, applicando la stessa regola che
vale per i dati nuovi (soggetti.servizi.imposta_denominazione):

  1. il nome dell'anagrafica ufficiale, dal periodo più recente che ne ha uno;
  2. altrimenti, se il soggetto non ha un nome vero, il nome confermato in un documento;
  3. altrimenti resta com'è (un segnaposto come "non rilevata" viene tolto).

Poi allinea il titolo del fascicolo nel faldone Aziende. Si può rilanciare: se è tutto
a posto non cambia nulla.
"""
from archivio import servizi as archivio
from elaborazione import models as elaborazione
from elaborazione.models import EntitaEstratta
from soggetti import servizi as anagrafica
from soggetti.models import DatiPerPeriodo, Soggetto


def esegui():
    """Restituisce [(soggetto, nome di prima, nome di dopo)] per i soggetti cambiati."""
    cambiati = []
    for soggetto in Soggetto.objects.order_by("pk"):
        prima = soggetto.denominazione
        ufficiale = next(
            (anagrafica.nome_vero(d.denominazione) for d in DatiPerPeriodo.objects.filter(soggetto=soggetto).order_by("-periodo")
             if anagrafica.nome_vero(d.denominazione)), "",
        )
        if ufficiale:
            anagrafica.imposta_denominazione(soggetto, ufficiale, ufficiale=True)
        elif not anagrafica.nome_vero(soggetto.denominazione):
            dal_documento = (
                EntitaEstratta.objects.utilizzabili()
                .filter(soggetto=soggetto, fonte=elaborazione.DA_DOCUMENTO, etichetta="DENOMINAZIONE")
                .order_by("-estratta_il").first()
            )
            if dal_documento is not None:
                anagrafica.imposta_denominazione(soggetto, dal_documento.valore)
            elif soggetto.denominazione:
                soggetto.denominazione = ""   # era un segnaposto, non un nome
                soggetto.save(update_fields=["denominazione"])
        archivio.allinea_titolo(soggetto)
        if soggetto.denominazione != prima:
            cambiati.append((soggetto, prima, soggetto.denominazione))
    return cambiati
