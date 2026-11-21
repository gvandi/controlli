from django.core.management.base import BaseCommand

from grafo import interrogazione, mappa


class Command(BaseCommand):
    help = "Scrive il report e la mappa investigativa di un soggetto (richiede networkx e pyvis)."

    def add_arguments(self, parser):
        parser.add_argument("--soggetto", help="Nome, numero di iscrizione o numero della società.")

    def handle(self, *args, **opzioni):
        from grafo import calcolo_cartella

        soggetto = None
        if opzioni["soggetto"]:
            soggetto, errore = interrogazione.risolvi_societa(opzioni["soggetto"])
            if errore:
                self.stderr.write(errore)
                return
        percorso = mappa.genera(calcolo_cartella.cartella_dati(), soggetto)
        if percorso is None:
            self.stdout.write("Nessuna irregolarità accertata nell'archivio: mappa non generata.")
        else:
            self.stdout.write(f"Mappa scritta in {percorso}")
