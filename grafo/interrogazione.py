# >>> NOVITA (generato da aggiorna_intestazioni.py da NOVITA.md: non modificare a mano)
#
#   interrogazione.py  -  app grafo, VERSIONE 21
#
#   NOVITÀ RISPETTO ALLA VERSIONE 12  ([NN] = versione che ha introdotto la novità)
#   Parte del registro: interrogazione
#
#   [13] stato_compliance(): irregolarità accertate, verificato senza rilievi o non ispezionato.
#   [13] Il contesto usa gli indicatori REALI di GNNExplainer (prima: una frase fissa) e riporta
#        stato noto e punteggi per tipo di ogni soggetto.
#   [13] Domande e istruzioni neutre: si chiede di valutare l'ipotesi, non di giustificarla.
#   [13] Fino alla versione 15: client del modello creato solo quando serve, eccezioni del
#        client OpenAI gestite, risposta restituita come testo.
#   [14] Quattro intenti: classifica, relazione, spiegazione, vicinato; smistamento a parole
#        chiave (smista_con_regole).
#   [14] Fino alla versione 15: smistamento proposto dall'LLM in JSON e validato campo per campo
#        (smista_domanda, valida_smistamento).
#   [14] classifica_rischio(): prime N aziende per punteggio, per tipo e per popolazione (non
#        ispezionate / ispezionate / tutte), con percentile e soglia.
#   [14] Funzioni di contesto: contesto_classifica(), genera_contesto_investigativo(),
#        contesto_spiegazione(), contesto_vicinato().
#   [15] Riscritte come query sul database: classifica_rischio(), vicini_diretti(),
#        stato_compliance(); nuove vicini_a_due_passi(), documenti_relazione(), punteggi_nodo(),
#        irregolarita_accertate(), leggi_esecuzione().
#   [15] Ogni contesto dichiara data e versione del calcolo (intestazione_dati) e, per le
#        relazioni, i documenti scambiati (descrivi_documenti).
#   [16] Nuovo modulo interrogazione.py, senza PyTorch: letture, contesti e strumenti.
#   [16] apri() si aggancia all'esecuzione più recente e solleva ArchivioIncompatibile se schema
#        o tassonomia non combaciano con il codice; avvisa se la versione del codice è diversa.
#   [16] Quattro strumenti per la chat (classifica, relazione, spiegazione, vicinato) con
#        controllo dei parametri: un valore non ammesso produce un messaggio in chiaro.
#   [16] Spiegazione non ancora calcolata: la richiesta viene messa in coda
#        (richiedi_spiegazione) e il contesto lo dichiara; la libreria non esegue più
#        GNNExplainer.
#   [16] verso_relazione() legge dal database; nuove dati_azienda(), relazioni_fra(),
#        soggetto_principale().
#   [16] genera_contesto_investigativo() riceve il tipo di irregolarità al posto degli
#        indicatori e li legge da sé.
#   [16] consulta(domanda) e uso da riga di comando, con smistamento a parole chiave.
#   [16] Rimossi chiama_llm, smista_domanda, estrai_json, valida_smistamento,
#        interroga_graph_rag e i relativi prompt: scelta dello strumento e stesura della
#        risposta passano alla chat (istruzioni in prompt_di_sistema.txt).
#   [17] Gli strumenti vengono eseguiti uno alla volta (_in_esclusiva): con mcp 2.x le funzioni
#        sono chiamate da thread di lavoro e la connessione al database è una sola.
#   [18] Le società si indicano anche per nome, anche parziale, numero di iscrizione o
#        identificativo fiscale (risolvi_societa, elenco_societa): maiuscole, accenti e
#        punteggiatura non contano.
#   [18] Un nome che corrisponde a più società non viene indovinato: lo strumento le elenca e
#        chiede quale; per un nome sconosciuto propone i più simili.
#   [18] Tutti i testi riportano nome e numero di iscrizione accanto al numero della società
#        (etichetta, nome_breve); verso_relazione() può nominare le società per nome.
#   [18] Nuovo strumento indicatore(termine, societa): cerca gli indicatori per parola della
#        descrizione (cerca_indicatori) e dice per quali società pesano di più
#        (contesto_indicatore), fra le spiegazioni già calcolate.
#   [18] consulta() riconosce nella domanda i nomi delle società e la ricerca di un indicatore;
#        gli strumenti accettano per la società sia un numero sia un testo.
#   [18] Nei testi le features si chiamano indicatori; il contesto ne riporta i primi 5.
#   [19] Letture riscritte per PostgreSQL: passano tutte da _righe(), unico punto di contatto
#        con il database, e usano la connessione di Django.
#   [19] Lettore tollerante: accetta gli schemi che soddisfano SCHEMA_RICHIESTO, nomina le
#        colonne una per una, ignora tabelle, colonne e campi JSON sconosciuti
#        (_normalizza_spiegazione).
#   [19] apri() sceglie la coppia calcolo/dati: la fotografia più recente fra i calcoli
#        accettati, oppure una coppia precisa (parametri o variabili GRAFO_VERSIONE_CALCOLO e
#        GRAFO_VERSIONE_DATI); ogni 60 secondi ricontrolla se ne esiste una più recente.
#   [19] Il numero di una società è la chiave interna del soggetto, stabile fra fotografie e
#        calcoli (prima: l'indice del nodo).
#   [19] I testi dichiarano la coppia in uso ("calcolo 1.0 / dati 2"); nuove
#        esecuzioni_disponibili() ed etichetta_esecuzione().
#   [19] La versione del progetto non produce più avvisi: è solo provenienza.
#   [19] Si prova senza chat con python manage.py grafo_consulta "domanda".
#   [20] apri() legge le restrizioni dell'amministratore (restrizioni_in_vigore) e le applica a
#        schema, calcolo e documenti di spiegazione; i messaggi di errore dicono quando il
#        rifiuto viene da una restrizione.
#   [20] in_esclusiva diventa un nome pubblico: lo usa lo strumento mappa.
#
# <<< NOVITA
"""
LIBRERIA DI INTERROGAZIONE: tutto ciò che serve per rispondere a una domanda
leggendo il database PostgreSQL dell'applicativo. Non usa PyTorch, non conosce
modello né grafo. È un LETTORE TOLLERANTE: vedi sezione 0 e COMPATIBILITA.md.

Quattro livelli, dal basso verso l'alto:
  0. ACCESSO      _righe(): unico punto di contatto con il database
  1. LETTURE      una funzione = una query (classifica_rischio, vicini_diretti, ...)
  2. CONTESTI     compongono il testo da dare al modello di linguaggio
  3. STRUMENTI    le cinque funzioni esposte alla chat, con controllo dei parametri

Importa contratto.py e la connessione di Django (non i modelli). Prova senza chat:
    python manage.py grafo_consulta "Quali sono le 3 aziende più rischiose?"
"""

import difflib
import functools
import json
import os
import re
import threading
import time
import unicodedata
from typing import Union

from django.db import connection

from . import contratto
from .contratto import DESCRIZIONE_POPOLAZIONE, POPOLAZIONI, TIPI_IRREGOLARITA

# Esecuzione su cui lavorano le interrogazioni: {id, versione_dati_id, numero_dati,
# versione_calcolo, versione_codice, calcolata_il, soglie}
_esecuzione = None
_aperta_alle = 0.0
# Restrizioni dell'amministratore sulle versioni accettate (tabella grafo_parametro),
# rilette a ogni apri(): {nome del parametro: intervallo PEP 440}
_restrizioni = {}

# Ogni quanti secondi si ricontrolla se esiste un'esecuzione più recente
# (il calcolo notturno ne aggiunge una mentre server e chat restano accesi)
SECONDI_DI_VALIDITA = 60


