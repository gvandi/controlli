"""
LA CODA DEI LAVORI: che cosa si può lanciare, come si chiede e come si esegue.

    richiedi()   chiamata dalle pagine: registra la richiesta (o restituisce quella già aperta)
    prendi()     chiamata dal processo esegui_lavori: prende il lavoro più vecchio
    esegui()     lo esegue e ne scrive l'esito; un errore diventa "fallito", non ferma il processo

Ogni tipo di lavoro è una funzione che riceve il Lavoro e restituisce l'esito in
parole, fatto di soli conteggi. Le funzioni importano ciò che serve al momento
dell'uso: il processo che elabora i file non ha bisogno di PyTorch, e viceversa.
"""
import datetime
import logging

from django.db import transaction
from django.utils import timezone

from .models import APERTI, FALLITO, FINITO, IN_CORSO, RICHIESTO, Esecutore, Lavoro

registro = logging.getLogger(__name__)

# Sezioni della pagina iniziale in cui compaiono i pulsanti
CARICAMENTO, ANALISI, RETE = "caricamento", "analisi", "rete"
# Dopo quanti secondi senza segnale un esecutore si considera fermo
SECONDI_DI_VITA = 30


# ---------------------------------------------------------------------
# Che cosa fa ciascun tipo di lavoro
# ---------------------------------------------------------------------
def _elabora_file(lavoro):
    from elaborazione import coda

    r = coda.esegui(minuti=lavoro.parametri.get("minuti"), massimo=lavoro.parametri.get("massimo"))
    testo = (
        f"Elaborati: {r[coda.ELABORATO]}; da rivedere: {r[coda.DA_RIVEDERE]}; solo regole, in attesa del modello: "
        f"{r[coda.PARZIALE]}; errori: {r[coda.ERRORE]}; saltati: {r[coda.SALTATO]}; ancora in attesa: {r['in attesa']}."
    )
    for motivo, numero in r["motivi"].items():
        testo += f"\nSaltati ({numero}): {motivo}"
    return testo


def _importa_anagrafica(lavoro):
    from indici import importazione

    r = importazione.importa(lavoro.ingresso, lavoro.parametri.get("fonte") or lavoro.nome_ingresso)
    testo = f"Righe nuove: {r['create']}; aggiornate: {r['aggiornate']}; rifiutate: {len(r['rifiutate'])}."
    for numero, motivo in r["rifiutate"][:20]:
        testo += f"\nRiga {numero}: {motivo}"
    if len(r["rifiutate"]) > 20:
        testo += f"\n... e altre {len(r['rifiutate']) - 20} righe rifiutate"
    return testo


def _calcola_indici(lavoro):
    from grafo import contratto
    from indici import calcolo

    r = calcolo.esegui()
    if r["esecuzione"] is None:
        return "Nessun dato reale: importare l'anagrafica o confermare almeno un documento."
    return (
        f"Calcolo {contratto.VERSIONE_CALCOLO_REGOLE} / dati n. {r['versione_dati'].numero}: {r['aziende']} aziende, "
        f"{r['segnalate']} sopra soglia, {r['senza_dati']} senza dati per periodo, {r['regole']} regole attive."
    )


def _allinea_denominazioni(lavoro):
    from indici import allineamento

    return f"Denominazioni cambiate: {len(allineamento.esegui())}."


def _dati_reali(lavoro):
    from grafo import dati_reali

    r = dati_reali.fotografa()
    if r["versione_dati"] is None:
        return "Nessuna azienda con dati per periodo e nessun documento confermato utilizzabile: nessuna fotografia."
    stato = "Nuova fotografia" if r["nuova"] else "Nessuna novità: resta la fotografia"
    testo = f"{stato} dati n. {r['versione_dati'].numero}: {r['soggetti']} soggetti, {r['relazioni']} relazioni."
    for motivo, quanti in sorted(r["esclusi"].items()):
        testo += f"\nDocumenti confermati non usati, {motivo}: {quanti}"
    return testo


def _calcola_gnn(lavoro):
    from grafo import calcolo  # richiede PyTorch

    calcolo.esegui_calcolo()
    return "Calcolo della GNN completato: vedere il cruscotto dell'analisi di rete per la coppia calcolo/dati in uso."


def _spiegazioni(lavoro):
    from grafo import calcolo  # richiede PyTorch

    calcolo.elabora_richieste()
    return "Spiegazioni in coda calcolate."


# tipo -> (titolo del pulsante, sezione, spiegazione, funzione)
TIPI = {
    "elabora_file": ("Elabora i file in attesa", CARICAMENTO,
                     "Legge i file caricati: testo, entità, documenti. Serve il modello locale acceso.", _elabora_file),
    "importa_anagrafica": ("Importa l'anagrafica da CSV", ANALISI,
                           "Attività, dipendenti e fatturato delle aziende, per periodo.", _importa_anagrafica),
    "calcola_indici": ("Calcola gli indici", ANALISI,
                       "Applica le regole di rischio ai dati reali; aggiorna ciò che la chat usa.", _calcola_indici),
    "allinea_denominazioni": ("Riallinea le denominazioni", ANALISI,
                              "Rimette in ordine i nomi delle aziende: prevale l'anagrafica ufficiale.", _allinea_denominazioni),
    "dati_reali": ("Aggiorna la fotografia dei dati reali", RETE,
                   "Aziende e rapporti dai documenti confermati, senza calcolare punteggi.", _dati_reali),
    "calcola_gnn": ("Calcola la GNN", RETE,
                    "Addestra il modello di rete e calcola i punteggi. Serve PyTorch sulla macchina che esegue.", _calcola_gnn),
    "spiegazioni": ("Calcola le spiegazioni in coda", RETE,
                    "Le spiegazioni chieste dalla chat e non ancora calcolate. Serve PyTorch.", _spiegazioni),
}


