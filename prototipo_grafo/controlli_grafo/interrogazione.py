# >>> NOVITA (generato da aggiorna_intestazioni.py da NOVITA.md: non modificare a mano)
#
#   interrogazione.py  -  progetto controlli_grafo, VERSIONE 16
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
#
# <<< NOVITA
"""
LIBRERIA DI INTERROGAZIONE: tutto ciò che serve per rispondere a una domanda
leggendo il database. Non usa PyTorch, non conosce modello né grafo.

Tre livelli, dal basso verso l'alto:
  1. LETTURE      una funzione = una query (classifica_rischio, vicini_diretti, ...)
  2. CONTESTI     compongono il testo da dare al modello di linguaggio
  3. STRUMENTI    le quattro funzioni esposte alla chat, con controllo dei parametri

Importa solo contratto.py. Prova dalla riga di comando, senza chat:
    python -m controlli_grafo.interrogazione "Quali sono le 3 aziende più rischiose?"
"""

import datetime
import json
import re
import sys

from . import contratto
from .contratto import DESCRIZIONE_POPOLAZIONE, POPOLAZIONI, TIPI_IRREGOLARITA

_conn = None  # connessione al database
_versione = None  # esecuzione del modello su cui lavorano le interrogazioni


# =====================================================================
# 0. APERTURA E CONTROLLO DI COMPATIBILITÀ
# =====================================================================
def apri(percorso=None):
    """
    Apre l'archivio e si aggancia all'esecuzione più recente. Si rifiuta di
    partire se l'archivio non combacia con questa versione del codice: meglio
    un errore chiaro di una risposta calcolata su dati letti male.
    """
    global _conn, _versione
    chiudi()
    conn = contratto.connetti(percorso)
    try:
        try:
            riga = conn.execute(
                "SELECT valore FROM info_archivio WHERE chiave = 'versione_schema'"
            ).fetchone()
        except Exception as errore:
            raise contratto.ArchivioIncompatibile(
                "Archivio senza versione di schema: non è stato creato dal processo "
                f"di calcolo di questa versione ({errore})."
            ) from errore
        if riga is None or riga["valore"] != str(contratto.VERSIONE_SCHEMA):
            trovato = "nessuno" if riga is None else riga["valore"]
            raise contratto.ArchivioIncompatibile(
                f"Schema dell'archivio: {trovato}; schema atteso dal codice: "
                f"{contratto.VERSIONE_SCHEMA}. Aggiorna il codice o riesegui il calcolo."
            )

        esecuzione = conn.execute(
            "SELECT versione, versione_codice, tassonomia_json FROM esecuzione_modello "
            "ORDER BY data_calcolo DESC, versione DESC LIMIT 1"
        ).fetchone()
        if esecuzione is None:
            raise contratto.ArchivioIncompatibile(
                "L'archivio non contiene nessuna esecuzione del modello: avvia prima il calcolo."
            )
        if tuple(json.loads(esecuzione["tassonomia_json"])) != tuple(TIPI_IRREGOLARITA):
            raise contratto.ArchivioIncompatibile(
                "I tipi di irregolarità usati nel calcolo sono diversi da quelli del codice: "
                "riesegui il calcolo con questa versione."
            )
        if esecuzione["versione_codice"] != contratto.VERSIONE_CODICE:
            # Non blocca: schema e tassonomia combaciano. Ma va saputo.
            print(
                f"Attenzione: punteggi calcolati con la versione {esecuzione['versione_codice']} "
                f"del codice, interrogati con la {contratto.VERSIONE_CODICE}.",
                file=sys.stderr,
            )
    except Exception:
        conn.close()
        raise
    _conn, _versione = conn, esecuzione["versione"]
    return _versione


def chiudi():
    global _conn, _versione
    if _conn is not None:
        _conn.close()
    _conn, _versione = None, None


def _db():
    if _conn is None:
        apri()
    return _conn


