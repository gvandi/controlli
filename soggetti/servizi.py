"""Operazioni sull'anagrafica: trovare un soggetto dal suo identificativo, o crearlo."""
from django.db import transaction

from .models import IdentificativoSoggetto, Soggetto


class IdentificativoNonValido(ValueError):
    """Il valore non rispetta il formato previsto per quel tipo di identificativo."""


def trova(tipo, valore):
    """Il soggetto che ha quell'identificativo, oppure None."""
    riga = (
        IdentificativoSoggetto.objects.select_related("soggetto")
        .filter(tipo=tipo, valore_normalizzato=tipo.normalizza(valore))
        .first()
    )
    return riga.soggetto if riga else None


def trova_o_crea(tipo, valore, denominazione=""):
    """
    Restituisce (soggetto, creato). Se nessun soggetto ha quell'identificativo ne
    crea uno provvisorio. Solleva IdentificativoNonValido se il valore non rispetta
    il formato del tipo (per il COE: cinque cifre, DECISIONI.md n. 20).
    """
    if not tipo.accetta(valore):
        raise IdentificativoNonValido(f"'{valore}' non è un valore valido per {tipo.codice}.")
    denominazione = (denominazione or "").strip()
    soggetto = trova(tipo, valore)
    if soggetto is not None:
        if denominazione and not soggetto.denominazione:
            soggetto.denominazione = denominazione
            soggetto.save(update_fields=["denominazione"])
        return soggetto, False
    with transaction.atomic():
        soggetto = Soggetto.objects.create(denominazione=denominazione)
        IdentificativoSoggetto.objects.create(
            soggetto=soggetto, tipo=tipo, valore_originale=str(valore).strip()[:60],
            valore_normalizzato=tipo.normalizza(valore),
        )
    return soggetto, True


def etichetta(soggetto):
    """Come si nomina un soggetto nelle pagine: denominazione e identificativi."""
    identificativi = ", ".join(str(i) for i in soggetto.identificativi.select_related("tipo").order_by("pk"))
    nome = soggetto.denominazione or "Senza denominazione"
    return f"{nome} ({identificativi})" if identificativi else nome
