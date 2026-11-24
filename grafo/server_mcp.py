# >>> NOVITA (generato da aggiorna_intestazioni.py da NOVITA.md: non modificare a mano)
#
#   server_mcp.py  -  app grafo, VERSIONE 29
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
#
# <<< NOVITA
"""
SERVER MCP SU STDIO: espone gli strumenti a una chat che gira sullo STESSO
computer e avvia il server come comando locale.

Dalla versione 20 il collegamento normale è il servizio HTTP dell'applicativo
(views.py, indirizzo /grafo/mcp/), che riconosce l'utente e registra la
sessione. Questo trasporto resta per le prove su un solo computer: NON chiede
chi sei e NON registra sessioni né richieste.

    pip install "mcp[cli]"                     (versione 1 o 2)
    python manage.py grafo_server_mcp          (trasporto stdio)

Importa contratto.py, interrogazione.py e servizio_mcp.py.
"""

# La libreria mcp ha cambiato nome alla classe del server fra la versione 1 e la 2:
# si usa quella disponibile nell'ambiente.
try:
    from mcp.server.mcpserver import MCPServer as ServerMCP  # mcp 2.x
except ModuleNotFoundError:
    from mcp.server.fastmcp import FastMCP as ServerMCP  # mcp 1.x

from . import contratto, interrogazione, servizio_mcp

server = ServerMCP("controlli-uae")

# Ogni funzione viene registrata con il proprio nome, i propri parametri tipizzati
# e la propria descrizione: è ciò che il modello della chat legge per scegliere.
for nome in contratto.NOMI_STRUMENTI:
    server.add_tool(servizio_mcp.STRUMENTI[nome])


def avvia():
    """Avvia il server sul trasporto stdio (da: python manage.py grafo_server_mcp)."""
    # Se l'archivio non combacia con il codice il server non parte: meglio un
    # errore all'avvio che risposte sbagliate in chat.
    interrogazione.apri()
    server.run(transport="stdio")
