# >>> NOVITA (generato da aggiorna_intestazioni.py da NOVITA.md: non modificare a mano)
#
#   contratto.py  -  progetto controlli_grafo, VERSIONE 16
#
#   NOVITÀ RISPETTO ALLA VERSIONE 12  ([NN] = versione che ha introdotto la novità)
#   Parte del registro: contratto
#
#   [13] Tassonomia TIPI_IRREGOLARITA: un'uscita della GNN per ogni tipo di irregolarità.
#   [15] Schema del database: azienda, irregolarita_accertata, relazione (un documento per arco,
#        con data e importo), esecuzione_modello, nodo_azienda, punteggio_rischio, spiegazione.
#   [15] Le tabelle usano l'identificativo fiscale dell'azienda; nodo_azienda conserva la
#        corrispondenza con l'indice del nodo per ogni esecuzione.
#   [16] Nuovo modulo contratto.py: unico posto per tassonomia, popolazioni, nomi degli
#        strumenti, dimensioni delle features, percorsi dei file e schema del database.
#   [16] Un solo numero di versione per tutto il progetto (VERSIONE_CODICE) e versione dello
#        schema (VERSIONE_SCHEMA, ora 2).
#   [16] Nuova tabella info_archivio con la versione dello schema; esecuzione_modello registra
#        anche versione del codice e tassonomia usate nel calcolo.
#   [16] Nuova tabella richiesta_spiegazione: coda delle spiegazioni chieste dalle
#        interrogazioni.
#   [16] Eccezione ArchivioIncompatibile e forma documentata della spiegazione.
#   [16] Percorsi dei file modificabili con le variabili d'ambiente CONTROLLI_DB e
#        CONTROLLI_MODELLO.
#
# <<< NOVITA
"""
CONTRATTO COMUNE del progetto: tutto ciò che più parti devono conoscere allo
stesso modo sta QUI e solo qui. Nessuna costante o definizione di tabella va
copiata in un altro file.

    calcolo.py + scrittura.py  -->  database  <--  interrogazione.py  <--  server_mcp.py
                                                                      <--  mappa.py

Questo modulo non importa nessun'altra parte del progetto.
"""

import os
import sqlite3

# =====================================================================
# 1. VERSIONI
# =====================================================================
# Un solo numero di versione per tutto il progetto (lo stesso di NOVITA.md)
VERSIONE_CODICE = "16"

# Va aumentata a ogni modifica di SCHEMA_DB: la libreria di interrogazione
# rifiuta di aprire un archivio scritto con uno schema diverso.
VERSIONE_SCHEMA = 2

# =====================================================================
# 2. TASSONOMIA E VALORI AMMESSI
# =====================================================================
# Una uscita della GNN per ogni tipo di irregolarità
TIPI_IRREGOLARITA = (
    "triangolazione",
    "falsa_fatturazione",
    "fuori_oggetto_licenza",
    "prodotti_diversi_dal_pubblicizzato",
)
NUM_TIPI = len(TIPI_IRREGOLARITA)

POPOLAZIONI = ("non_ispezionate", "ispezionate", "tutte")
DESCRIZIONE_POPOLAZIONE = {
    "non_ispezionate": "aziende NON ancora ispezionate (dove dirigere i controlli)",
    "ispezionate": "aziende già ispezionate",
    "tutte": "tutte le aziende",
}

# Strumenti che il server MCP espone alla chat: uno per intento
NOMI_STRUMENTI = ("classifica", "relazione", "spiegazione", "vicinato")

# Limiti dei parametri degli strumenti
MAX_AZIENDE_IN_CLASSIFICA = 50

# Struttura del vettore di features di ogni nodo
DIM_TESTO = 384
DIM_STRUTTURATI = 616
DIM_TOTALI = DIM_TESTO + DIM_STRUTTURATI

# =====================================================================
# 3. FILE
# =====================================================================
def percorso_db():
    """File del database (modificabile con la variabile d'ambiente CONTROLLI_DB)."""
    return os.environ.get("CONTROLLI_DB", "controlli_grafo.sqlite")


def percorso_modello():
    """File con pesi del modello e grafo (variabile d'ambiente CONTROLLI_MODELLO)."""
    return os.environ.get("CONTROLLI_MODELLO", "modello_grafo.pt")


