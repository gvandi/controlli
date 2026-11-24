"""
    python manage.py esegui_lavori [--tipi elabora_file,calcola_indici] [--pausa 3] [--una-volta]

Il processo che esegue i lavori lanciati dall'interfaccia. Va avviato insieme
all'applicativo (avvia.sh lo fa) e lasciato acceso: senza di lui i lavori restano
"richiesti". Su più macchine se ne avvia uno per macchina, con --tipi: per esempio
sulla macchina con il modello locale "--tipi elabora_file", su quella con PyTorch
"--tipi calcola_gnn,spiegazioni".
"""
import os
import socket
import time

from django.core.management.base import BaseCommand, CommandError
from django.db import close_old_connections

from lavori import servizi


class Command(BaseCommand):
    help = "Esegue i lavori lanciati dall'interfaccia (elaborazione dei file, indici, analisi di rete)."

    def add_arguments(self, parser):
        parser.add_argument("--tipi", default="", help="Tipi di lavoro da eseguire, separati da virgola. Vuoto: tutti.")
        parser.add_argument("--pausa", type=int, default=3, help="Secondi di attesa quando non c'è nulla da fare.")
        parser.add_argument("--una-volta", action="store_true", help="Esegue i lavori richiesti e termina (per le prove).")

    def handle(self, *args, **opzioni):
        tipi = [t.strip() for t in opzioni["tipi"].split(",") if t.strip()]
        sconosciuti = [t for t in tipi if t not in servizi.TIPI]
        if sconosciuti:
            raise CommandError(f"Tipi sconosciuti: {', '.join(sconosciuti)}. Ammessi: {', '.join(servizi.TIPI)}")
        nome = f"{socket.gethostname()}:{os.getpid()}"
        interrotti = servizi.chiudi_interrotti(tipi)
        if interrotti:
            self.stdout.write(f"Lavori rimasti in corso da un'esecuzione precedente, chiusi come falliti: {interrotti}")
        self.stdout.write(f"In ascolto ({', '.join(tipi) or 'tutti i tipi'}). Ctrl+C per fermare.")
        try:
            while True:
                close_old_connections()
                servizi.segnala(nome, tipi)
                lavoro = servizi.prendi(tipi)
                if lavoro is None:
                    if opzioni["una_volta"]:
                        return
                    time.sleep(opzioni["pausa"])
                    continue
                self.stdout.write(f"Lavoro n. {lavoro.pk}, {lavoro.tipo}: avviato")
                servizi.esegui(lavoro)
                self.stdout.write(f"Lavoro n. {lavoro.pk}, {lavoro.tipo}: {lavoro.stato}. {lavoro.esito.splitlines()[0] if lavoro.esito else ''}")
        except KeyboardInterrupt:
            self.stdout.write("Fermato.")
