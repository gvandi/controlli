# >>> NOVITA (generato da aggiorna_intestazioni.py da NOVITA.md: non modificare a mano)
#
#   calcolatrice.py  -  app grafo, VERSIONE 23
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
#
# <<< NOVITA
"""
CALCOLATRICE: calcola in modo esatto un'espressione aritmetica scritta come testo.

Serve alla chat per non fare i conti "a mente": il modello passa l'espressione,
Python la calcola. L'espressione NON viene eseguita come codice: viene letta come
albero sintattico e si valutano solo numeri, operatori aritmetici e poche funzioni
matematiche. Tutto il resto è rifiutato.

Non usa Django né il database, e non importa nessun'altra parte dell'app: si
prova da sola.

    python -c "from grafo.calcolatrice import calcola; print(calcola('123456*3434'))"
"""
import ast
import math
import operator

OPERATORI = {
    ast.Add: operator.add, ast.Sub: operator.sub,
    ast.Mult: operator.mul, ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv, ast.Mod: operator.mod,
    ast.Pow: operator.pow, ast.USub: operator.neg, ast.UAdd: operator.pos,
}
FUNZIONI = {"sqrt": math.sqrt, "log": math.log, "exp": math.exp,
            "sin": math.sin, "cos": math.cos, "tan": math.tan,
            "abs": abs, "round": round}
COSTANTI = {"pi": math.pi, "e": math.e}

# Limiti: una richiesta dalla chat non deve poter tenere occupato il server
MAX_CARATTERI = 500
MAX_ESPONENTE = 10000
MAX_CIFRE = 4000  # cifre di un risultato intero


def _troppo_grande(base, esponente):
    """Vero se base ** esponente, fra interi, supererebbe MAX_CIFRE cifre (stima senza calcolarlo)."""
    if not (isinstance(base, int) and isinstance(esponente, int)) or esponente <= 1:
        return False
    return abs(base).bit_length() * esponente > MAX_CIFRE * 3.33


def valuta(nodo):
    """Valuta solo aritmetica: niente eval(), niente codice arbitrario."""
    if isinstance(nodo, ast.Constant) and type(nodo.value) in (int, float):
        return nodo.value
    if isinstance(nodo, ast.BinOp) and type(nodo.op) in OPERATORI:
        a, b = valuta(nodo.left), valuta(nodo.right)
        if isinstance(nodo.op, ast.Pow) and (abs(b) > MAX_ESPONENTE or _troppo_grande(a, b)):
            raise ValueError("potenza troppo grande")
        return OPERATORI[type(nodo.op)](a, b)
    if isinstance(nodo, ast.UnaryOp) and type(nodo.op) in OPERATORI:
        return OPERATORI[type(nodo.op)](valuta(nodo.operand))
    if isinstance(nodo, ast.Name) and nodo.id in COSTANTI:
        return COSTANTI[nodo.id]
    if (isinstance(nodo, ast.Call) and isinstance(nodo.func, ast.Name)
            and nodo.func.id in FUNZIONI and not nodo.keywords):
        return FUNZIONI[nodo.func.id](*[valuta(a) for a in nodo.args])
    raise ValueError("espressione non ammessa")


def calcola_espressione(espressione):
    """Il risultato come testo, oppure 'Errore: ...' (mai un'eccezione)."""
    espressione = str(espressione).strip()
    if not espressione:
        return "Errore: indicare l'espressione da calcolare."
    if len(espressione) > MAX_CARATTERI:
        return f"Errore: espressione troppo lunga (massimo {MAX_CARATTERI} caratteri)."
    try:
        albero = ast.parse(espressione.replace("^", "**"), mode="eval")
        return str(valuta(albero.body))
    except ZeroDivisionError:
        return "Errore: divisione per zero."
    except SyntaxError:
        return "Errore: espressione scritta male."
    except Exception as errore:
        return f"Errore: {errore}"


def calcola(espressione: str) -> str:
    """Calcola in modo esatto un'espressione aritmetica, es. "123456*3434".
    Usalo per QUALSIASI calcolo numerico (somme di importi, percentuali, differenze)
    invece di calcolare a mente.
    espressione: ammessi + - * / // % ** parentesi, sqrt log exp sin cos tan abs round, pi, e.
    Il separatore decimale è il punto; non usare separatori delle migliaia."""
    return calcola_espressione(espressione)
