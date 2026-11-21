# >>> NOVITA (generato da aggiorna_intestazioni.py da NOVITA.md: non modificare a mano)
#
#   contratto.py  -  app grafo, VERSIONE 19.0
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
#   [17] connetti() apre la connessione con check_same_thread=False, perché il server esegue gli
#        strumenti in un thread diverso da quello che ha aperto l'archivio.
#   [18] Nuova tabella feature con le descrizioni degli indicatori (da
#        dizionario_descrizioni.json); VERSIONE_SCHEMA passa a 3: l'archivio va ricreato
#        rieseguendo il calcolo.
#   [18] Nuovo strumento indicatore in NOMI_STRUMENTI; nuove costanti FEATURES_PER_SPIEGAZIONE
#        (10) e FEATURES_NEL_CONTESTO (5).
#   [19] Lo schema del database non sta più qui: è in models.py e nelle migrazioni Django
#        (PostgreSQL). Tolti SCHEMA_DB, connetti(), percorso_db(), percorso_modello().
#   [19] Quattro versioni distinte in formato PEP 440: progetto (VERSIONE_CODICE 19.0), schema
#        (VERSIONE_SCHEMA 4.0), calcolo (VERSIONE_CALCOLO 1.0), dati (contatore nel database).
#   [19] I lettori dichiarano cosa gli serve invece di pretendere una versione identica:
#        SCHEMA_RICHIESTO e CALCOLO_ACCETTATO con l'operatore ~= ; nuove funzioni compatibile()
#        e documento_leggibile().
#   [19] Schema 4.0: chiave interna del soggetto (Soggetto), fotografie dei dati (VersioneDati)
#        e risultati per coppia calcolo/dati (Esecuzione); la versione dello schema la scrivono
#        le migrazioni nella tabella grafo_info.
#   [19] Documenti JSON auto-descrittivi: SCHEMA_SPIEGAZIONE "spiegazione/1.0" e
#        SPIEGAZIONE_ACCETTATA.
#   [19] Le regole complete sono in COMPATIBILITA.md, con la lista di controllo per le modifiche
#        di schema.
#
# <<< NOVITA
"""
CONTRATTO COMUNE dell'app grafo: tutto ciò che più parti devono conoscere allo
stesso modo sta QUI e solo qui. Lo schema del database sta in models.py e nelle
migrazioni; qui stanno i valori ammessi e le REGOLE DI COMPATIBILITÀ fra le parti.

    calcolo.py + scrittura.py  -->  PostgreSQL  <--  interrogazione.py  <--  server_mcp.py
                                                                       <--  mappa.py

Questo modulo non importa nessun'altra parte dell'app, né Django.
Le regole complete sono in COMPATIBILITA.md.
"""

from packaging.specifiers import SpecifierSet
from packaging.version import InvalidVersion, Version

# =====================================================================
# 1. LE QUATTRO VERSIONI
# =====================================================================
# Ognuna ha un compito diverso. Formato dei numeri: PEP 440.
#
# 1) PROGETTO: quale rilascio è installato. Solo provenienza: non blocca nulla.
VERSIONE_CODICE = "19.0"

# 2) SCHEMA del database: decide se un lettore può aprire l'archivio.
#    Secondo numero: modifiche che AGGIUNGONO (tabella, colonna facoltativa, indice).
#    Primo numero: modifiche che TOLGONO o cambiano significato.
#    La versione reale è quella scritta nel database dall'ultima migrazione
#    applicata; questa costante dichiara quella prodotta dalle migrazioni del codice.
VERSIONE_SCHEMA = "4.0"
#    Ciò che serve ai lettori (interrogazione, mappa, server): "~=4.0" significa
#    almeno 4.0 e comunque 4.x. Un lettore così accetta le espansioni future.
SCHEMA_RICHIESTO = "~=4.0"

# 3) CALCOLO: sale solo quando cambia qualcosa che altera i punteggi (modello,
#    features, addestramento). È il primo livello della coppia calcolo/dati.
VERSIONE_CALCOLO = "1.0"
#    Esecuzioni che i lettori considerano confrontabili fra loro
CALCOLO_ACCETTATO = "~=1.0"

# 4) DATI: non è una versione di software ma una fotografia dei dati in ingresso.
#    È un contatore (1, 2, 3...) assegnato dal database: vedi models.VersioneDati.

# Documenti JSON auto-descrittivi: ogni documento salvato dichiara "nome/versione"
# nel campo "schema"; chi lo legge dichiara quali versioni accetta.
SCHEMA_SPIEGAZIONE = "spiegazione/1.0"
SPIEGAZIONE_ACCETTATA = "~=1.0"


class ArchivioIncompatibile(RuntimeError):
    """L'archivio non combacia con questa versione del codice: non va usato."""


def compatibile(versione, richiesta):
    """Vero se la versione (es. "4.2") soddisfa la richiesta (es. "~=4.0")."""
    try:
        return Version(str(versione)) in SpecifierSet(richiesta)
    except InvalidVersion:
        return False


def documento_leggibile(documento, nome, richiesta):
    """
    Vero se un documento JSON auto-descrittivo è del tipo atteso e di una versione
    accettata. Un documento senza campo "schema" non è leggibile.
    """
    dichiarato = str((documento or {}).get("schema", ""))
    nome_dichiarato, _, versione = dichiarato.partition("/")
    return nome_dichiarato == nome and compatibile(versione, richiesta)


# =====================================================================
# 2. TASSONOMIA E VALORI AMMESSI
# =====================================================================
# Una uscita della GNN per ogni tipo di irregolarità. Cambiarla altera i
# punteggi: richiede di aumentare il primo numero di VERSIONE_CALCOLO.
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
NOMI_STRUMENTI = ("classifica", "relazione", "spiegazione", "vicinato", "indicatore")

# Limiti dei parametri degli strumenti
MAX_AZIENDE_IN_CLASSIFICA = 50

# Quanti indicatori (features) conserva ogni spiegazione, e quanti ne riporta il
# testo dato alla chat. La ricerca per indicatore lavora su quelli conservati.
FEATURES_PER_SPIEGAZIONE = 10
FEATURES_NEL_CONTESTO = 5

# Struttura del vettore di features di ogni nodo
DIM_TESTO = 384
DIM_STRUTTURATI = 616
DIM_TOTALI = DIM_TESTO + DIM_STRUTTURATI
