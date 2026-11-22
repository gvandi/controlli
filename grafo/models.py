"""Schema dell'app grafo: analisi di rete con GNN (prototipo su dati simulati).

Quattro gruppi di tabelle:

  SOGGETTI            Soggetto: chiave interna stabile (DECISIONI.md, n. 14)
  DATI IN INGRESSO    una fotografia per ogni VersioneDati: DatiSoggetto,
                      IrregolaritaAccertata, Relazione, Indicatore
  RISULTATI           uno per ogni Esecuzione (versione del calcolo + versione dei
                      dati): NodoSoggetto, PunteggioRischio, Spiegazione,
                      RichiestaSpiegazione
  SESSIONI (4.1-4.2)      Parametro (impostazioni dell'amministratore), TokenAccesso,
                      Sessione, Richiesta, MappaProdotta

Nulla viene cancellato quando arrivano dati nuovi o cambia il calcolo: si
aggiunge una fotografia o un'esecuzione. Le regole per modificare questo schema
sono in grafo/COMPATIBILITA.md: ogni modifica passa da una migrazione e aggiorna
la versione dello schema (InfoArchivio).

I nomi delle tabelle sono fissati con db_table perché interrogazione.py li usa
in SQL: rinominarne una è una modifica che TOGLIE (primo numero dello schema).
"""
from django.conf import settings
from django.db import models


class InfoArchivio(models.Model):
    """Coppie chiave/valore sull'archivio. 'versione_schema' la scrivono le migrazioni."""

    chiave = models.CharField(max_length=50, primary_key=True)
    valore = models.CharField(max_length=255)

    class Meta:
        db_table = "grafo_info"

    def __str__(self):
        return f"{self.chiave} = {self.valore}"


class Soggetto(models.Model):
    """Un'azienda, con chiave interna stabile nel tempo.

    Provvisorio: quando arriverà la gestione dei soggetti dell'applicativo questo
    modello andrà fuso con quello definitivo. 'riferimento' è l'aggancio alla
    fonte che ha fatto nascere il soggetto (nella simulazione: SIM-00012).
    """

    riferimento = models.CharField(max_length=80, unique=True)
    creato_il = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "grafo_soggetto"

    def __str__(self):
        return f"{self.pk} ({self.riferimento})"


class VersioneDati(models.Model):
    """Una fotografia congelata dei dati in ingresso (secondo livello della coppia)."""

    numero = models.PositiveIntegerField(unique=True)
    creata_il = models.DateTimeField(auto_now_add=True)
    descrizione = models.CharField(max_length=255, blank=True, default="")
    # Impronta dei dati: gli stessi dati non generano una seconda fotografia
    impronta = models.CharField(max_length=64, unique=True)

    class Meta:
        db_table = "grafo_versione_dati"

    def __str__(self):
        return f"dati n. {self.numero}"


class DatiSoggetto(models.Model):
    """Come si presenta un soggetto in una fotografia dei dati."""

    versione_dati = models.ForeignKey(VersioneDati, on_delete=models.CASCADE, related_name="+")
    soggetto = models.ForeignKey(Soggetto, on_delete=models.PROTECT, related_name="+")
    nome = models.CharField(max_length=255)
    nr_iscrizione = models.CharField(max_length=80, blank=True, default="")
    id_fiscale = models.CharField(max_length=80, blank=True, default="")
    # Vero se esiste un verbale ispettivo confermato: solo allora c'è un'etichetta
    ispezionata = models.BooleanField(default=False)

    class Meta:
        db_table = "grafo_dati_soggetto"
        constraints = [
            models.UniqueConstraint(
                fields=["versione_dati", "soggetto"], name="grafo_dati_soggetto_unico"
            ),
        ]


class IrregolaritaAccertata(models.Model):
    """Esito di un verbale ispettivo confermato: un tipo di irregolarità accertato."""

    versione_dati = models.ForeignKey(VersioneDati, on_delete=models.CASCADE, related_name="+")
    soggetto = models.ForeignKey(Soggetto, on_delete=models.PROTECT, related_name="+")
    tipo = models.CharField(max_length=60)

    class Meta:
        db_table = "grafo_irregolarita"
        constraints = [
            models.UniqueConstraint(
                fields=["versione_dati", "soggetto", "tipo"], name="grafo_irregolarita_unica"
            ),
        ]


class Relazione(models.Model):
    """Un documento commerciale (fattura, DDT) fra un venditore e un acquirente."""

    versione_dati = models.ForeignKey(VersioneDati, on_delete=models.CASCADE, related_name="+")
    venditore = models.ForeignKey(Soggetto, on_delete=models.PROTECT, related_name="+")
    acquirente = models.ForeignKey(Soggetto, on_delete=models.PROTECT, related_name="+")
    documento = models.CharField(max_length=80)
    data = models.DateField()
    importo = models.DecimalField(max_digits=14, decimal_places=2)

    class Meta:
        db_table = "grafo_relazione"
        indexes = [
            models.Index(fields=["versione_dati", "venditore"], name="grafo_rel_venditore"),
            models.Index(fields=["versione_dati", "acquirente"], name="grafo_rel_acquirente"),
        ]


