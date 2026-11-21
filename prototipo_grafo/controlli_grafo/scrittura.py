# >>> NOVITA (generato da aggiorna_intestazioni.py da NOVITA.md: non modificare a mano)
#
#   scrittura.py  -  progetto controlli_grafo, VERSIONE 18
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
#
# <<< NOVITA
"""
SCRITTURA DELL'ARCHIVIO: è la metà del processo di calcolo che NON usa PyTorch.

Riceve liste Python (punteggi, etichette, archi) e le scrive nel database.
Tenerla separata da calcolo.py permette di provare l'intero cablaggio con un
modello finto, senza addestrare nulla.

Importa solo contratto.py.
"""

import datetime
import json
import random

from . import contratto
from .contratto import TIPI_IRREGOLARITA


def apri_in_scrittura(percorso=None):
    """
    Apre il database per il processo di calcolo, crea le tabelle mancanti e
    controlla che lo schema sia quello di questa versione del codice.
    """
    conn = contratto.connetti(percorso)

    # Un archivio creato prima della versione 16 ha tabelle con colonne diverse
    colonne = [r["name"] for r in conn.execute("PRAGMA table_info(esecuzione_modello)")]
    if colonne and "versione_codice" not in colonne:
        conn.close()
        raise contratto.ArchivioIncompatibile(
            "Il database è stato creato da una versione precedente del programma "
            "(schema senza versione). Elimina il file o migra i dati prima di procedere."
        )

    conn.executescript(contratto.SCHEMA_DB)
    riga = conn.execute(
        "SELECT valore FROM info_archivio WHERE chiave = 'versione_schema'"
    ).fetchone()
    if riga is None:
        with conn:
            conn.execute(
                "INSERT INTO info_archivio (chiave, valore) VALUES ('versione_schema', ?)",
                (str(contratto.VERSIONE_SCHEMA),),
            )
    elif riga["valore"] != str(contratto.VERSIONE_SCHEMA):
        conn.close()
        raise contratto.ArchivioIncompatibile(
            f"Il database ha schema {riga['valore']}, questo codice scrive lo schema "
            f"{contratto.VERSIONE_SCHEMA}. Serve una migrazione."
        )
    return conn


def id_fiscale_simulato(nodo):
    """Identificativo fittizio per la simulazione (nei dati reali: COE, partita IVA...)."""
    return f"SIM-{int(nodo):05d}"


def salva_dati_simulati(conn, archi, ha_etichetta_nodi, y_nodi, elenco_aziende):
    """
    Riempie azienda, irregolarita_accertata e relazione con i dati simulati.

    - archi: [lista venditori, lista acquirenti] (indici di nodo)
    - ha_etichetta_nodi: per ogni nodo, True se esiste un verbale confermato
    - y_nodi: per ogni nodo, lista di 0/1 nell'ordine di TIPI_IRREGOLARITA
    - elenco_aziende: {"<nodo>": {"nome_Azienda": ..., "nr_iscrizione_reg_società": ...}}

    NOTA: nel sistema reale queste tabelle sono alimentate dai documenti caricati
    e NON vengono mai svuotate. Qui le rigeneriamo a ogni esecuzione perché la
    simulazione produce ogni volta le stesse aziende e gli stessi archi.
    """
    generatore = random.Random(42)  # indipendente dal seed dell'addestramento

    with conn:
        for tabella in ("richiesta_spiegazione", "spiegazione", "punteggio_rischio",
                        "nodo_azienda", "esecuzione_modello", "relazione",
                        "irregolarita_accertata", "azienda"):
            conn.execute(f"DELETE FROM {tabella}")

        for nodo, ispezionata in enumerate(ha_etichetta_nodi):
            dati = elenco_aziende.get(str(nodo), {})
            conn.execute(
                "INSERT INTO azienda (id_fiscale, nome, nr_iscrizione, ispezionata) VALUES (?, ?, ?, ?)",
                (
                    id_fiscale_simulato(nodo),
                    dati.get("nome_Azienda", f"Azienda simulata {nodo}"),
                    dati.get("nr_iscrizione_reg_società"),
                    int(bool(ispezionata)),
                ),
            )
            if ispezionata:
                for indice_tipo, valore in enumerate(y_nodi[nodo]):
                    if valore == 1:
                        conn.execute(
                            "INSERT INTO irregolarita_accertata (id_fiscale, tipo) VALUES (?, ?)",
                            (id_fiscale_simulato(nodo), TIPI_IRREGOLARITA[indice_tipo]),
                        )

        # Ogni arco orientato (venditore -> acquirente) diventa un documento
        for progressivo, (venditore, acquirente) in enumerate(zip(archi[0], archi[1]), start=1):
            giorno = generatore.randrange(365)
            conn.execute(
                "INSERT INTO relazione (venditore, acquirente, documento, data, importo) VALUES (?, ?, ?, ?, ?)",
                (
                    id_fiscale_simulato(venditore),
                    id_fiscale_simulato(acquirente),
                    f"FATT-SIM-{progressivo:06d}",
                    (datetime.date(2025, 1, 1) + datetime.timedelta(days=giorno)).isoformat(),
                    round(generatore.expovariate(1 / 8000) + 50, 2),
                ),
            )


