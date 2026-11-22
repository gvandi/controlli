"""
CARICAMENTO DEI FILE: le regole di un fascicolo del faldone Caricamenti.

    bozza  --conferma-->  confermato  --annulla-->  annullato
      |
      +--elimina--> (cancellato davvero: nessun dato ne è ancora derivato)

In bozza l'ispettore aggiunge file, completa i metadati e indica i soggetti; alla
conferma i file passano da "bozza" a "ricevuto" e diventano lavoro per
l'elaborazione. Dopo la conferma non si cancella più: si annulla, lasciando
traccia (DECISIONI.md, n. 65).

I file non si spostano mai (n. 64): il contenuto sta nel deposito, qui si scrivono
solo le righe del database.
"""
import datetime
import mimetypes
import pathlib

from django.conf import settings
from django.db import transaction

from soggetti import servizi as anagrafica

from . import deposito, ingresso, models
from .models import Caricamento, Evento, Faldone, Fascicolo, FileCaricato, SoggettoDichiarato

# Funzioni da chiamare quando un caricamento viene annullato, con il fascicolo: chi ha
# derivato dati dai suoi file (l'app elaborazione) vi si iscrive per ritirarli. Così
# l'archivio non ha bisogno di conoscere chi lo usa.
AL_RITIRO = []

CAMPI_EREDITABILI = ("provenienza", "tipo_documento", "natura", "periodo_dal", "periodo_al")


class NonAmmesso(Exception):
    """L'operazione non si può fare su questo caricamento, in questo stato o da questo utente."""


# ---------------------------------------------------------------------
# Impostazioni
# ---------------------------------------------------------------------
def cartella_deposito():
    return pathlib.Path(getattr(settings, "ARCHIVIO_DEPOSITO", pathlib.Path(settings.MEDIA_ROOT) / "archivio"))


def _limite(nome, predefinito):
    return int(getattr(settings, nome, predefinito))


def massimo_per_file():
    return _limite("ARCHIVIO_MASSIMO_BYTE_PER_FILE", 500 * 1024 * 1024)


def massimo_file_nello_zip():
    return _limite("ARCHIVIO_ZIP_MASSIMO_FILE", 2000)


def massimo_byte_nello_zip():
    return _limite("ARCHIVIO_ZIP_MASSIMO_BYTE", 2 * 1024 * 1024 * 1024)


# ---------------------------------------------------------------------
# Diritti e stato
# ---------------------------------------------------------------------
def e_caricamento(fascicolo):
    return fascicolo.faldone.codice == models.CARICAMENTI


def puo_caricare(utente):
    return utente.has_perm("archivio.add_filecaricato")


def _modificabile(fascicolo, utente, solo_in_bozza=True):
    """Chi può lavorare su un caricamento: chi lo vede e ha il diritto di caricare."""
    if not e_caricamento(fascicolo) or not puo_caricare(utente):
        raise NonAmmesso("Non hai il diritto di modificare questo caricamento.")
    if not Fascicolo.objects.visibili_a(utente).filter(pk=fascicolo.pk).exists():
        raise NonAmmesso("Non hai il diritto di modificare questo caricamento.")
    if solo_in_bozza and fascicolo.stato != models.BOZZA:
        raise NonAmmesso("Il caricamento è già stato confermato: non si può più modificare.")


def _registra(fascicolo, utente, azione, dettaglio=""):
    Evento.objects.create(fascicolo=fascicolo, utente=utente, azione=azione, dettaglio=dettaglio[:500])


# ---------------------------------------------------------------------
# Nascita del caricamento
# ---------------------------------------------------------------------
def indagini_di(utente):
    """Le indagini a cui l'utente è assegnato: quelle a cui può riservare un caricamento."""
    return Fascicolo.objects.filter(faldone__codice=models.INDAGINI, assegnazioni__utente=utente).distinct()