class Indicatore(models.Model):
    """Descrizione di una posizione del vettore di features (da dizionario_descrizioni.json)."""

    versione_dati = models.ForeignKey(VersioneDati, on_delete=models.CASCADE, related_name="+")
    indice = models.PositiveIntegerField()
    descrizione = models.TextField()

    class Meta:
        db_table = "grafo_indicatore"
        constraints = [
            models.UniqueConstraint(
                fields=["versione_dati", "indice"], name="grafo_indicatore_unico"
            ),
        ]


class Esecuzione(models.Model):
    """Un calcolo dei punteggi: una versione del calcolo applicata a una fotografia dei dati.

    La coppia (versione_calcolo, versione_dati) è unica: ripetere il calcolo sulla
    stessa coppia sostituisce l'esecuzione precedente e i suoi risultati.
    """

    versione_calcolo = models.CharField(max_length=20)
    versione_dati = models.ForeignKey(VersioneDati, on_delete=models.PROTECT, related_name="+")
    versione_codice = models.CharField(max_length=20)  # rilascio che ha calcolato: solo provenienza
    calcolata_il = models.DateTimeField(auto_now_add=True)
    tassonomia = models.JSONField()  # tipi di irregolarità usati
    soglie = models.JSONField()  # soglia di decisione per tipo
    metriche = models.JSONField()  # metriche sul test set

    class Meta:
        db_table = "grafo_esecuzione"
        constraints = [
            models.UniqueConstraint(
                fields=["versione_calcolo", "versione_dati"], name="grafo_esecuzione_unica"
            ),
        ]

    def __str__(self):
        return f"calcolo {self.versione_calcolo}, {self.versione_dati}"


class NodoSoggetto(models.Model):
    """Posizione di un soggetto nel grafo di un'esecuzione (serve solo al calcolo)."""

    esecuzione = models.ForeignKey(Esecuzione, on_delete=models.CASCADE, related_name="+")
    indice_nodo = models.PositiveIntegerField()
    soggetto = models.ForeignKey(Soggetto, on_delete=models.PROTECT, related_name="+")

    class Meta:
        db_table = "grafo_nodo"
        constraints = [
            models.UniqueConstraint(fields=["esecuzione", "indice_nodo"], name="grafo_nodo_unico"),
            models.UniqueConstraint(fields=["esecuzione", "soggetto"], name="grafo_nodo_soggetto_unico"),
        ]


class PunteggioRischio(models.Model):
    """Punteggio assegnato dalla GNN a un soggetto per un tipo di irregolarità."""

    esecuzione = models.ForeignKey(Esecuzione, on_delete=models.CASCADE, related_name="+")
    soggetto = models.ForeignKey(Soggetto, on_delete=models.PROTECT, related_name="+")
    tipo = models.CharField(max_length=60)
    punteggio = models.FloatField()
    sopra_soglia = models.BooleanField()

    class Meta:
        db_table = "grafo_punteggio"
        constraints = [
            models.UniqueConstraint(
                fields=["esecuzione", "soggetto", "tipo"], name="grafo_punteggio_unico"
            ),
        ]


class Spiegazione(models.Model):
    """Output di GNNExplainer per (soggetto, tipo): documento JSON auto-descrittivo."""

    esecuzione = models.ForeignKey(Esecuzione, on_delete=models.CASCADE, related_name="+")
    soggetto = models.ForeignKey(Soggetto, on_delete=models.PROTECT, related_name="+")
    tipo = models.CharField(max_length=60)
    calcolata_il = models.DateTimeField(auto_now=True)
    dati = models.JSONField()  # forma: contratto.SCHEMA_SPIEGAZIONE, vedi COMPATIBILITA.md

    class Meta:
        db_table = "grafo_spiegazione"
        constraints = [
            models.UniqueConstraint(
                fields=["esecuzione", "soggetto", "tipo"], name="grafo_spiegazione_unica"
            ),
        ]


class RichiestaSpiegazione(models.Model):
    """Coda: spiegazioni chieste dalle interrogazioni e non ancora calcolate."""

    esecuzione = models.ForeignKey(Esecuzione, on_delete=models.CASCADE, related_name="+")
    soggetto = models.ForeignKey(Soggetto, on_delete=models.PROTECT, related_name="+")
    tipo = models.CharField(max_length=60)
    richiesta_il = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "grafo_richiesta_spiegazione"
        constraints = [
            models.UniqueConstraint(
                fields=["esecuzione", "soggetto", "tipo"], name="grafo_richiesta_unica"
            ),
        ]


