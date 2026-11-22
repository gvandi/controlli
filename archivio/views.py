"""
Pagine dell'archivio.

    /archivio/                    i faldoni, con il numero di fascicoli visibili
    /archivio/faldone/CODICE/     i fascicoli visibili di un faldone
    /archivio/fascicolo/N/        un fascicolo (indagine, azienda o caricamento)
    /archivio/file/N/             un file caricato: metadati propri e soggetti
    /archivio/file/N/scarica/     il contenuto originale del file

Ogni pagina parte da Fascicolo.objects.visibili_a(utente). Un fascicolo che
l'utente non può vedere risponde 404, come uno che non esiste.
"""
import datetime

from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required, permission_required
from django.db.models import Q
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render

from decodifiche.models import TipoDocumento, TipoIdentificativo
from soggetti import servizi as anagrafica

from . import caricamento, models, servizi
from .models import Caricamento, Faldone, Fascicolo, FileCaricato

MASSIMO_IN_ELENCO = 200


def _tipi_identificativo():
    return TipoIdentificativo.valide_il(datetime.date.today()).order_by("ordine", "codice")


def _tipi_documento():
    return TipoDocumento.valide_il(datetime.date.today()).order_by("ordine", "codice")


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
    puo_caricare = faldone.codice == models.CARICAMENTI and caricamento.puo_caricare(request.user)

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
            if request.POST.get("azione") == "nuovo_caricamento" and puo_caricare:
                numero = request.POST.get("indagine", "")
                indagine = (
                    caricamento.indagini_di(request.user).filter(pk=int(numero)).first() if numero.isdigit() else None
                )
                if numero and indagine is None:
                    raise caricamento.NonAmmesso("Indagine non valida.")
                nuovo = caricamento.nuovo(request.user, request.POST.get("titolo", ""), indagine)
                return redirect("archivio:fascicolo", numero=nuovo.pk)
        except (servizi.OperazioneNonAmmessa, caricamento.NonAmmesso, anagrafica.IdentificativoNonValido) as problema:
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
        "puo_caricare": puo_caricare,
        "indagini": caricamento.indagini_di(request.user).order_by("titolo") if puo_caricare else [],
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
    if caricamento.e_caricamento(fascicolo):
        return _pagina_caricamento(request, fascicolo)
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


# =====================================================================
# CARICAMENTO DEI FILE
# =====================================================================
def _numero(request, campo):
    valore = request.POST.get(campo, "")
    return int(valore) if valore.isdigit() else 0


def _azioni_sui_soggetti(request, su):
    """Le tre azioni sui campi COE, uguali per il caricamento e per il singolo file. Vero se ne ha eseguita una."""
    azione = request.POST.get("azione")
    if azione == "coe_aggiungi":
        tipo = _tipo_scelto(request)
        if tipo is None:
            raise caricamento.NonAmmesso("Scegliere il tipo di identificativo.")
        caricamento.dichiara_soggetto(su, request.user, tipo, request.POST.get("valore", ""))
    elif azione == "coe_togli":
        caricamento.togli_soggetto_dichiarato(su, request.user, _numero(request, "riga"))
    elif azione == "coe_principale":
        caricamento.rendi_principale(su, request.user, _numero(request, "riga"))
    else:
        return False
    return True


