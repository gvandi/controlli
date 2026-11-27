"""
CANCELLAZIONE DEFINITIVA di un file e di tutto ciò che ne è stato ricavato.

È l'eccezione alla regola (DECISIONI.md, n. 65) per cui dopo la conferma un
caricamento si annulla e non si cancella: serve quando un file non doveva proprio
entrare (caricato per errore, appartenente a un'altra pratica, da rimuovere per
obbligo). Per questo richiede un diritto apposito, una motivazione scritta, e
mostra prima che cosa verrà tolto.

Che cosa sparisce:
  - la riga del file e tutto ciò che vi è legato nel database: elaborazioni, testo
    delle pagine, entità estratte, soggetti dichiarati sul file, collegamenti ai
    fascicoli delle aziende. Non c'è un elenco scritto a mano: si segue ogni
    legame verso il file, quindi anche le tabelle che nasceranno in futuro;
  - il contenuto nel deposito, se nessun altro file ha lo stesso contenuto;
  - a richiesta, i soggetti che esistevano solo per questo file (vedi sotto).

Che cosa resta: una riga nel registro con chi, quando, il motivo, il numero e
l'impronta del file. Non il nome né il percorso, che possono essere proprio ciò
che andava rimosso.

SOGGETTI. Un soggetto creato perché nominato nel file può restare senza nessun
altro dato. Si toglie solo se è provvisorio e se, cancellato il file, nulla lo
cita più: nessuna entità, nessuna dichiarazione, nessuna indagine, nessun altro
file collegato al suo fascicolo.

CHI HA DERIVATO ALTRI DATI dal file fuori dal database, o in forma aggregata,
si iscrive in ALLA_CANCELLAZIONE: viene chiamato con il file prima che sparisca.
"""
from django.contrib.admin.utils import NestedObjects
from django.db import router, transaction

from soggetti.models import IdentificativoSoggetto, Soggetto

from . import caricamento, models
from .models import Evento, Fascicolo, FileCaricato

# Funzioni chiamate con (file, in_prova) prima della cancellazione. in_prova è vero
# quando si sta solo calcolando l'anteprima: in quel caso non devono toccare nulla
# fuori dal database, perché tutto verrà disfatto.
ALLA_CANCELLAZIONE = []

# Come chiamare, nella pagina, le righe che spariscono
NOMI = {
    "archivio.FileCaricato": "file",
    "archivio.SoggettoDichiarato": "società dichiarate sul file",
    "archivio.CollegamentoFile": "collegamenti ai fascicoli delle società",
    "elaborazione.Elaborazione": "elaborazioni",
    "elaborazione.TestoPagina": "pagine di testo",
    "elaborazione.EntitaEstratta": "entità estratte",
    "elaborazione.Documento": "documenti riconosciuti",
    "elaborazione.ParteDelDocumento": "parti dei documenti (mittente, destinatario, vettore)",
    "archivio.Fascicolo": "fascicoli di società rimasti vuoti",
    "soggetti.Soggetto": "società che esistevano solo per questo file",
    "soggetti.IdentificativoSoggetto": "identificativi di quelle società",
}


class NonAmmessa(Exception):
    """La cancellazione non si può fare: manca il diritto, la motivazione, o il file è in lavorazione."""


def puo_cancellare(utente, file):
    """Serve il diritto apposito E poter vedere il file: nemmeno chi cancella vede le indagini altrui."""
    return (
        utente.has_perm("archivio.cancella_definitivamente")
        and Fascicolo.objects.visibili_a(utente).filter(pk=file.fascicolo_id).exists()
    )


def _legati(oggetti):
    """Tutte le righe che spariscono cancellando gli oggetti dati: {modello: {righe}}."""
    raccolta = NestedObjects(using=router.db_for_write(FileCaricato))
    raccolta.collect(oggetti)
    return raccolta.model_objs


def _citato_altrove(soggetto):
    """Vero se, a questo punto, qualcosa cita ancora il soggetto oltre ai suoi identificativi e al suo fascicolo vuoto."""
    for legame in Soggetto._meta.get_fields(include_hidden=True):
        if not (legame.auto_created and legame.is_relation) or legame.related_model is IdentificativoSoggetto:
            continue
        righe = legame.related_model._base_manager.filter(**{legame.field.name: soggetto})
        if legame.related_model is Fascicolo:
            righe = righe.filter(file_collegati__isnull=False)  # un fascicolo d'azienda con altri file
        if righe.exists():
            return True
    return False