# =====================================================================
# 0. ACCESSO AL DATABASE, APERTURA E CONTROLLO DI COMPATIBILITÀ
# =====================================================================
# LETTORE TOLLERANTE: tutte le letture passano da _righe(), nominano una per una
# le colonne che usano e ignorano tabelle e colonne che non conoscono. Per questo
# l'archivio può ricevere espansioni (schema 4.1, 4.2...) senza toccare questo file.
def _righe(sql, parametri=None):
    """Esegue una lettura e restituisce le righe come dizionari {colonna: valore}."""
    with connection.cursor() as cursore:
        cursore.execute(sql, parametri or {})
        colonne = [colonna[0] for colonna in cursore.description]
        return [dict(zip(colonne, riga)) for riga in cursore.fetchall()]


def _esegui(sql, parametri=None):
    """Esegue una scrittura (la libreria ne fa una sola: la coda delle spiegazioni)."""
    with connection.cursor() as cursore:
        cursore.execute(sql, parametri or {})


def _json(valore):
    """Un campo JSON arriva come testo o già decodificato, secondo il connettore."""
    return json.loads(valore) if isinstance(valore, str) else valore


def _data_leggibile(momento):
    """Data e ora nel fuso del computer, al minuto."""
    if hasattr(momento, "astimezone"):
        return momento.astimezone().strftime("%Y-%m-%d %H:%M")
    return str(momento)[:16]


def restrizioni_in_vigore():
    """
    Restrizioni scritte dall'amministratore nel cruscotto. Si aggiungono a ciò che
    il codice sa leggere (contratto.py): possono restringere, mai allargare.
    """
    righe = _righe(
        "SELECT nome, valore FROM grafo_parametro WHERE nome = ANY(%(nomi)s)",
        {"nomi": [contratto.PARAMETRO_SCHEMA, contratto.PARAMETRO_CALCOLO, contratto.PARAMETRO_SPIEGAZIONE]},
    )
    return {riga["nome"]: (riga["valore"] or "").strip() for riga in righe if (riga["valore"] or "").strip()}


def _richiesto(richiesta_del_codice, nome_parametro):
    """Testo per i messaggi: la richiesta del codice più l'eventuale restrizione."""
    restrizione = _restrizioni.get(nome_parametro)
    return f"{richiesta_del_codice} e {restrizione} (restrizione dell'amministratore)" if restrizione else richiesta_del_codice


def esecuzioni_disponibili():
    """Tutte le esecuzioni presenti, dalla fotografia dei dati più recente alla più vecchia."""
    righe = _righe(
        "SELECT e.id, e.versione_calcolo, e.versione_codice, e.calcolata_il, e.tassonomia, "
        "e.soglie, e.versione_dati_id, v.numero AS numero_dati "
        "FROM grafo_esecuzione e JOIN grafo_versione_dati v ON v.id = e.versione_dati_id "
        "ORDER BY v.numero DESC, e.calcolata_il DESC"
    )
    for riga in righe:
        riga["tassonomia"] = _json(riga["tassonomia"])
        riga["soglie"] = _json(riga["soglie"])
    return righe


def apri(versione_calcolo=None, numero_dati=None):
    """
    Sceglie l'esecuzione su cui lavorare e controlla la compatibilità.

    Senza parametri: fra le esecuzioni di un calcolo compatibile con
    contratto.CALCOLO_ACCETTATO (e con la restrizione dell'amministratore, se c'è), quella sulla fotografia dei dati più recente.
    Con i parametri (o con le variabili d'ambiente GRAFO_VERSIONE_CALCOLO e
    GRAFO_VERSIONE_DATI) si sceglie una coppia precisa, per i confronti.

    Solleva ArchivioIncompatibile se lo schema non soddisfa SCHEMA_RICHIESTO o se
    non esiste un'esecuzione utilizzabile: meglio un errore chiaro di una
    risposta calcolata su dati letti male.
    """
    global _esecuzione, _aperta_alle, _elenco_societa, _restrizioni
    versione_calcolo = versione_calcolo or os.environ.get("GRAFO_VERSIONE_CALCOLO") or None
    numero_dati = numero_dati or os.environ.get("GRAFO_VERSIONE_DATI") or None

    # 1. Schema: il lettore dichiara cosa gli serve, non pretende una versione identica
    try:
        info = _righe("SELECT valore FROM grafo_info WHERE chiave = 'versione_schema'")
    except Exception as errore:
        raise contratto.ArchivioIncompatibile(
            f"Tabelle dell'app grafo non trovate: eseguire 'python manage.py migrate' ({errore})."
        ) from errore
    schema = info[0]["valore"] if info else None
    if schema is None or not contratto.compatibile(schema, contratto.SCHEMA_RICHIESTO):
        raise contratto.ArchivioIncompatibile(
            f"Schema dell'archivio: {schema or 'non dichiarato'}; questo codice richiede "
            f"{contratto.SCHEMA_RICHIESTO}. Aggiornare il codice oppure applicare le migrazioni "
            "('python manage.py migrate')."
        )
    # Lo schema è quello atteso: la tabella dei parametri esiste e si può leggere
    _restrizioni = restrizioni_in_vigore()
    if not contratto.accettata(schema, contratto.SCHEMA_RICHIESTO, _restrizioni.get(contratto.PARAMETRO_SCHEMA)):
        raise contratto.ArchivioIncompatibile(
            f"Schema dell'archivio: {schema}; richiesto: "
            f"{_richiesto(contratto.SCHEMA_RICHIESTO, contratto.PARAMETRO_SCHEMA)}. "
            "La restrizione si modifica dal cruscotto dell'amministratore."
        )

    # 2. Esecuzione: coppia (versione del calcolo, fotografia dei dati)
    candidate = esecuzioni_disponibili()
    if not candidate:
        raise contratto.ArchivioIncompatibile(
            "L'archivio non contiene nessuna esecuzione: avviare 'python manage.py grafo_calcolo'."
        )
    if versione_calcolo:
        adatte = [e for e in candidate if e["versione_calcolo"] == str(versione_calcolo)]
    else:
        adatte = [
            e for e in candidate
            if contratto.accettata(
                e["versione_calcolo"], contratto.CALCOLO_ACCETTATO,
                _restrizioni.get(contratto.PARAMETRO_CALCOLO),
            )
        ]
    if numero_dati:
        adatte = [e for e in adatte if e["numero_dati"] == int(numero_dati)]
    # Solo esecuzioni con la tassonomia di questo codice: tipi diversi non sono confrontabili
    adatte = [e for e in adatte if tuple(e["tassonomia"]) == tuple(TIPI_IRREGOLARITA)]
    if not adatte:
        presenti = ", ".join(
            f"calcolo {e['versione_calcolo']} / dati {e['numero_dati']}" for e in candidate
        )
        raise contratto.ArchivioIncompatibile(
            f"Nessuna esecuzione utilizzabile (richiesto: calcolo "
            f"{versione_calcolo or _richiesto(contratto.CALCOLO_ACCETTATO, contratto.PARAMETRO_CALCOLO)}"
            f"{', dati ' + str(numero_dati) if numero_dati else ''}). Presenti: {presenti}. "
            "Rieseguire il calcolo con questa versione."
        )
    # Fra le adatte: dati più recenti; a parità, la versione del calcolo più alta
    numero_piu_recente = adatte[0]["numero_dati"]
    scelta = max(
        (e for e in adatte if e["numero_dati"] == numero_piu_recente),
        key=lambda e: contratto.Version(e["versione_calcolo"]),
    )
    if _esecuzione is None or _esecuzione["id"] != scelta["id"]:
        _elenco_societa = None  # i nomi appartengono alla fotografia dei dati
    _esecuzione, _aperta_alle = scelta, time.monotonic()
    return etichetta_esecuzione()


def chiudi():
    global _esecuzione, _aperta_alle, _elenco_societa
    _esecuzione, _aperta_alle, _elenco_societa = None, 0.0, None


def _corrente():
    """L'esecuzione in uso, riaperta se è passato il tempo di validità."""
    if _esecuzione is None or time.monotonic() - _aperta_alle > SECONDI_DI_VALIDITA:
        apri()
    return _esecuzione


def _chiavi(**altre):
    """Parametri comuni alle query: e = esecuzione, d = fotografia dei dati."""
    esecuzione = _corrente()
    return {"e": esecuzione["id"], "d": esecuzione["versione_dati_id"], **altre}


