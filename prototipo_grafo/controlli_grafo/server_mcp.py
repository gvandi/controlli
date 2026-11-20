# >>> NOVITA (generato da aggiorna_intestazioni.py da NOVITA.md: non modificare a mano)
#
#   server_mcp.py  -  progetto controlli_grafo, VERSIONE 16
#
#   NOVITÀ RISPETTO ALLA VERSIONE 12  ([NN] = versione che ha introdotto la novità)
#   Parte del registro: server
#
#   [16] Nuovo server MCP (server_mcp.py) che registra i quattro strumenti della libreria, per
#        usare Unsloth Studio come chat.
#   [16] All'avvio apre l'archivio: se non combacia con il codice il server non parte.
#
# <<< NOVITA
"""
SERVER MCP: espone alla chat (Unsloth Studio o qualsiasi client MCP) i quattro
strumenti della libreria di interrogazione.

Qui non c'è logica: nomi, parametri, descrizioni e controlli degli strumenti
stanno in interrogazione.py; l'elenco dei nomi sta in contratto.py.

    pip install "mcp[cli]"
    python -m controlli_grafo.server_mcp        (trasporto stdio)

Importa contratto.py e interrogazione.py.
"""

from mcp.server.fastmcp import FastMCP

from . import contratto, interrogazione

server = FastMCP("controlli-uae")

# Ogni funzione viene registrata con il proprio nome, i propri parametri tipizzati
# e la propria descrizione: è ciò che il modello della chat legge per scegliere.
for nome in contratto.NOMI_STRUMENTI:
    server.tool()(interrogazione.STRUMENTI[nome])


if __name__ == "__main__":
    # Se l'archivio non combacia con il codice il server non parte: meglio un
    # errore all'avvio che risposte sbagliate in chat.
    interrogazione.apri()
    server.run()
