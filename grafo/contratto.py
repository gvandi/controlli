# >>> NOVITA (generato da aggiorna_intestazioni.py da NOVITA.md: non modificare a mano)
#
#   contratto.py  -  app grafo, VERSIONE 23
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
#   [20] Il numero di versione del codice diventa un intero (20); schema e calcolo restano a due
#        numeri.
#   [20] Schema 4.1 (migrazione 0002, sola espansione): tabelle grafo_parametro, grafo_token,
#        grafo_sessione, grafo_richiesta, grafo_mappa; SCHEMA_RICHIESTO passa a ~=4.1.
#   [20] Restrizioni dell'amministratore sulle versioni accettate (PARAMETRI, accettata(),
#        restrizione_valida()): si aggiungono a ciò che il codice sa leggere, possono
#        restringere e mai allargare; una restrizione scritta male viene ignorata.
#   [20] Sesto strumento mappa in NOMI_STRUMENTI; versioni del protocollo MCP parlate dal
#        servizio HTTP (PROTOCOLLI_MCP).
#   [21] Schema 4.2 (migrazione 0003, sola espansione): su grafo_sessione le colonne accesso e
#        client_oauth; nuovo parametro token_personali_ammessi; SCHEMA_RICHIESTO passa a ~=4.2.
#   [21] Nuove costanti ACCESSO_TOKEN, ACCESSO_OAUTH e AMBITO_OAUTH (l'ambito "grafo" richiesto
#        dal servizio MCP).
#   [22] Settimo strumento calcola in NOMI_STRUMENTI; STRUMENTI_SENZA_ARCHIVIO elenca gli
#        strumenti che non leggono punteggi e dati.
#   [23] Ottavo strumento scheda in NOMI_STRUMENTI e in STRUMENTI_SENZA_ARCHIVIO: legge
#        l'archivio dei file caricati, non quello dell'analisi di rete.
#
# <<< NOVITA
"""
CONTRATTO COMUNE dell'app grafo: tutto ciò che più parti devono conoscere allo
stesso modo sta QUI e solo qui. Lo schema del database sta in models.py e nelle
migrazioni; qui stanno i valori ammessi e le REGOLE DI COMPATIBILITÀ fra le parti.

    calcolo.py + scrittura.py  -->  PostgreSQL  <--  interrogazione.py  <--  mappa.py
                                        ^                    ^
                                   sessioni.py  <--  servizio_mcp.py  <--  views.py (HTTP)
                                                                      <--  server_mcp.py (stdio)

Questo modulo non importa nessun'altra parte dell'app, né Django.
Le regole complete sono in COMPATIBILITA.md.
"""

from packaging.specifiers import InvalidSpecifier, SpecifierSet
from packaging.version import InvalidVersion, Version

# =====================================================================
# 1. LE QUATTRO VERSIONI
# =====================================================================
# Ognuna ha un compito diverso. Formato dei numeri: PEP 440.
#
# 1) PROGETTO: quale rilascio è installato. Solo provenienza: non blocca nulla.
#    Dalla versione 20 è un numero intero (20, 21...): non essendo mai confrontato
#    con un intervallo, un secondo numero non serviva.
VERSIONE_CODICE = "23"

# 2) SCHEMA del database: decide se un lettore può aprire l'archivio.
#    Secondo numero: modifiche che AGGIUNGONO (tabella, colonna facoltativa, indice).
#    Primo numero: modifiche che TOLGONO o cambiano significato.
#    La versione reale è quella scritta nel database dall'ultima migrazione
#    applicata; questa costante dichiara quella prodotta dalle migrazioni del codice.
VERSIONE_SCHEMA = "4.2"
#    Ciò che serve ai lettori (interrogazione, mappa, server): "~=4.2" significa
#    almeno 4.2 e comunque 4.x. Un lettore così accetta le espansioni future.
#    (4.1: parametri dell'amministratore, token, sessioni, richieste, mappe.
#     4.2: per ogni sessione, come è stato fatto l'accesso e da quale programma.)
SCHEMA_RICHIESTO = "~=4.2"

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


