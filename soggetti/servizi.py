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


# Testi che NON sono un nome: chi li ha scritti voleva dire "non lo so"
SEGNAPOSTO = (
    "", "-", "--", "nd", "n.d.", "n.d", "n/d", "non rilevata", "non rilevato", "non rilevabile", "non disponibile",
    "non nota", "non noto", "sconosciuta", "sconosciuto", "senza denominazione", "da definire", "?",
)


def nome_vero(testo):
    """Il nome ripulito, oppure "" se è vuoto o è un segnaposto come "non rilevata"."""
    nome = " ".join(str(testo or "").split())
    return "" if nome.lower().rstrip(".") in {s.rstrip(".") for s in SEGNAPOSTO} else nome


def imposta_denominazione(soggetto, nome, ufficiale=False):
    """
    L'UNICO punto in cui si decide come si chiama un soggetto (DECISIONI.md, n. 93).
    Tutte le pagine e gli strumenti mostrano Soggetto.denominazione; qui si stabilisce
    chi può scriverla:

      - ufficiale=True   il nome viene dall'anagrafica ufficiale (file CSV): PREVALE
                         su qualsiasi nome precedente;
      - ufficiale=False  il nome viene da un documento o da una dichiarazione: vale
                         solo se il soggetto non ha ancora un nome vero (vuoto o segnaposto).

    Un segnaposto ("non rilevata") non è mai un nome: non sostituisce nulla.
    Restituisce True se la denominazione è cambiata.
    """
    nome = nome_vero(nome)[:255]
    if not nome or nome == soggetto.denominazione:
        return False
    if not ufficiale and nome_vero(soggetto.denominazione):
        return False
    soggetto.denominazione = nome
    soggetto.save(update_fields=["denominazione"])
    return True


def trova_o_crea(tipo, valore, denominazione=""):
    """
    Restituisce (soggetto, creato). Se nessun soggetto ha quell'identificativo ne
    crea uno provvisorio. Solleva IdentificativoNonValido se il valore non rispetta
    il formato del tipo (per il COE: cinque cifre, DECISIONI.md n. 20).
    """
    if not tipo.accetta(valore):
        raise IdentificativoNonValido(f"'{valore}' non è un valore valido per {tipo.codice}.")
    denominazione = nome_vero(denominazione)[:255]
    soggetto = trova(tipo, valore)
    if soggetto is not None:
        imposta_denominazione(soggetto, denominazione)
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
    nome = nome_vero(soggetto.denominazione) or "Senza denominazione"
    return f"{nome} ({identificativi})" if identificativi else nome