# =====================================================================
# SESSIONI DELLA CHAT (schema 4.1)
# =====================================================================
class Parametro(models.Model):
    """Impostazione che l'amministratore modifica dal cruscotto.

    I nomi ammessi, i valori predefiniti e le descrizioni sono in
    contratto.PARAMETRI; le righe le crea la migrazione 0002.
    """

    nome = models.CharField(max_length=60, primary_key=True)
    valore = models.CharField(max_length=255, blank=True, default="")
    descrizione = models.TextField(blank=True, default="")
    modificato_il = models.DateTimeField(auto_now=True)
    modificato_da = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        db_table = "grafo_parametro"

    def __str__(self):
        return f"{self.nome} = {self.valore}"


class TokenAccesso(models.Model):
    """Token personale con cui la chat si presenta al servizio MCP.

    Nel database c'è solo l'impronta (SHA-256): il token in chiaro viene mostrato
    una volta sola a chi lo crea. Provvisorio: dalla versione 21 i token li
    rilascerà l'accesso OAuth.
    """

    utente = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    impronta = models.CharField(max_length=64, unique=True)
    etichetta = models.CharField(max_length=80, blank=True, default="")
    creato_il = models.DateTimeField(auto_now_add=True)
    ultimo_uso = models.DateTimeField(null=True, blank=True)
    revocato_il = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "grafo_token"

    def __str__(self):
        return f"token n. {self.pk} di {self.utente}"


class Sessione(models.Model):
    """Una sessione di lavoro in chat: il numero di sessione è la chiave (id).

    Nasce quando la chat si collega al servizio MCP e viene chiusa dopo il
    periodo di inattività scelto dall'amministratore.
    """

    utente = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    token = models.ForeignKey(TokenAccesso, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    # Identificativo della connessione assegnato alla chat (intestazione Mcp-Session-Id)
    id_connessione = models.CharField(max_length=120, blank=True, default="", db_index=True)
    iniziata_il = models.DateTimeField(auto_now_add=True)
    ultima_attivita = models.DateTimeField()
    chiusa_il = models.DateTimeField(null=True, blank=True)
    motivo_chiusura = models.CharField(max_length=20, blank=True, default="")
    client = models.CharField(max_length=200, blank=True, default="")
    indirizzo = models.GenericIPAddressField(null=True, blank=True)
    versione_codice = models.CharField(max_length=20, blank=True, default="")
    # 4.2: come è stato fatto l'accesso (contratto.ACCESSO_TOKEN / ACCESSO_OAUTH) e,
    # per OAuth, il nome con cui il programma della chat si è registrato
    accesso = models.CharField(max_length=10, blank=True, default="token")
    client_oauth = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        db_table = "grafo_sessione"
        permissions = [("usa_chat", "Può interrogare l'analisi di rete dalla chat")]

    def __str__(self):
        return f"sessione n. {self.pk}"


class Richiesta(models.Model):
    """Una chiamata a uno strumento fatta dalla chat per conto dell'ispettore."""

    sessione = models.ForeignKey(Sessione, on_delete=models.PROTECT, related_name="+")
    ricevuta_il = models.DateTimeField(auto_now_add=True)
    strumento = models.CharField(max_length=40)
    parametri = models.JSONField(default=dict)
    # Domanda dell'ispettore, se il modello della chat l'ha ricopiata (non garantito)
    domanda = models.TextField(blank=True, default="")
    esito = models.CharField(max_length=20, blank=True, default="")
    durata_ms = models.PositiveIntegerField(null=True, blank=True)
    # Coppia calcolo/dati con cui è stata data la risposta
    versione_calcolo = models.CharField(max_length=20, blank=True, default="")
    numero_dati = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        db_table = "grafo_richiesta"
        indexes = [models.Index(fields=["sessione", "ricevuta_il"], name="grafo_richiesta_sessione")]


class MappaProdotta(models.Model):
    """Una mappa investigativa scritta su file su richiesta di una sessione."""

    sessione = models.ForeignKey(Sessione, on_delete=models.PROTECT, related_name="+")
    richiesta = models.ForeignKey(Richiesta, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    soggetto = models.ForeignKey(Soggetto, on_delete=models.PROTECT, related_name="+")
    nome_file = models.CharField(max_length=255)
    prodotta_il = models.DateTimeField(auto_now=True)
    versione_calcolo = models.CharField(max_length=20, blank=True, default="")
    numero_dati = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        db_table = "grafo_mappa"
        constraints = [
            models.UniqueConstraint(fields=["sessione", "nome_file"], name="grafo_mappa_unica"),
        ]
