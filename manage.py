#!/usr/bin/env python
"""Punto di ingresso dei comandi di amministrazione di Django."""
import os
import sys


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Django non è installato o l'ambiente virtuale non è attivo. "
            "Vedi README.md, sezione 'Primo avvio'."
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
