"""
CODA DI ELABORAZIONE: prende i file ricevuti, li fa leggere e ne salva testo ed entità.

    ricevuto --> in elaborazione --> elaborato        tutto a posto
                                 --> da rivedere      qualcosa va confermato da una persona
                                 --> errore           lettura fallita: si ritenta, fino a un massimo
                                 --> ricevuto         lettura PARZIALE: fatte le sole regole perché il
                                                      modello non era disponibile; il file resta da
                                                      elaborare e viene completato quando il modello torna

Regole (DECISIONI.md, n. 66 e 70-75):
  - un file si elabora UNA volta: "elaborato" è definitivo;
  - se il tempo finisce, i file non presi restano "ricevuto" e si riprende la volta dopo,
    prima quelli con priorità più alta, poi i più vecchi;
  - un file che nessun lettore disponibile sa leggere viene saltato, non segnato come errore;
  - ogni entità è salvata con il file, la pagina e la citazione da cui viene;
  - le entità fuori catalogo si raccolgono comunque, con la voce vuota.

I LETTORI sono intercambiabili: ognuno dichiara quali nature di file sa leggere e
restituisce una Lettura. Qui ce ne sono due: i file che sono già testo (regole, più
il modello per le entità) e le scansioni e i PDF (modello visivo). Le prove ne usano
uno finto.
"""
import collections
import datetime
import logging
import os
import re
import time

from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from archivio import caricamento, deposito
from archivio import models as archivio
from archivio import servizi as servizi_archivio
from archivio.models import Fascicolo, FileCaricato
from decodifiche.models import TipoIdentificativo
from soggetti import servizi as anagrafica

from . import lettura_modello, models, regole, riconoscimento
from .models import Elaborazione, EntitaEstratta, TestoPagina, VoceCatalogo

registro = logging.getLogger("elaborazione.coda")

ELABORATO, DA_RIVEDERE, ERRORE, SALTATO, PARZIALE = "elaborato", "da rivedere", "errore", "saltato", "parziale"

# Un file di testo lungo si passa al modello a pezzi di questa lunghezza (caratteri)
CARATTERI_PER_PEZZO = 6000

# Etichetta prodotta dalle regole -> codice del tipo di identificativo in anagrafica
TIPO_PER_REGOLA = {regole.COE: "COE", regole.PARTITA_IVA: "PIVA_IT"}
# Etichette delle regole che, lette da una scansione, vanno confermate da una persona
DELICATE_SE_DA_SCANSIONE = (regole.COE, regole.PARTITA_IVA, regole.IMPORTO)

# pagine: [(numero, testo, origine)]   entita: [dizionari con etichetta, valore, pagina, fonte, ...]
# completa: falso se sono state applicate le sole regole perché il modello non era disponibile
Lettura = collections.namedtuple("Lettura", "pagine entita modello versione_prompt completa", defaults=(True,))


def _impostazione(nome, predefinito):
    return getattr(settings, nome, predefinito)


def massimo_tentativi():
    return int(_impostazione("ELABORAZIONE_MASSIMO_TENTATIVI", 3))


def _compatto(testo):
    return re.sub(r"[\W_]+", "", str(testo or "").lower())


# =====================================================================
# 1. LETTORI
# =====================================================================
def _pezzi(testo, massimo=CARATTERI_PER_PEZZO):
    """Divide un testo lungo in pezzi, tagliando dove finisce un paragrafo o almeno una riga."""
    pezzi = []
    while len(testo) > massimo:
        taglio = max(testo.rfind("\n\n", 0, massimo), testo.rfind("\n", 0, massimo))
        taglio = taglio if taglio > massimo // 2 else massimo
        pezzi.append(testo[:taglio])
        testo = testo[taglio:]
    return pezzi + [testo] if testo or not pezzi else pezzi