# =====================================================================
# 1. LETTURE (una funzione = una query)
# =====================================================================
# In ingresso e in uscita si usa l'indice del nodo dell'esecuzione corrente;
# la traduzione verso l'identificativo fiscale avviene qui dentro.
def id_fiscale_di(nodo):
    riga = _db().execute(
        "SELECT id_fiscale FROM nodo_azienda WHERE versione_modello = ? AND indice_nodo = ?",
        (_versione, int(nodo)),
    ).fetchone()
    if riga is None:
        raise KeyError(f"Società {nodo} non presente nell'archivio")
    return riga["id_fiscale"]


def nodi_di(id_fiscali):
    """Traduce un elenco di identificativi fiscali negli indici di nodo correnti."""
    id_fiscali = list(id_fiscali)
    if not id_fiscali:
        return []
    segnaposto = ", ".join("?" * len(id_fiscali))
    righe = _db().execute(
        f"SELECT id_fiscale, indice_nodo FROM nodo_azienda "
        f"WHERE versione_modello = ? AND id_fiscale IN ({segnaposto})",
        [_versione, *id_fiscali],
    ).fetchall()
    corrispondenza = {riga["id_fiscale"]: riga["indice_nodo"] for riga in righe}
    return [corrispondenza[i] for i in id_fiscali if i in corrispondenza]


def esiste(nodo):
    try:
        id_fiscale_di(nodo)
        return True
    except (KeyError, TypeError, ValueError):
        return False


def leggi_esecuzione():
    """Versione, data di calcolo e soglie dell'esecuzione corrente."""
    riga = _db().execute(
        "SELECT versione, data_calcolo, soglie_json FROM esecuzione_modello WHERE versione = ?",
        (_versione,),
    ).fetchone()
    return {
        "versione": riga["versione"],
        "data_calcolo": riga["data_calcolo"],
        "soglie": json.loads(riga["soglie_json"]),
    }


def dati_azienda(nodo):
    """Nome e numero di iscrizione dell'azienda."""
    riga = _db().execute(
        "SELECT id_fiscale, nome, nr_iscrizione FROM azienda WHERE id_fiscale = ?",
        (id_fiscale_di(nodo),),
    ).fetchone()
    return dict(riga)


def irregolarita_accertate(nodo):
    """Tipi di irregolarità accertati per un nodo (lista vuota se nessuno)."""
    righe = _db().execute(
        "SELECT tipo FROM irregolarita_accertata WHERE id_fiscale = ?", (id_fiscale_di(nodo),)
    ).fetchall()
    trovati = {riga["tipo"] for riga in righe}
    return [tipo for tipo in TIPI_IRREGOLARITA if tipo in trovati]


def stato_compliance(nodo):
    """Stato noto di un nodo: irregolarità accertate, verificato o non ispezionato."""
    riga = _db().execute(
        "SELECT ispezionata FROM azienda WHERE id_fiscale = ?", (id_fiscale_di(nodo),)
    ).fetchone()
    if not riga["ispezionata"]:
        return "Non ispezionato (nessuna etichetta)"
    tipi = irregolarita_accertate(nodo)
    if tipi:
        return "IRREGOLARITÀ ACCERTATE: " + ", ".join(tipi)
    return "Verificato senza rilievi"


def vicini_diretti(nodo):
    """Insieme dei nodi che hanno almeno un documento in comune con il nodo."""
    id_fiscale = id_fiscale_di(nodo)
    righe = _db().execute(
        "SELECT acquirente AS altro FROM relazione WHERE venditore = ? "
        "UNION SELECT venditore FROM relazione WHERE acquirente = ?",
        (id_fiscale, id_fiscale),
    ).fetchall()
    return set(nodi_di(riga["altro"] for riga in righe)) - {int(nodo)}


def vicini_a_due_passi(nodo):
    """Nodi raggiungibili in esattamente 2 passi (esclusi il nodo e i vicini diretti)."""
    righe = _db().execute(
        """
        WITH diretti AS (
            SELECT acquirente AS altro FROM relazione WHERE venditore = :id
            UNION SELECT venditore FROM relazione WHERE acquirente = :id
        ),
        secondi AS (
            SELECT r.acquirente AS altro FROM relazione r JOIN diretti d ON r.venditore = d.altro
            UNION SELECT r.venditore FROM relazione r JOIN diretti d ON r.acquirente = d.altro
        )
        SELECT altro FROM secondi
        WHERE altro != :id AND altro NOT IN (SELECT altro FROM diretti)
        """,
        {"id": id_fiscale_di(nodo)},
    ).fetchall()
    return set(nodi_di(riga["altro"] for riga in righe))