def etichetta_esecuzione():
    """La coppia in uso, in chiaro: 'calcolo 1.0 / dati 2'."""
    esecuzione = _corrente()
    return f"calcolo {esecuzione['versione_calcolo']} / dati {esecuzione['numero_dati']}"


def leggi_esecuzione():
    """Coppia calcolo/dati, data di calcolo e soglie dell'esecuzione in uso."""
    esecuzione = _corrente()
    return {
        "versione": etichetta_esecuzione(),
        "versione_calcolo": esecuzione["versione_calcolo"],
        "numero_dati": esecuzione["numero_dati"],
        "versione_codice": esecuzione["versione_codice"],
        "data_calcolo": _data_leggibile(esecuzione["calcolata_il"]),
        "soglie": esecuzione["soglie"],
    }


# =====================================================================
# 1. LETTURE (una funzione = una query)
# =====================================================================
# Una società è identificata dalla chiave interna del soggetto (grafo_soggetto.id),
# stabile fra una fotografia dei dati e l'altra: è il "numero" che vede l'ispettore.
# L'indice del nodo nel grafo non esce mai dal processo di calcolo.
def esiste(soggetto):
    try:
        soggetto = int(soggetto)
    except (TypeError, ValueError):
        return False
    return bool(
        _righe(
            "SELECT 1 AS presente FROM grafo_dati_soggetto "
            "WHERE versione_dati_id = %(d)s AND soggetto_id = %(s)s",
            _chiavi(s=soggetto),
        )
    )


def dati_azienda(soggetto):
    """Nome, numero di iscrizione, identificativo fiscale e stato ispettivo dell'azienda."""
    righe = _righe(
        "SELECT a.nome, a.nr_iscrizione, a.id_fiscale, a.ispezionata, s.riferimento "
        "FROM grafo_dati_soggetto a JOIN grafo_soggetto s ON s.id = a.soggetto_id "
        "WHERE a.versione_dati_id = %(d)s AND a.soggetto_id = %(s)s",
        _chiavi(s=int(soggetto)),
    )
    if not righe:
        raise KeyError(f"Società {soggetto} non presente nell'archivio")
    return righe[0]


def irregolarita_accertate(soggetto):
    """Tipi di irregolarità accertati per un soggetto (lista vuota se nessuno)."""
    trovati = {
        riga["tipo"]
        for riga in _righe(
            "SELECT tipo FROM grafo_irregolarita "
            "WHERE versione_dati_id = %(d)s AND soggetto_id = %(s)s",
            _chiavi(s=int(soggetto)),
        )
    }
    return [tipo for tipo in TIPI_IRREGOLARITA if tipo in trovati]


def stato_compliance(soggetto):
    """Stato noto di un soggetto: irregolarità accertate, verificato o non ispezionato."""
    if not dati_azienda(soggetto)["ispezionata"]:
        return "Non ispezionato (nessuna etichetta)"
    tipi = irregolarita_accertate(soggetto)
    if tipi:
        return "IRREGOLARITÀ ACCERTATE: " + ", ".join(tipi)
    return "Verificato senza rilievi"


def vicini_diretti(soggetto):
    """Insieme dei soggetti che hanno almeno un documento in comune con il soggetto."""
    righe = _righe(
        "SELECT acquirente_id AS altro FROM grafo_relazione "
        "WHERE versione_dati_id = %(d)s AND venditore_id = %(s)s "
        "UNION SELECT venditore_id FROM grafo_relazione "
        "WHERE versione_dati_id = %(d)s AND acquirente_id = %(s)s",
        _chiavi(s=int(soggetto)),
    )
    return {riga["altro"] for riga in righe} - {int(soggetto)}


def vicini_a_due_passi(soggetto):
    """Soggetti raggiungibili in esattamente 2 passi (esclusi il soggetto e i vicini diretti)."""
    righe = _righe(
        """
        WITH diretti AS (
            SELECT acquirente_id AS altro FROM grafo_relazione
            WHERE versione_dati_id = %(d)s AND venditore_id = %(s)s
            UNION SELECT venditore_id FROM grafo_relazione
            WHERE versione_dati_id = %(d)s AND acquirente_id = %(s)s
        ),
        secondi AS (
            SELECT r.acquirente_id AS altro FROM grafo_relazione r
            JOIN diretti d ON r.venditore_id = d.altro WHERE r.versione_dati_id = %(d)s
            UNION SELECT r.venditore_id FROM grafo_relazione r
            JOIN diretti d ON r.acquirente_id = d.altro WHERE r.versione_dati_id = %(d)s
        )
        SELECT altro FROM secondi
        WHERE altro <> %(s)s AND altro NOT IN (SELECT altro FROM diretti)
        """,
        _chiavi(s=int(soggetto)),
    )
    return {riga["altro"] for riga in righe}


def relazioni_fra(soggetti):
    """Coppie (a, b) con a < b di soggetti dell'elenco che hanno documenti in comune."""
    soggetti = [int(s) for s in soggetti]
    if not soggetti:
        return set()
    righe = _righe(
        "SELECT DISTINCT venditore_id, acquirente_id FROM grafo_relazione "
        "WHERE versione_dati_id = %(d)s AND venditore_id = ANY(%(elenco)s) "
        "AND acquirente_id = ANY(%(elenco)s)",
        _chiavi(elenco=soggetti),
    )
    return {
        (min(r["venditore_id"], r["acquirente_id"]), max(r["venditore_id"], r["acquirente_id"]))
        for r in righe
        if r["venditore_id"] != r["acquirente_id"]
    }


def verso_relazione(a, b, descrivi=str):
    """
    Verso commerciale reale fra due soggetti (chi vende a chi). 'descrivi' sceglie
    come nominarli: il solo numero (predefinito) oppure nome_breve.
    """
    righe = _righe(
        "SELECT venditore_id, COUNT(*) AS documenti FROM grafo_relazione "
        "WHERE versione_dati_id = %(d)s AND ((venditore_id = %(a)s AND acquirente_id = %(b)s) "
        "OR (venditore_id = %(b)s AND acquirente_id = %(a)s)) GROUP BY venditore_id",
        _chiavi(a=int(a), b=int(b)),
    )
    venditori = {riga["venditore_id"] for riga in righe}
    a_vende, b_vende = int(a) in venditori, int(b) in venditori
    if a_vende and b_vende:
        return f"scambi in entrambi i versi fra {descrivi(a)} e {descrivi(b)}"
    if a_vende:
        return f"{descrivi(a)} vende a {descrivi(b)}"
    if b_vende:
        return f"{descrivi(b)} vende a {descrivi(a)}"
    return f"nessun arco diretto fra {descrivi(a)} e {descrivi(b)}"


def documenti_relazione(soggetto_a, soggetto_b):
    """
    Riepilogo dei documenti scambiati fra due soggetti (in entrambi i versi):
    numero, importo totale e documento più recente. None se non ce ne sono.
    """
    filtro = (
        "versione_dati_id = %(d)s AND ((venditore_id = %(a)s AND acquirente_id = %(b)s) "
        "OR (venditore_id = %(b)s AND acquirente_id = %(a)s))"
    )
    parametri = _chiavi(a=int(soggetto_a), b=int(soggetto_b))
    riepilogo = _righe(
        f"SELECT COUNT(*) AS numero, SUM(importo) AS totale FROM grafo_relazione WHERE {filtro}",
        parametri,
    )[0]
    if not riepilogo["numero"]:
        return None
    ultimo = _righe(
        f"SELECT documento, data FROM grafo_relazione WHERE {filtro} ORDER BY data DESC, id DESC LIMIT 1",
        parametri,
    )[0]
    return {
        "numero": riepilogo["numero"],
        "totale": float(riepilogo["totale"]),
        "ultimo_documento": ultimo["documento"],
        "ultima_data": str(ultimo["data"]),
    }