def nuovo(utente, titolo, indagine=None):
    """
    Apre un fascicolo di caricamento in bozza. La visibilità si decide qui, prima
    di caricare qualsiasi file: generale, oppure riservata a un'indagine a cui
    l'utente è assegnato.
    """
    if not puo_caricare(utente):
        raise NonAmmesso("Non hai il diritto di caricare file.")
    titolo = (titolo or "").strip()
    if not titolo:
        raise NonAmmesso("Indicare un titolo per il caricamento.")
    if indagine is not None and not indagini_di(utente).filter(pk=indagine.pk).exists():
        raise NonAmmesso("Puoi riservare un caricamento solo a un'indagine a cui sei assegnato.")
    with transaction.atomic():
        fascicolo = Fascicolo.objects.create(
            faldone=Faldone.objects.get(codice=models.CARICAMENTI), titolo=titolo[:200],
            stato=models.BOZZA, creato_da=utente, riservato_a=indagine,
        )
        Caricamento.objects.create(fascicolo=fascicolo)
        _registra(fascicolo, utente, "creato", "riservato a un'indagine" if indagine else "visibilità generale")
    return fascicolo


# ---------------------------------------------------------------------
# File
# ---------------------------------------------------------------------
def _percorso_libero(fascicolo, percorso):
    """Se il percorso è già usato nel fascicolo, aggiunge " (2)", " (3)"... prima dell'estensione."""
    usati = set(fascicolo.file.values_list("percorso_originale", flat=True))
    if percorso not in usati:
        return percorso
    base, punto, estensione = percorso.rpartition(".")
    if not punto or "/" in estensione:
        base, estensione = percorso, ""
    numero = 2
    while True:
        candidato = f"{base} ({numero})" + (f".{estensione}" if estensione else "")
        if candidato not in usati:
            return candidato
        numero += 1


def _aggiungi(fascicolo, utente, percorso, blocchi, limite):
    """
    Salva un contenuto e ne scrive la riga. Restituisce (esito, file):
      "aggiunto"       file nuovo
      "già presente"   stesso percorso e stesso contenuto: non si duplica
      "rinominato"     stesso percorso ma contenuto diverso: tenuto con un suffisso
    """
    impronta, dimensione = deposito.salva(cartella_deposito(), blocchi, limite)
    esistente = fascicolo.file.filter(percorso_originale=percorso).first()
    if esistente is not None and esistente.impronta == impronta:
        return "già presente", esistente
    libero = _percorso_libero(fascicolo, percorso)
    riga = FileCaricato.objects.create(
        fascicolo=fascicolo, percorso_originale=libero, impronta=impronta, dimensione=dimensione,
        tipo_mime=(mimetypes.guess_type(libero)[0] or "")[:100], caricato_da=utente,
    )
    return ("aggiunto" if libero == percorso else "rinominato"), riga


def aggiungi_file(fascicolo, utente, caricati, percorsi=()):
    """
    Aggiunge i file scelti dal browser. 'percorsi' sono i percorsi relativi nello
    stesso ordine (scelta di una cartella); se mancano vale il nome del file.
    Un file ZIP viene aperto e ne entrano i file contenuti.
    Restituisce il resoconto: {"aggiunti", "presenti", "rinominati", "rifiutati": [(nome, motivo)]}
    ("presenti": stesso percorso e stesso contenuto di un file già nel caricamento).
    """
    _modificabile(fascicolo, utente)
    resoconto = {"aggiunti": 0, "presenti": 0, "rinominati": 0, "rifiutati": []}
    chiave = {"aggiunto": "aggiunti", "già presente": "presenti", "rinominato": "rinominati"}

    def prendi(percorso, blocchi, nome_mostrato):
        try:
            esito, _ = _aggiungi(fascicolo, utente, percorso, blocchi, massimo_per_file())
            resoconto[chiave[esito]] += 1
        except deposito.TroppoGrande:
            resoconto["rifiutati"].append((nome_mostrato, "supera la dimensione massima per file"))

    for posizione, caricato in enumerate(caricati):
        dichiarato = percorsi[posizione] if posizione < len(percorsi) and percorsi[posizione] else caricato.name
        percorso = ingresso.pulisci_percorso(dichiarato)
        if percorso is None:
            resoconto["rifiutati"].append((str(dichiarato)[:200], "percorso non ammesso"))
        elif percorso.lower().endswith(".zip"):
            try:
                voci, rifiutate = ingresso.apri_zip(caricato, massimo_file_nello_zip(), massimo_byte_nello_zip())
            except ingresso.ArchivioNonValido as problema:
                resoconto["rifiutati"].append((percorso, str(problema)))
                continue
            resoconto["rifiutati"].extend(rifiutate)
            for percorso_interno, lettore in voci:
                prendi(percorso_interno, lettore(), percorso_interno)
        elif ingresso.e_un_archivio(percorso):
            resoconto["rifiutati"].append((percorso, "tipo di archivio non gestito: usare un file ZIP"))
        else:
            prendi(percorso, caricato.chunks(), percorso)

    _registra(
        fascicolo, utente, "file aggiunti",
        f"{resoconto['aggiunti']} aggiunti, {resoconto['presenti']} già presenti, "
        f"{resoconto['rinominati']} rinominati, {len(resoconto['rifiutati'])} rifiutati",
    )
    return resoconto