def relazioni_fra(nodi):
    """Coppie (a, b) con a < b di nodi dell'elenco che hanno documenti in comune."""
    id_fiscali = [id_fiscale_di(n) for n in nodi]
    if not id_fiscali:
        return set()
    segnaposto = ", ".join("?" * len(id_fiscali))
    righe = _db().execute(
        f"SELECT DISTINCT venditore, acquirente FROM relazione "
        f"WHERE venditore IN ({segnaposto}) AND acquirente IN ({segnaposto})",
        id_fiscali + id_fiscali,
    ).fetchall()
    coppie = set()
    for riga in righe:
        a, b = nodi_di([riga["venditore"], riga["acquirente"]])
        coppie.add((min(a, b), max(a, b)))
    return coppie


def verso_relazione(a, b):
    """Verso commerciale reale fra due nodi (chi vende a chi)."""
    id_a, id_b = id_fiscale_di(a), id_fiscale_di(b)
    conta = "SELECT COUNT(*) AS n FROM relazione WHERE venditore = ? AND acquirente = ?"
    a_vende = _db().execute(conta, (id_a, id_b)).fetchone()["n"] > 0
    b_vende = _db().execute(conta, (id_b, id_a)).fetchone()["n"] > 0
    if a_vende and b_vende:
        return f"scambi in entrambi i versi fra {a} e {b}"
    if a_vende:
        return f"{a} vende a {b}"
    if b_vende:
        return f"{b} vende a {a}"
    return f"nessun arco diretto fra {a} e {b}"


def documenti_relazione(nodo_a, nodo_b):
    """
    Riepilogo dei documenti scambiati fra due nodi (in entrambi i versi):
    numero, importo totale e documento più recente. None se non ce ne sono.
    """
    id_a, id_b = id_fiscale_di(nodo_a), id_fiscale_di(nodo_b)
    filtro = "(venditore = ? AND acquirente = ?) OR (venditore = ? AND acquirente = ?)"
    parametri = (id_a, id_b, id_b, id_a)
    riga = _db().execute(
        f"SELECT COUNT(*) AS numero, SUM(importo) AS totale FROM relazione WHERE {filtro}", parametri
    ).fetchone()
    if riga["numero"] == 0:
        return None
    ultimo = _db().execute(
        f"SELECT documento, data FROM relazione WHERE {filtro} ORDER BY data DESC, id DESC LIMIT 1",
        parametri,
    ).fetchone()
    return {
        "numero": riga["numero"],
        "totale": riga["totale"],
        "ultimo_documento": ultimo["documento"],
        "ultima_data": ultimo["data"],
    }


