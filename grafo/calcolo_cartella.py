"""Cartella dei file del prototipo (JSON in ingresso, modelli, mappe): fuori dal repository.

Sta in un modulo a parte perché serve anche a chi non ha PyTorch (comando grafo_mappa).
Non importa nessun'altra parte dell'app.
"""
from pathlib import Path

from django.conf import settings


def cartella_dati():
    cartella = Path(getattr(settings, "GRAFO_CARTELLA", Path(settings.BASE_DIR) / "dati_grafo"))
    cartella.mkdir(parents=True, exist_ok=True)
    return cartella