def _esegui(file, anche_soggetti, in_prova):
    """Cancella nel database e restituisce il riepilogo {nome: quante righe}. Da chiamare dentro una transazione."""
    for avvisa in ALLA_CANCELLAZIONE:
        avvisa(file, in_prova)

    legati = _legati([file])
    riepilogo = {}
    # I soggetti toccati dal file: chiunque, fra le righe che spariscono, ne citi uno
    candidati = {
        riga.soggetto_id for righe in legati.values() for riga in righe if getattr(riga, "soggetto_id", None)
    }
    for modello, righe in legati.items():
        riepilogo[modello._meta.label] = len(righe)
    file.delete()

    if anche_soggetti:
        for soggetto in Soggetto.objects.filter(pk__in=candidati, provvisorio=True):
            if _citato_altrove(soggetto):
                continue
            # Prima il suo fascicolo d'azienda, rimasto senza file, poi il soggetto con i suoi identificativi
            vuoti = list(Fascicolo.objects.filter(soggetto=soggetto, faldone__codice=models.AZIENDE))
            for gruppo in ([vuoti] if vuoti else []) + [[soggetto]]:
                for modello, righe in _legati(gruppo).items():
                    riepilogo[modello._meta.label] = riepilogo.get(modello._meta.label, 0) + len(righe)
                for riga in gruppo:
                    riga.delete()
    return riepilogo


def _leggibile(riepilogo):
    """Il riepilogo con i nomi per la pagina, nell'ordine di NOMI; ciò che non ha un nome mostra il suo."""
    ordinati = [(NOMI[chiave], riepilogo[chiave]) for chiave in NOMI if riepilogo.get(chiave)]
    return ordinati + [(chiave, numero) for chiave, numero in riepilogo.items() if chiave not in NOMI and numero]


def anteprima(file, anche_soggetti=False):
    """
    Che cosa verrebbe cancellato, senza cancellare nulla: la cancellazione viene
    eseguita davvero in una transazione che poi si disfa, così l'elenco è esatto.
    Restituisce {"righe": [(nome, quante)], "contenuto_condiviso": bool}.
    """
    condiviso = FileCaricato.objects.filter(impronta=file.impronta).exclude(pk=file.pk).exists()
    with transaction.atomic():
        riepilogo = _esegui(FileCaricato.objects.get(pk=file.pk), anche_soggetti, in_prova=True)
        transaction.set_rollback(True)
    return {"righe": _leggibile(riepilogo), "contenuto_condiviso": condiviso}


def cancella(file, utente, motivazione, anche_soggetti=False):
    """
    Cancella definitivamente il file e ciò che ne deriva. Restituisce il riepilogo
    [(nome, quante)]. Solleva NonAmmessa senza toccare nulla se manca qualcosa.
    """
    motivazione = " ".join((motivazione or "").split())
    if not puo_cancellare(utente, file):
        raise NonAmmessa("Non hai il diritto di cancellare questo file.")
    if len(motivazione) < 10:
        raise NonAmmessa("Scrivere il motivo della cancellazione (almeno dieci caratteri).")
    if file.stato == models.FILE_IN_ELABORAZIONE:
        raise NonAmmessa("Il file è in elaborazione in questo momento: riprovare quando ha finito.")

    numero, impronta, fascicolo = file.pk, file.impronta, file.fascicolo
    with transaction.atomic():
        riepilogo = _leggibile(_esegui(FileCaricato.objects.select_for_update().get(pk=numero), anche_soggetti, False))
        dettaglio = ", ".join(f"{quante} {nome}" for nome, quante in riepilogo)
        Evento.objects.create(
            fascicolo=fascicolo, utente=utente, azione="file cancellato",
            dettaglio=f"file n. {numero}, impronta {impronta[:16]}; motivo: {motivazione}"[:500],
        )
        Evento.objects.create(
            fascicolo=fascicolo, utente=utente, azione="dati cancellati", dettaglio=dettaglio[:500]
        )
    # Il contenuto si toglie solo a cancellazione riuscita, e solo se nessun altro file lo usa
    caricamento._elimina_contenuti_orfani([impronta])
    return riepilogo
