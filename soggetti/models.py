"""
ANAGRAFICA UNICA DEI SOGGETTI (passo 2, versione minima).

Aziende analizzate e controparti stanno nello stesso archivio (DECISIONI.md, n. 13).
L'identificativo fiscale NON è la chiave del soggetto (n. 14): la chiave è interna,
e ogni soggetto ha una o più righe di identificativi, ciascuna con il suo tipo
(COE, partita IVA...). Due scritture dello stesso identificativo ("SM 12345" e
"12345") coincidono perché si confrontano dopo la normalizzazione.

Qui non c'è nessuna informazione su indagini o controlli (n. 17).
"""
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