def _pagina_caricamento(request, fascicolo):
    errore, resoconto = None, None
    # Un fascicolo del faldone Caricamenti ha sempre la sua riga di metadati
    dati_caricamento, _ = Caricamento.objects.get_or_create(fascicolo=fascicolo)
    if request.method == "POST":
        azione = request.POST.get("azione")
        try:
            if azione == "carica":
                singoli = request.FILES.getlist("file")
                di_cartella = request.FILES.getlist("cartella")
                percorsi = [""] * len(singoli) + request.POST.getlist("percorso_cartella")
                if not singoli and not di_cartella:
                    raise caricamento.NonAmmesso("Scegliere almeno un file, una cartella o un file ZIP.")
                # Qui non si rimanda alla pagina: il resoconto va mostrato subito
                resoconto = caricamento.aggiungi_file(fascicolo, request.user, singoli + di_cartella, percorsi)
            else:
                if azione == "metadati":
                    caricamento.salva_metadati(dati_caricamento, request.user, request.POST, _tipi_documento())
                elif azione == "conferma":
                    caricamento.conferma(fascicolo, request.user)
                elif azione == "annulla":
                    caricamento.annulla(fascicolo, request.user)
                elif azione == "elimina":
                    caricamento.elimina_bozza(fascicolo, request.user)
                    return redirect("archivio:faldone", codice=models.CARICAMENTI)
                else:
                    _azioni_sui_soggetti(request, fascicolo)
                return redirect("archivio:fascicolo", numero=fascicolo.pk)
        except (caricamento.NonAmmesso, anagrafica.IdentificativoNonValido) as problema:
            errore = str(problema)

    ripetute = caricamento.doppioni(fascicolo)
    elenco = list(fascicolo.file.order_by("percorso_originale"))
    for riga in elenco:
        riga.doppione = riga.impronta in ripetute
    puo_caricare = caricamento.puo_caricare(request.user)
    return render(request, "archivio/caricamento.html", {
        "fascicolo": fascicolo,
        "caricamento": Caricamento.objects.select_related("tipo_documento").get(pk=fascicolo.pk),
        "errore": errore,
        "resoconto": resoconto,
        "file": elenco,
        "dimensione_totale": sum(riga.dimensione for riga in elenco),
        "dichiarati": [
            {"riga": riga, "etichetta": anagrafica.etichetta(riga.soggetto)}
            for riga in caricamento.dichiarati(fascicolo)
        ],
        "in_bozza": fascicolo.stato == models.BOZZA and puo_caricare,
        "annullabile": fascicolo.stato == models.CONFERMATO and puo_caricare,
        "tipi": _tipi_identificativo(),
        "tipi_documento": _tipi_documento(),
        "nature": models.NATURE,
        "eventi": fascicolo.eventi.select_related("utente").order_by("-quando")[:30],
    })


def _file_visibile(request, numero):
    """Il file, solo se l'utente può vedere il fascicolo a cui appartiene; altrimenti 404."""
    riga = (
        FileCaricato.objects.filter(pk=numero, fascicolo__in=Fascicolo.objects.visibili_a(request.user))
        .select_related("fascicolo__faldone", "fascicolo__caricamento", "tipo_documento").first()
    )
    if riga is None:
        raise Http404
    return riga


@login_required
@permission_required("archivio.view_fascicolo", raise_exception=True)
def file(request, numero):
    riga = _file_visibile(request, numero)
    fascicolo, errore = riga.fascicolo, None
    if request.method == "POST":
        try:
            if request.POST.get("azione") == "togli_file":
                caricamento.togli_file(riga, request.user)
                return redirect("archivio:fascicolo", numero=fascicolo.pk)
            if request.POST.get("azione") == "metadati":
                caricamento.salva_metadati(riga, request.user, request.POST, _tipi_documento())
            else:
                _azioni_sui_soggetti(request, riga)
            return redirect("archivio:file", numero=riga.pk)
        except (caricamento.NonAmmesso, anagrafica.IdentificativoNonValido) as problema:
            errore = str(problema)

    effettivi = caricamento.metadati_effettivi(riga)
    soggetti, ereditati = caricamento.soggetti_effettivi(riga)
    return render(request, "archivio/file.html", {
        "file": riga,
        "fascicolo": fascicolo,
        "errore": errore,
        "effettivi": [
            {"nome": nome, "valore": effettivi[campo][0], "ereditato": effettivi[campo][1]}
            for campo, nome in (
                ("provenienza", "Provenienza"), ("tipo_documento", "Tipo di documento"), ("natura", "Natura"),
                ("periodo_dal", "Periodo dal"), ("periodo_al", "Periodo al"),
            )
        ],
        "soggetti": [{"riga": s, "etichetta": anagrafica.etichetta(s.soggetto)} for s in soggetti],
        "soggetti_ereditati": ereditati,
        "in_bozza": fascicolo.stato == models.BOZZA and caricamento.puo_caricare(request.user),
        "tipi": _tipi_identificativo(),
        "tipi_documento": _tipi_documento(),
        "nature": models.NATURE,
    })


@login_required
@permission_required("archivio.view_fascicolo", raise_exception=True)
def scarica(request, numero):
    """Il contenuto originale, così com'è arrivato, come file da salvare."""
    riga = _file_visibile(request, numero)
    try:
        contenuto = caricamento.apri_contenuto(riga)
    except OSError:
        raise Http404
    return FileResponse(contenuto, as_attachment=True, filename=riga.percorso_originale.rsplit("/", 1)[-1])