# RESTRIZIONI DELL'AMMINISTRATORE. Le tre richieste qui sopra (SCHEMA_RICHIESTO,
# CALCOLO_ACCETTATO, SPIEGAZIONE_ACCETTATA) dicono ciò che questo codice SA leggere:
# sono il limite e si cambiano solo rilasciando codice nuovo. L'amministratore può
# aggiungere dal cruscotto una restrizione per ciascuna (tabella grafo_parametro):
# vale insieme a quella del codice, quindi può restringere, mai allargare.
# Esempio: "==1.0" per restare sul calcolo 1.0 mentre si valuta l'1.1.
PARAMETRO_SCHEMA = "restrizione_schema"
PARAMETRO_CALCOLO = "restrizione_calcolo"
PARAMETRO_SPIEGAZIONE = "restrizione_spiegazione"
PARAMETRO_INATTIVITA = "minuti_inattivita_sessione"
PARAMETRO_TOKEN_PERSONALI = "token_personali_ammessi"
MINUTI_INATTIVITA_PREDEFINITI = 30
# nome -> (valore predefinito, descrizione mostrata all'amministratore)
PARAMETRI = {
    PARAMETRO_INATTIVITA: (
        str(MINUTI_INATTIVITA_PREDEFINITI),
        "Minuti senza richieste dopo i quali una sessione della chat viene chiusa (da 1 a 1440).",
    ),
    PARAMETRO_TOKEN_PERSONALI: (
        "si",
        "Accettare anche i token personali copiati a mano (si / no). Con 'no' la chat entra "
        "solo con l'accesso OAuth dal browser.",
    ),
    PARAMETRO_SCHEMA: (
        "",
        "Restrizione sulle versioni dello schema accettate, in aggiunta a quella del codice. "
        "Vuoto = nessuna. Esempio: ==4.1",
    ),
    PARAMETRO_CALCOLO: (
        "",
        "Restrizione sulle versioni del calcolo usate dalle interrogazioni, in aggiunta a quella "
        "del codice. Vuoto = nessuna. Esempio: ==1.0",
    ),
    PARAMETRO_SPIEGAZIONE: (
        "",
        "Restrizione sulle versioni dei documenti di spiegazione accettate, in aggiunta a quella "
        "del codice. Vuoto = nessuna. Esempio: ==1.0",
    ),
}


class ArchivioIncompatibile(RuntimeError):
    """L'archivio non combacia con questa versione del codice: non va usato."""


def compatibile(versione, richiesta):
    """Vero se la versione (es. "4.2") soddisfa la richiesta (es. "~=4.0")."""
    try:
        return Version(str(versione)) in SpecifierSet(richiesta)
    except (InvalidVersion, InvalidSpecifier):
        return False


def restrizione_valida(testo):
    """Vero se il testo è vuoto oppure un intervallo PEP 440 ben scritto (es. "==1.0", ">=1.0,<1.2")."""
    try:
        SpecifierSet(str(testo or "").strip())
        return True
    except InvalidSpecifier:
        return False


def accettata(versione, richiesta_del_codice, restrizione=""):
    """
    Vero se la versione soddisfa la richiesta del codice E la restrizione
    dell'amministratore. Una restrizione vuota o scritta male non restringe nulla:
    un errore di battitura non deve spegnere il servizio.
    """
    restrizione = str(restrizione or "").strip()
    if not compatibile(versione, richiesta_del_codice):
        return False
    return not restrizione or not restrizione_valida(restrizione) or compatibile(versione, restrizione)


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
NOMI_STRUMENTI = (
    "classifica", "relazione", "spiegazione", "vicinato", "indicatore", "mappa", "calcola", "scheda",
)
# I primi cinque stanno in interrogazione.py; "mappa" in servizio_mcp.py, perché
# scrive un file e lo registra nella sessione; "calcola" in calcolatrice.py; "scheda"
# in servizio_mcp.py, perché ha bisogno dell'utente della sessione.
# Strumenti che non leggono l'archivio dell'analisi di rete: per loro non si registra la coppia calcolo/dati
STRUMENTI_SENZA_ARCHIVIO = ("calcola", "scheda")

# Come una sessione ha dimostrato chi è l'utente
ACCESSO_TOKEN = "token"  # token personale copiato a mano (versione 20)
ACCESSO_OAUTH = "oauth"  # accesso dal browser con OAuth 2.0 (versione 21)
# Ambito OAuth richiesto dal servizio MCP: lo stesso nome è in config/settings.py
AMBITO_OAUTH = "grafo"

# Versioni del protocollo MCP che il servizio HTTP sa parlare (la prima è la preferita)
PROTOCOLLI_MCP = ("2025-11-25", "2025-06-18", "2025-03-26", "2024-11-05")

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
