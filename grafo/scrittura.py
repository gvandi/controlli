# >>> NOVITA (generato da aggiorna_intestazioni.py da NOVITA.md: non modificare a mano)
#
#   scrittura.py  -  app grafo, VERSIONE 20
#
#   NOVITÀ RISPETTO ALLA VERSIONE 12  ([NN] = versione che ha introdotto la novità)
#   Parte del registro: calcolo
#
#   [13] Etichette per TIPO di irregolarità: y passa da [N, 1] a [N, 4].
#   [13] Solo 150 aziende su 500 sono "ispezionate" e hanno un'etichetta (grafo.ha_etichetta);
#        le altre restano nel grafo ma fuori da train/val/test: non ispezionata != regolare.
#   [13] Gli archi conservano il verso venditore -> acquirente; GAT e GNNExplainer usano
#        l'edge_index simmetrico.
#   [13] ComplianceGAT restituisce i LOGIT (tolto il sigmoid dal forward) con un'uscita per
#        tipo; calcola_mappa_rischi() applica il sigmoid in inferenza.
#   [13] La BCEWithLogitsLoss pesata viene usata davvero, con un pos_weight per ogni tipo.
#   [13] Accuracy sostituita da PR-AUC, precision e recall per tipo (evaluate).
#   [13] Soglie di decisione scelte sul validation set (scegli_soglie) al posto di 0.5 fisso.
#   [13] GNNExplainer spiega un tipo di irregolarità alla volta (classe UscitaSingola), con
#        return_type='raw' coerente con i logit.
#   [14] GNNExplainer racchiuso nella funzione spiega_nodo(); dizionario_descrizioni.json
#        caricato prima della spiegazione.
#   [15] Ogni esecuzione viene registrata nel database con versione, data, soglie e metriche
#        (salva_dati_simulati, salva_esecuzione); le spiegazioni vengono salvate in tabella
#        (salva_spiegazione).
#   [16] Diviso in calcolo.py (PyTorch) e scrittura.py (senza PyTorch, riceve liste Python): il
#        cablaggio si può provare con un modello finto.
#   [16] Il codice è organizzato in funzioni (costruisci_grafo_simulato, addestra,
#        esegui_calcolo) invece che eseguito all'importazione.
#   [16] Pesi del modello e grafo salvati su file (modello_grafo.pt) con la versione
#        dell'esecuzione.
#   [16] Spiegazioni calcolate subito per l'irregolarità accertata con punteggio più alto e per
#        le prime 5 aziende non ispezionate della classifica.
#   [16] Nuovo comando "spiegazioni" (elabora_richieste): calcola le spiegazioni in coda senza
#        riaddestrare, e si rifiuta se modello su file e archivio sono di esecuzioni diverse.
#   [16] apri_in_scrittura() controlla la versione dello schema e rifiuta gli archivi creati da
#        versioni precedenti.
#   [16] Non contiene più report, mappa né domande di esempio; non usa più il generatore casuale
#        di numpy per date e importi (ora random.Random).
#   [18] Il dizionario delle descrizioni viene caricato nel database
#        (salva_dizionario_indicatori) a ogni calcolo.
#   [18] Ogni spiegazione conserva 10 indicatori invece di 3, per rendere utile la ricerca per
#        indicatore.
#   [18] Il messaggio per uno schema diverso dice di eliminare il file e rieseguire il calcolo.
#   [19] scrittura.py usa i modelli Django: registra_dati_simulati(), registra_esecuzione(),
#        salva_spiegazione(), richieste_pendenti(), esecuzione_piu_recente(),
#        nodi_dei_soggetti().
#   [19] Nulla viene più cancellato a ogni avvio: dati nuovi aggiungono una fotografia, dati
#        identici riusano quella esistente (impronta), e solo il ricalcolo della stessa coppia
#        calcolo/dati la sostituisce.
#   [19] Le spiegazioni si salvano come documenti auto-descrittivi che nominano i soggetti con
#        la chiave interna, non con l'indice del nodo (documento_spiegazione).
#   [19] Un file di modello per ogni coppia calcolo/dati, nella cartella dati_grafo insieme ai
#        file JSON in ingresso (calcolo_cartella.py).
#   [19] Si avvia con python manage.py grafo_calcolo (--spiegazioni per la sola coda).
#
# <<< NOVITA
"""
SCRITTURA DELL'ARCHIVIO: è la metà del processo di calcolo che NON usa PyTorch.

Riceve liste Python (punteggi, etichette, archi) e le scrive nel database
tramite i modelli Django. Tenerla separata da calcolo.py permette di provare
l'intero cablaggio con un modello finto, senza addestrare nulla.

Nulla viene cancellato all'arrivo di dati nuovi: si aggiunge una fotografia
(VersioneDati). Solo ripetere il calcolo sulla stessa coppia calcolo/dati
sostituisce l'esecuzione precedente.

Importa contratto.py e models.py.
"""

