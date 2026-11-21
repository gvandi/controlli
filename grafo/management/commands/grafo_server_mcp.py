from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Avvia il server MCP per la chat (trasporto stdio; richiede la libreria mcp)."

    def handle(self, *args, **opzioni):
        # Importato qui: la libreria mcp serve solo a questo comando
        from grafo import server_mcp

        server_mcp.avvia()
