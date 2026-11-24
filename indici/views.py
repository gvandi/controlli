"""
Pagine dell'app indici.

    /indici/spazio/?tipo=falsa_fatturazione    le aziende come punti in tre dimensioni
                                               (classe di dipendenti, classe di fatturato,
                                               attività): vedi indici/spazio.py
"""
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import render
from django.urls import reverse

from grafo import contratto

from . import spazio as spazio_degli_indici


@login_required
@permission_required("indici.view_regoladirischio", raise_exception=True)
def spazio(request):
    tipo = request.GET.get("tipo", "")
    if tipo not in contratto.TIPI_IRREGOLARITA:
        tipo = contratto.TIPI_IRREGOLARITA[0]
    dati = spazio_degli_indici.costruisci(tipo)
    # Il collegamento alla scheda dell'azienda solo per chi può aprirla
    apre_le_schede = request.user.has_perm("elaborazione.view_entitaestratta")
    for punto in dati["punti"]:
        fascicolo = punto.pop("fascicolo")
        punto["scheda"] = reverse("elaborazione:soggetto", args=[fascicolo]) if apre_le_schede and fascicolo else ""
    return render(request, "indici/spazio.html", {
        "dati": dati, "tipo": tipo, "tipi": contratto.TIPI_IRREGOLARITA,
        "aziende": len(dati["punti"]),
    })