class LettoreTesto:
    """
    File che sono già testo (testo semplice, XML): niente OCR. Le regole fisse
    leggono identificativi, date e importi; il modello propone le altre entità.

    Costruito con un LettoreModello, gli chiede le entità. Se il modello non è
    disponibile applica le sole regole e dichiara la lettura NON completa: il file
    resta da elaborare e verrà completato quando il modello torna.
    Costruito senza modello usa le sole regole e la lettura è completa: serve
    alle prove e a chi vuole espressamente fare a meno del modello.
    """

    nome = "testo-2"
    nature = (riconoscimento.TESTO, riconoscimento.XML)

    def __init__(self, modello=None):
        self._modello = modello

    def disponibile(self):
        return True, ""

    def leggi(self, percorso, natura, voci):
        with open(percorso, "rb") as contenuto:
            testo = contenuto.read().decode("utf-8", errors="replace")
        con_modello = self._modello is not None and self._modello.disponibile()[0]
        pagine, entita, evento = [], [], ""
        for numero, pezzo in enumerate(_pezzi(testo), start=1):
            pagine.append((numero, pezzo, models.TESTO_DIRETTO))
            entita += [dict(e, pagina=numero, fonte=models.DA_REGOLA) for e in regole.estrai(pezzo)]
            if con_modello:
                proposte, evento = self._modello.entita_dal_testo(pezzo, voci, evento)
                entita += [dict(proposta, pagina=numero, fonte=models.DA_MODELLO) for proposta in proposte]
        if con_modello:
            return Lettura(pagine, entita, self._modello.modello, lettura_modello.VERSIONE_PROMPT)
        return Lettura(pagine, entita, "", "", completa=self._modello is None)


class LettoreModello:
    """
    Scansioni e PDF, con il modello visivo locale: per ogni pagina la trascrizione,
    poi le regole sul testo, poi le entità proposte dal modello.
    """

    nome = "modello-visivo-1"
    nature = (riconoscimento.PDF, riconoscimento.IMMAGINE)

    def __init__(self, cliente=None, pagine_del_pdf=None, immagine_come_jpeg=None):
        self._cliente = cliente
        self._pagine_del_pdf = pagine_del_pdf or lettura_modello.pagine_del_pdf
        self._immagine_come_jpeg = immagine_come_jpeg or lettura_modello.immagine_come_jpeg

    @property
    def modello(self):
        return _impostazione("ELABORAZIONE_MODELLO_NOME", "")

    def disponibile(self):
        if self._cliente is not None:
            return True, ""
        indirizzo = _impostazione("ELABORAZIONE_MODELLO_URL", "")
        chiave = os.environ.get(_impostazione("ELABORAZIONE_MODELLO_VARIABILE_CHIAVE", ""), "")
        if not indirizzo or not self.modello or not chiave:
            return False, "modello locale non configurato (indirizzo, nome o chiave mancanti)"
        try:
            from openai import OpenAI
            import pdf2image  # noqa: F401
        except ImportError as errore:
            return False, f"libreria mancante: {errore.name} (vedi elaborazione/requirements-lettura.txt)"
        self._cliente = OpenAI(base_url=indirizzo, api_key=chiave)
        return True, ""

    def _parametri(self):
        return (
            int(_impostazione("ELABORAZIONE_MODELLO_MASSIMO_TOKEN", 6000)),
            dict(_impostazione("ELABORAZIONE_MODELLO_OPZIONI", {})),
        )

    def entita_dal_testo(self, testo, voci, evento_precedente=""):
        """
        Le entità che il modello propone per un testo, e l'ultimo evento incontrato.
        Gli identificativi li leggono le regole: quelli proposti dal modello non si usano (n. 23).
        """
        massimo, opzioni = self._parametri()
        proposte, evento = lettura_modello.estrai_entita(
            self._cliente, self.modello, testo, voci, evento_precedente, massimo, opzioni
        )
        riservate_alle_regole = {_compatto(etichetta) for etichetta in TIPO_PER_REGOLA}
        return [p for p in proposte if _compatto(p["etichetta"]) not in riservate_alle_regole], evento

    def leggi(self, percorso, natura, voci):
        massimo, opzioni = self._parametri()
        if natura == riconoscimento.PDF:
            immagini = self._pagine_del_pdf(percorso, int(_impostazione("ELABORAZIONE_PUNTI_PER_POLLICE", 200)))
        else:
            immagini = [self._immagine_come_jpeg(percorso)]
        pagine, entita, evento = [], [], ""
        for numero, jpeg in enumerate(immagini, start=1):
            testo = lettura_modello.trascrivi(self._cliente, self.modello, jpeg, massimo, opzioni)
            pagine.append((numero, testo, models.TESTO_OCR))
            entita += [dict(e, pagina=numero, fonte=models.DA_REGOLA) for e in regole.estrai(testo)]
            proposte, evento = self.entita_dal_testo(testo, voci, evento)
            entita += [dict(proposta, pagina=numero, fonte=models.DA_MODELLO) for proposta in proposte]
        return Lettura(pagine, entita, self.modello, lettura_modello.VERSIONE_PROMPT)