def punteggi_nodo(soggetto):
    """Punteggi di rischio di un soggetto, uno per tipo, nell'ordine di TIPI_IRREGOLARITA."""
    per_tipo = {
        riga["tipo"]: riga
        for riga in _righe(
            "SELECT tipo, punteggio, sopra_soglia FROM grafo_punteggio "
            "WHERE esecuzione_id = %(e)s AND soggetto_id = %(s)s",
            _chiavi(s=int(soggetto)),
        )
    }
    return [
        {
            "tipo": tipo,
            "punteggio": per_tipo[tipo]["punteggio"],
            "sopra_soglia": bool(per_tipo[tipo]["sopra_soglia"]),
        }
        for tipo in TIPI_IRREGOLARITA
        if tipo in per_tipo
    ]


def classifica_rischio(n=3, tipo=None, popolazione="non_ispezionate"):
    """
    Restituisce le n aziende con il punteggio di rischio più alto.

    - tipo: nome di un tipo di irregolarità, oppure None per usare, azienda per
      azienda, il tipo con il punteggio più alto.
    - popolazione: "non_ispezionate" (predefinito: indica dove dirigere i
      controlli), "ispezionate" oppure "tutte".

    Ogni voce: posizione, nodo (chiave del soggetto), tipo, punteggio, percentile,
    sopra_soglia, stato.

    NOTA: la loss pesata gonfia le probabilità, quindi il punteggio serve per
    ORDINARE le aziende, non va letto come probabilità reale. Per questo ogni
    voce riporta anche il percentile nella popolazione confrontata.
    """
    filtri = ""
    if tipo:
        filtri += " AND p.tipo = %(tipo)s"
    if popolazione != "tutte":
        filtri += " AND a.ispezionata = %(ispezionata)s"
    righe = _righe(
        f"""
        WITH candidati AS (
            SELECT p.soggetto_id, p.tipo, p.punteggio, p.sopra_soglia,
                   ROW_NUMBER() OVER (
                       PARTITION BY p.soggetto_id ORDER BY p.punteggio DESC, p.tipo
                   ) AS rango_tipo
            FROM grafo_punteggio p
            JOIN grafo_dati_soggetto a
              ON a.soggetto_id = p.soggetto_id AND a.versione_dati_id = %(d)s
            WHERE p.esecuzione_id = %(e)s{filtri}
        ),
        migliori AS (SELECT * FROM candidati WHERE rango_tipo = 1)
        SELECT m.soggetto_id, m.tipo, m.punteggio, m.sopra_soglia,
               (100.0 * (SELECT COUNT(*) FROM migliori m2 WHERE m2.punteggio < m.punteggio)
                      / (SELECT COUNT(*) FROM migliori))::float8 AS percentile
        FROM migliori m
        ORDER BY m.punteggio DESC, m.soggetto_id
        LIMIT %(n)s
        """,
        _chiavi(tipo=tipo, ispezionata=(popolazione == "ispezionate"), n=int(n)),
    )
    return [
        {
            "posizione": posizione,
            "nodo": riga["soggetto_id"],
            "tipo": riga["tipo"],
            "punteggio": riga["punteggio"],
            "percentile": riga["percentile"],  # quota di aziende con punteggio inferiore
            "sopra_soglia": bool(riga["sopra_soglia"]),
            "stato": stato_compliance(riga["soggetto_id"]),
        }
        for posizione, riga in enumerate(righe, start=1)
    ]


def soggetto_principale():
    """
    L'irregolarità ACCERTATA a cui il modello assegna il punteggio più alto:
    è il caso meglio "capito" dalla GNN, usato come esempio nel report.
    Restituisce {nodo, tipo, indice_tipo, punteggio, soglia} oppure None.
    """
    righe = _righe(
        "SELECT p.soggetto_id, p.tipo, p.punteggio FROM grafo_punteggio p "
        "JOIN grafo_irregolarita i ON i.soggetto_id = p.soggetto_id AND i.tipo = p.tipo "
        "AND i.versione_dati_id = %(d)s "
        "WHERE p.esecuzione_id = %(e)s ORDER BY p.punteggio DESC, p.soggetto_id LIMIT 1",
        _chiavi(),
    )
    if not righe or righe[0]["tipo"] not in TIPI_IRREGOLARITA:
        return None
    riga = righe[0]
    return {
        "nodo": riga["soggetto_id"],
        "tipo": riga["tipo"],
        "indice_tipo": TIPI_IRREGOLARITA.index(riga["tipo"]),
        "punteggio": riga["punteggio"],
        "soglia": leggi_esecuzione()["soglie"][riga["tipo"]],
    }


def _normalizza_spiegazione(documento):
    """
    Lettura TOLLERANTE di una spiegazione: si usano i campi conosciuti, si
    ignorano quelli in più e si dà un valore predefinito a quelli facoltativi.
    None se il documento non è di un tipo o di una versione che si sa leggere.
    """
    documento = _json(documento)
    if not contratto.documento_leggibile(documento, "spiegazione", contratto.SPIEGAZIONE_ACCETTATA):
        return None
    restrizione = _restrizioni.get(contratto.PARAMETRO_SPIEGAZIONE)
    versione_documento = str(documento.get("schema", "")).partition("/")[2]
    if not contratto.accettata(versione_documento, contratto.SPIEGAZIONE_ACCETTATA, restrizione):
        return None
    if documento.get("tipo_irregolarita") not in TIPI_IRREGOLARITA or "soggetto" not in documento:
        return None
    return {
        "nodo": documento["soggetto"],
        "tipo_irregolarita": documento["tipo_irregolarita"],
        "indice_tipo": TIPI_IRREGOLARITA.index(documento["tipo_irregolarita"]),
        "features": [
            {
                "indice": feat["indice"],
                "tipo": feat.get("tipo", ""),
                "descrizione": feat.get("descrizione", f"Indicatore {feat['indice']}"),
                "peso": feat.get("peso", 0.0),
            }
            for feat in documento.get("features", [])
        ],
        # JSON trasforma le tuple in liste: ripristiniamo la forma ((a, b), importanza)
        "relazioni": [
            ((coppia[0], coppia[1]), importanza) for coppia, importanza in documento.get("relazioni", [])
        ],
        "impatto_testo": documento.get("impatto_testo", 0.0),
        "impatto_strutturati": documento.get("impatto_strutturati", 0.0),
    }


def leggi_spiegazione(soggetto, indice_tipo):
    """Spiegazione GNNExplainer già calcolata per (soggetto, tipo), oppure None."""
    righe = _righe(
        "SELECT dati FROM grafo_spiegazione "
        "WHERE esecuzione_id = %(e)s AND soggetto_id = %(s)s AND tipo = %(tipo)s",
        _chiavi(s=int(soggetto), tipo=TIPI_IRREGOLARITA[int(indice_tipo)]),
    )
    return _normalizza_spiegazione(righe[0]["dati"]) if righe else None


def tipo_gia_spiegato(soggetto):
    """Indice del tipo per cui esiste già una spiegazione del soggetto, oppure None."""
    righe = _righe(
        "SELECT tipo FROM grafo_spiegazione WHERE esecuzione_id = %(e)s AND soggetto_id = %(s)s "
        "ORDER BY calcolata_il, tipo LIMIT 1",
        _chiavi(s=int(soggetto)),
    )
    if not righe or righe[0]["tipo"] not in TIPI_IRREGOLARITA:
        return None
    return TIPI_IRREGOLARITA.index(righe[0]["tipo"])


def richiedi_spiegazione(soggetto, indice_tipo):
    """
    Mette in coda la richiesta di una spiegazione non ancora calcolata. È l'unica
    scrittura fatta dalla libreria: il calcolo vero resta al processo di calcolo,
    che è il solo ad avere modello e grafo.
    """
    _esegui(
        "INSERT INTO grafo_richiesta_spiegazione (esecuzione_id, soggetto_id, tipo, richiesta_il) "
        "VALUES (%(e)s, %(s)s, %(tipo)s, NOW()) ON CONFLICT DO NOTHING",
        _chiavi(s=int(soggetto), tipo=TIPI_IRREGOLARITA[int(indice_tipo)]),
    )


