# >>> NOVITA (generato da aggiorna_intestazioni.py da NOVITA.md: non modificare a mano)
#
#   server_mcp.py  -  app grafo, VERSIONE 19.0
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
#
# <<< NOVITA
"""
SERVER MCP: espone alla chat (Unsloth Studio o qualsiasi client MCP) i cinque
strumenti della libreria di interrogazione.

Qui non c'è logica: nomi, parametri, descrizioni e controlli degli strumenti
stanno in interrogazione.py; l'elenco dei nomi sta in contratto.py.

    pip install "mcp[cli]"                     (versione 1 o 2)
    python manage.py grafo_server_mcp          (trasporto stdio)

Importa contratto.py e interrogazione.py.
"""

# La libreria mcp ha cambiato nome alla classe del server fra la versione 1 e la 2:
# si usa quella disponibile nell'ambiente.
try:
    from mcp.server.mcpserver import MCPServer as ServerMCP  # mcp 2.x
except ModuleNotFoundError:
    from mcp.server.fastmcp import FastMCP as ServerMCP  # mcp 1.x

from . import contratto, interrogazione

server = ServerMCP("controlli-uae")

# Ogni funzione viene registrata con il proprio nome, i propri parametri tipizzati
# e la propria descrizione: è ciò che il modello della chat legge per scegliere.
for nome in contratto.NOMI_STRUMENTI:
    server.add_tool(interrogazione.STRUMENTI[nome])



def avvia():
    """Avvia il server sul trasporto stdio (da: python manage.py grafo_server_mcp)."""
    # Se l'archivio non combacia con il codice il server non parte: meglio un
    # errore all'avvio che risposte sbagliate in chat.
    interrogazione.apri()
    server.run(transport="stdio")
