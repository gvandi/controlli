"""
ANAGRAFICA UNICA DEI SOGGETTI (passo 2, versione minima).

Aziende analizzate e controparti stanno nello stesso archivio (DECISIONI.md, n. 13).
L'identificativo fiscale NON è la chiave del soggetto (n. 14): la chiave è interna,
e ogni soggetto ha una o più righe di identificativi, ciascuna con il suo tipo
(COE, partita IVA...). Due scritture dello stesso identificativo ("SM 12345" e
"12345") coincidono perché si confrontano dopo la normalizzazione.

Qui non c'è nessuna informazione su indagini o controlli (n. 17).

DATI PER PERIODO (n. 86): attività economica, dipendenti e fatturato di un soggetto
in un periodo. La chiave è la coppia soggetto + periodo: lo stesso COE compare una
volta per periodo. Il periodo è un anno ("2025") e potrà essere un mese ("2025-03").
I dati arrivano da un file CSV (indici/importazione.py), non dai file caricati.
"""
import re
from django.core.exceptions import ValidationError
from django.db import models


class Soggetto(models.Model):
    denominazione = models.CharField(max_length=255, blank=True, default="")
    # Provvisorio: creato da un identificativo dichiarato o letto in un documento,
    # in attesa dei dati dell'anagrafica ufficiale
    provvisorio = models.BooleanField(default=True)
    creato_il = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.denominazione or f"Soggetto n. {self.pk}"


class IdentificativoSoggetto(models.Model):
    soggetto = models.ForeignKey(Soggetto, on_delete=models.CASCADE, related_name="identificativi")
    tipo = models.ForeignKey("decodifiche.TipoIdentificativo", on_delete=models.PROTECT, related_name="+")
    valore_originale = models.CharField(max_length=60)
    valore_normalizzato = models.CharField(max_length=60)
    valido_dal = models.DateField(null=True, blank=True)
    valido_al = models.DateField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["tipo", "valore_normalizzato"], name="identificativo_unico"),
        ]

    def __str__(self):
        return f"{self.tipo.codice} {self.valore_normalizzato}"


PERIODO = re.compile(r"\d{4}(-(0[1-9]|1[0-2]))?")


def periodo_valido(valore):
    """Un anno ("2025") oppure anno e mese ("2025-03")."""
    if not PERIODO.fullmatch(str(valore)):
        raise ValidationError("Il periodo è un anno (2025) oppure anno e mese (2025-03).")


class DatiPerPeriodo(models.Model):
    """I dati di un soggetto in un periodo, come li dà l'anagrafica ufficiale."""

    soggetto = models.ForeignKey(Soggetto, on_delete=models.CASCADE, related_name="dati_per_periodo")
    periodo = models.CharField(max_length=7, validators=[periodo_valido])
    # Come il soggetto è chiamato nella fonte, in quel periodo
    denominazione = models.CharField(max_length=255, blank=True, default="")
    # Codice dell'attività economica (ATECO), così come è nella fonte: "47.26"
    codice_attivita = models.CharField(max_length=20, blank=True, default="")
    # Vuoto = la fonte non lo dice: è un dato mancante, non zero
    dipendenti = models.PositiveIntegerField(null=True, blank=True)
    fatturato = models.DecimalField(max_digits=16, decimal_places=2, null=True, blank=True)
    # Quando la fonte dà la CLASSE statistica e non il valore (per esempio "D0", "F2"):
    # codice della classe nelle decodifiche. Se c'è, vale lei; il valore resta vuoto.
    classe_dipendenti = models.CharField(max_length=20, blank=True, default="")
    classe_fatturato = models.CharField(max_length=20, blank=True, default="")
    fonte = models.CharField(max_length=120, blank=True, default="")
    importato_il = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["soggetto", "periodo"], name="dati_per_periodo_unici"),
        ]

    def __str__(self):
        return f"{self.soggetto} - {self.periodo}"
