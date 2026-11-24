"""
LAVORI (DECISIONI.md, n. 94): le elaborazioni e i calcoli che l'amministratore lancia
dall'interfaccia.

Elaborare i file, calcolare gli indici o addestrare la GNN dura da pochi secondi a
ore: non si può fare dentro la risposta a un clic. Il pulsante REGISTRA una richiesta
(un Lavoro in stato "richiesto"); un processo a parte, avviato insieme
all'applicativo, la prende e la esegue:

    python manage.py esegui_lavori        (vedi lavori/servizi.py e avvia.sh)

    richiesto  -->  in corso  -->  finito
                              -->  fallito   (con il motivo nell'esito)

Di ogni lavoro resta chi l'ha chiesto, quando, quanto è durato e l'esito. L'esito
riporta solo conteggi: chi lancia un calcolo non per questo vede i dati delle aziende.
Per ogni tipo c'è al più un lavoro richiesto o in corso: un secondo clic non ne avvia un altro.

Esecutore è il "sono vivo" del processo che esegue: la pagina avvisa se nessuno
sta eseguendo, perché in quel caso i lavori resterebbero richiesti per sempre.
"""
from django.conf import settings
from django.db import models

RICHIESTO, IN_CORSO, FINITO, FALLITO = "richiesto", "in corso", "finito", "fallito"
APERTI = (RICHIESTO, IN_CORSO)


class Lavoro(models.Model):
    tipo = models.CharField(max_length=40)
    stato = models.CharField(max_length=20, default=RICHIESTO)
    richiesto_da = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    richiesto_il = models.DateTimeField(auto_now_add=True)
    iniziato_il = models.DateTimeField(null=True, blank=True)
    finito_il = models.DateTimeField(null=True, blank=True)
    parametri = models.JSONField(default=dict, blank=True)
    # Per l'importazione dell'anagrafica: il contenuto del file CSV, tolto a lavoro finito
    ingresso = models.TextField(blank=True, default="")
    nome_ingresso = models.CharField(max_length=255, blank=True, default="")
    esito = models.TextField(blank=True, default="")

    class Meta:
        verbose_name = "lavoro"
        ordering = ["-richiesto_il", "-pk"]
        verbose_name_plural = "lavori"
        permissions = [("lancia_lavori", "Può lanciare elaborazioni e calcoli")]

    def __str__(self):
        return f"{self.tipo} n. {self.pk} ({self.stato})"

    @property
    def durata(self):
        return self.finito_il - self.iniziato_il if self.iniziato_il and self.finito_il else None


class Esecutore(models.Model):
    """Un processo esegui_lavori in funzione: aggiorna ultimo_segnale a ogni giro."""

    nome = models.CharField(max_length=80, unique=True)
    tipi = models.CharField(max_length=255, blank=True, default="")
    ultimo_segnale = models.DateTimeField()

    class Meta:
        verbose_name = "esecutore"
        verbose_name_plural = "esecutori"

    def __str__(self):
        return self.nome
