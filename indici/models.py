"""
INDICI DI RISCHIO A REGOLE (DECISIONI.md, n. 86-87).

Una regola dice: "un'azienda con queste caratteristiche è a rischio di questo tipo
di irregolarità, con questo peso". Le caratteristiche sono quelle dell'anagrafica
per periodo (soggetti.DatiPerPeriodo) lette attraverso le classi statistiche delle
decodifiche: attività economica, classe di dipendenti, classe di fatturato.

    Esempio: nessun dipendente (D0), fatturato da 100.000 euro in su (F1...F7),
             commercio (attività che cominciano per 46.1 o 47)
             -> falsa_fatturazione, peso 0,60

Le regole stanno in questa tabella e le gestisce il Configuratore: non sono nel codice.
L'indice che ne risulta è un calcolo a sé, distinto dal punteggio della GNN: una
regola è un indicatore dichiarato da una persona, non qualcosa che il modello ha
imparato dalle irregolarità accertate.
"""
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class RegolaDiRischio(models.Model):
    codice = models.CharField(max_length=40, unique=True)
    descrizione = models.CharField(max_length=255)
    # Uno dei tipi di grafo.contratto.TIPI_IRREGOLARITA
    tipo = models.CharField(max_length=60)
    # Quanto pesa, da 0 a 1: più regole dello stesso tipo si combinano, senza superare 1
    peso = models.DecimalField(
        max_digits=3, decimal_places=2, validators=[MinValueValidator(0), MaxValueValidator(1)]
    )
    # Condizioni: devono valere TUTTE quelle compilate; una lasciata vuota non conta.
    # Più valori si separano con la virgola; ne basta uno.
    prefissi_attivita = models.CharField(
        max_length=255, blank=True, default="",
        help_text="Inizio del codice dell'attività economica. Esempio: 46.1, 47",
    )
    classi_dipendenti = models.CharField(
        max_length=255, blank=True, default="", help_text="Codici delle classi di dipendenti. Esempio: D0",
    )
    classi_fatturato = models.CharField(
        max_length=255, blank=True, default="", help_text="Codici delle classi di fatturato. Esempio: F1, F2, F3",
    )
    attiva = models.BooleanField(default=True)
    note = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["codice"]
        verbose_name = "regola di rischio"
        verbose_name_plural = "regole di rischio"

    def __str__(self):
        return f"{self.codice} ({self.tipo}, peso {self.peso})"
