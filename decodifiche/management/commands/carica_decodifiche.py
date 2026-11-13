from django.core.management.base import BaseCommand
from django.db import transaction

from decodifiche import dati_iniziali as dati
from decodifiche import models


class Command(BaseCommand):
    help = (
        "Carica i valori iniziali delle tabelle di decodifica. Si può rieseguire: "
        "crea le voci mancanti e non modifica quelle già presenti."
    )

    @transaction.atomic
    def handle(self, *args, **options):
        self._intervalli(models.ClasseDipendenti, dati.CLASSI_DIPENDENTI)
        self._intervalli(models.ClasseFatturato, dati.CLASSI_FATTURATO)
        self._semplici(models.FormaGiuridica, dati.FORME_GIURIDICHE)
        self._semplici(models.PosizioneGruppo, dati.POSIZIONI_GRUPPO)
        self._semplici(models.Clientela, dati.CLIENTELA)
        self._semplici(models.Stagionalita, dati.STAGIONALITA)
        self._semplici(models.UsoContante, dati.USO_CONTANTE)
        self._semplici(models.OperativitaEstero, dati.OPERATIVITA_ESTERO)
        self._semplici(models.TipoDocumento, dati.TIPI_DOCUMENTO)
        self._semplici(models.RuoloNelDocumento, dati.RUOLI_NEL_DOCUMENTO)
        self._tipi_identificativo()
        self._attivita()

    def _riepilogo(self, modello, create):
        self.stdout.write(f"{modello._meta.verbose_name_plural}: {create} voci create")

    def _semplici(self, modello, righe):
        create = 0
        for ordine, (codice, descrizione) in enumerate(righe, start=1):
            _, creata = modello.objects.get_or_create(
                codice=codice, defaults={"descrizione": descrizione, "ordine": ordine}
            )
            create += creata
        self._riepilogo(modello, create)

    def _intervalli(self, modello, righe):
        create = 0
        for ordine, (codice, descrizione, minimo, massimo) in enumerate(righe, start=1):
            _, creata = modello.objects.get_or_create(
                codice=codice,
                defaults={
                    "descrizione": descrizione,
                    "ordine": ordine,
                    "minimo": minimo,
                    "massimo": massimo,
                },
            )
            create += creata
        self._riepilogo(modello, create)

    def _tipi_identificativo(self):
        create = 0
        righe = enumerate(dati.TIPI_IDENTIFICATIVO, start=1)
        for ordine, (codice, descrizione, paese, prefissi, espressione) in righe:
            _, creata = models.TipoIdentificativo.objects.get_or_create(
                codice=codice,
                defaults={
                    "descrizione": descrizione,
                    "ordine": ordine,
                    "paese": paese,
                    "prefissi": prefissi,
                    "espressione_controllo": espressione,
                },
            )
            create += creata
        self._riepilogo(models.TipoIdentificativo, create)

    def _attivita(self):
        versione = dati.VERSIONE_ATTIVITA_ESEMPIO
        create = 0
        # L'elenco è ordinato dal livello più alto al più basso: il padre esiste già.
        for codice, descrizione, livello, codice_padre, contanti, stagionale in dati.ATTIVITA_ESEMPIO:
            padre = None
            if codice_padre:
                padre = models.AttivitaEconomica.objects.get(
                    versione_classificazione=versione, codice=codice_padre
                )
            _, creata = models.AttivitaEconomica.objects.get_or_create(
                versione_classificazione=versione,
                codice=codice,
                defaults={
                    "descrizione": descrizione,
                    "livello": livello,
                    "padre": padre,
                    "contanti_per_natura": contanti,
                    "stagionale_per_natura": stagionale,
                },
            )
            create += creata
        self._riepilogo(models.AttivitaEconomica, create)