def punteggi_nodo(nodo):
    """Punteggi di rischio di un nodo, uno per tipo, nell'ordine di TIPI_IRREGOLARITA."""
    righe = _db().execute(
        "SELECT tipo, punteggio, sopra_soglia FROM punteggio_rischio "
        "WHERE versione_modello = ? AND id_fiscale = ?",
        (_versione, id_fiscale_di(nodo)),
    ).fetchall()
    per_tipo = {riga["tipo"]: riga for riga in righe}
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

    Ogni voce: posizione, nodo, tipo, punteggio, percentile, sopra_soglia, stato.

    NOTA: la loss pesata gonfia le probabilità, quindi il punteggio serve per
    ORDINARE le aziende, non va letto come probabilità reale. Per questo ogni
    voce riporta anche il percentile nella popolazione confrontata.
    """
    righe = _db().execute(
        """
        WITH candidati AS (
            SELECT p.id_fiscale, p.tipo, p.punteggio, p.sopra_soglia,
                   ROW_NUMBER() OVER (
                       PARTITION BY p.id_fiscale ORDER BY p.punteggio DESC
                   ) AS rango_tipo
            FROM punteggio_rischio p
            JOIN azienda a ON a.id_fiscale = p.id_fiscale
            WHERE p.versione_modello = :versione
              AND (:tipo IS NULL OR p.tipo = :tipo)
              AND (:popolazione = 'tutte' OR a.ispezionata = :ispezionata)
        ),
        migliori AS (SELECT * FROM candidati WHERE rango_tipo = 1)
        SELECT m.id_fiscale, m.tipo, m.punteggio, m.sopra_soglia,
               100.0 * (SELECT COUNT(*) FROM migliori m2 WHERE m2.punteggio < m.punteggio)
                     / (SELECT COUNT(*) FROM migliori) AS percentile
        FROM migliori m
        ORDER BY m.punteggio DESC, m.id_fiscale
        LIMIT :n
        """,
        {
            "versione": _versione,
            "tipo": tipo,
            "popolazione": popolazione,
            "ispezionata": 1 if popolazione == "ispezionate" else 0,
            "n": int(n),
        },
    ).fetchall()

    classifica = []
    for posizione, riga in enumerate(righe, start=1):
        nodo = nodi_di([riga["id_fiscale"]])[0]
        classifica.append(
            {
                "posizione": posizione,
                "nodo": nodo,
                "tipo": riga["tipo"],
                "punteggio": riga["punteggio"],
                "percentile": riga["percentile"],  # quota di aziende con punteggio inferiore
                "sopra_soglia": bool(riga["sopra_soglia"]),
                "stato": stato_compliance(nodo),
            }
        )
    return classifica


def soggetto_principale():
    """
    L'irregolarità ACCERTATA a cui il modello assegna il punteggio più alto:
    è il caso meglio "capito" dalla GNN, usato come esempio nel report.
    Restituisce {nodo, tipo, indice_tipo, punteggio, soglia} oppure None.
    """
    riga = _db().execute(
        "SELECT p.id_fiscale, p.tipo, p.punteggio FROM punteggio_rischio p "
        "JOIN irregolarita_accertata i ON i.id_fiscale = p.id_fiscale AND i.tipo = p.tipo "
        "WHERE p.versione_modello = ? ORDER BY p.punteggio DESC, p.id_fiscale LIMIT 1",
        (_versione,),
    ).fetchone()
    if riga is None:
        return None
    return {
        "nodo": nodi_di([riga["id_fiscale"]])[0],
        "tipo": riga["tipo"],
        "indice_tipo": TIPI_IRREGOLARITA.index(riga["tipo"]),
        "punteggio": riga["punteggio"],
        "soglia": leggi_esecuzione()["soglie"][riga["tipo"]],
    }


def leggi_spiegazione(nodo, indice_tipo):
    """Spiegazione GNNExplainer già calcolata per (nodo, tipo), oppure None."""
    riga = _db().execute(
        "SELECT dati_json FROM spiegazione WHERE versione_modello = ? AND id_fiscale = ? AND tipo = ?",
        (_versione, id_fiscale_di(nodo), TIPI_IRREGOLARITA[int(indice_tipo)]),
    ).fetchone()
    if riga is None:
        return None
    risultato = json.loads(riga["dati_json"])
    # JSON trasforma le tuple in liste: ripristiniamo la forma ((a, b), importanza)
    risultato["relazioni"] = [
        ((coppia[0], coppia[1]), importanza) for coppia, importanza in risultato["relazioni"]
    ]
    return risultato


def tipo_gia_spiegato(nodo):
    """Indice del tipo per cui esiste già una spiegazione del nodo, oppure None."""
    riga = _db().execute(
        "SELECT tipo FROM spiegazione WHERE versione_modello = ? AND id_fiscale = ? "
        "ORDER BY calcolata_il LIMIT 1",
        (_versione, id_fiscale_di(nodo)),
    ).fetchone()
    return None if riga is None else TIPI_IRREGOLARITA.index(riga["tipo"])


def richiedi_spiegazione(nodo, indice_tipo):
    """
    Mette in coda la richiesta di una spiegazione non ancora calcolata. È l'unica
    scrittura fatta dalla libreria: il calcolo vero resta al processo di calcolo,
    che è il solo ad avere modello e grafo.
    """
    conn = _db()
    with conn:
        conn.execute(
            "INSERT OR IGNORE INTO richiesta_spiegazione "
            "(versione_modello, id_fiscale, tipo, richiesta_il) VALUES (?, ?, ?, ?)",
            (
                _versione,
                id_fiscale_di(nodo),
                TIPI_IRREGOLARITA[int(indice_tipo)],
                datetime.datetime.now().isoformat(timespec="seconds"),
            ),
        )


# =====================================================================
# 2. CONTESTI (il testo che viene dato al modello di linguaggio)
# =====================================================================
def intestazione_dati():
    """Dichiara a quale calcolo risalgono i punteggi."""
    esecuzione = leggi_esecuzione()
    return (
        f"Punteggi calcolati il {esecuzione['data_calcolo']} (modello {esecuzione['versione']}): "
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
        f"Spiegazione GNNExplainer per la Società {indicatori['nodo']}, "
        f"irregolarità '{indicatori['tipo_irregolarita']}'.\n"
        "Features più influenti:\n"
    )
    for feat in indicatori["features"]:
        testo += (
            f"  - Feature #{feat['indice']} [{feat['tipo']}] {feat['descrizione']} "
            f"| peso {feat['peso']*100:.2f}%\n"
        )
    testo += "Relazioni più influenti:\n"
    if indicatori["relazioni"]:
        for (a, b), importanza in indicatori["relazioni"]:
            testo += f"  - {verso_relazione(a, b)} | impatto {importanza*100:.2f}%\n"
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
        f"Spiegazione GNNExplainer NON ancora calcolata per la Società {nodo}, irregolarità "
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
            f"{voce['posizione']}. Società {voce['nodo']} | irregolarità: {voce['tipo']} "
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
            f"Soggetto {sigla}: Società {nodo}\n"
            f"  Stato noto: {stato_compliance(nodo)}\n"
            f"  Punteggi di rischio GNN: {descrivi_rischi(nodo)}\n"
        )

    if connessione_diretta:
        testo += (
            f"Connessione diretta fra A e B: SI ({verso_relazione(nodo_a, nodo_b)}; "
            f"{descrivi_documenti(nodo_a, nodo_b)})\n"
        )
    else:
        testo += "Connessione diretta fra A e B: NO\n"

    if intermediari:
        testo += "Nodi intermediari collegati sia ad A sia a B (possibile percorso a 2 passi):\n"
        for inter in intermediari:
            testo += (
                f"  - Società {inter} | {verso_relazione(nodo_a, inter)} ({descrivi_documenti(nodo_a, inter)}); "
                f"{verso_relazione(inter, nodo_b)} ({descrivi_documenti(inter, nodo_b)})\n"
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
    testo += f"Soggetto: Società {nodo}\n"
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
    testo += f"Soggetto: Società {nodo} | Stato noto: {stato_compliance(nodo)}\n"
    testo += f"Controparti dirette ({len(diretti)}):\n"
    for vicino in diretti:
        migliore = max(punteggi_nodo(vicino), key=lambda voce: voce["punteggio"])
        testo += (
            f"  - Società {vicino} | {verso_relazione(nodo, vicino)} | {descrivi_documenti(nodo, vicino)}\n"
            f"    Stato noto: {stato_compliance(vicino)} "
            f"| punteggio GNN più alto: {migliore['punteggio']*100:.2f}% ({migliore['tipo']})\n"
        )
    if not diretti:
        testo += "  - nessuna\n"
    testo += f"Soggetti raggiungibili in 2 passi: {len(indiretti)}\n"
    testo += (
        "Fra questi, con irregolarità accertate: "
        + (", ".join(f"Società {v}" for v in indiretti_irregolari) or "nessuno")
        + "\n"
    )
    return testo


# =====================================================================
# 3. STRUMENTI ESPOSTI ALLA CHAT
# =====================================================================
# Nome della funzione, parametri e descrizione sono ciò che il modello della chat
# legge per decidere quale strumento chiamare: fanno parte del contratto
# (contratto.NOMI_STRUMENTI). I parametri vengono controllati qui; un valore non
# ammesso produce un messaggio in chiaro, mai un errore del programma.
def _errore_tipo(tipo):
    if tipo and tipo not in TIPI_IRREGOLARITA:
        return f"Tipo di irregolarità non riconosciuto: '{tipo}'. Valori ammessi: {', '.join(TIPI_IRREGOLARITA)}."
    return None


def _errore_societa(*numeri):
    for numero in numeri:
        if not esiste(numero):
            return f"La società {numero} non è presente nell'archivio."
    return None


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


def relazione(societa_a: int, societa_b: int, tipo: str = "") -> str:
    """Descrive il rapporto fra due società: connessione diretta, documenti scambiati,
    intermediari comuni, punteggi di rischio. Da usare quando la domanda cita due società.
    societa_a, societa_b: numeri identificativi delle due società.
    tipo: lasciare vuoto, oppure il tipo di irregolarità su cui concentrare la spiegazione."""
    errore = _errore_tipo(tipo) or _errore_societa(societa_a, societa_b)
    if errore:
        return errore
    if int(societa_a) == int(societa_b):
        return "Indicare due società diverse."
    return genera_contesto_investigativo(int(societa_a), int(societa_b), tipo or None)


def spiegazione(societa: int, tipo: str = "") -> str:
    """Spiega perché una società è considerata a rischio: punteggi, caratteristiche e
    relazioni che hanno pesato di più. Da usare per domande come "perché la società 12 è a rischio".
    societa: numero identificativo della società.
    tipo: lasciare vuoto per l'irregolarità con il punteggio più alto, oppure indicarne una."""
    errore = _errore_tipo(tipo) or _errore_societa(societa)
    if errore:
        return errore
    return contesto_spiegazione(int(societa), tipo or None)


