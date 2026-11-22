"""
Operazioni sull'archivio. Le pagine (views.py) non scrivono mai direttamente
nelle tabelle: passano da qui, così le regole stanno in un posto solo.
"""
from django.db import transaction

from soggetti import servizi as anagrafica

from . import models
from .models import Assegnazione, CollegamentoFile, Faldone, Fascicolo, SoggettoInIndagine


class OperazioneNonAmmessa(Exception):
    """L'utente non può fare questa operazione su questo fascicolo."""


def conteggi_per_faldone(utente):
    """[(faldone, numero di fascicoli che l'utente può vedere)]: mai il totale reale."""
    visibili = Fascicolo.objects.visibili_a(utente)
    return [(faldone, visibili.filter(faldone=faldone).count()) for faldone in Faldone.objects.order_by("ordine")]


def fascicolo_azienda(soggetto):
    """Il fascicolo del soggetto nel faldone Aziende; lo crea se non c'è. Restituisce (fascicolo, creato)."""
    return Fascicolo.objects.get_or_create(
        faldone=Faldone.objects.get(codice=models.AZIENDE),
        soggetto=soggetto,
        defaults={"titolo": anagrafica.etichetta(soggetto)[:200]},
    )


def acquisisci_azienda(tipo, valore, denominazione=""):
    """
    Trova o crea il soggetto con quell'identificativo e il suo fascicolo nel faldone
    Aziende. Può sollevare anagrafica.IdentificativoNonValido.
    """
    with transaction.atomic():
        soggetto, _ = anagrafica.trova_o_crea(tipo, valore, denominazione)
        fascicolo, creato = fascicolo_azienda(soggetto)
        if not creato:
            # la denominazione può essere arrivata dopo: il titolo la segue
            titolo = anagrafica.etichetta(soggetto)[:200]
            if fascicolo.titolo != titolo:
                fascicolo.titolo = titolo
                fascicolo.save(update_fields=["titolo"])
    return fascicolo


def apri_indagine(utente, titolo, descrizione=""):
    """Apre un fascicolo d'indagine: chi lo apre vi è assegnato e ne decide le persone (DECISIONI.md, n. 18)."""
    if not utente.has_perm("archivio.apre_indagini"):
        raise OperazioneNonAmmessa("Non hai il diritto di aprire indagini.")
    titolo = (titolo or "").strip()
    if not titolo:
        raise OperazioneNonAmmessa("Indicare il titolo dell'indagine.")
    with transaction.atomic():
        fascicolo = Fascicolo.objects.create(
            faldone=Faldone.objects.get(codice=models.INDAGINI), titolo=titolo[:200],
            descrizione=(descrizione or "").strip(), creato_da=utente,
        )
        Assegnazione.objects.create(fascicolo=fascicolo, utente=utente, assegnato_da=utente)
    return fascicolo


def e_indagine(fascicolo):
    return fascicolo.faldone.codice == models.INDAGINI


def _solo_chi_ha_aperto(fascicolo, utente):
    if not e_indagine(fascicolo) or fascicolo.creato_da_id != utente.pk:
        raise OperazioneNonAmmessa("Le persone assegnate le decide chi ha aperto l'indagine.")


def _solo_assegnati(fascicolo, utente):
    if not e_indagine(fascicolo) or not fascicolo.assegnazioni.filter(utente=utente).exists():
        raise OperazioneNonAmmessa("Operazione riservata alle persone assegnate all'indagine.")


def assegna(fascicolo, persona, da):
    _solo_chi_ha_aperto(fascicolo, da)
    Assegnazione.objects.get_or_create(fascicolo=fascicolo, utente=persona, defaults={"assegnato_da": da})


def revoca(fascicolo, persona, da):
    _solo_chi_ha_aperto(fascicolo, da)
    if persona.pk == fascicolo.creato_da_id:
        raise OperazioneNonAmmessa("Chi ha aperto l'indagine non può essere tolto.")
    Assegnazione.objects.filter(fascicolo=fascicolo, utente=persona).delete()


def aggiungi_soggetto(fascicolo, tipo, valore, da, nota=""):
    """Collega all'indagine il soggetto con quell'identificativo (creandolo provvisorio se manca)."""
    _solo_assegnati(fascicolo, da)
    with transaction.atomic():
        soggetto, _ = anagrafica.trova_o_crea(tipo, valore)
        SoggettoInIndagine.objects.get_or_create(
            fascicolo=fascicolo, soggetto=soggetto, defaults={"aggiunto_da": da, "nota": (nota or "")[:255]}
        )
    return soggetto


def togli_soggetto(fascicolo, numero, da):
    _solo_assegnati(fascicolo, da)
    SoggettoInIndagine.objects.filter(fascicolo=fascicolo, pk=numero).delete()


def collega_file_all_azienda(file, soggetto, origine):
    """
    Collega un file al fascicolo dell'azienda (creandolo se manca). Il file non si
    sposta: resta nel suo caricamento. Restituisce il fascicolo dell'azienda.
    """
    fascicolo, _ = fascicolo_azienda(soggetto)
    CollegamentoFile.objects.get_or_create(file=file, fascicolo=fascicolo, defaults={"origine": origine})
    return fascicolo


def file_collegati_visibili(fascicolo, utente):
    """I file collegati a un fascicolo d'azienda che l'utente può vedere: quelli dei caricamenti a lui visibili."""
    return (
        CollegamentoFile.objects.filter(
            fascicolo=fascicolo, file__fascicolo__in=Fascicolo.objects.visibili_a(utente)
        )
        .exclude(file__stato=models.FILE_ANNULLATO)
        .select_related("file", "file__fascicolo").order_by("-collegato_il")
    )