def lettori_predefiniti():
    """I lettori della coda vera: lo stesso modello serve i file di testo e le scansioni."""
    modello = LettoreModello()
    return [LettoreTesto(modello), modello]


# =====================================================================
# 2. CATALOGO
# =====================================================================
def voci_valide():
    oggi = datetime.date.today()
    return VoceCatalogo.objects.filter(
        Q(valida_dal__isnull=True) | Q(valida_dal__lte=oggi), Q(valida_al__isnull=True) | Q(valida_al__gte=oggi)
    ).order_by("ordine", "codice")


def _indice_delle_voci():
    """{etichetta compatta: voce}: per codice, descrizione e sinonimi."""
    indice = {}
    for voce in voci_valide():
        for nome in [voce.codice, voce.descrizione] + voce.sinonimi.splitlines():
            if _compatto(nome):
                indice.setdefault(_compatto(nome), voce)
    return indice


def promuovi(etichetta, voce):
    """
    Riconosce un'etichetta fuori catalogo come un altro nome di una voce: la aggiunge
    ai sinonimi e collega le entità già raccolte con quell'etichetta. I file non si
    rileggono. Restituisce quante entità sono diventate significative.
    """
    etichetta = " ".join(str(etichetta).split())
    if not _compatto(etichetta):
        return 0
    if _compatto(etichetta) not in {_compatto(s) for s in [voce.codice, voce.descrizione] + voce.sinonimi.splitlines()}:
        voce.sinonimi = (voce.sinonimi.rstrip("\n") + "\n" + etichetta).lstrip("\n")
        voce.save(update_fields=["sinonimi"])
    promosse = [
        e.pk for e in EntitaEstratta.objects.filter(voce__isnull=True).only("pk", "etichetta")
        if _compatto(e.etichetta) == _compatto(etichetta)
    ]
    return EntitaEstratta.objects.filter(pk__in=promosse).update(voce=voce)


# =====================================================================
# 3. ELABORAZIONE DI UN FILE
# =====================================================================
def _fallito(file, messaggio, elaborazione=None, definitivo=False):
    tentativi = massimo_tentativi() if definitivo else file.tentativi + 1
    FileCaricato.objects.filter(pk=file.pk).update(
        stato=archivio.FILE_ERRORE, tentativi=tentativi, ultimo_errore=messaggio[:2000]
    )
    if elaborazione is not None:
        Elaborazione.objects.filter(pk=elaborazione.pk).update(
            esito=models.ESITO_ERRORE, errore=messaggio[:2000], finita_il=timezone.now()
        )
    return ERRORE, messaggio


def elabora_file(file, lettori):
    """
    Elabora un file già preso dalla coda. Restituisce (esito, messaggio), con esito
    fra ELABORATO, DA_RIVEDERE, PARZIALE, ERRORE e SALTATO. Non solleva eccezioni: un file
    andato male non deve fermare la coda.
    """
    percorso = deposito.percorso(caricamento.cartella_deposito(), file.impronta)
    try:
        with open(percorso, "rb") as contenuto:
            natura = riconoscimento.natura(contenuto.read(2048))
    except OSError:
        return _fallito(file, "Il contenuto del file non è nel deposito.", definitivo=True)

    lettore = next((l for l in lettori if natura in l.nature), None)
    if lettore is None:
        return _fallito(file, f"Tipo di file non gestito ({natura}).", definitivo=True)
    disponibile, motivo = lettore.disponibile()
    if not disponibile:
        return SALTATO, motivo

    gia_parziale = Elaborazione.objects.filter(file=file, esito=models.ESITO_PARZIALE).exists()
    elaborazione = Elaborazione.objects.create(file=file, natura=natura, motore=lettore.nome)
    try:
        lettura = lettore.leggi(percorso, natura, [(v.codice, v.descrizione) for v in voci_valide()])
        if not lettura.completa and gia_parziale:
            # Le regole sono già state applicate una volta: finché il modello non torna non c'è altro da fare
            elaborazione.delete()
            return SALTATO, "file di testo già letti con le sole regole, in attesa del modello"
        with transaction.atomic():
            return _salva(file, elaborazione, lettura), ""
    except lettura_modello.LetturaFallita as errore:
        return _fallito(file, str(errore), elaborazione)
    except Exception as errore:
        registro.exception("Errore nell'elaborazione del file %s", file.pk)
        return _fallito(file, f"Errore imprevisto: {errore}", elaborazione)