def vicinato(societa: int) -> str:
    """Elenca le controparti commerciali di una società con i documenti scambiati, e conta i
    soggetti raggiungibili in due passi. Da usare per domande come "con chi commercia la società 12".
    societa: numero identificativo della società."""
    errore = _errore_societa(societa)
    if errore:
        return errore
    return contesto_vicinato(int(societa))


STRUMENTI = {
    "classifica": classifica,
    "relazione": relazione,
    "spiegazione": spiegazione,
    "vicinato": vicinato,
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
    "relazione fra due società, spiegazione del rischio di una società, controparti di una società "
    "(indicando le società con il loro numero, es. 'società 12')."
)


def estrai_nodi_dalla_domanda(domanda):
    """
    Estrae dalla domanda i numeri delle società citate (es. "società 12").
    Con i dati reali andrà sostituita da una risoluzione per nome o identificativo fiscale.
    """
    trovati = []
    for testo_numero in re.findall(
        r"(?:societ[àa]|nodo|azienda|soggetto|impresa)\s+#?(\d+)", domanda, flags=re.IGNORECASE
    ):
        nodo = int(testo_numero)
        if nodo not in trovati:
            trovati.append(nodo)
    return trovati


def smista_con_regole(domanda):
    """Riconosce l'intento con parole chiave: {intento, nodi, n, tipo, popolazione}."""
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

    chiede_classifica = re.search(
        r"più\s+(?:a\s+)?risch|maggior(?:e)?\s+rischio|classifica|graduatoria|"
        r"(?:prime|primi|top)\s+\w+|da\s+(?:ispezionare|controllare)",
        testo,
    )
    chiede_vicinato = re.search(
        r"con\s+chi|commerci|clienti|fornitori|controparti|collegat|vicin", testo
    )
    if chiede_classifica and not nodi:
        intento = "classifica"
    elif len(nodi) >= 2:
        intento = "relazione"
    elif len(nodi) == 1:
        intento = "vicinato" if chiede_vicinato else "spiegazione"
    else:
        intento = "non_supportata"

    return {"intento": intento, "nodi": nodi, "n": n, "tipo": tipo, "popolazione": popolazione}


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
    return MESSAGGIO_NON_SUPPORTATA


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('Uso: python -m controlli_grafo.interrogazione "domanda"')
        sys.exit(2)
    apri()
    print(consulta(" ".join(sys.argv[1:])))
    chiudi()
