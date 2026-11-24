"""
Pagine dei lavori.

    /lavori/            la sequenza dei lavori con i pulsanti per lanciarli, e lo storico con gli esiti
    /lavori/richiedi/   (POST) registra la richiesta di un lavoro e torna alla pagina di partenza
"""
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from . import servizi
from .models import APERTI, Lavoro

MASSIMO_IN_ELENCO = 100


@login_required
@permission_required("lavori.view_lavoro", raise_exception=True)
def elenco(request):
    lavori = list(Lavoro.objects.select_related("richiesto_da")[:MASSIMO_IN_ELENCO])
    for lavoro in lavori:
        lavoro.titolo = servizi.TIPI[lavoro.tipo].titolo if lavoro.tipo in servizi.TIPI else lavoro.tipo
    return render(request, "lavori/elenco.html", {
        "lavori": lavori, "percorso": servizi.per_le_pagine(),
        "in_attivita": any(lavoro.stato in APERTI for lavoro in lavori),
        "nessun_esecutore": not servizi.tipi_serviti(),
        "puo_lanciare": request.user.has_perm("lavori.lancia_lavori"),
    })


@login_required
@permission_required("lavori.lancia_lavori", raise_exception=True)
@require_POST
def richiedi(request):
    ritorno = request.POST.get("ritorno", "")
    if not url_has_allowed_host_and_scheme(ritorno, allowed_hosts={request.get_host()}):
        ritorno = "lavori:elenco"
    tipo = request.POST.get("tipo", "")
    if tipo not in servizi.TIPI:
        messages.error(request, "Tipo di lavoro sconosciuto.")
        return redirect(ritorno)
    titolo = servizi.TIPI[tipo].titolo
    parametri, ingresso, nome_ingresso = {}, "", ""

    if tipo == "elabora_file" and request.POST.get("massimo", "").strip():
        if not request.POST["massimo"].strip().isdigit() or int(request.POST["massimo"]) < 1:
            messages.error(request, "Il numero massimo di file deve essere un intero positivo.")
            return redirect(ritorno)
        parametri["massimo"] = int(request.POST["massimo"])
    if tipo == "importa_anagrafica":
        caricato = request.FILES.get("file")
        if caricato is None:
            messages.error(request, "Scegliere il file CSV da importare.")
            return redirect(ritorno)
        if caricato.size > settings.LAVORI_CSV_MASSIMO:
            messages.error(request, f"Il file supera il limite di {settings.LAVORI_CSV_MASSIMO // (1024 * 1024)} MB.")
            return redirect(ritorno)
        try:
            ingresso = caricato.read().decode("utf-8-sig")
        except UnicodeDecodeError:
            messages.error(request, "Il file non è un testo UTF-8: salvarlo come CSV UTF-8 e riprovare.")
            return redirect(ritorno)
        nome_ingresso = caricato.name
        parametri["fonte"] = " ".join(request.POST.get("fonte", "").split())[:120] or caricato.name

    lavoro, nuovo = servizi.richiedi(tipo, request.user, parametri, ingresso, nome_ingresso)
    if not nuovo:
        messages.error(request, f"«{titolo}» è già {lavoro.stato} (lavoro n. {lavoro.pk}): attendere che finisca.")
    elif tipo not in servizi.tipi_serviti():
        messages.success(
            request,
            f"«{titolo}» richiesto (lavoro n. {lavoro.pk}). Attenzione: nessun processo sta eseguendo questo tipo "
            "di lavoro; resterà in attesa finché non viene avviato «python manage.py esegui_lavori».",
        )
    else:
        messages.success(request, f"«{titolo}» richiesto (lavoro n. {lavoro.pk}): l'esito comparirà nella pagina dei lavori.")
    return redirect(ritorno)
