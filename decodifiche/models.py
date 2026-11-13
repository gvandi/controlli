"""Tabelle di decodifica usate per descrivere l'attività economica di un'azienda.

Tutte condividono gli stessi campi di base: codice, descrizione, ordine e
intervallo di validità. Un valore non più in uso si chiude con "valida al" e non
si cancella, così la storia resta leggibile (DECISIONI.md, n. 5).
"""
import re

from django.db import models
from django.db.models import Q


class Decodifica(models.Model):
    """Campi comuni a tutte le tabelle di decodifica."""

    codice = models.CharField(max_length=20)
    descrizione = models.CharField(max_length=255)
    ordine = models.PositiveSmallIntegerField(default=0, help_text="Ordine di visualizzazione")
    valida_dal = models.DateField(null=True, blank=True, help_text="Vuoto: valida da sempre")
    valida_al = models.DateField(null=True, blank=True, help_text="Vuoto: ancora valida")

    class Meta:
        abstract = True
        ordering = ["ordine", "codice"]

    def __str__(self):
        return f"{self.codice} - {self.descrizione}"

    def valida_il(self, data):
        """Vero se la voce è valida nel giorno indicato (estremi inclusi)."""
        if self.valida_dal and data < self.valida_dal:
            return False
        if self.valida_al and data > self.valida_al:
            return False
        return True

    @classmethod
    def valide_il(cls, data):
        """Voci valide nel giorno indicato."""
        return cls.objects.filter(
            Q(valida_dal__isnull=True) | Q(valida_dal__lte=data),
            Q(valida_al__isnull=True) | Q(valida_al__gte=data),
        )


class DecodificaSemplice(Decodifica):
    """Tabella di decodifica in cui il codice è unico."""

    class Meta(Decodifica.Meta):
        abstract = True
        constraints = [
            models.UniqueConstraint(fields=["codice"], name="%(app_label)s_%(class)s_codice_unico"),
        ]


class ClasseIntervallo(DecodificaSemplice):
    """Classe definita da un intervallo: minimo incluso, massimo escluso.

    La classe di un'azienda si calcola dal valore, non si inserisce a mano
    (DECISIONI.md, n. 10).
    """

    minimo = models.DecimalField(max_digits=16, decimal_places=2, help_text="Incluso")
    massimo = models.DecimalField(
        max_digits=16, decimal_places=2, null=True, blank=True, help_text="Escluso. Vuoto: nessun limite"
    )

    class Meta(DecodificaSemplice.Meta):
        abstract = True

    def contiene(self, valore):
        return valore >= self.minimo and (self.massimo is None or valore < self.massimo)

    @classmethod
    def per_valore(cls, valore, data):
        """Classe valida nel giorno indicato che contiene il valore, oppure None."""
        for classe in cls.valide_il(data).order_by("minimo"):
            if classe.contiene(valore):
                return classe
        return None


class AttivitaEconomica(Decodifica):
    """Classificazione delle attività economiche (NACE o variante nazionale, es. ATECO)."""

    class Livello(models.TextChoices):
        SEZIONE = "sezione", "Sezione"
        DIVISIONE = "divisione", "Divisione (2 cifre)"
        GRUPPO = "gruppo", "Gruppo (3 cifre)"
        CLASSE = "classe", "Classe (4 cifre)"
        DETTAGLIO = "dettaglio", "Dettaglio nazionale"

    versione_classificazione = models.CharField(
        max_length=30, help_text="Esempio: ATECO 2025, NACE Rev. 2.1"
    )
    livello = models.CharField(max_length=10, choices=Livello.choices)
    padre = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="figli",
        help_text="Voce di livello superiore: serve per allargare il gruppo di confronto",
    )
    contanti_per_natura = models.BooleanField(
        default=False, help_text="Valore predefinito del settore, modificabile sulla singola azienda"
    )
    stagionale_per_natura = models.BooleanField(
        default=False, help_text="Valore predefinito del settore, modificabile sulla singola azienda"
    )

    class Meta(Decodifica.Meta):
        verbose_name = "attività economica"
        verbose_name_plural = "attività economiche"
        ordering = ["versione_classificazione", "codice"]
        constraints = [
            models.UniqueConstraint(
                fields=["versione_classificazione", "codice"],
                name="decodifiche_attivita_versione_codice_unico",
            ),
        ]

    def antenati(self):
        """Voci di livello superiore, dalla più vicina alla più lontana."""
        voce = self.padre
        while voce is not None:
            yield voce
            voce = voce.padre


