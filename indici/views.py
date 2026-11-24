"""
Pagine dell'app indici.

    /indici/spazio/?regola=CODICE              le aziende come punti in tre dimensioni
                                               (classe di dipendenti, classe di fatturato,
                                               attività): vedi indici/spazio.py
"""
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import render
from django.urls import reverse

from . import spazio as spazio_degli_indici
from .models import RegolaDiRischio


@login_required
@permission_required("indici.view_regoladirischio", raise_exception=True)
def spazio(request):
    # Si sceglie una regola fra quelle definite; senza scelta, la prima attiva
    regole = list(RegolaDiRischio.objects.order_by("-attiva", "codice"))
    scelta = next((r for r in regole if r.codice == request.GET.get("regola", "")), regole[0] if regole else None)
    dati = spazio_degli_indici.costruisci(scelta)
    # Il collegamento alla scheda dell'azienda solo per chi può aprirla
    apre_le_schede = request.user.has_perm("elaborazione.view_entitaestratta")
    for punto in dati["punti"]:
        fascicolo = punto.pop("fascicolo")
        punto["scheda"] = reverse("elaborazione:soggetto", args=[fascicolo]) if apre_le_schede and fascicolo else ""
    return render(request, "indici/spazio.html", {
        "dati": dati, "regola": scelta, "regole": regole,
        "aziende": len(dati["punti"]),
    })