def _salva(file, elaborazione, lettura):
    """Scrive testo, entità e collegamenti di una lettura riuscita. Restituisce lo stato finale del file."""
    testi = {numero: testo for numero, testo, _ in lettura.pagine}
    origini = {numero: origine for numero, _, origine in lettura.pagine}
    TestoPagina.objects.bulk_create([
        TestoPagina(elaborazione=elaborazione, pagina=numero, testo=testo, origine=origine)
        for numero, testo, origine in lettura.pagine
    ])

    indice = _indice_delle_voci()
    tipi = {t.codice: t for t in TipoIdentificativo.objects.filter(codice__in=TIPO_PER_REGOLA.values())}
    dichiarati, _ = caricamento.soggetti_effettivi(file)
    principale = next((d.soggetto for d in dichiarati if d.principale), None)
    rivedi_le_scansioni = bool(_impostazione("ELABORAZIONE_RIVEDI_LE_SCANSIONI", True))

    # Primo giro: riconoscere i soggetti nominati nel file attraverso i loro identificativi
    trovati, preparate = {}, []
    for entita in lettura.entita:
        nominato = None
        tipo = tipi.get(TIPO_PER_REGOLA.get(entita["etichetta"], ""))
        if entita["fonte"] == models.DA_REGOLA and tipo is not None and tipo.accetta(entita.get("normalizzato", "")):
            nominato, _ = anagrafica.trova_o_crea(tipo, entita["normalizzato"])
            trovati[nominato.pk] = nominato
        preparate.append((entita, nominato))

    if principale is None and len(trovati) == 1:
        principale = next(iter(trovati.values()))  # nessuno dichiarato, uno solo nominato: è lui
    # L'ispettore ha dichiarato dei soggetti, ma il file ne nomina solo altri
    estraneo = bool(dichiarati and trovati and not ({d.soggetto_id for d in dichiarati} & set(trovati)))

    # Ciò che una lettura parziale precedente ha già raccolto da questo file non si ripete
    def chiave(etichetta, normalizzato, pagina):
        return _compatto(etichetta), _compatto(normalizzato), pagina

    gia_raccolte = {
        chiave(*riga) for riga in EntitaEstratta.objects.filter(file=file).values_list(
            "etichetta", "valore_normalizzato", "pagina"
        )
    }

    # Secondo giro: scrivere le entità
    nuove = []
    for entita, nominato in preparate:
        normalizzato = (entita.get("normalizzato") or " ".join(entita["valore"].split()))[:500]
        if chiave(entita["etichetta"][:120], normalizzato, entita.get("pagina")) in gia_raccolte:
            continue
        voce = indice.get(_compatto(entita["etichetta"]))
        da_scansione = origini.get(entita.get("pagina")) == models.TESTO_OCR
        verificata = entita["fonte"] == models.DA_REGOLA or regole.compare_nel_testo(
            entita["valore"], testi.get(entita.get("pagina"), "")
        )
        motivo = ""
        if estraneo and nominato is None:
            motivo = "Il file non nomina nessuno dei soggetti dichiarati"
        elif rivedi_le_scansioni and da_scansione and (
            entita["etichetta"] in DELICATE_SE_DA_SCANSIONE
            or (voce is not None and voce.tipo_valore in ("identificativo", "importo"))
        ):
            motivo = "Identificativo o importo letto da una scansione"
        nuove.append(EntitaEstratta(
            elaborazione=elaborazione, file=file, voce=voce,
            etichetta=entita["etichetta"][:120], valore=entita["valore"][:500],
            valore_normalizzato=normalizzato,
            pagina=entita.get("pagina"), citazione=entita.get("citazione", ""),
            evento=entita.get("evento", "")[:200], periodo=entita.get("periodo", "")[:20],
            fonte=entita["fonte"], verificata=verificata, soggetto=nominato or principale,
            da_rivedere=bool(motivo), motivo_revisione=motivo,
        ))
    EntitaEstratta.objects.bulk_create(nuove)
    _segnala_valori_in_conflitto(file)

    # Il file riguarda anche le aziende dichiarate e quelle che nomina
    for dichiarato in dichiarati:
        servizi_archivio.collega_file_all_azienda(file, dichiarato.soggetto, "dichiarato")
    for soggetto in trovati.values():
        servizi_archivio.collega_file_all_azienda(file, soggetto, "estratto")

    if not lettura.completa:
        # Fatte le sole regole: il file resta da elaborare, e lo completerà il modello
        FileCaricato.objects.filter(pk=file.pk).update(stato=archivio.FILE_RICEVUTO, ultimo_errore="")
        Elaborazione.objects.filter(pk=elaborazione.pk).update(
            esito=models.ESITO_PARZIALE, finita_il=timezone.now(), pagine=len(lettura.pagine)
        )
        return PARZIALE

    da_rivedere = EntitaEstratta.objects.filter(file=file, da_rivedere=True, ritirata=False).exists()
    stato = archivio.FILE_DA_RIVEDERE if da_rivedere else archivio.FILE_ELABORATO
    FileCaricato.objects.filter(pk=file.pk).update(stato=stato, ultimo_errore="")
    Elaborazione.objects.filter(pk=elaborazione.pk).update(
        esito=models.ESITO_DA_RIVEDERE if da_rivedere else models.ESITO_OK, finita_il=timezone.now(),
        modello=lettura.modello[:120], versione_prompt=lettura.versione_prompt[:20], pagine=len(lettura.pagine),
    )
    return DA_RIVEDERE if da_rivedere else ELABORATO


