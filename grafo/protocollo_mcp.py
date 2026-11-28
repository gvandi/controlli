# >>> NOVITA (generato da aggiorna_intestazioni.py da NOVITA.md: non modificare a mano)
#
#   protocollo_mcp.py  -  app grafo, VERSIONE 39
#
#   NOVITÀ RISPETTO ALLA VERSIONE 12  ([NN] = versione che ha introdotto la novità)
#   Parte del registro: server
#
#   [16] Nuovo server MCP (server_mcp.py) che registra i quattro strumenti della libreria, per
#        usare Unsloth Studio come chat.
#   [16] All'avvio apre l'archivio: se non combacia con il codice il server non parte.
#   [17] Compatibile con la libreria mcp 1.x (FastMCP) e 2.x (MCPServer): con la 2.x la versione
#        16 non partiva (ModuleNotFoundError).
#   [17] Strumenti registrati con add_tool() e trasporto stdio indicato in modo esplicito.
#   [18] Registra anche il quinto strumento, indicatore (nessuna modifica al codice: l'elenco
#        viene da contratto.py).
#   [19] Si avvia con python manage.py grafo_server_mcp, che carica le impostazioni
#        dell'applicativo.
#   [20] Nuovo servizio MCP su HTTP dentro l'applicativo (views.py, indirizzo /grafo/mcp/): la
#        chat si collega dalla rete e si presenta con un token personale; senza token valido la
#        risposta è 401.
#   [20] Il protocollo è scritto in protocollo_mcp.py (initialize, ping, tools/list,
#        tools/call), senza la libreria mcp, che resta solo per il trasporto stdio.
#   [20] Ogni chiamata passa da servizio_mcp.esegui_strumento(): la richiesta viene registrata
#        nella sessione prima dell'esecuzione e completata con esito, durata e coppia
#        calcolo/dati.
#   [20] Ogni strumento ha in più il parametro facoltativo domanda, in cui il modello della chat
#        ricopia la domanda dell'ispettore per il registro.
#   [20] Nuovo strumento mappa(societa): produce la mappa investigativa e restituisce il
#        collegamento alla pagina /grafo/mappe/N/, visibile dopo l'accesso solo a chi l'ha
#        chiesta.
#   [20] Nuove pagine: /grafo/collegamento/ (l'analista crea e revoca i propri token, ritrova le
#        proprie mappe) e /grafo/cruscotto/ (l'amministratore vede le quattro versioni, i
#        calcoli presenti, le sessioni, e modifica i parametri).
#   [20] Il server stdio (grafo_server_mcp) resta per le prove su un solo computer: non
#        riconosce l'utente e non registra sessioni.
#   [21] Accesso OAuth 2.0 dal browser: l'applicativo è il server di autorizzazione (libreria
#        django-oauth-toolkit 3.4, indirizzi sotto /o/); la chat si registra da sola, l'analista
#        accede e autorizza, il token non si copia più a mano.
#   [21] Il rifiuto 401 indica alla chat il documento da cui partire (intestazione WWW-
#        Authenticate con resource_metadata); i documenti di scoperta sono alla radice del sito
#        (/.well-known/...).
#   [21] views.py riconosce chi chiama in un solo punto (_identita_della_richiesta): token OAuth
#        verificato dalla libreria (scadenza, ambito, servizio a cui è destinato) oppure token
#        personale.
#   [21] Utente riconosciuto ma senza il diritto usa_chat: risposta 403, distinta dal 401 che fa
#        ripartire l'accesso.
#   [21] Nuova pagina di consenso in italiano (templates/oauth2_provider/authorize.html): mostra
#        il programma che chiede l'accesso e l'indirizzo a cui si viene rimandati.
#   [21] La pagina "Collegamento alla chat" indica l'accesso OAuth come via normale e i token
#        personali come ripiego; il cruscotto mostra per ogni sessione il tipo di accesso.
#   [21] La pagina di consenso si salta quando l'utente ha già autorizzato lo stesso programma e
#        il suo token non è scaduto (REQUEST_APPROVAL_PROMPT auto; con
#        CONTROLLI_OAUTH_CONSENSO=force torna a ogni accesso).
#   [22] Nuovo strumento calcola(espressione), nel modulo calcolatrice.py: aritmetica esatta per
#        la chat, valutata come albero sintattico senza eseguire codice; limiti su lunghezza,
#        esponente e dimensione del risultato.
#   [22] Le chiamate a calcola sono registrate nella sessione come le altre, senza coppia
#        calcolo/dati; lo strumento funziona anche se l'archivio non è utilizzabile.
#   [23] Nuovo strumento scheda(azienda): dice ciò che l'archivio sa di un'azienda (voci note
#        con il file di provenienza, voci non ancora arrivate, documenti confermati in cui
#        compare con il ruolo e le altre parti); l'azienda si indica con COE, partita IVA o
#        nome.
#   [23] scheda usa solo ciò che viene da file che l'utente della sessione può vedere (stessa
#        regola delle pagine); senza sessione (trasporto stdio) non risponde.
#   [26] Nuovo strumento spazio(regola, azienda): racconta lo spazio degli indici (per quali
#        aziende scatta una regola, quali si discostano dalle aziende simili, i rapporti di
#        un'azienda dai documenti confermati) e dà il collegamento alla pagina in tre
#        dimensioni, con regola e azienda già scelte.
#   [26] esegui_strumento() riceve l'indirizzo pubblico dell'applicativo, per i collegamenti
#        alle pagine che non sono mappe.
#   [27] Lo strumento classifica risponde per criteri distinti: 1) regole di rischio che
#        scattano (tutte quelle attive, o quella indicata nel nuovo parametro regola), 2)
#        scostamento dalle aziende simili, 3) rapporti con aziende segnalate, 4) punteggio
#        dell'analisi di rete; in testa le aziende segnalate da più criteri.
#   [27] Quando l'esecuzione in uso è l'indice a regole (dati reali), classifica non la presenta
#        come un quarto criterio: dichiara che la GNN non è calcolata su quei dati. Senza
#        sessione (stdio) classifica resta la sola analisi di rete.
#   [28] Lo strumento indicatore, se riceve come termine solo parole che indicano lo spazio
#        degli indici (indici, spazio, regole), passa la domanda allo strumento spazio; le
#        descrizioni dei due strumenti dicono esplicitamente quando usare l'uno e quando
#        l'altro.
#   [30] La pagina di una mappa che non si può mostrare resta 404 ma spiega che cosa fare: con
#        quale utente si è collegati e che la mappa si apre con l'utente che ha autorizzato la
#        chat, oppure che il file non c'è più e va richiesta di nuovo; il motivo preciso va nel
#        registro del server.
#   [31] Gli strumenti mappa e spazio dicono con quale utente va aperto il collegamento (quello
#        che ha autorizzato la chat); la pagina di collegamento elenca le chat autorizzate con
#        il proprio utente e permette di scollegarle.
#   [35] Le risposte degli strumenti e il prompt di sistema dicono «società».
#   [36] Quando l'archivio non è utilizzabile la chat risponde che l'analisi di rete non è
#        disponibile e che non dipende dalla domanda; il motivo tecnico segue come dettaglio per
#        l'amministratore.
#   [39] La mappa di rete si può chiedere anche da una pagina dell'applicativo: nuovo indirizzo
#        /grafo/mappe/nuova/ (views.nuova_mappa) e mappa_dalla_pagina() in servizio_mcp.py, con
#        la richiesta nel registro come per la chat.
#
# <<< NOVITA
"""
PROTOCOLLO MCP SU HTTP, nella parte che serve a un servizio di soli strumenti.

MCP è JSON-RPC 2.0: la chat manda un messaggio, il servizio risponde. Su HTTP
("Streamable HTTP") ogni messaggio è una POST e la risposta può essere un
semplice documento JSON. Qui ci sono solo le regole del protocollo:

    initialize        presentazione reciproca e scelta della versione
    ping              controllo che il servizio sia vivo
    tools/list        elenco degli strumenti con nome, descrizione e parametri
    tools/call        esecuzione di uno strumento
    notifications/*   avvisi della chat: non hanno risposta

Questo modulo non conosce Django, il database né le sessioni: riceve gli
strumenti come funzioni Python e chi lo chiama decide come eseguirli. Per questo
si prova da solo. Importa soltanto contratto.py.

Perché non la libreria mcp: l'identità di chi chiama (token, sessione) deve
arrivare fino allo strumento, e il servizio deve stare dentro l'applicativo per
usarne utenti e accesso. Con una vista Django il percorso è breve e tutto nostro.
La libreria resta in uso per il trasporto stdio (server_mcp.py).
"""
import inspect
import typing