class ClasseDipendenti(ClasseIntervallo):
    class Meta(ClasseIntervallo.Meta):
        verbose_name = "classe di dipendenti"
        verbose_name_plural = "classi di dipendenti"


class ClasseFatturato(ClasseIntervallo):
    class Meta(ClasseIntervallo.Meta):
        verbose_name = "classe di fatturato"
        verbose_name_plural = "classi di fatturato"


class FormaGiuridica(DecodificaSemplice):
    class Meta(DecodificaSemplice.Meta):
        verbose_name = "forma giuridica"
        verbose_name_plural = "forme giuridiche"


class PosizioneGruppo(DecodificaSemplice):
    """Posizione dell'azienda in un gruppo societario. Distinta dalla forma giuridica."""

    class Meta(DecodificaSemplice.Meta):
        verbose_name = "posizione nel gruppo"
        verbose_name_plural = "posizioni nel gruppo"


# Modello di business: quattro attributi indipendenti (DECISIONI.md, n. 7).


class Clientela(DecodificaSemplice):
    class Meta(DecodificaSemplice.Meta):
        verbose_name = "clientela"
        verbose_name_plural = "modello di business: clientela"


class Stagionalita(DecodificaSemplice):
    class Meta(DecodificaSemplice.Meta):
        verbose_name = "stagionalità"
        verbose_name_plural = "modello di business: stagionalità"


class UsoContante(DecodificaSemplice):
    class Meta(DecodificaSemplice.Meta):
        verbose_name = "uso del contante"
        verbose_name_plural = "modello di business: uso del contante"


class OperativitaEstero(DecodificaSemplice):
    class Meta(DecodificaSemplice.Meta):
        verbose_name = "operatività con l'estero"
        verbose_name_plural = "modello di business: operatività con l'estero"


# Soggetti e documenti (DECISIONI.md, n. 13-16).


class TipoIdentificativo(DecodificaSemplice):
    """Tipo di identificativo fiscale di un soggetto.

    Un soggetto può avere più identificativi, di tipo e paese diversi: COE per
    San Marino, partita IVA per l'Italia, altri per gli altri paesi. Il valore
    si confronta dopo la normalizzazione, così "SM 12345" e "12345" coincidono.
    """

    paese = models.CharField(
        max_length=2, blank=True, help_text="Codice ISO a due lettere. Vuoto: valido per più paesi"
    )
    prefissi = models.CharField(
        max_length=100,
        blank=True,
        help_text="Prefissi da togliere nella normalizzazione, separati da virgola. Esempio: COE,SM",
    )
    espressione_controllo = models.CharField(
        max_length=200,
        blank=True,
        help_text="Espressione regolare applicata al valore normalizzato. Vuoto: nessun controllo",
    )

    class Meta(DecodificaSemplice.Meta):
        verbose_name = "tipo di identificativo"
        verbose_name_plural = "tipi di identificativo fiscale"

    def normalizza(self, valore):
        """Toglie spazi, punteggiatura e prefissi noti; porta in maiuscolo."""
        testo = re.sub(r"[^0-9A-Za-z]", "", valore or "").upper()
        prefissi = sorted(
            (p.strip().upper() for p in self.prefissi.split(",") if p.strip()), key=len, reverse=True
        )
        for prefisso in prefissi:
            if testo.startswith(prefisso) and len(testo) > len(prefisso):
                testo = testo[len(prefisso):]
                break
        return testo

    def accetta(self, valore):
        """Vero se il valore, una volta normalizzato, rispetta il formato del tipo."""
        normalizzato = self.normalizza(valore)
        if not normalizzato:
            return False
        if not self.espressione_controllo:
            return True
        return re.fullmatch(self.espressione_controllo, normalizzato) is not None


class TipoDocumento(DecodificaSemplice):
    """Tipo di documento: fattura, DDT, nota di credito, contratto e simili."""

    class Meta(DecodificaSemplice.Meta):
        verbose_name = "tipo di documento"
        verbose_name_plural = "tipi di documento"


class RuoloNelDocumento(DecodificaSemplice):
    """Ruolo con cui un soggetto compare in un documento: emittente, destinatario, vettore."""

    class Meta(DecodificaSemplice.Meta):
        verbose_name = "ruolo nel documento"
        verbose_name_plural = "ruoli nel documento"
