from django.contrib import admin

from . import models


class DecodificaAdmin(admin.ModelAdmin):
    list_display = ("codice", "descrizione", "ordine", "valida_dal", "valida_al")
    search_fields = ("codice", "descrizione")
    ordering = ("ordine", "codice")


class ClasseIntervalloAdmin(DecodificaAdmin):
    list_display = ("codice", "descrizione", "minimo", "massimo", "valida_dal", "valida_al")
    ordering = ("minimo",)


@admin.register(models.AttivitaEconomica)
class AttivitaEconomicaAdmin(admin.ModelAdmin):
    list_display = (
        "codice",
        "descrizione",
        "livello",
        "padre",
        "versione_classificazione",
        "contanti_per_natura",
        "stagionale_per_natura",
    )
    list_filter = ("versione_classificazione", "livello", "contanti_per_natura", "stagionale_per_natura")
    search_fields = ("codice", "descrizione")
    autocomplete_fields = ("padre",)
    ordering = ("versione_classificazione", "codice")


admin.site.register(models.ClasseDipendenti, ClasseIntervalloAdmin)
admin.site.register(models.ClasseFatturato, ClasseIntervalloAdmin)
admin.site.register(models.FormaGiuridica, DecodificaAdmin)
admin.site.register(models.PosizioneGruppo, DecodificaAdmin)
admin.site.register(models.Clientela, DecodificaAdmin)
admin.site.register(models.Stagionalita, DecodificaAdmin)
admin.site.register(models.UsoContante, DecodificaAdmin)
admin.site.register(models.OperativitaEstero, DecodificaAdmin)