from . import contratto

ERRORE_RICHIESTA_NON_VALIDA = -32600
ERRORE_METODO_SCONOSCIUTO = -32601
ERRORE_PARAMETRI = -32602

# Parametro aggiunto a ogni strumento: il modello della chat vi ricopia la domanda
# dell'ispettore, che altrimenti il servizio non vedrebbe mai.
PARAMETRO_DOMANDA = "domanda"
DESCRIZIONE_DOMANDA = (
    "Ricopia qui, parola per parola, l'ultima domanda scritta dall'ispettore. "
    "Serve solo al registro delle richieste: non cambia la risposta."
)

_TIPI_JSON = {int: "integer", str: "string", float: "number", bool: "boolean"}


def _schema_del_tipo(annotazione):
    """Traduce un'annotazione Python (int, str, Union[int, str]) in JSON Schema."""
    if annotazione in _TIPI_JSON:
        return {"type": _TIPI_JSON[annotazione]}
    if typing.get_origin(annotazione) is typing.Union:
        return {"anyOf": [_schema_del_tipo(parte) for parte in typing.get_args(annotazione)]}
    return {}


def descrivi_strumento(funzione):
    """
    Ciò che la chat legge per scegliere uno strumento: nome della funzione,
    descrizione (docstring) e parametri ricavati dalla firma.
    """
    proprieta, obbligatori = {}, []
    for nome, parametro in inspect.signature(funzione).parameters.items():
        schema = _schema_del_tipo(parametro.annotation)
        if parametro.default is inspect.Parameter.empty:
            obbligatori.append(nome)
        else:
            schema["default"] = parametro.default
        proprieta[nome] = schema
    proprieta[PARAMETRO_DOMANDA] = {"type": "string", "description": DESCRIZIONE_DOMANDA}
    schema = {"type": "object", "properties": proprieta}
    if obbligatori:
        schema["required"] = obbligatori
    return {
        "name": funzione.__name__,
        "description": inspect.cleandoc(funzione.__doc__ or ""),
        "inputSchema": schema,
    }