def _segnala_valori_in_conflitto(file):
    """
    Due file danno valori diversi per la stessa voce dello stesso soggetto e periodo.
    Se la voce cambia nel tempo o ammette più valori non è un conflitto; altrimenti
    entrambe le entità vanno riviste (DECISIONI.md, n. 73).
    """
    candidate = EntitaEstratta.objects.filter(
        file=file, voce__isnull=False, soggetto__isnull=False, verificata=True,
        voce__multipla=False, voce__cambia_nel_tempo=False,
    )
    for entita in candidate:
        altre = EntitaEstratta.objects.filter(
            voce=entita.voce_id, soggetto=entita.soggetto_id, periodo=entita.periodo, ritirata=False, verificata=True
        ).exclude(pk=entita.pk)
        diverse = [a.pk for a in altre if _compatto(a.valore_normalizzato) != _compatto(entita.valore_normalizzato)]
        if diverse:
            motivo = "Valore diverso da quello di un'altra fonte per lo stesso soggetto e periodo"
            EntitaEstratta.objects.filter(pk__in=diverse + [entita.pk]).update(da_rivedere=True, motivo_revisione=motivo)
            FileCaricato.objects.filter(entita__pk__in=diverse, stato=archivio.FILE_ELABORATO).update(
                stato=archivio.FILE_DA_RIVEDERE
            )


# =====================================================================
# 4. LA CODA
# =====================================================================
def sblocca_interrotti(ore=6):
    """
    Un file rimasto "in elaborazione" dopo un'interruzione torna "ricevuto". Si
    considera interrotto se nessuna sua elaborazione è cominciata nelle ultime ore.
    Da usare con un solo processo di coda alla volta.
    """
    limite = timezone.now() - datetime.timedelta(hours=ore)
    return (
        FileCaricato.objects.filter(stato=archivio.FILE_IN_ELABORAZIONE)
        .exclude(elaborazioni__iniziata_il__gte=limite)
        .update(stato=archivio.FILE_RICEVUTO)
    )


def _prendi(gia_presi):
    """
    Il prossimo file da elaborare, già segnato "in elaborazione": prima i ricevuti
    (priorità più alta, poi i più vecchi), poi gli errori ancora ritentabili.
    Solo i file di caricamenti confermati: una bozza o un caricamento annullato non si tocca.
    Un file già preso in questo giro non si riprende: un errore si ritenta la volta dopo.
    """
    with transaction.atomic():
        in_attesa = (
            FileCaricato.objects.select_for_update(skip_locked=True, of=("self",))
            .filter(fascicolo__stato=archivio.CONFERMATO).exclude(pk__in=gia_presi)
            .order_by("-priorita", "caricato_il", "pk")
        )
        file = (
            in_attesa.filter(stato=archivio.FILE_RICEVUTO).first()
            or in_attesa.filter(stato=archivio.FILE_ERRORE, tentativi__lt=massimo_tentativi()).first()
        )
        if file is not None:
            file.stato_precedente = file.stato
            FileCaricato.objects.filter(pk=file.pk).update(stato=archivio.FILE_IN_ELABORAZIONE)
    return file