# =====================================================================
# 4. SCHEMA DEL DATABASE
# =====================================================================
# Le tabelle usano l'identificativo fiscale dell'azienda, NON l'indice del nodo,
# che cambia a ogni ricostruzione del grafo. nodo_azienda conserva la
# corrispondenza valida per ciascuna esecuzione del modello.
#
# Chi scrive e chi legge:
#   azienda, irregolarita_accertata, relazione   scrive: calcolo (in futuro i documenti)
#   esecuzione_modello, nodo_azienda,
#   punteggio_rischio, spiegazione               scrive: calcolo
#   richiesta_spiegazione                        scrive: interrogazione, svuota: calcolo
#   info_archivio                                scrive: calcolo
#   tutte                                        legge: interrogazione
SCHEMA_DB = """
CREATE TABLE IF NOT EXISTS info_archivio (
    chiave          TEXT PRIMARY KEY,
    valore          TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS azienda (
    id_fiscale      TEXT PRIMARY KEY,
    nome            TEXT NOT NULL,
    nr_iscrizione   TEXT,
    ispezionata     INTEGER NOT NULL DEFAULT 0   -- 1 = esiste un verbale ispettivo confermato
);
CREATE TABLE IF NOT EXISTS irregolarita_accertata (
    id_fiscale      TEXT NOT NULL REFERENCES azienda(id_fiscale),
    tipo            TEXT NOT NULL,
    PRIMARY KEY (id_fiscale, tipo)
);
CREATE TABLE IF NOT EXISTS relazione (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    venditore       TEXT NOT NULL REFERENCES azienda(id_fiscale),
    acquirente      TEXT NOT NULL REFERENCES azienda(id_fiscale),
    documento       TEXT NOT NULL,               -- fattura / DDT di origine
    data            TEXT NOT NULL,
    importo         REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_relazione_venditore  ON relazione(venditore);
CREATE INDEX IF NOT EXISTS idx_relazione_acquirente ON relazione(acquirente);
CREATE TABLE IF NOT EXISTS esecuzione_modello (
    versione        TEXT PRIMARY KEY,
    data_calcolo    TEXT NOT NULL,
    versione_codice TEXT NOT NULL,               -- VERSIONE_CODICE di chi ha calcolato
    tassonomia_json TEXT NOT NULL,               -- TIPI_IRREGOLARITA usati nel calcolo
    soglie_json     TEXT NOT NULL,               -- soglia di decisione per tipo
    metriche_json   TEXT NOT NULL                -- metriche sul test set
);
CREATE TABLE IF NOT EXISTS nodo_azienda (
    versione_modello TEXT NOT NULL REFERENCES esecuzione_modello(versione),
    indice_nodo      INTEGER NOT NULL,
    id_fiscale       TEXT NOT NULL REFERENCES azienda(id_fiscale),
    PRIMARY KEY (versione_modello, indice_nodo)
);
CREATE TABLE IF NOT EXISTS punteggio_rischio (
    versione_modello TEXT NOT NULL REFERENCES esecuzione_modello(versione),
    id_fiscale       TEXT NOT NULL REFERENCES azienda(id_fiscale),
    tipo             TEXT NOT NULL,
    punteggio        REAL NOT NULL,
    sopra_soglia     INTEGER NOT NULL,
    PRIMARY KEY (versione_modello, id_fiscale, tipo)
);
CREATE TABLE IF NOT EXISTS spiegazione (
    versione_modello TEXT NOT NULL REFERENCES esecuzione_modello(versione),
    id_fiscale       TEXT NOT NULL REFERENCES azienda(id_fiscale),
    tipo             TEXT NOT NULL,
    calcolata_il     TEXT NOT NULL,
    dati_json        TEXT NOT NULL,              -- output di GNNExplainer
    PRIMARY KEY (versione_modello, id_fiscale, tipo)
);
CREATE TABLE IF NOT EXISTS richiesta_spiegazione (
    versione_modello TEXT NOT NULL REFERENCES esecuzione_modello(versione),
    id_fiscale       TEXT NOT NULL REFERENCES azienda(id_fiscale),
    tipo             TEXT NOT NULL,
    richiesta_il     TEXT NOT NULL,
    PRIMARY KEY (versione_modello, id_fiscale, tipo)
);
"""

# Forma di una SPIEGAZIONE (campo dati_json e valore restituito dalle funzioni):
#   {"nodo": int, "indice_tipo": int, "tipo_irregolarita": str,
#    "features": [{"indice": int, "tipo": str, "descrizione": str, "peso": float}],
#    "relazioni": [[[nodo_a, nodo_b], importanza], ...],
#    "impatto_testo": float, "impatto_strutturati": float}
# Gli indici di nodo al suo interno valgono solo per la versione_modello della riga.


class ArchivioIncompatibile(RuntimeError):
    """L'archivio non combacia con questa versione del codice: non va usato."""


def connetti(percorso=None):
    """Apre una connessione al database (senza creare né modificare tabelle)."""
    conn = sqlite3.connect(percorso or percorso_db())
    conn.row_factory = sqlite3.Row
    return conn