# ---------------------------------------------------------------------
# Riconoscimento di società e indicatori a partire dalle parole dell'ispettore
# ---------------------------------------------------------------------
# I nomi delle società e le descrizioni degli indicatori arrivano dai file
# elenco_aziende.json e dizionario_descrizioni.json, che il processo di calcolo
# carica nelle tabelle azienda e feature: la libreria li legge da lì.
_elenco_societa = None  # memoria dell'elenco, svuotata a ogni apri()/chiudi()


def _normalizza(testo):
    """Minuscole, senza accenti né punteggiatura: 'L'Oro S.r.l.' -> 'l oro s r l'."""
    testo = unicodedata.normalize("NFKD", str(testo).lower())
    testo = "".join(c for c in testo if not unicodedata.combining(c))
    return " ".join(re.sub(r"[^a-z0-9]+", " ", testo).split())


def elenco_societa():
    """Tutte le società della fotografia dei dati in uso: nodo (chiave del soggetto),
    id_fiscale, nome, nr_iscrizione, chiave (nome normalizzato)."""
    global _elenco_societa
    if _elenco_societa is None:
        righe = _righe(
            "SELECT a.soggetto_id, a.id_fiscale, a.nome, a.nr_iscrizione, s.riferimento "
            "FROM grafo_dati_soggetto a JOIN grafo_soggetto s ON s.id = a.soggetto_id "
            "WHERE a.versione_dati_id = %(d)s ORDER BY a.soggetto_id",
            _chiavi(),
        )
        _elenco_societa = [
            {
                "nodo": riga["soggetto_id"],
                "id_fiscale": riga["id_fiscale"] or riga["riferimento"],
                "nome": riga["nome"],
                "nr_iscrizione": riga["nr_iscrizione"],
                "chiave": _normalizza(riga["nome"]),  # nome normalizzato, per i confronti
            }
            for riga in righe
        ]
    return _elenco_societa


def etichetta(nodo):
    """Come si nomina una società nei testi: numero, nome e numero di iscrizione."""
    dati = dati_azienda(nodo)
    if dati["nr_iscrizione"]:
        return f"Società {nodo} «{dati['nome']}» (iscrizione {dati['nr_iscrizione']})"
    return f"Società {nodo} «{dati['nome']}» ({dati['id_fiscale'] or dati['riferimento']})"


def nome_breve(nodo):
    """Forma corta per le frasi sulle relazioni: nome e numero."""
    return f"{dati_azienda(nodo)['nome']} (n. {nodo})"


def _elenca(societa, massimo=8):
    righe = [f"  - {etichetta(s['nodo'])}" for s in societa[:massimo]]
    if len(societa) > massimo:
        righe.append(f"  - ... e altre {len(societa) - massimo}")
    return "\n".join(righe)


def risolvi_societa(riferimento):
    """
    Riconosce una società da ciò che ha scritto l'ispettore: numero ("12",
    "società 12"), identificativo fiscale, numero di iscrizione oppure nome,
    anche parziale. Restituisce (nodo, None) oppure (None, messaggio).

    Non tira mai a indovinare: se il nome corrisponde a più società le elenca
    e chiede quale; se non corrisponde a nessuna propone i nomi più simili.
    """
    testo = str(riferimento).strip()
    if not testo:
        return None, "Indicare una società, per nome o per numero."
    societa = elenco_societa()

    # 1. Numero identificativo
    numero = re.fullmatch(
        r"(?:(?:societ[àa]|nodo|azienda|soggetto|impresa|n\.?)\s*)?#?\s*(\d+)", testo, flags=re.IGNORECASE
    )
    if numero and esiste(int(numero.group(1))):
        return int(numero.group(1)), None

    # 2. Identificativo fiscale o numero di iscrizione, scritti per intero
    chiave = _normalizza(testo)
    per_codice = [
        s for s in societa
        if chiave and chiave in (_normalizza(s["id_fiscale"]), _normalizza(s["nr_iscrizione"] or ""))
    ]
    if len(per_codice) == 1:
        return per_codice[0]["nodo"], None
    if numero and not per_codice:
        return None, f"La società {int(numero.group(1))} non è presente nell'archivio."

    # 3. Nome: uguale, poi tutte le parole presenti, poi parte del nome
    parole = chiave.split()
    candidati = [s for s in societa if s["chiave"] == chiave]
    if not candidati:
        candidati = [s for s in societa if parole and all(p in s["chiave"].split() for p in parole)]
    if not candidati:
        candidati = [s for s in societa if chiave and chiave in s["chiave"]]
    if len(candidati) == 1:
        return candidati[0]["nodo"], None
    if candidati:
        return None, (
            f"Il nome '{testo}' corrisponde a {len(candidati)} società: chiedere all'ispettore quale intende.\n"
            + _elenca(candidati)
        )

    # 4. Nessuna corrispondenza: si propongono i nomi più simili
    simili = difflib.get_close_matches(chiave, [s["chiave"] for s in societa], n=5, cutoff=0.6)
    messaggio = f"Nessuna società trovata con il nome '{testo}'."
    if simili:
        messaggio += " Nomi simili:\n" + _elenca([s for s in societa if s["chiave"] in simili])
    return None, messaggio


def cerca_indicatori(termine):
    """
    Indicatori (features) la cui descrizione contiene tutte le parole del termine,
    oppure quello con il numero indicato. Restituisce (trovati, voci nel dizionario),
    dove trovati = [{"indice", "descrizione"}].
    """
    righe = _righe(
        "SELECT indice, descrizione FROM grafo_indicatore WHERE versione_dati_id = %(d)s ORDER BY indice",
        _chiavi(),
    )
    chiave = _normalizza(termine)
    parole = chiave.split()
    trovati = []
    for riga in righe:
        descrizione = _normalizza(riga["descrizione"])
        if (chiave.isdigit() and int(chiave) == riga["indice"]) or (
            parole and not chiave.isdigit() and all(p in descrizione for p in parole)
        ):
            trovati.append({"indice": riga["indice"], "descrizione": riga["descrizione"]})
    return trovati, len(righe)


def spiegazioni_calcolate():
    """Tutte le spiegazioni leggibili dell'esecuzione in uso: [(soggetto, spiegazione)]."""
    righe = _righe(
        "SELECT soggetto_id, dati FROM grafo_spiegazione WHERE esecuzione_id = %(e)s "
        "ORDER BY soggetto_id, tipo",
        _chiavi(),
    )
    lette = [(riga["soggetto_id"], _normalizza_spiegazione(riga["dati"])) for riga in righe]
    return [(soggetto, dati) for soggetto, dati in lette if dati is not None]


# =====================================================================
# 2. CONTESTI (il testo che viene dato al modello di linguaggio)
# =====================================================================
def intestazione_dati():
    """Dichiara a quale calcolo e a quale fotografia dei dati risalgono i punteggi."""
    esecuzione = leggi_esecuzione()
    return (
        f"Punteggi calcolati il {esecuzione['data_calcolo']} ({esecuzione['versione']}): "
        "documenti caricati dopo questa data non sono considerati.\n"
    )


def descrivi_rischi(nodo):
    """Punteggi della GNN per ogni tipo di irregolarità, in forma testuale."""
    return "; ".join(
        f"{voce['tipo']}: {voce['punteggio']*100:.2f}%" for voce in punteggi_nodo(nodo)
    )


def descrivi_documenti(nodo_a, nodo_b):
    """Riepilogo testuale dei documenti scambiati fra due nodi."""
    riepilogo = documenti_relazione(nodo_a, nodo_b)
    if riepilogo is None:
        return "nessun documento"
    etichetta = "documento" if riepilogo["numero"] == 1 else "documenti"
    return (
        f"{riepilogo['numero']} {etichetta}, totale {riepilogo['totale']:.2f} euro, "
        f"ultimo {riepilogo['ultimo_documento']} del {riepilogo['ultima_data']}"
    )