def esegui(minuti=None, massimo=None, lettori=None):
    """
    Elabora i file in attesa finché ce ne sono, per al più 'minuti' di tempo o
    'massimo' file lavorati (i file saltati non contano nel massimo). Restituisce il
    resoconto: quanti per esito e perché alcuni sono stati saltati. I file non presi
    restano in attesa per la prossima volta.
    """
    lettori = lettori if lettori is not None else lettori_predefiniti()
    scadenza = time.monotonic() + minuti * 60 if minuti else None
    resoconto = {
        ELABORATO: 0, DA_RIVEDERE: 0, PARZIALE: 0, ERRORE: 0, SALTATO: 0, "motivi": {},
        "sbloccati": sblocca_interrotti(),
    }
    # Ogni file si prende al più una volta per giro. Senza questo, un file andato in
    # errore verrebbe ripreso subito e consumerebbe tutti i tentativi in pochi secondi,
    # per esempio mentre il server del modello è spento.
    gia_presi, lavorati = [], 0
    while (massimo is None or lavorati < massimo) and (scadenza is None or time.monotonic() < scadenza):
        file = _prendi(gia_presi)
        if file is None:
            break
        gia_presi.append(file.pk)
        esito, messaggio = elabora_file(file, lettori)
        if esito == SALTATO:
            # Nessun lettore disponibile per questo file: torna com'era
            FileCaricato.objects.filter(pk=file.pk).update(stato=file.stato_precedente)
            resoconto["motivi"][messaggio] = resoconto["motivi"].get(messaggio, 0) + 1
        else:
            lavorati += 1
        resoconto[esito] += 1
    resoconto["in attesa"] = FileCaricato.objects.filter(
        fascicolo__stato=archivio.CONFERMATO, stato=archivio.FILE_RICEVUTO
    ).count()
    return resoconto


# =====================================================================
# 5. RITIRO E REVISIONE
# =====================================================================
def ritira_caricamento(fascicolo):
    """Il caricamento è stato annullato: le entità estratte dai suoi file non valgono più."""
    return EntitaEstratta.objects.filter(file__fascicolo=fascicolo, ritirata=False).update(ritirata=True)


def _aggiorna_stato(file):
    """Finita la revisione di tutte le sue entità, il file passa da "da rivedere" a "elaborato"."""
    if not EntitaEstratta.objects.filter(file=file, da_rivedere=True, ritirata=False).exists():
        FileCaricato.objects.filter(pk=file.pk, stato=archivio.FILE_DA_RIVEDERE).update(stato=archivio.FILE_ELABORATO)


def conferma(file, numeri=None):
    """Un revisore conferma le entità in attesa del file (tutte, o solo quelle indicate)."""
    in_attesa = EntitaEstratta.objects.filter(file=file, da_rivedere=True, ritirata=False)
    if numeri is not None:
        in_attesa = in_attesa.filter(pk__in=numeri)
    confermate = in_attesa.update(da_rivedere=False, motivo_revisione="")
    _aggiorna_stato(file)
    return confermate


def scarta(file, numeri):
    """Un revisore scarta delle entità: restano nel registro come ritirate, fuori da tutto."""
    scartate = EntitaEstratta.objects.filter(file=file, pk__in=numeri, ritirata=False).update(
        ritirata=True, da_rivedere=False
    )
    _aggiorna_stato(file)
    return scartate


# =====================================================================
# 6. LA SCHEDA DI UN SOGGETTO
# =====================================================================
def scheda_del_soggetto(soggetto, utente):
    """
    Ciò che si sa oggi di un soggetto, voce per voce, dalle entità utilizzabili dei
    file che l'utente può vedere. Restituisce un elenco, una riga per voce del catalogo:
        {"voce", "valori": [entità, la più recente per prima], "mancante": bool}
    Una voce senza valori è "mancante": non ancora arrivata, non zero.
    """
    visibili = Fascicolo.objects.visibili_a(utente)
    note = collections.defaultdict(list)
    entita = (
        EntitaEstratta.objects.utilizzabili().filter(soggetto=soggetto, file__fascicolo__in=visibili)
        .select_related("voce", "file").order_by("-estratta_il", "-pk")
    )
    for riga in entita:
        note[riga.voce_id].append(riga)
    return [
        {"voce": voce, "valori": note.get(voce.pk, []), "mancante": voce.pk not in note}
        for voce in voci_valide()
    ]
