"""
ARCHIVIO: faldoni e fascicoli (passo 3).

    FALDONE            raccoglitore di primo livello. Sono righe di tabella, non
                       codice: aggiungerne uno (per esempio le sanzioni) non
                       richiede di cambiare la struttura.
    FASCICOLO          sta in un faldone. A seconda del faldone è un caricamento,
                       un'azienda oppure un'indagine.

    Caricamenti        un fascicolo per ogni caricamento di file (parte 2)
    Aziende            un fascicolo per ogni azienda acquisita; lo crea il sistema
    Indagini           un fascicolo per ogni indagine; riservato alle persone assegnate

VISIBILITÀ (DECISIONI.md, n. 17-19). Un fascicolo si vede se:
  - sta in un faldone non riservato e non è legato a un'indagine, oppure
  - l'utente è assegnato al fascicolo, oppure
  - il fascicolo è legato a un'indagine a cui l'utente è assegnato.
Vale per tutti, superutente compreso: chi amministra gli utenti non vede per
questo le indagini. Ogni elenco, conteggio e ricerca parte da
Fascicolo.objects.visibili_a(utente): è l'unico punto in cui la regola è scritta.

Il legame fra un'indagine e i soggetti che riguarda (SoggettoInIndagine) si
raggiunge solo dal fascicolo d'indagine: dall'azienda non si risale alle indagini.
"""
from django.conf import settings
from django.db import models
from django.db.models import Q

# Codici dei faldoni creati dalla migrazione iniziale
CARICAMENTI = "CARICAMENTI"
AZIENDE = "AZIENDE"
INDAGINI = "INDAGINI"


class Faldone(models.Model):
    codice = models.CharField(max_length=20, unique=True)
    nome = models.CharField(max_length=80)
    ordine = models.PositiveSmallIntegerField(default=0)
    # Riservato: i fascicoli li vede solo chi vi è assegnato
    riservato = models.BooleanField(default=False)
    # I fascicoli li crea il sistema (non una persona)
    creato_dal_sistema = models.BooleanField(default=False)
    # A cosa è legato un fascicolo di questo faldone: caricamento, soggetto, indagine
    legato_a = models.CharField(max_length=20, blank=True, default="")

    def __str__(self):
        return self.nome


class FascicoloQuerySet(models.QuerySet):
    def visibili_a(self, utente):
        """I soli fascicoli che l'utente può sapere che esistono."""
        return self.filter(
            Q(faldone__riservato=False, riservato_a__isnull=True)
            | Q(assegnazioni__utente=utente)
            | Q(riservato_a__assegnazioni__utente=utente)
        ).distinct()


class Fascicolo(models.Model):
    faldone = models.ForeignKey(Faldone, on_delete=models.PROTECT, related_name="fascicoli")
    titolo = models.CharField(max_length=200)
    descrizione = models.TextField(blank=True, default="")
    stato = models.CharField(max_length=20, default="aperto")
    creato_da = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    creato_il = models.DateTimeField(auto_now_add=True)
    # Faldone Aziende: il soggetto a cui il fascicolo è intestato
    soggetto = models.ForeignKey(
        "soggetti.Soggetto", null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )
    # Fascicolo d'indagine a cui questo fascicolo è riservato (per i caricamenti, parte 2)
    riservato_a = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.PROTECT, related_name="riservati"
    )

    objects = FascicoloQuerySet.as_manager()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["faldone", "soggetto"], name="fascicolo_unico_per_soggetto"),
        ]
        permissions = [("apre_indagini", "Può aprire fascicoli d'indagine")]

    def __str__(self):
        return self.titolo


class Assegnazione(models.Model):
    """Una persona assegnata a un fascicolo d'indagine."""

    fascicolo = models.ForeignKey(Fascicolo, on_delete=models.CASCADE, related_name="assegnazioni")
    utente = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    assegnato_da = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    assegnato_il = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["fascicolo", "utente"], name="assegnazione_unica"),
        ]


class SoggettoInIndagine(models.Model):
    """Un soggetto che un'indagine riguarda. Si legge solo passando dal fascicolo d'indagine."""

    fascicolo = models.ForeignKey(Fascicolo, on_delete=models.CASCADE, related_name="soggetti_in_indagine")
    soggetto = models.ForeignKey("soggetti.Soggetto", on_delete=models.PROTECT, related_name="+")
    nota = models.CharField(max_length=255, blank=True, default="")
    aggiunto_da = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    aggiunto_il = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["fascicolo", "soggetto"], name="soggetto_in_indagine_unico"),
        ]