import datetime
import hashlib
import json
import random

from django.db import transaction
from django.db.models import Max

from . import contratto
from .contratto import TIPI_IRREGOLARITA
from .models import (
    DatiSoggetto,
    Esecuzione,
    Indicatore,
    IrregolaritaAccertata,
    NodoSoggetto,
    PunteggioRischio,
    Relazione,
    RichiestaSpiegazione,
    Soggetto,
    Spiegazione,
    VersioneDati,
)


def riferimento_simulato(nodo):
    """Riferimento fittizio per la simulazione (nei dati reali: aggancio alla fonte)."""
    return f"SIM-{int(nodo):05d}"


def _impronta(*parti):
    """Impronta dei dati in ingresso: gli stessi dati danno la stessa impronta."""
    testo = json.dumps(parti, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(testo.encode("utf-8")).hexdigest()


@transaction.atomic
def registra_dati_simulati(archi, ha_etichetta_nodi, y_nodi, elenco_aziende, dizionario_descrizioni,
                           descrizione="dati simulati"):
    """
    Registra una fotografia dei dati in ingresso e restituisce
    (versione_dati, soggetti_per_nodo), dove soggetti_per_nodo[i] è la chiave
    interna del soggetto che nel grafo occupa il nodo i.

    - archi: [lista venditori, lista acquirenti] (indici di nodo)
    - ha_etichetta_nodi: per ogni nodo, True se esiste un verbale confermato
    - y_nodi: per ogni nodo, lista di 0/1 nell'ordine di TIPI_IRREGOLARITA
    - elenco_aziende: {"<nodo>": {"nome_Azienda": ..., "nr_iscrizione_reg_società": ...}}
    - dizionario_descrizioni: {"<indice feature>": "descrizione"}

    Se dati identici sono già stati registrati NON crea una nuova fotografia:
    restituisce quella esistente. Nel sistema reale questa funzione sarà
    sostituita dalla fotografia dei dati estratti dai documenti.
    """
    num_nodi = len(ha_etichetta_nodi)
    riferimenti = [riferimento_simulato(n) for n in range(num_nodi)]

    # I soggetti hanno una chiave interna stabile: si creano una volta sola
    esistenti = dict(
        Soggetto.objects.filter(riferimento__in=riferimenti).values_list("riferimento", "id")
    )
    Soggetto.objects.bulk_create(
        [Soggetto(riferimento=r) for r in riferimenti if r not in esistenti]
    )
    per_riferimento = dict(
        Soggetto.objects.filter(riferimento__in=riferimenti).values_list("riferimento", "id")
    )
    soggetti_per_nodo = [per_riferimento[r] for r in riferimenti]

    impronta = _impronta(
        archi, [bool(v) for v in ha_etichetta_nodi], y_nodi, elenco_aziende, dizionario_descrizioni
    )
    esistente = VersioneDati.objects.filter(impronta=impronta).first()
    if esistente is not None:
        return esistente, soggetti_per_nodo

    ultimo = VersioneDati.objects.aggregate(massimo=Max("numero"))["massimo"] or 0
    versione_dati = VersioneDati.objects.create(
        numero=ultimo + 1, impronta=impronta, descrizione=descrizione
    )

    dati_soggetti, irregolarita = [], []
    for nodo, ispezionata in enumerate(ha_etichetta_nodi):
        voce = elenco_aziende.get(str(nodo), {})
        dati_soggetti.append(
            DatiSoggetto(
                versione_dati=versione_dati,
                soggetto_id=soggetti_per_nodo[nodo],
                nome=voce.get("nome_Azienda") or f"Azienda simulata {nodo}",
                nr_iscrizione=voce.get("nr_iscrizione_reg_società") or "",
                id_fiscale=riferimenti[nodo],
                ispezionata=bool(ispezionata),
            )
        )
        if ispezionata:
            for indice_tipo, valore in enumerate(y_nodi[nodo]):
                if valore == 1:
                    irregolarita.append(
                        IrregolaritaAccertata(
                            versione_dati=versione_dati,
                            soggetto_id=soggetti_per_nodo[nodo],
                            tipo=TIPI_IRREGOLARITA[indice_tipo],
                        )
                    )
    DatiSoggetto.objects.bulk_create(dati_soggetti)
    IrregolaritaAccertata.objects.bulk_create(irregolarita)

    # Ogni arco orientato (venditore -> acquirente) diventa un documento
    generatore = random.Random(42)  # indipendente dal seed dell'addestramento
    relazioni = []
    for progressivo, (venditore, acquirente) in enumerate(zip(archi[0], archi[1]), start=1):
        relazioni.append(
            Relazione(
                versione_dati=versione_dati,
                venditore_id=soggetti_per_nodo[venditore],
                acquirente_id=soggetti_per_nodo[acquirente],
                documento=f"FATT-SIM-{progressivo:06d}",
                data=datetime.date(2025, 1, 1) + datetime.timedelta(days=generatore.randrange(365)),
                importo=round(generatore.expovariate(1 / 8000) + 50, 2),
            )
        )
    Relazione.objects.bulk_create(relazioni)

    Indicatore.objects.bulk_create(
        [
            Indicatore(versione_dati=versione_dati, indice=int(indice), descrizione=str(testo))
            for indice, testo in dizionario_descrizioni.items()
        ]
    )
    return versione_dati, soggetti_per_nodo


@transaction.atomic
def registra_esecuzione(versione_dati, soggetti_per_nodo, punteggi_nodi, soglie, metriche):
    """
    Registra i risultati di un calcolo per la coppia (VERSIONE_CALCOLO, versione_dati).
    Se la coppia esiste già, la sostituisce insieme a punteggi, spiegazioni e coda.

    - soggetti_per_nodo: chiave interna del soggetto per ogni nodo del grafo
    - punteggi_nodi: per ogni nodo, lista di probabilità nell'ordine di TIPI_IRREGOLARITA
    - soglie: una soglia di decisione per tipo, nello stesso ordine
    """
    Esecuzione.objects.filter(
        versione_calcolo=contratto.VERSIONE_CALCOLO, versione_dati=versione_dati
    ).delete()

    esecuzione = Esecuzione.objects.create(
        versione_calcolo=contratto.VERSIONE_CALCOLO,
        versione_dati=versione_dati,
        versione_codice=contratto.VERSIONE_CODICE,
        tassonomia=list(TIPI_IRREGOLARITA),
        soglie={tipo: float(soglia) for tipo, soglia in zip(TIPI_IRREGOLARITA, soglie)},
        # passaggio per json: converte i numeri di numpy e toglie i NaN non ammessi da PostgreSQL
        metriche=json.loads(json.dumps(metriche, default=float).replace("NaN", "null")),
    )
    NodoSoggetto.objects.bulk_create(
        [
            NodoSoggetto(esecuzione=esecuzione, indice_nodo=nodo, soggetto_id=soggetto)
            for nodo, soggetto in enumerate(soggetti_per_nodo)
        ]
    )
    punteggi = []
    for nodo, valori in enumerate(punteggi_nodi):
        for indice_tipo, punteggio in enumerate(valori):
            punteggi.append(
                PunteggioRischio(
                    esecuzione=esecuzione,
                    soggetto_id=soggetti_per_nodo[nodo],
                    tipo=TIPI_IRREGOLARITA[indice_tipo],
                    punteggio=float(punteggio),
                    sopra_soglia=bool(punteggio >= soglie[indice_tipo]),
                )
            )
    PunteggioRischio.objects.bulk_create(punteggi, batch_size=2000)
    return esecuzione


@transaction.atomic
def salva_spiegazione(esecuzione, spiegazione):
    """
    Conserva una spiegazione di GNNExplainer ed elimina l'eventuale richiesta in
    coda. 'spiegazione' è un documento auto-descrittivo (contratto.SCHEMA_SPIEGAZIONE)
    che nomina i soggetti con la loro chiave interna, non con l'indice del nodo.
    """
    if not contratto.documento_leggibile(spiegazione, "spiegazione", contratto.SPIEGAZIONE_ACCETTATA):
        raise ValueError(f"Documento non valido come spiegazione: schema {spiegazione.get('schema')!r}")
    chiave = {
        "esecuzione": esecuzione,
        "soggetto_id": spiegazione["soggetto"],
        "tipo": spiegazione["tipo_irregolarita"],
    }
    Spiegazione.objects.update_or_create(**chiave, defaults={"dati": spiegazione})
    RichiestaSpiegazione.objects.filter(**chiave).delete()


def richieste_pendenti(esecuzione):
    """Spiegazioni chieste dalle interrogazioni e non ancora calcolate: [(soggetto, indice_tipo)]."""
    return [
        (soggetto, TIPI_IRREGOLARITA.index(tipo))
        for soggetto, tipo in RichiestaSpiegazione.objects.filter(esecuzione=esecuzione)
        .order_by("richiesta_il")
        .values_list("soggetto_id", "tipo")
        if tipo in TIPI_IRREGOLARITA
    ]


def esecuzione_piu_recente():
    """L'esecuzione più recente di QUESTA versione del calcolo, oppure None."""
    return (
        Esecuzione.objects.filter(versione_calcolo=contratto.VERSIONE_CALCOLO)
        .select_related("versione_dati")
        .order_by("-versione_dati__numero")
        .first()
    )


def nodi_dei_soggetti(esecuzione):
    """Corrispondenza soggetto -> indice del nodo nel grafo di un'esecuzione."""
    return dict(
        NodoSoggetto.objects.filter(esecuzione=esecuzione).values_list("soggetto_id", "indice_nodo")
    )
