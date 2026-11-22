"""
Nell'amministrazione c'è solo il catalogo delle entità, che gestisce il Configuratore.
Testi ed entità estratte NON vanno registrati qui: seguono la visibilità del file
da cui vengono (DECISIONI.md, n. 27) e l'amministrazione la aggirerebbe.
"""
from django.contrib import admin

from .models import VoceCatalogo


@admin.register(VoceCatalogo)
class VoceCatalogoAdmin(admin.ModelAdmin):
    list_display = ("codice", "descrizione", "tipo_valore", "ha_periodo", "multipla", "cambia_nel_tempo", "valida_al")
    search_fields = ("codice", "descrizione", "sinonimi")
    ordering = ("ordine", "codice")
