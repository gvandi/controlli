"""
LA CODA DEI LAVORI: che cosa si può lanciare, come si chiede e come si esegue.

NOVITÀ
    [2] I lavori sono presentati come UNA SEQUENZA ordinata (PERCORSO), non più divisi fra le
        sezioni della pagina iniziale: prima il percorso dei dati reali, passo per passo e
        con i passi che fa una persona, poi la rete simulata, poi gli strumenti di servizio.
        Ogni voce dice a che cosa serve, che cosa le serve prima e che cosa aggiorna.
        "Calcola gli indici" si chiama ora "Aggiorna il grafo e calcola gli indici", perché
        è ciò che fa. Il tipo resta "calcola_indici": lo storico non cambia.
    [1] Prima versione: coda nel database, processo esegui_lavori.

    richiedi()   chiamata dalle pagine: registra la richiesta (o restituisce quella già aperta)
    prendi()     chiamata dal processo esegui_lavori: prende il lavoro più vecchio
    esegui()     lo esegue e ne scrive l'esito; un errore diventa "fallito", non ferma il processo

Ogni tipo di lavoro è una funzione che riceve il Lavoro e restituisce l'esito in
parole, fatto di soli conteggi. Le funzioni importano ciò che serve al momento
dell'uso: il processo che elabora i file non ha bisogno di PyTorch, e viceversa.
"""
import collections
import datetime
import logging

from django.db import transaction
from django.utils import timezone

from .models import APERTI, FALLITO, FINITO, IN_CORSO, RICHIESTO, Esecutore, Lavoro

registro = logging.getLogger(__name__)

# I tre gruppi in cui la sequenza è divisa
REALI, SIMULATA, SERVIZIO = "reali", "simulata", "servizio"
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
        f"Calcolo {contratto.VERSIONE_CALCOLO_REGOLE} / dati n. {r['versione_dati'].numero}: {r['aziende']} società, "
        f"{r['segnalate']} sopra soglia, {r['senza_dati']} senza dati per periodo, {r['regole']} regole attive."
    )


def _allinea_denominazioni(lavoro):
    from indici import allineamento

    return f"Denominazioni cambiate: {len(allineamento.esegui())}."


def _dati_reali(lavoro):
    from grafo import dati_reali

    r = dati_reali.fotografa()
    if r["versione_dati"] is None:
        return "Nessuna società con dati per periodo e nessun documento confermato utilizzabile: nessuna fotografia."
    stato = "Nuova fotografia" if r["nuova"] else "Nessuna novità: resta la fotografia"
    testo = f"{stato} dati n. {r['versione_dati'].numero}: {r['soggetti']} società, {r['relazioni']} relazioni."
    if r["nuova"]:
        testo += f"\nChat e mappa non la usano ancora: lanciare «{TIPI['calcola_indici'].titolo}»."
    for motivo, quanti in sorted(r["esclusi"].items()):
        testo += f"\nDocumenti confermati non usati, {motivo}: {quanti}"
    return testo


def _calcola_gnn(lavoro):
    from grafo import calcolo  # richiede PyTorch

    calcolo.esegui_calcolo()
    return (
        "Calcolo della GNN completato sui dati simulati: le fatture e i DDT caricati non vi entrano. "
        "Vedere il cruscotto dell'analisi di rete per la coppia calcolo/dati in uso."
    )


def _spiegazioni(lavoro):
    from grafo import calcolo  # richiede PyTorch

    calcolo.elabora_richieste()
    return "Spiegazioni in coda calcolate."


# Un tipo di lavoro. "serve" = che cosa deve esserci prima; "aggiorna" = che cosa cambia dopo.
Tipo = collections.namedtuple("Tipo", "titolo gruppo spiegazione funzione serve aggiorna")

