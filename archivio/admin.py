"""
Nell'amministrazione ci sono solo i faldoni. Fascicoli, assegnazioni e soggetti
delle indagini NON vanno registrati qui: l'amministrazione li mostrerebbe a chi
gestisce gli utenti, aggirando la regola di visibilità (DECISIONI.md, n. 18).
"""
from django.contrib import admin

from .models import Faldone


@admin.register(Faldone)
class FaldoneAdmin(admin.ModelAdmin):
    list_display = ("codice", "nome", "ordine", "riservato", "creato_dal_sistema", "legato_a")
    ordering = ("ordine",)
    readonly_fields = ("codice", "riservato", "creato_dal_sistema", "legato_a")

    def has_add_permission(self, request):
        return False  # un faldone nuovo ha regole proprie: nasce con una migrazione

    def has_delete_permission(self, request, obj=None):
        return False