def tipo_da_spiegare(nodo, tipo_richiesto=None):
    """Sceglie quale irregolarità spiegare per un nodo."""
    if tipo_richiesto in TIPI_IRREGOLARITA:
        return TIPI_IRREGOLARITA.index(tipo_richiesto)
    # Se esiste già una spiegazione salvata per il nodo, la riutilizziamo
    indice_salvato = tipo_gia_spiegato(nodo)
    if indice_salvato is not None:
        return indice_salvato
    # Altrimenti il tipo con il punteggio più alto
    migliore = max(punteggi_nodo(nodo), key=lambda voce: voce["punteggio"])
    return TIPI_IRREGOLARITA.index(migliore["tipo"])


def formatta_indicatori(indicatori):
    """Trasforma l'output reale di GNNExplainer in testo."""
    testo = (
        f"Spiegazione GNNExplainer per {etichetta(indicatori['nodo'])}, "
        f"irregolarità '{indicatori['tipo_irregolarita']}'.\n"
        "Indicatori più influenti:\n"
    )
    for feat in indicatori["features"][: contratto.FEATURES_NEL_CONTESTO]:
        testo += (
            f"  - Indicatore #{feat['indice']} [{feat['tipo']}] {feat['descrizione']} "
            f"| peso {feat['peso']*100:.2f}%\n"
        )
    testo += "Relazioni più influenti:\n"
    if indicatori["relazioni"]:
        for (a, b), importanza in indicatori["relazioni"]:
            testo += f"  - {verso_relazione(a, b, nome_breve)} | impatto {importanza*100:.2f}%\n"
    else:
        testo += "  - nessuna relazione sopra la soglia di rilevanza\n"
    return testo


def indicatori_o_richiesta(nodo, indice_tipo):
    """
    Testo degli indicatori di GNNExplainer per (nodo, tipo). Se la spiegazione
    non è ancora stata calcolata, la mette in coda e lo dichiara nel testo.
    """
    indicatori = leggi_spiegazione(nodo, indice_tipo)
    if indicatori is not None:
        return formatta_indicatori(indicatori)
    richiedi_spiegazione(nodo, indice_tipo)
    return (
        f"Spiegazione GNNExplainer NON ancora calcolata per {etichetta(nodo)}, irregolarità "
        f"'{TIPI_IRREGOLARITA[indice_tipo]}'. La richiesta è stata registrata e sarà elaborata dal "
        "processo di calcolo: per ora sono disponibili solo i punteggi, non le cause.\n"
    )


def contesto_classifica(n, tipo, popolazione):
    """Contesto per l'intento 'classifica'."""
    classifica = classifica_rischio(n=n, tipo=tipo, popolazione=popolazione)

    testo = "--- CLASSIFICA DI RISCHIO CALCOLATA DAL GRAFO DI COMPLIANCE ---\n"
    testo += intestazione_dati()
    testo += f"Popolazione confrontata: {DESCRIZIONE_POPOLAZIONE[popolazione]}\n"
    testo += f"Irregolarità considerata: {tipo if tipo else 'qualsiasi (per ogni azienda il tipo con punteggio più alto)'}\n"
    testo += (
        "AVVERTENZA: i punteggi servono a ordinare le aziende, non sono probabilità "
        "calibrate. Il percentile indica la quota di aziende confrontate con punteggio inferiore.\n"
    )
    if not classifica:
        return testo + "Nessuna azienda nella popolazione richiesta.\n"

    for voce in classifica:
        diretti = vicini_diretti(voce["nodo"])
        testo += (
            f"{voce['posizione']}. {etichetta(voce['nodo'])} | irregolarità: {voce['tipo']} "
            f"| punteggio GNN: {voce['punteggio']*100:.2f}% | percentile: {voce['percentile']:.1f} "
            f"| soglia di decisione {'superata' if voce['sopra_soglia'] else 'NON superata'}\n"
            f"   Stato noto: {voce['stato']}\n"
            f"   Controparti dirette: {len(diretti)}, di cui con irregolarità "
            f"accertate: {sum(1 for v in diretti if irregolarita_accertate(v))}\n"
        )
    return testo


def genera_contesto_investigativo(nodo_a, nodo_b, tipo=None):
    """Contesto per l'intento 'relazione': elementi sulla relazione fra due soggetti."""
    set_vicini_a = vicini_diretti(nodo_a)
    set_vicini_b = vicini_diretti(nodo_b)

    # Gli intermediari sono l'intersezione dei vicini di entrambi i nodi
    intermediari = sorted(set_vicini_a.intersection(set_vicini_b))
    connessione_diretta = nodo_b in set_vicini_a

    testo = "--- CONTESTO ESTRATTO DAL GRAFO DI COMPLIANCE ---\n"
    testo += intestazione_dati()
    for sigla, nodo in (("A", nodo_a), ("B", nodo_b)):
        testo += (
            f"Soggetto {sigla}: {etichetta(nodo)}\n"
            f"  Stato noto: {stato_compliance(nodo)}\n"
            f"  Punteggi di rischio GNN: {descrivi_rischi(nodo)}\n"
        )

    if connessione_diretta:
        testo += (
            f"Connessione diretta fra A e B: SI ({verso_relazione(nodo_a, nodo_b, nome_breve)}; "
            f"{descrivi_documenti(nodo_a, nodo_b)})\n"
        )
    else:
        testo += "Connessione diretta fra A e B: NO\n"

    if intermediari:
        testo += "Nodi intermediari collegati sia ad A sia a B (possibile percorso a 2 passi):\n"
        for inter in intermediari:
            testo += (
                f"  - {etichetta(inter)} | {verso_relazione(nodo_a, inter, nome_breve)} ({descrivi_documenti(nodo_a, inter)}); "
                f"{verso_relazione(inter, nodo_b, nome_breve)} ({descrivi_documenti(inter, nodo_b)})\n"
                f"    Stato noto: {stato_compliance(inter)}\n"
                f"    Punteggi di rischio GNN: {descrivi_rischi(inter)}\n"
            )
    else:
        testo += "Nessun nodo intermediario comune fra A e B.\n"

    testo += "\n--- INDICATORI ISOLATI DA GNNEXPLAINER (soggetto A) ---\n"
    return testo + indicatori_o_richiesta(nodo_a, tipo_da_spiegare(nodo_a, tipo))


def contesto_spiegazione(nodo, tipo=None):
    """Contesto per l'intento 'spiegazione': perché un'azienda è considerata a rischio."""
    indice_tipo = tipo_da_spiegare(nodo, tipo)
    nome_tipo = TIPI_IRREGOLARITA[indice_tipo]
    punteggio = next(v["punteggio"] for v in punteggi_nodo(nodo) if v["tipo"] == nome_tipo)
    soglia = leggi_esecuzione()["soglie"][nome_tipo]

    testo = "--- SPIEGAZIONE DEL RISCHIO ESTRATTA DAL GRAFO DI COMPLIANCE ---\n"
    testo += intestazione_dati()
    testo += f"Soggetto: {etichetta(nodo)}\n"
    testo += f"  Stato noto: {stato_compliance(nodo)}\n"
    testo += f"  Punteggi di rischio GNN: {descrivi_rischi(nodo)}\n"
    testo += (
        f"  Irregolarità spiegata: {nome_tipo} (punteggio {punteggio*100:.2f}%, "
        f"soglia di decisione {soglia*100:.2f}%)\n\n"
    )
    return testo + indicatori_o_richiesta(nodo, indice_tipo)


def contesto_vicinato(nodo):
    """Contesto per l'intento 'vicinato': con chi è collegata un'azienda."""
    diretti = sorted(vicini_diretti(nodo))
    indiretti = sorted(vicini_a_due_passi(nodo))
    indiretti_irregolari = [v for v in indiretti if irregolarita_accertate(v)]

    testo = "--- RELAZIONI COMMERCIALI ESTRATTE DAL GRAFO DI COMPLIANCE ---\n"
    testo += intestazione_dati()
    testo += f"Soggetto: {etichetta(nodo)} | Stato noto: {stato_compliance(nodo)}\n"
    testo += f"Controparti dirette ({len(diretti)}):\n"
    for vicino in diretti:
        migliore = max(punteggi_nodo(vicino), key=lambda voce: voce["punteggio"])
        testo += (
            f"  - {etichetta(vicino)} | {verso_relazione(nodo, vicino, nome_breve)} | {descrivi_documenti(nodo, vicino)}\n"
            f"    Stato noto: {stato_compliance(vicino)} "
            f"| punteggio GNN più alto: {migliore['punteggio']*100:.2f}% ({migliore['tipo']})\n"
        )
    if not diretti:
        testo += "  - nessuna\n"
    testo += f"Soggetti raggiungibili in 2 passi: {len(indiretti)}\n"
    testo += (
        "Fra questi, con irregolarità accertate: "
        + ("; ".join(etichetta(v) for v in indiretti_irregolari) or "nessuno")
        + "\n"
    )
    return testo


