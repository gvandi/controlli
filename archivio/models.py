"""
ARCHIVIO: faldoni e fascicoli (passo 3).

    FALDONE            raccoglitore di primo livello. Sono righe di tabella, non
                       codice: aggiungerne uno (per esempio le sanzioni) non
                       richiede di cambiare la struttura.
    FASCICOLO          sta in un faldone. A seconda del faldone è un caricamento,
                       un'azienda oppure un'indagine.

    Caricamenti        un fascicolo per ogni caricamento di file: Caricamento (i
                       metadati dichiarati), FileCaricato, SoggettoDichiarato
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

# Stati di un fascicolo di caricamento
BOZZA = "bozza"            # l'ispettore sta caricando e completando i metadati
CONFERMATO = "confermato"  # consegnato all'elaborazione
ANNULLATO = "annullato"    # ritirato dopo la conferma: resta la traccia

# Stati di un file (DECISIONI.md, n. 66)
FILE_BOZZA = "bozza"
FILE_RICEVUTO = "ricevuto"
FILE_IN_ELABORAZIONE = "in elaborazione"
FILE_ELABORATO = "elaborato"
FILE_DA_RIVEDERE = "da rivedere"
FILE_ERRORE = "errore"
FILE_ANNULLATO = "annullato"

# Natura del contenuto di un file: dice a quale importazione è destinato
NATURE = (
    ("documenti", "Documenti (fatture, DDT, verbali...)"),
    ("transazioni", "Estratto di transazioni"),
    ("dati_economici", "Dati economici"),
    ("altro", "Altro"),
)

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

    class Meta:
        verbose_name = "faldone"
        verbose_name_plural = "faldoni"

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
        verbose_name = "fascicolo"
        verbose_name_plural = "fascicoli"
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
        verbose_name = "assegnazione"
        verbose_name_plural = "assegnazioni"
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
        verbose_name = "soggetto in indagine"
        verbose_name_plural = "soggetti in indagine"
        constraints = [
            models.UniqueConstraint(fields=["fascicolo", "soggetto"], name="soggetto_in_indagine_unico"),
        ]


# =====================================================================
# CARICAMENTO DEI FILE (parte 2; DECISIONI.md, n. 64-68)
# =====================================================================
class Caricamento(models.Model):
    """Metadati dichiarati dall'ispettore per un fascicolo del faldone Caricamenti.

    Valgono per tutti i file del fascicolo che non ne dichiarano di propri.
    """

    fascicolo = models.OneToOneField(
        Fascicolo, on_delete=models.CASCADE, primary_key=True, related_name="caricamento"
    )
    provenienza = models.CharField(max_length=200, blank=True, default="")
    tipo_documento = models.ForeignKey(
        "decodifiche.TipoDocumento", null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )
    natura = models.CharField(max_length=20, blank=True, default="")
    periodo_dal = models.DateField(null=True, blank=True)
    periodo_al = models.DateField(null=True, blank=True)
    note = models.TextField(blank=True, default="")

    class Meta:
        verbose_name = "caricamento"
        verbose_name_plural = "caricamenti"


class FileCaricato(models.Model):
    """Un file di un caricamento.

    Il contenuto sta nel deposito (deposito.py) sotto un nome ricavato
    dall'impronta e non si sposta mai. Qui c'è il percorso con cui il file è
    arrivato: due file omonimi in sottocartelle diverse sono due righe distinte.
    I campi dei metadati, se vuoti, ereditano quelli del caricamento.
    """

    fascicolo = models.ForeignKey(Fascicolo, on_delete=models.CASCADE, related_name="file")
    percorso_originale = models.CharField(max_length=500)
    impronta = models.CharField(max_length=64, db_index=True)
    dimensione = models.BigIntegerField()
    tipo_mime = models.CharField(max_length=100, blank=True, default="")
    stato = models.CharField(max_length=20, default="bozza")
    priorita = models.SmallIntegerField(default=0)
    tentativi = models.PositiveSmallIntegerField(default=0)
    ultimo_errore = models.TextField(blank=True, default="")
    caricato_da = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    caricato_il = models.DateTimeField(auto_now_add=True)
    # Metadati propri del file: vuoto = eredita dal caricamento
    provenienza = models.CharField(max_length=200, blank=True, default="")
    tipo_documento = models.ForeignKey(
        "decodifiche.TipoDocumento", null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )
    natura = models.CharField(max_length=20, blank=True, default="")
    periodo_dal = models.DateField(null=True, blank=True)
    periodo_al = models.DateField(null=True, blank=True)

    class Meta:
        verbose_name = "file caricato"
        verbose_name_plural = "file caricati"
        constraints = [
            models.UniqueConstraint(fields=["fascicolo", "percorso_originale"], name="file_unico_per_percorso"),
        ]
        permissions = [
            ("cancella_definitivamente", "Può cancellare definitivamente un file e i dati che ne derivano"),
        ]

    def __str__(self):
        return self.percorso_originale


class SoggettoDichiarato(models.Model):
    """Un identificativo (di norma un COE) indicato dall'ispettore.

    Sta su un fascicolo di caricamento oppure su un singolo file (uno dei due).
    Il primo è il soggetto principale, gli altri sono collegati. Un file che ne
    dichiara di propri non eredita quelli del caricamento.
    """

    fascicolo = models.ForeignKey(
        Fascicolo, null=True, blank=True, on_delete=models.CASCADE, related_name="soggetti_dichiarati"
    )
    file = models.ForeignKey(
        FileCaricato, null=True, blank=True, on_delete=models.CASCADE, related_name="soggetti_dichiarati"
    )
    tipo = models.ForeignKey("decodifiche.TipoIdentificativo", on_delete=models.PROTECT, related_name="+")
    valore_originale = models.CharField(max_length=60)
    valore_normalizzato = models.CharField(max_length=60)
    principale = models.BooleanField(default=False)
    soggetto = models.ForeignKey("soggetti.Soggetto", on_delete=models.PROTECT, related_name="+")

    class Meta:
        verbose_name = "soggetto dichiarato"
        verbose_name_plural = "soggetti dichiarati"

    def __str__(self):
        return f"{self.tipo.codice} {self.valore_normalizzato}"


class Evento(models.Model):
    """Registro: chi ha fatto cosa su un caricamento."""

    fascicolo = models.ForeignKey(
        Fascicolo, null=True, blank=True, on_delete=models.SET_NULL, related_name="eventi"
    )
    utente = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    quando = models.DateTimeField(auto_now_add=True)
    azione = models.CharField(max_length=30)
    dettaglio = models.CharField(max_length=500, blank=True, default="")

    class Meta:
        verbose_name = "evento del registro"
        verbose_name_plural = "eventi del registro"


class CollegamentoFile(models.Model):
    """Un file collegato a un fascicolo diverso da quello in cui è stato caricato.

    Il file resta dov'è (nel suo fascicolo di caricamento e nel deposito): qui si
    scrive solo che riguarda anche un'azienda. Chi consulta il fascicolo
    dell'azienda vede il file solo se può vedere il caricamento da cui viene.
    """

    file = models.ForeignKey(FileCaricato, on_delete=models.CASCADE, related_name="collegamenti")
    fascicolo = models.ForeignKey(Fascicolo, on_delete=models.CASCADE, related_name="file_collegati")
    # "dichiarato" dall'ispettore nei campi COE, oppure "estratto" dal contenuto del file
    origine = models.CharField(max_length=20, blank=True, default="")
    collegato_il = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "collegamento di un file"
        verbose_name_plural = "collegamenti dei file"
        constraints = [
            models.UniqueConstraint(fields=["file", "fascicolo"], name="collegamento_unico"),
        ]