def salva_esecuzione(conn, versione, punteggi_nodi, soglie, metriche):
    """
    Registra un'esecuzione del modello: versione, codice e tassonomia usati,
    soglie, metriche, corrispondenza nodo <-> azienda e punteggi di rischio.

    - punteggi_nodi: per ogni nodo, lista di probabilità nell'ordine di TIPI_IRREGOLARITA
    - soglie: una soglia di decisione per tipo, nello stesso ordine
    """
    with conn:
        conn.execute(
            "INSERT INTO esecuzione_modello "
            "(versione, data_calcolo, versione_codice, tassonomia_json, soglie_json, metriche_json) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                versione,
                datetime.datetime.now().isoformat(timespec="seconds"),
                contratto.VERSIONE_CODICE,
                json.dumps(list(TIPI_IRREGOLARITA)),
                json.dumps(dict(zip(TIPI_IRREGOLARITA, soglie))),
                json.dumps(metriche, default=float),
            ),
        )
        for nodo, punteggi in enumerate(punteggi_nodi):
            id_fiscale = id_fiscale_simulato(nodo)
            conn.execute(
                "INSERT INTO nodo_azienda (versione_modello, indice_nodo, id_fiscale) VALUES (?, ?, ?)",
                (versione, nodo, id_fiscale),
            )
            for indice_tipo, punteggio in enumerate(punteggi):
                conn.execute(
                    "INSERT INTO punteggio_rischio "
                    "(versione_modello, id_fiscale, tipo, punteggio, sopra_soglia) VALUES (?, ?, ?, ?, ?)",
                    (
                        versione,
                        id_fiscale,
                        TIPI_IRREGOLARITA[indice_tipo],
                        float(punteggio),
                        int(punteggio >= soglie[indice_tipo]),
                    ),
                )


def _id_fiscale_del_nodo(conn, versione, nodo):
    riga = conn.execute(
        "SELECT id_fiscale FROM nodo_azienda WHERE versione_modello = ? AND indice_nodo = ?",
        (versione, int(nodo)),
    ).fetchone()
    if riga is None:
        raise KeyError(f"Nodo {nodo} non presente nell'esecuzione {versione}")
    return riga["id_fiscale"]


def salva_spiegazione(conn, versione, risultato):
    """
    Conserva una spiegazione di GNNExplainer (forma descritta in contratto.py)
    ed elimina l'eventuale richiesta in coda per lo stesso (nodo, tipo).
    """
    id_fiscale = _id_fiscale_del_nodo(conn, versione, risultato["nodo"])
    with conn:
        conn.execute(
            "INSERT OR REPLACE INTO spiegazione "
            "(versione_modello, id_fiscale, tipo, calcolata_il, dati_json) VALUES (?, ?, ?, ?, ?)",
            (
                versione,
                id_fiscale,
                risultato["tipo_irregolarita"],
                datetime.datetime.now().isoformat(timespec="seconds"),
                json.dumps(risultato),
            ),
        )
        conn.execute(
            "DELETE FROM richiesta_spiegazione WHERE versione_modello = ? AND id_fiscale = ? AND tipo = ?",
            (versione, id_fiscale, risultato["tipo_irregolarita"]),
        )


def richieste_pendenti(conn, versione):
    """Spiegazioni chieste dalle interrogazioni e non ancora calcolate: [(nodo, indice_tipo)]."""
    righe = conn.execute(
        "SELECT n.indice_nodo, r.tipo FROM richiesta_spiegazione r "
        "JOIN nodo_azienda n ON n.versione_modello = r.versione_modello AND n.id_fiscale = r.id_fiscale "
        "WHERE r.versione_modello = ? ORDER BY r.richiesta_il",
        (versione,),
    ).fetchall()
    return [(riga["indice_nodo"], TIPI_IRREGOLARITA.index(riga["tipo"])) for riga in righe]


def ultima_esecuzione(conn):
    """Versione dell'esecuzione più recente, oppure None se non ce ne sono."""
    riga = conn.execute(
        "SELECT versione FROM esecuzione_modello ORDER BY data_calcolo DESC, versione DESC LIMIT 1"
    ).fetchone()
    return None if riga is None else riga["versione"]