def contesto_indicatore(termine, nodo=None):
    """
    Contesto per l'intento 'indicatore': quali indicatori corrispondono al termine
    e per quali società sono fra i più influenti. La ricerca avviene fra le
    spiegazioni già calcolate; con 'nodo' si limita a quella società.
    """
    trovati, voci_dizionario = cerca_indicatori(termine)

    testo = f"--- INDICATORI DI RISCHIO CORRISPONDENTI A '{termine}' ---\n"
    testo += intestazione_dati()
    if voci_dizionario == 0:
        return testo + (
            "Il dizionario degli indicatori è vuoto: copiare dizionario_descrizioni.json nella "
            "cartella del prototipo e rieseguire il calcolo.\n"
        )
    if not trovati:
        return testo + f"Nessun indicatore fra i {voci_dizionario} del dizionario contiene '{termine}'.\n"

    massimo = 10
    testo += f"Indicatori trovati: {len(trovati)}\n"
    for voce in trovati[:massimo]:
        testo += f"  - Indicatore #{voce['indice']}: {voce['descrizione']}\n"
    if len(trovati) > massimo:
        testo += f"  - ... e altri {len(trovati) - massimo}: restringere il termine\n"

    indici = {voce["indice"] for voce in trovati}
    spiegazioni = [(n, s) for n, s in spiegazioni_calcolate() if nodo is None or n == nodo]
    presenze = []
    for nodo_spiegato, dati in spiegazioni:
        for posizione, feat in enumerate(dati["features"], start=1):
            if feat["indice"] in indici:
                presenze.append((feat["peso"], nodo_spiegato, dati["tipo_irregolarita"], feat["indice"], posizione))
    presenze.sort(key=lambda p: -p[0])

    if nodo is None:
        testo += (
            f"\nSocietà per cui questi indicatori sono fra i {contratto.FEATURES_PER_SPIEGAZIONE} più influenti "
            f"(ricerca limitata alle {len({n for n, _ in spiegazioni})} società con spiegazione già calcolata):\n"
        )
    else:
        testo += f"\nPeso di questi indicatori per {etichetta(nodo)}:\n"
        if not spiegazioni:
            indice_tipo = tipo_da_spiegare(nodo)
            richiedi_spiegazione(nodo, indice_tipo)
            return testo + (
                "  Spiegazione GNNExplainer NON ancora calcolata per questa società: la richiesta è stata "
                "registrata e sarà elaborata dal processo di calcolo.\n"
            )
    if not presenze:
        return testo + (
            f"  - nessuna: l'indicatore non compare fra i {contratto.FEATURES_PER_SPIEGAZIONE} più influenti "
            "nelle spiegazioni disponibili\n"
        )
    for peso, nodo_spiegato, tipo, indice, posizione in presenze[:20]:
        testo += (
            f"  - {etichetta(nodo_spiegato)} | irregolarità: {tipo} | indicatore #{indice} "
            f"in posizione {posizione} | peso {peso*100:.2f}%\n"
        )
    return testo


# =====================================================================
# 3. STRUMENTI ESPOSTI ALLA CHAT
# =====================================================================
# Nome della funzione, parametri e descrizione sono ciò che il modello della chat
# legge per decidere quale strumento chiamare: fanno parte del contratto
# (contratto.NOMI_STRUMENTI). I parametri vengono controllati qui; un valore non
# ammesso produce un messaggio in chiaro, mai un errore del programma.
_lucchetto = threading.RLock()


def _in_esclusiva(funzione):
    """
    Fa eseguire uno strumento alla volta. Il server MCP può chiamare gli
    strumenti da più thread, ma la connessione al database è una sola.
    functools.wraps conserva nome, parametri e descrizione letti dalla chat.
    """
    @functools.wraps(funzione)
    def protetta(*args, **kwargs):
        with _lucchetto:
            return funzione(*args, **kwargs)
    return protetta


# Nome pubblico: lo usa servizio_mcp.py per lo strumento "mappa"
in_esclusiva = _in_esclusiva


def _errore_tipo(tipo):
    if tipo and tipo not in TIPI_IRREGOLARITA:
        return f"Tipo di irregolarità non riconosciuto: '{tipo}'. Valori ammessi: {', '.join(TIPI_IRREGOLARITA)}."
    return None


def _societa_o_errore(riferimento):
    """Come risolvi_societa(), usato dagli strumenti: (nodo, None) oppure (None, messaggio)."""
    return risolvi_societa(riferimento)


@_in_esclusiva
def classifica(n: int = 3, tipo: str = "", popolazione: str = "non_ispezionate") -> str:
    """Elenca le aziende con il punteggio di rischio più alto. Da usare per domande come
    "quali sono le aziende più rischiose" o "dove conviene dirigere i controlli".
    n: quante aziende elencare (da 1 a 50).
    tipo: lasciare vuoto per qualsiasi irregolarità, oppure uno fra triangolazione,
    falsa_fatturazione, fuori_oggetto_licenza, prodotti_diversi_dal_pubblicizzato.
    popolazione: non_ispezionate (predefinito), ispezionate oppure tutte."""
    errore = _errore_tipo(tipo)
    if errore:
        return errore
    if popolazione not in POPOLAZIONI:
        return f"Popolazione non riconosciuta: '{popolazione}'. Valori ammessi: {', '.join(POPOLAZIONI)}."
    try:
        n = int(n)
    except (TypeError, ValueError):
        return "Il numero di aziende deve essere un intero."
    if not 1 <= n <= contratto.MAX_AZIENDE_IN_CLASSIFICA:
        return f"Il numero di aziende deve essere fra 1 e {contratto.MAX_AZIENDE_IN_CLASSIFICA}."
    return contesto_classifica(n, tipo or None, popolazione)


@_in_esclusiva
def relazione(societa_a: Union[int, str], societa_b: Union[int, str], tipo: str = "") -> str:
    """Descrive il rapporto fra due società: connessione diretta, documenti scambiati,
    intermediari comuni, punteggi di rischio. Da usare quando la domanda cita due società.
    societa_a, societa_b: nome (anche parziale), numero di iscrizione o numero identificativo
    di ciascuna società, così come li ha scritti l'ispettore.
    tipo: lasciare vuoto, oppure il tipo di irregolarità su cui concentrare la spiegazione."""
    errore = _errore_tipo(tipo)
    if errore:
        return errore
    nodo_a, errore = _societa_o_errore(societa_a)
    if errore:
        return errore
    nodo_b, errore = _societa_o_errore(societa_b)
    if errore:
        return errore
    if nodo_a == nodo_b:
        return "Indicare due società diverse."
    return genera_contesto_investigativo(nodo_a, nodo_b, tipo or None)


@_in_esclusiva
def spiegazione(societa: Union[int, str], tipo: str = "") -> str:
    """Spiega perché una società è considerata a rischio: punteggi, caratteristiche e
    relazioni che hanno pesato di più. Da usare per domande come "perché la società Rossi è a rischio".
    societa: nome (anche parziale), numero di iscrizione o numero identificativo della società,
    così come l'ha scritto l'ispettore.
    tipo: lasciare vuoto per l'irregolarità con il punteggio più alto, oppure indicarne una."""
    errore = _errore_tipo(tipo)
    if errore:
        return errore
    nodo, errore = _societa_o_errore(societa)
    if errore:
        return errore
    return contesto_spiegazione(nodo, tipo or None)


