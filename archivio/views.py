"""
Pagine dell'archivio.

    /archivio/                    i faldoni, con il numero di fascicoli visibili
    /archivio/faldone/CODICE/     i fascicoli visibili di un faldone
    /archivio/fascicolo/N/        un fascicolo

Ogni pagina parte da Fascicolo.objects.visibili_a(utente). Un fascicolo che
l'utente non può vedere risponde 404, come uno che non esiste.
"""
import datetime

from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required, permission_required
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render

from decodifiche.models import TipoIdentificativo
from soggetti import servizi as anagrafica

from . import models, servizi
from .models import Faldone, Fascicolo

MASSIMO_IN_ELENCO = 200


def _tipi_identificativo():
    return TipoIdentificativo.valide_il(datetime.date.today()).order_by("ordine", "codice")


def _tipo_scelto(request):
    numero = request.POST.get("tipo", "")
    return _tipi_identificativo().filter(pk=int(numero) if numero.isdigit() else 0).first()


@login_required
@permission_required("archivio.view_fascicolo", raise_exception=True)
def faldoni(request):
    return render(request, "archivio/faldoni.html", {"faldoni": servizi.conteggi_per_faldone(request.user)})


@login_required
@permission_required("archivio.view_fascicolo", raise_exception=True)
def faldone(request, codice):
    faldone = get_object_or_404(Faldone, codice=codice.upper())
    errore = None
    puo_aprire_indagini = faldone.codice == models.INDAGINI and request.user.has_perm("archivio.apre_indagini")
    puo_aggiungere_aziende = faldone.codice == models.AZIENDE and request.user.has_perm("soggetti.add_soggetto")

    if request.method == "POST":
        try:
            if request.POST.get("azione") == "apri_indagine" and puo_aprire_indagini:
                nuovo = servizi.apri_indagine(
                    request.user, request.POST.get("titolo", ""), request.POST.get("descrizione", "")
                )
                return redirect("archivio:fascicolo", numero=nuovo.pk)
            if request.POST.get("azione") == "aggiungi_azienda" and puo_aggiungere_aziende:
                tipo = _tipo_scelto(request)
                if tipo is None:
                    raise servizi.OperazioneNonAmmessa("Scegliere il tipo di identificativo.")
                nuovo = servizi.acquisisci_azienda(
                    tipo, request.POST.get("valore", ""), request.POST.get("denominazione", "")
                )
                return redirect("archivio:fascicolo", numero=nuovo.pk)
        except (servizi.OperazioneNonAmmessa, anagrafica.IdentificativoNonValido) as problema:
            errore = str(problema)

    fascicoli = Fascicolo.objects.visibili_a(request.user).filter(faldone=faldone)
    cerca = request.GET.get("q", "").strip()
    if cerca:
        fascicoli = fascicoli.filter(
            Q(titolo__icontains=cerca) | Q(soggetto__identificativi__valore_normalizzato__icontains=cerca)
        ).distinct()
    return render(request, "archivio/faldone.html", {
        "faldone": faldone,
        "fascicoli": fascicoli.order_by("-creato_il")[:MASSIMO_IN_ELENCO],
        "cerca": cerca,
        "errore": errore,
        "puo_aprire_indagini": puo_aprire_indagini,
        "puo_aggiungere_aziende": puo_aggiungere_aziende,
        "tipi": _tipi_identificativo() if puo_aggiungere_aziende else [],
    })


@login_required
@permission_required("archivio.view_fascicolo", raise_exception=True)
def fascicolo(request, numero):
    fascicolo = (
        Fascicolo.objects.visibili_a(request.user)
        .filter(pk=numero).select_related("faldone", "soggetto", "creato_da").first()
    )
    if fascicolo is None:
        raise Http404  # stessa risposta per "non esiste" e "non lo puoi vedere"
    indagine = servizi.e_indagine(fascicolo)
    errore = None

    if request.method == "POST" and indagine:
        azione = request.POST.get("azione")
        try:
            if azione in ("assegna", "revoca"):
                numero_persona = request.POST.get("utente", "")
                persona = get_user_model().objects.filter(
                    pk=int(numero_persona) if numero_persona.isdigit() else 0, is_active=True
                ).first()
                if persona is None:
                    raise servizi.OperazioneNonAmmessa("Scegliere una persona.")
                (servizi.assegna if azione == "assegna" else servizi.revoca)(fascicolo, persona, request.user)
            elif azione == "aggiungi_soggetto":
                tipo = _tipo_scelto(request)
                if tipo is None:
                    raise servizi.OperazioneNonAmmessa("Scegliere il tipo di identificativo.")
                servizi.aggiungi_soggetto(
                    fascicolo, tipo, request.POST.get("valore", ""), request.user, request.POST.get("nota", "")
                )
            elif azione == "togli_soggetto":
                riga = request.POST.get("riga", "")
                servizi.togli_soggetto(fascicolo, int(riga) if riga.isdigit() else 0, request.user)
            return redirect("archivio:fascicolo", numero=fascicolo.pk)
        except (servizi.OperazioneNonAmmessa, anagrafica.IdentificativoNonValido) as problema:
            errore = str(problema)

    contesto = {"fascicolo": fascicolo, "indagine": indagine, "errore": errore}
    if indagine:
        assegnazioni = list(fascicolo.assegnazioni.select_related("utente").order_by("assegnato_il"))
        assegnati = [a.utente_id for a in assegnazioni]
        contesto.update({
            "assegnazioni": assegnazioni,
            "decide_le_persone": fascicolo.creato_da_id == request.user.pk,
            "persone_assegnabili": get_user_model().objects.filter(is_active=True)
            .exclude(pk__in=assegnati).order_by("username"),
            "soggetti": [
                {"riga": riga, "etichetta": anagrafica.etichetta(riga.soggetto)}
                for riga in fascicolo.soggetti_in_indagine.select_related("soggetto").order_by("aggiunto_il")
            ],
            "tipi": _tipi_identificativo(),
        })
    elif fascicolo.soggetto_id:
        contesto["identificativi"] = fascicolo.soggetto.identificativi.select_related("tipo").order_by("pk")
    return render(request, "archivio/fascicolo.html", contesto)
