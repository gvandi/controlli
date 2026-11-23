"""
ELABORAZIONE DEI FILE: dal file ricevuto alle entità che descrivono un soggetto.

    VoceCatalogo      le entità SIGNIFICATIVE: ciò che si intende estrarre
                      (COE, amministratore, soci, ricavi dell'anno...). È una
                      tabella: le voci le gestisce il Configuratore.
    Elaborazione      una lettura di un file: con quale motore e modello, quando,
                      con quale esito. Un file si elabora una volta sola.
    TestoPagina       il testo di ogni pagina, salvato a parte: serve alla ricerca
                      e a verificare i valori estratti.
    EntitaEstratta    un valore trovato in un file, sempre con il file e la pagina
                      di provenienza e con la citazione dal testo.

SIGNIFICATIVA O NO. Un'entità collegata a una voce del catalogo è significativa.
Quelle che il modello trova e che non corrispondono a nessuna voce si raccolgono
lo stesso, con voce vuota: restano consultabili e si possono promuovere in seguito
senza rileggere il file (coda.promuovi).

COSA ENTRA NEL CALCOLO. Solo le entità di EntitaEstratta.objects.utilizzabili():
significative, verificate nel testo, attribuite a un soggetto, non in attesa di
revisione e non ritirate. Un file caricato che non c'entra nulla attraversa tutto
il percorso e non produce nessuna entità utilizzabile.

LA DESCRIZIONE DI UN SOGGETTO CRESCE NEL TEMPO. Le entità arrivano da file diversi
in giorni diversi: a una certa data la descrizione è parziale. Ogni entità porta la
data di estrazione; le voci non ancora note sono "mancanti", non zero.
"""
from django.db import models

# Tipi di valore di una voce del catalogo
TIPI_VALORE = ("testo", "identificativo", "data", "importo", "numero", "luogo")

# Da dove viene un'entità
DA_REGOLA = "regola"    # letta nel testo da un'espressione fissa
DA_MODELLO = "modello"  # proposta dal modello linguistico

# Da dove viene il testo di una pagina
TESTO_DIRETTO = "diretto"  # il file era già testo
TESTO_OCR = "ocr"          # trascritto da un'immagine

# Esiti di un'elaborazione
ESITO_OK = "ok"
ESITO_DA_RIVEDERE = "da rivedere"
ESITO_ERRORE = "errore"
# Sole regole, in attesa del modello: il file resta da elaborare e verrà completato
ESITO_PARZIALE = "parziale"


class VoceCatalogo(models.Model):
    codice = models.CharField(max_length=30, unique=True)
    descrizione = models.CharField(max_length=200)
    tipo_valore = models.CharField(max_length=20, default="testo")
    # Il valore si riferisce a un periodo (il bilancio di un anno)
    ha_periodo = models.BooleanField(default=False)
    # Un soggetto può averne più di una (i soci)
    multipla = models.BooleanField(default=False)
    # Il valore cambia nel tempo (l'amministratore): vale il più recente, gli altri sono storia.
    # Se non cambia, due valori diversi per lo stesso soggetto e periodo vanno rivisti.
    cambia_nel_tempo = models.BooleanField(default=False)
    # Altri nomi con cui il modello può chiamare questa voce, uno per riga
    sinonimi = models.TextField(blank=True, default="")
    ordine = models.PositiveSmallIntegerField(default=0)
    valida_dal = models.DateField(null=True, blank=True)
    valida_al = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"{self.codice} - {self.descrizione}"


class Elaborazione(models.Model):
    file = models.ForeignKey("archivio.FileCaricato", on_delete=models.CASCADE, related_name="elaborazioni")
    iniziata_il = models.DateTimeField(auto_now_add=True)
    finita_il = models.DateTimeField(null=True, blank=True)
    esito = models.CharField(max_length=20, blank=True, default="")
    natura = models.CharField(max_length=20, blank=True, default="")
    # Con cosa è stata fatta: i risultati sono confrontabili solo a parità di questi tre
    motore = models.CharField(max_length=60, blank=True, default="")
    modello = models.CharField(max_length=120, blank=True, default="")
    versione_prompt = models.CharField(max_length=20, blank=True, default="")
    pagine = models.PositiveIntegerField(default=0)
    errore = models.TextField(blank=True, default="")


class TestoPagina(models.Model):
    elaborazione = models.ForeignKey(Elaborazione, on_delete=models.CASCADE, related_name="testi")
    pagina = models.PositiveIntegerField()
    testo = models.TextField(blank=True, default="")
    origine = models.CharField(max_length=20, blank=True, default="")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["elaborazione", "pagina"], name="testo_unico_per_pagina"),
        ]


class EntitaQuerySet(models.QuerySet):
    def utilizzabili(self):
        """Le sole entità che possono descrivere un soggetto ed entrare nel calcolo."""
        return self.filter(
            voce__isnull=False, verificata=True, soggetto__isnull=False, da_rivedere=False, ritirata=False
        )

    def fuori_catalogo(self):
        """Raccolte ma non significative: nessuna voce del catalogo le riconosce."""
        return self.filter(voce__isnull=True, ritirata=False)


class EntitaEstratta(models.Model):
    elaborazione = models.ForeignKey(Elaborazione, on_delete=models.CASCADE, related_name="entita")
    # Il file da cui è stata presa: ripetuto qui perché è la domanda più frequente
    file = models.ForeignKey("archivio.FileCaricato", on_delete=models.CASCADE, related_name="entita")
    # Vuota = non significativa (fuori catalogo)
    voce = models.ForeignKey(VoceCatalogo, null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    # L'etichetta così come è stata prodotta dalla regola o dal modello
    etichetta = models.CharField(max_length=120)
    valore = models.CharField(max_length=500)
    valore_normalizzato = models.CharField(max_length=500, blank=True, default="")
    pagina = models.PositiveIntegerField(null=True, blank=True)
    citazione = models.TextField(blank=True, default="")
    # L'evento a cui l'entità si riferisce: è un contesto, non un oggetto a sé
    evento = models.CharField(max_length=200, blank=True, default="")
    periodo = models.CharField(max_length=20, blank=True, default="")
    fonte = models.CharField(max_length=20, blank=True, default="")
    # Il valore si ritrova nel testo della pagina (DECISIONI.md, n. 25)
    verificata = models.BooleanField(default=False)
    soggetto = models.ForeignKey(
        "soggetti.Soggetto", null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )
    da_rivedere = models.BooleanField(default=False)
    motivo_revisione = models.CharField(max_length=200, blank=True, default="")
    # Ritirata: il caricamento è stato annullato, oppure un revisore l'ha scartata
    ritirata = models.BooleanField(default=False)
    estratta_il = models.DateTimeField(auto_now_add=True)

    objects = EntitaQuerySet.as_manager()

    class Meta:
        indexes = [models.Index(fields=["soggetto", "voce"], name="entita_soggetto_voce")]

    @property
    def significativa(self):
        return self.voce_id is not None