def _elimina_contenuti_orfani(impronte):
    """Toglie dal deposito i contenuti che nessun file usa più."""
    for impronta in set(impronte):
        if not FileCaricato.objects.filter(impronta=impronta).exists():
            deposito.elimina(cartella_deposito(), impronta)


def togli_file(file, utente):
    _modificabile(file.fascicolo, utente)
    impronta, percorso, fascicolo = file.impronta, file.percorso_originale, file.fascicolo
    file.delete()
    _elimina_contenuti_orfani([impronta])
    _registra(fascicolo, utente, "file tolto", percorso)


def doppioni(fascicolo):
    """Impronte che nel fascicolo compaiono in più di un file (stesso contenuto, percorsi diversi)."""
    viste, ripetute = set(), set()
    for impronta in fascicolo.file.values_list("impronta", flat=True):
        (ripetute if impronta in viste else viste).add(impronta)
    return ripetute


def apri_contenuto(file):
    """Il contenuto originale del file, in lettura."""
    return open(deposito.percorso(cartella_deposito(), file.impronta), "rb")


# ---------------------------------------------------------------------
# Metadati dichiarati ed ereditarietà
# ---------------------------------------------------------------------
def _data(testo):
    testo = (testo or "").strip()
    if not testo:
        return None
    try:
        return datetime.date.fromisoformat(testo)
    except ValueError:
        raise NonAmmesso(f"'{testo}' non è una data valida (formato: AAAA-MM-GG).")


def salva_metadati(oggetto, utente, dati, tipi_documento):
    """
    Scrive i metadati su un Caricamento o su un FileCaricato. Su un file, un campo
    lasciato vuoto significa "eredita dal caricamento".
    dati: provenienza, tipo_documento (numero), natura, periodo_dal, periodo_al, note.
    """
    fascicolo = oggetto.fascicolo
    _modificabile(fascicolo, utente)
    natura = (dati.get("natura") or "").strip()
    if natura and natura not in dict(models.NATURE):
        raise NonAmmesso("Natura del file non prevista.")
    numero = str(dati.get("tipo_documento") or "")
    tipo = tipi_documento.filter(pk=int(numero)).first() if numero.isdigit() else None
    dal, al = _data(dati.get("periodo_dal")), _data(dati.get("periodo_al"))
    if dal and al and dal > al:
        raise NonAmmesso("Il periodo finisce prima di cominciare.")
    oggetto.provenienza = (dati.get("provenienza") or "").strip()[:200]
    oggetto.tipo_documento, oggetto.natura, oggetto.periodo_dal, oggetto.periodo_al = tipo, natura, dal, al
    if isinstance(oggetto, Caricamento):
        oggetto.note = (dati.get("note") or "").strip()
    oggetto.save()


def metadati_effettivi(file):
    """
    I metadati che valgono per un file: {campo: (valore, ereditato)}.
    Vale il valore del file se c'è, altrimenti quello del caricamento.
    """
    # Letto dal database ogni volta: i metadati del caricamento possono essere stati
    # corretti dopo che questo oggetto è stato caricato in memoria.
    caricamento = Caricamento.objects.select_related("tipo_documento").filter(pk=file.fascicolo_id).first()
    effettivi = {}
    for campo in CAMPI_EREDITABILI:
        proprio = getattr(file, campo)
        effettivi[campo] = (proprio, False) if proprio else (getattr(caricamento, campo, None), True)
    return effettivi


# ---------------------------------------------------------------------
# Soggetti dichiarati (i campi COE)
# ---------------------------------------------------------------------
def dichiarati(su):
    """Le righe dichiarate su un fascicolo o su un file, il principale per primo."""
    filtro = {"file": su} if isinstance(su, FileCaricato) else {"fascicolo": su}
    return SoggettoDichiarato.objects.filter(**filtro).select_related("tipo", "soggetto").order_by("-principale", "pk")


