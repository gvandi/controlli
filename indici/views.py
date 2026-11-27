"""
Pagine dell'app indici.

    /indici/spazio/?regola=CODICE&azienda=N    le aziende come punti in tre dimensioni;
                                               azienda = soggetto da selezionare all'apertura
                                               (classe di dipendenti, classe di fatturato,
                                               attività): vedi indici/spazio.py
"""
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import render
from django.urls import reverse

from grafo import dati_reali

from . import spazio as spazio_degli_indici
from .models import RegolaDiRischio


@login_required
@permission_required("indici.view_regoladirischio", raise_exception=True)
def spazio(request):
    # Si sceglie una regola fra quelle definite; senza scelta, la prima attiva
    regole = list(RegolaDiRischio.objects.order_by("-attiva", "codice"))
    scelta = next((r for r in regole if r.codice == request.GET.get("regola", "")), regole[0] if regole else None)
    dati = spazio_degli_indici.costruisci(scelta)
    # L'azienda da mostrare già selezionata (così arriva il collegamento dato dalla chat)
    dati["apri"] = int(request.GET["azienda"]) if request.GET.get("azienda", "").isdigit() else None
    # Il collegamento alla scheda dell'azienda solo per chi può aprirla
    apre_le_schede = request.user.has_perm("elaborazione.view_entitaestratta")
    for punto in dati["punti"]:
        fascicolo = punto.pop("fascicolo")
        punto["scheda"] = reverse("elaborazione:soggetto", args=[fascicolo]) if apre_le_schede and fascicolo else ""
    return render(request, "indici/spazio.html", {
        "dati": dati, "regola": scelta, "regole": regole,
        "aziende": len(dati["punti"]),
        # i rapporti disegnati qui vengono dall'archivio di adesso; classifica e mappa da un calcolo: dirlo se divergono
        "stato": dati_reali.stato_per_le_pagine(), "puo_lanciare": request.user.has_perm("lavori.lancia_lavori"),
    })
