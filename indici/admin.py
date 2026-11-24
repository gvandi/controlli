from django import forms
from django.contrib import admin

from grafo import contratto

from .models import RegolaDiRischio


class RegolaForm(forms.ModelForm):
    tipo = forms.ChoiceField(choices=[(tipo, tipo) for tipo in contratto.TIPI_IRREGOLARITA])

    class Meta:
        model = RegolaDiRischio
        fields = "__all__"


@admin.register(RegolaDiRischio)
class RegolaDiRischioAdmin(admin.ModelAdmin):
    form = RegolaForm
    list_display = ("codice", "descrizione", "tipo", "peso", "prefissi_attivita", "classi_dipendenti", "classi_fatturato", "attiva")
    list_filter = ("tipo", "attiva")
    search_fields = ("codice", "descrizione")
