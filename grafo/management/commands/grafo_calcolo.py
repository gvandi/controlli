from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Calcola i punteggi di rischio (richiede PyTorch) oppure le sole spiegazioni in coda."

    def add_arguments(self, parser):
        parser.add_argument(
            "--spiegazioni", action="store_true",
            help="Non riaddestra: calcola solo le spiegazioni chieste dalle interrogazioni.",
        )

    def handle(self, *args, **opzioni):
        # Importato qui: PyTorch serve solo a questo comando
        from grafo import calcolo

        if opzioni["spiegazioni"]:
            calcolo.elabora_richieste()
        else:
            calcolo.esegui_calcolo()
