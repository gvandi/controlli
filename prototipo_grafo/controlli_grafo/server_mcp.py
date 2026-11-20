# >>> NOVITA (generato da aggiorna_intestazioni.py da NOVITA.md: non modificare a mano)
#
#   server_mcp.py  -  progetto controlli_grafo, VERSIONE 17
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
#
# <<< NOVITA
"""
SERVER MCP: espone alla chat (Unsloth Studio o qualsiasi client MCP) i quattro
strumenti della libreria di interrogazione.

Qui non c'è logica: nomi, parametri, descrizioni e controlli degli strumenti
stanno in interrogazione.py; l'elenco dei nomi sta in contratto.py.

    pip install "mcp[cli]"
    python -m controlli_grafo.server_mcp        (trasporto stdio; mcp 1.x o 2.x)

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


if __name__ == "__main__":
    # Se l'archivio non combacia con il codice il server non parte: meglio un
    # errore all'avvio che risposte sbagliate in chat.
    interrogazione.apri()
    server.run(transport="stdio")
