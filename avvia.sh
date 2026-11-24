#!/usr/bin/env bash
# Avvia l'applicativo e, insieme, il processo che esegue i lavori lanciati dall'interfaccia
# (elaborazione dei file, indici, analisi di rete). Ctrl+C ferma entrambi.
#
#   ./avvia.sh              applicativo su 127.0.0.1:8000
#   ./avvia.sh 0.0.0.0:8000 applicativo raggiungibile dalla rete
#
# Per l'uso in produzione i due processi vanno affidati a un gestore di servizi (systemd):
# questo file serve per lo sviluppo e le prove.
set -euo pipefail
cd "$(dirname "$0")"
if [ -f .venv/bin/activate ]; then source .venv/bin/activate; fi

python manage.py esegui_lavori &
ESECUTORE=$!
trap 'kill "$ESECUTORE" 2>/dev/null || true' EXIT INT TERM

python manage.py runserver "${1:-127.0.0.1:8000}"