TIPI = {
    "elabora_file": Tipo(
        "Elabora i file in attesa", REALI,
        "Il modello locale legge i file caricati: testo, entità, documento con mittente e destinatario.", _elabora_file,
        "File caricati e confermati; il modello locale acceso.",
        "Lo stato dei file (elaborato, da rivedere). Niente ancora nel grafo.",
    ),
    "importa_anagrafica": Tipo(
        "Importa l'anagrafica da CSV", REALI,
        "Attività, dipendenti e fatturato delle società, per periodo: sono i dati su cui lavorano le regole.",
        _importa_anagrafica,
        "Un file CSV. Non dipende dai passi precedenti.",
        "L'anagrafica per periodo e il nome delle società. Niente ancora negli indici.",
    ),
    "calcola_indici": Tipo(
        "Aggiorna il grafo e calcola gli indici", REALI,
        "Fa tre cose insieme: fotografa società e rapporti (dai documenti confermati), applica le regole di "
        "rischio, e mette il risultato in uso.", _calcola_indici,
        "Documenti confermati e/o anagrafica importata. Va rilanciato ogni volta che uno dei due cambia.",
        "Ciò che leggono chat, mappa di rete, classifica e spazio degli indici.",
    ),
    "calcola_gnn": Tipo(
        "Calcola la GNN (dati simulati)", SIMULATA,
        "Addestra il modello di rete e calcola i punteggi su una rete inventata dal programma.", _calcola_gnn,
        "PyTorch sulla macchina che esegue. Non usa né i file caricati né l'anagrafica.",
        "Un'esecuzione sui dati simulati, che si sceglie dal cruscotto: non tocca i dati reali.",
    ),
    "spiegazioni": Tipo(
        "Calcola le spiegazioni in coda", SIMULATA,
        "Le spiegazioni dei punteggi della GNN chieste dalla chat e non ancora calcolate.", _spiegazioni,
        "Un calcolo della GNN già fatto; PyTorch.",
        "Le spiegazioni che la chat mostra per l'esecuzione della GNN.",
    ),
    "allinea_denominazioni": Tipo(
        "Riallinea le denominazioni", SERVIZIO,
        "Rimette in ordine i nomi delle società: prevale l'anagrafica ufficiale.", _allinea_denominazioni,
        "Serve solo se una società compare con un nome sbagliato o come «non rilevata».",
        "Il nome delle società in anagrafica.",
    ),
    "dati_reali": Tipo(
        "Fotografa i dati reali senza calcolare", SERVIZIO,
        "La sola prima parte di «Aggiorna il grafo e calcola gli indici»: conta società e rapporti e dice quali "
        "documenti restano fuori.", _dati_reali,
        "Serve per un controllo. Per l'uso normale basta il passo del percorso.",
        "Una fotografia che chat e mappa NON usano finché non si calcolano gli indici.",
    ),
}

# Ciò che fa una persona, e che nessun pulsante può fare al suo posto
_CARICARE = ("Caricare i file", "Fatture, DDT e altri documenti: file singoli, una cartella o uno ZIP.",
             "Lo fa l'ispettore, da Caricamento dati.")
_CONFERMARE = (
    "Rivedere e confermare i documenti",
    "Per ogni file letto, controllare entità, mittente e destinatario e confermare. Solo un documento "
    "confermato, con mittente, destinatario, data e totale, diventa un rapporto nel grafo.",
    "Lo fa l'ispettore, dalla pagina «Testo ed entità estratte» del file.",
)

# LA SEQUENZA: (gruppo, titolo, nota, voci). Una voce è il nome di un tipo oppure un passo manuale.
PERCORSO = (
    (REALI, "Percorso dei dati reali",
     "In quest'ordine. I passi 1-3 portano i rapporti fra società, il passo 4 i dati per le regole: sono "
     "indipendenti fra loro, e il passo 5 li usa entrambi.",
     (_CARICARE, "elabora_file", _CONFERMARE, "importa_anagrafica", "calcola_indici")),
    (SIMULATA, "Rete simulata (prototipo)",
     "La GNN non è ancora calcolata sui dati reali: questi due lavori servono a provare il modello e non "
     "cambiano ciò che si vede delle società vere.",
     ("calcola_gnn", "spiegazioni")),
    (SERVIZIO, "Strumenti di servizio",
     "Non fanno parte della sequenza: si lanciano quando serve.",
     ("allinea_denominazioni", "dati_reali")),
)


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
        esito, stato = TIPI[lavoro.tipo].funzione(lavoro), FINITO
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
    La sequenza dei lavori con il loro ultimo stato, per le pagine:
        [{"codice", "titolo", "nota", "voci": [voce, ...]}]
    Una voce ha sempre "titolo", "spiegazione", "passo" (numero nel percorso dei dati reali, o None).
    Se è un lavoro ha anche "tipo", "serve", "aggiorna", "ultimo" (Lavoro o None), "aperto", "servito";
    se è un passo che fa una persona ha "tipo" None e "chi".
    """
    serviti = tipi_serviti()
    ultimi = {}
    for lavoro in Lavoro.objects.select_related("richiesto_da").order_by("-richiesto_il", "-pk")[:200]:
        ultimi.setdefault(lavoro.tipo, lavoro)
    gruppi = []
    for codice, titolo, nota, elenco in PERCORSO:
        voci = []
        for posizione, voce in enumerate(elenco, start=1):
            passo = posizione if codice == REALI else None
            if not isinstance(voce, str):
                voci.append({"tipo": None, "titolo": voce[0], "spiegazione": voce[1], "chi": voce[2], "passo": passo})
                continue
            tipo, ultimo = TIPI[voce], ultimi.get(voce)
            voci.append({
                "tipo": voce, "titolo": tipo.titolo, "spiegazione": tipo.spiegazione, "serve": tipo.serve,
                "aggiorna": tipo.aggiorna, "passo": passo, "ultimo": ultimo,
                "aperto": ultimo is not None and ultimo.stato in APERTI, "servito": voce in serviti,
            })
        gruppi.append({"codice": codice, "titolo": titolo, "nota": nota, "voci": voci})
    return gruppi
