from django.contrib import admin

from . import models


class IdentificativoInline(admin.TabularInline):
    model = models.IdentificativoSoggetto
    extra = 0


@admin.register(models.Soggetto)
class SoggettoAdmin(admin.ModelAdmin):
    list_display = ("id", "denominazione", "provvisorio", "creato_il")
    list_filter = ("provvisorio",)
    search_fields = ("denominazione", "identificativi__valore_normalizzato")
    inlines = [IdentificativoInline]


@admin.register(models.DatiPerPeriodo)
class DatiPerPeriodoAdmin(admin.ModelAdmin):
    list_display = ("soggetto", "periodo", "codice_attivita", "dipendenti", "classe_dipendenti", "fatturato", "classe_fatturato", "fonte", "importato_il")
    list_filter = ("periodo",)
    search_fields = ("soggetto__denominazione", "soggetto__identificativi__valore_normalizzato", "codice_attivita")