# ---------------------------------------------------------------------
# Chiedere
# ---------------------------------------------------------------------
def richiedi(tipo, utente, parametri=None, ingresso="", nome_ingresso=""):
    """
    Registra la richiesta di un lavoro. Se per quel tipo ce n'è già uno richiesto o in
    corso NON ne crea un altro. Restituisce (lavoro, nuovo).
    """
    if tipo not in TIPI:
        raise ValueError(f"Tipo di lavoro sconosciuto: {tipo}")
    with transaction.atomic():
        aperto = Lavoro.objects.select_for_update().filter(tipo=tipo, stato__in=APERTI).first()
        if aperto is not None:
            return aperto, False
        return Lavoro.objects.create(
            tipo=tipo, richiesto_da=utente, parametri=parametri or {}, ingresso=ingresso,
            nome_ingresso=nome_ingresso[:255],
        ), True


# ---------------------------------------------------------------------
# Eseguire
# ---------------------------------------------------------------------
def prendi(tipi=None):
    """Il lavoro richiesto da più tempo fra i tipi indicati (tutti, se None), messo "in corso"; None se non ce n'è."""
    tipi = list(tipi or TIPI)
    with transaction.atomic():
        occupati = Lavoro.objects.filter(stato=IN_CORSO).values_list("tipo", flat=True)
        lavoro = (
            Lavoro.objects.select_for_update(skip_locked=True)
            .filter(stato=RICHIESTO, tipo__in=tipi).exclude(tipo__in=list(occupati))
            .order_by("richiesto_il", "pk").first()
        )
        if lavoro is None:
            return None
        lavoro.stato, lavoro.iniziato_il = IN_CORSO, timezone.now()
        lavoro.save(update_fields=["stato", "iniziato_il"])
    return lavoro


def esegui(lavoro):
    """Esegue un lavoro preso con prendi() e ne scrive l'esito. Non solleva mai: un errore diventa "fallito"."""
    try:
        esito, stato = TIPI[lavoro.tipo][3](lavoro), FINITO
    except ModuleNotFoundError as errore:
        esito, stato = (
            f"Su questa macchina manca la libreria '{errore.name}': questo lavoro va eseguito dal processo "
            "avviato sulla macchina che la possiede.", FALLITO,
        )
    except Exception as errore:
        registro.exception("Lavoro %s fallito", lavoro.pk)
        esito, stato = f"{type(errore).__name__}: {errore}"[:2000], FALLITO
    lavoro.stato, lavoro.esito, lavoro.finito_il, lavoro.ingresso = stato, esito, timezone.now(), ""
    lavoro.save(update_fields=["stato", "esito", "finito_il", "ingresso"])
    return lavoro


def chiudi_interrotti(tipi=None):
    """All'avvio del processo: un lavoro rimasto "in corso" è stato interrotto da uno spegnimento."""
    return Lavoro.objects.filter(stato=IN_CORSO, tipo__in=list(tipi or TIPI)).update(
        stato=FALLITO, finito_il=timezone.now(),
        esito="Interrotto: il processo che lo eseguiva si è fermato. Si può lanciare di nuovo.",
    )


def segnala(nome, tipi=None):
    """Il processo dice che è vivo."""
    Esecutore.objects.update_or_create(
        nome=nome, defaults={"tipi": ",".join(tipi or []), "ultimo_segnale": timezone.now()}
    )


def tipi_serviti():
    """I tipi di lavoro per cui c'è un processo in funzione in questo momento."""
    da = timezone.now() - datetime.timedelta(seconds=SECONDI_DI_VITA)
    serviti = set()
    for esecutore in Esecutore.objects.filter(ultimo_segnale__gte=da):
        serviti |= set(esecutore.tipi.split(",")) if esecutore.tipi else set(TIPI)
    return serviti


# ---------------------------------------------------------------------
# Per le pagine
# ---------------------------------------------------------------------
def per_le_pagine():
    """
    Per ogni sezione, i lavori che vi si possono lanciare con il loro ultimo stato:
        {sezione: [{"tipo", "titolo", "spiegazione", "ultimo" (Lavoro o None), "aperto", "servito"}]}
    """
    serviti = tipi_serviti()
    ultimi = {}
    for lavoro in Lavoro.objects.select_related("richiesto_da").order_by("-richiesto_il", "-pk")[:200]:
        ultimi.setdefault(lavoro.tipo, lavoro)
    sezioni = {CARICAMENTO: [], ANALISI: [], RETE: []}
    for tipo, (titolo, sezione, spiegazione, _) in TIPI.items():
        ultimo = ultimi.get(tipo)
        sezioni[sezione].append({
            "tipo": tipo, "titolo": titolo, "spiegazione": spiegazione, "ultimo": ultimo,
            "aperto": ultimo is not None and ultimo.stato in APERTI, "servito": tipo in serviti,
        })
    return sezioni
