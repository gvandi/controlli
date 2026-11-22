"""Registro di sessioni, richieste e mappe nell'amministrazione: sola lettura.

I parametri si modificano dal cruscotto (/grafo/cruscotto/), che ne controlla i
valori; i token li crea ciascun utente dalla pagina "Collegamento alla chat".
"""
from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from . import models, sessioni


class SolaLettura(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(models.Sessione)
class SessioneAdmin(SolaLettura):
    list_display = ("id", "utente", "iniziata_il", "ultima_attivita", "chiusa_il", "motivo_chiusura", "client")
    list_filter = ("motivo_chiusura", "utente")
    ordering = ("-id",)


@admin.register(models.Richiesta)
class RichiestaAdmin(SolaLettura):
    list_display = ("id", "sessione", "ricevuta_il", "strumento", "parametri", "esito", "versione_calcolo", "numero_dati")
    list_filter = ("strumento", "esito")
    search_fields = ("domanda",)
    ordering = ("-id",)


@admin.register(models.MappaProdotta)
class MappaProdottaAdmin(SolaLettura):
    list_display = ("id", "sessione", "soggetto", "nome_file", "prodotta_il")
    ordering = ("-id",)


@admin.register(models.TokenAccesso)
class TokenAccessoAdmin(SolaLettura):
    """L'amministratore vede chi ha un token e può revocarlo; non può crearne per altri."""

    list_display = ("id", "utente", "etichetta", "creato_il", "ultimo_uso", "revocato_il")
    list_filter = ("utente",)
    exclude = ("impronta",)
    actions = ("revoca",)

    @admin.action(description=_("Revoca i token selezionati"), permissions=["revoca"])
    def revoca(self, request, queryset):
        for riga in queryset:
            sessioni.revoca_token(riga)

    def has_revoca_permission(self, request):
        return request.user.has_perm("grafo.change_tokenaccesso")