def dichiara_soggetto(su, utente, tipo, valore):
    """
    Aggiunge un identificativo a un fascicolo di caricamento o a un file. Il primo
    diventa il soggetto principale, i successivi sono collegati. Il soggetto viene
    cercato in anagrafica e, se manca, creato come provvisorio.
    Può sollevare anagrafica.IdentificativoNonValido.
    """
    fascicolo = su.fascicolo if isinstance(su, FileCaricato) else su
    _modificabile(fascicolo, utente)
    with transaction.atomic():
        soggetto, _ = anagrafica.trova_o_crea(tipo, valore)
        esistenti = dichiarati(su)
        if esistenti.filter(soggetto=soggetto).exists():
            raise NonAmmesso("Questo soggetto è già indicato.")
        return SoggettoDichiarato.objects.create(
            fascicolo=None if isinstance(su, FileCaricato) else su,
            file=su if isinstance(su, FileCaricato) else None,
            tipo=tipo, valore_originale=str(valore).strip()[:60], valore_normalizzato=tipo.normalizza(valore),
            principale=not esistenti.exists(), soggetto=soggetto,
        )


def togli_soggetto_dichiarato(su, utente, numero):
    fascicolo = su.fascicolo if isinstance(su, FileCaricato) else su
    _modificabile(fascicolo, utente)
    with transaction.atomic():
        dichiarati(su).filter(pk=numero).delete()
        rimasti = dichiarati(su)
        if rimasti.exists() and not rimasti.filter(principale=True).exists():
            primo = rimasti.order_by("pk").first()
            primo.principale = True
            primo.save(update_fields=["principale"])


def rendi_principale(su, utente, numero):
    fascicolo = su.fascicolo if isinstance(su, FileCaricato) else su
    _modificabile(fascicolo, utente)
    with transaction.atomic():
        if dichiarati(su).filter(pk=numero).exists():
            dichiarati(su).update(principale=False)
            dichiarati(su).filter(pk=numero).update(principale=True)


def soggetti_effettivi(file):
    """(righe, ereditati): i soggetti del file se ne dichiara di propri, altrimenti quelli del caricamento."""
    propri = list(dichiarati(file))
    return (propri, False) if propri else (list(dichiarati(file.fascicolo)), True)


# ---------------------------------------------------------------------
# Conferma, eliminazione, annullamento
# ---------------------------------------------------------------------
def conferma(fascicolo, utente):
    """Consegna il caricamento all'elaborazione: i file passano da "bozza" a "ricevuto"."""
    _modificabile(fascicolo, utente)
    with transaction.atomic():
        numero = fascicolo.file.filter(stato=models.FILE_BOZZA).update(stato=models.FILE_RICEVUTO)
        if not numero:
            raise NonAmmesso("Il caricamento non contiene file.")
        Fascicolo.objects.filter(pk=fascicolo.pk).update(stato=models.CONFERMATO)
        _registra(fascicolo, utente, "confermato", f"{numero} file")
    fascicolo.stato = models.CONFERMATO


def elimina_bozza(fascicolo, utente):
    """Cancella davvero un caricamento mai confermato, con i suoi file."""
    _modificabile(fascicolo, utente)
    impronte = list(fascicolo.file.values_list("impronta", flat=True))
    titolo, numero = fascicolo.titolo, fascicolo.pk
    with transaction.atomic():
        _registra(None, utente, "bozza eliminata", f"fascicolo n. {numero} «{titolo}», {len(impronte)} file")
        fascicolo.delete()
    _elimina_contenuti_orfani(impronte)


def annulla(fascicolo, utente):
    """
    Ritira un caricamento confermato. I file restano nel deposito e nel registro,
    in stato "annullato": l'elaborazione non li prende più.
    """
    _modificabile(fascicolo, utente, solo_in_bozza=False)
    if fascicolo.stato != models.CONFERMATO:
        raise NonAmmesso("Si annulla solo un caricamento confermato.")
    with transaction.atomic():
        numero = fascicolo.file.exclude(stato=models.FILE_ANNULLATO).update(stato=models.FILE_ANNULLATO)
        Fascicolo.objects.filter(pk=fascicolo.pk).update(stato=models.ANNULLATO)
        models.CollegamentoFile.objects.filter(file__fascicolo=fascicolo).delete()
        for ritira in AL_RITIRO:
            ritira(fascicolo)
        _registra(fascicolo, utente, "annullato", f"{numero} file")
    fascicolo.stato = models.ANNULLATO
