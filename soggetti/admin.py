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