@_in_esclusiva
def vicinato(societa: Union[int, str]) -> str:
    """Elenca le controparti commerciali di una società con i documenti scambiati, e conta i
    soggetti raggiungibili in due passi. Da usare per domande come "con chi commercia la società Rossi".
    societa: nome (anche parziale), numero di iscrizione o numero identificativo della società,
    così come l'ha scritto l'ispettore."""
    nodo, errore = _societa_o_errore(societa)
    if errore:
        return errore
    return contesto_vicinato(nodo)


@_in_esclusiva
def indicatore(termine: str, societa: Union[int, str] = "") -> str:
    """Cerca un indicatore di rischio (caratteristica usata dal modello) partendo da una parola
    della sua descrizione, e dice per quali società pesa di più. Da usare per domande come
    "quali aziende hanno l'indicatore sui paesi offshore" o "per la società Rossi conta il fatturato?".
    termine: una o più parole della descrizione dell'indicatore, oppure il suo numero.
    societa: lasciare vuoto per cercare fra tutte le società, oppure indicarne una per nome o numero."""
    if not str(termine).strip():
        return "Indicare una parola della descrizione dell'indicatore da cercare."
    nodo = None
    if str(societa).strip():
        nodo, errore = _societa_o_errore(societa)
        if errore:
            return errore
    return contesto_indicatore(str(termine), nodo)


STRUMENTI = {
    "classifica": classifica,
    "relazione": relazione,
    "spiegazione": spiegazione,
    "vicinato": vicinato,
    "indicatore": indicatore,
}


# =====================================================================
# 4. CONSULTAZIONE SENZA CHAT (smistamento a parole chiave)
# =====================================================================
# Serve per provare la libreria dalla riga di comando e come ripiego se il
# modello della chat sceglie male lo strumento.
NUMERI_IN_LETTERE = {
    "due": 2, "tre": 3, "quattro": 4, "cinque": 5, "sei": 6,
    "sette": 7, "otto": 8, "nove": 9, "dieci": 10, "venti": 20,
}
NOMI_COLLETTIVI = r"(?:aziende|societ[àa]|soggetti|imprese|nodi)"

MESSAGGIO_NON_SUPPORTATA = (
    "Domanda non riconosciuta. Posso rispondere a: classifica delle aziende più rischiose, "
    "relazione fra due società, spiegazione del rischio di una società, controparti di una società, "
    "ricerca di un indicatore di rischio (le società si indicano per nome o per numero, es. 'società 12')."
)


def estrai_nodi_dalla_domanda(domanda):
    """
    Trova le società citate in una domanda, nell'ordine in cui compaiono:
    per numero ("società 12") oppure per nome, se il nome intero compare nel testo.
    Un numero viene restituito anche se la società non esiste: lo segnalerà lo strumento.
    """
    testo = _normalizza(domanda)
    trovate = []  # (inizio, fine, nodo)

    # Nomi: prima i più lunghi, così "Rossi Costruzioni" vince su "Rossi"
    for societa in sorted(elenco_societa(), key=lambda s: -len(s["chiave"])):
        if len(societa["chiave"]) < 3:
            continue
        trovata = re.search(rf"(?<![a-z0-9]){re.escape(societa['chiave'])}(?![a-z0-9])", testo)
        if trovata and not any(i < trovata.end() and trovata.start() < f for i, f, _ in trovate):
            trovate.append((trovata.start(), trovata.end(), societa["nodo"]))

    # Numeri: "società 12", "nodo 12"...
    for trovata in re.finditer(r"(?<![a-z0-9])(?:societa|nodo|azienda|soggetto|impresa) (\d+)(?![a-z0-9])", testo):
        if not any(i < trovata.end() and trovata.start() < f for i, f, _ in trovate):
            trovate.append((trovata.start(), trovata.end(), int(trovata.group(1))))

    nodi = []
    for _, _, nodo in sorted(trovate):
        if nodo not in nodi:
            nodi.append(nodo)
    return nodi


def smista_con_regole(domanda):
    """Riconosce l'intento con parole chiave: {intento, nodi, n, tipo, popolazione, termine}."""
    testo = domanda.lower()
    nodi = estrai_nodi_dalla_domanda(domanda)

    # Quante aziende vuole in classifica ("le 3 aziende", "prime 5", "top 10", "le tre società")
    n = 3
    trovato = re.search(rf"(\d+)\s+{NOMI_COLLETTIVI}", testo) or re.search(
        r"(?:prime|primi|top)\s+(\d+)", testo
    )
    if trovato:
        n = int(trovato.group(1))
    else:
        for parola, valore in NUMERI_IN_LETTERE.items():
            if re.search(rf"\b{parola}\b(?:\s+\w+)?\s+{NOMI_COLLETTIVI}", testo) or re.search(
                rf"(?:prime|primi|top)\s+{parola}\b", testo
            ):
                n = valore
                break

    tipo = ""
    if "triangolaz" in testo:
        tipo = "triangolazione"
    elif "fals" in testo and "fattur" in testo:
        tipo = "falsa_fatturazione"
    elif "fuori oggetto" in testo or "licenza" in testo:
        tipo = "fuori_oggetto_licenza"
    elif "pubblicizz" in testo or "affiliat" in testo:
        tipo = "prodotti_diversi_dal_pubblicizzato"

    if re.search(r"non\s+(?:ancora\s+)?ispezionat", testo):
        popolazione = "non_ispezionate"
    elif "ispezionat" in testo or "accertat" in testo:
        popolazione = "ispezionate"
    elif "tutte le" in testo or "in assoluto" in testo:
        popolazione = "tutte"
    else:
        popolazione = "non_ispezionate"

    # Ricerca di un indicatore: il termine è il testo fra virgolette doppie,
    # altrimenti ciò che segue la parola "indicatore" / "caratteristica" / "feature"
    termine = ""
    if re.search(r"indicator|caratteristic|feature", testo):
        fra_virgolette = re.search(r"[\"«“]([^\"»”]+)[\"»”]", domanda)
        if fra_virgolette:
            termine = fra_virgolette.group(1).strip()
        else:
            dopo = re.search(
                r"(?:indicator[ei]|caratteristic[ah]e?|features?)\s+(?:(?:di|del|dello|della|dei|sui|sul|sulla|sulle|su|con|per)\s+)?(.+)",
                testo,
            )
            termine = dopo.group(1).strip(" ?.!") if dopo else ""

    chiede_classifica = re.search(
        r"più\s+(?:a\s+)?risch|maggior(?:e)?\s+rischio|classifica|graduatoria|"
        r"(?:prime|primi|top)\s+\w+|da\s+(?:ispezionare|controllare)",
        testo,
    )
    chiede_vicinato = re.search(
        r"con\s+chi|commerci|clienti|fornitori|controparti|collegat|vicin", testo
    )
    if termine:
        intento = "indicatore"
    elif chiede_classifica and not nodi:
        intento = "classifica"
    elif len(nodi) >= 2:
        intento = "relazione"
    elif len(nodi) == 1:
        intento = "vicinato" if chiede_vicinato else "spiegazione"
    else:
        intento = "non_supportata"

    return {
        "intento": intento, "nodi": nodi, "n": n, "tipo": tipo,
        "popolazione": popolazione, "termine": termine,
    }


def consulta(domanda):
    """Risponde a una domanda in linguaggio naturale chiamando lo strumento adatto."""
    smistamento = smista_con_regole(domanda)
    intento, nodi = smistamento["intento"], smistamento["nodi"]
    if intento == "classifica":
        return classifica(smistamento["n"], smistamento["tipo"], smistamento["popolazione"])
    if intento == "relazione":
        return relazione(nodi[0], nodi[1], smistamento["tipo"])
    if intento == "spiegazione":
        return spiegazione(nodi[0], smistamento["tipo"])
    if intento == "vicinato":
        return vicinato(nodi[0])
    if intento == "indicatore":
        return indicatore(smistamento["termine"], nodi[0] if nodi else "")
    return MESSAGGIO_NON_SUPPORTATA