def prepara_argomenti(funzione, argomenti):
    """
    Separa la domanda ricopiata dal modello dai parametri veri dello strumento.
    Restituisce (parametri, domanda, errore). Gli argomenti che lo strumento non
    conosce si ignorano (lettore tollerante); se ne manca uno obbligatorio
    l'errore è un testo da restituire alla chat.
    """
    argomenti = dict(argomenti or {})
    domanda = str(argomenti.pop(PARAMETRO_DOMANDA, "") or "")
    firma = inspect.signature(funzione).parameters
    parametri = {nome: valore for nome, valore in argomenti.items() if nome in firma}
    mancanti = [
        nome for nome, parametro in firma.items()
        if parametro.default is inspect.Parameter.empty and nome not in parametri
    ]
    if mancanti:
        return parametri, domanda, f"Parametri mancanti: {', '.join(mancanti)}."
    return parametri, domanda, None


def scegli_protocollo(richiesto):
    """La versione chiesta dalla chat se la conosciamo, altrimenti la nostra preferita."""
    return richiesto if richiesto in contratto.PROTOCOLLI_MCP else contratto.PROTOCOLLI_MCP[0]


def e_una_richiesta(messaggio):
    """Vero se il messaggio aspetta una risposta (ha un 'id'); falso per gli avvisi."""
    return isinstance(messaggio, dict) and "method" in messaggio and "id" in messaggio


def metodo(messaggio):
    return messaggio.get("method") if isinstance(messaggio, dict) else None


def _risultato(messaggio, risultato):
    return {"jsonrpc": "2.0", "id": messaggio.get("id"), "result": risultato}


def errore(messaggio, codice, testo):
    identificativo = messaggio.get("id") if isinstance(messaggio, dict) else None
    return {"jsonrpc": "2.0", "id": identificativo, "error": {"code": codice, "message": testo}}


def testo_per_la_chat(testo, e_errore=False):
    """Forma del risultato di tools/call: un blocco di testo."""
    return {"content": [{"type": "text", "text": str(testo)}], "isError": bool(e_errore)}


def rispondi(messaggio, strumenti, esegui, istruzioni=""):
    """
    Risponde a UN messaggio JSON-RPC. Restituisce il documento di risposta, oppure
    None se il messaggio è un avviso (o una risposta della chat) e non ne vuole.

    strumenti: {nome: funzione}
    esegui(nome, parametri, domanda) -> (testo, e_errore): chi chiama decide come
        eseguire lo strumento (registro delle richieste, sessione, lucchetto).
    """
    if not isinstance(messaggio, dict) or messaggio.get("jsonrpc") != "2.0":
        return errore(messaggio, ERRORE_RICHIESTA_NON_VALIDA, "Messaggio JSON-RPC 2.0 non valido.")
    if not e_una_richiesta(messaggio):
        return None

    nome_metodo, parametri = messaggio["method"], messaggio.get("params") or {}

    if nome_metodo == "initialize":
        risultato = {
            "protocolVersion": scegli_protocollo(parametri.get("protocolVersion")),
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": "controlli-uae", "version": contratto.VERSIONE_CODICE},
        }
        if istruzioni:
            risultato["instructions"] = istruzioni
        return _risultato(messaggio, risultato)

    if nome_metodo == "ping":
        return _risultato(messaggio, {})

    if nome_metodo == "tools/list":
        return _risultato(messaggio, {"tools": [descrivi_strumento(f) for f in strumenti.values()]})

    if nome_metodo == "tools/call":
        nome = parametri.get("name")
        if nome not in strumenti:
            return errore(messaggio, ERRORE_PARAMETRI, f"Strumento sconosciuto: {nome}")
        argomenti = parametri.get("arguments")
        if argomenti is not None and not isinstance(argomenti, dict):
            return errore(messaggio, ERRORE_PARAMETRI, "'arguments' deve essere un oggetto.")
        valori, domanda, mancanti = prepara_argomenti(strumenti[nome], argomenti)
        if mancanti:
            return _risultato(messaggio, testo_per_la_chat(mancanti, e_errore=True))
        testo, e_errore = esegui(nome, valori, domanda)
        return _risultato(messaggio, testo_per_la_chat(testo, e_errore))

    return errore(messaggio, ERRORE_METODO_SCONOSCIUTO, f"Metodo non supportato: {nome_metodo}")
