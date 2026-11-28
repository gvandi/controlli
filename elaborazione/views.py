"""
Pagine dell'elaborazione.

    /elaborazione/file/N/        testo ed entità estratte da un file; revisione:
                                 si scelgono le entità da conservare, le altre sono
                                 scartate, e si torna alla pagina del file in archivio.
                                 Se il file contiene un documento commerciale (DDT,
                                 fattura...) qui si correggono i suoi dati e il ruolo
                                 di ogni parte (mittente, destinatario, vettore...)
    /elaborazione/soggetto/N/    la scheda di un soggetto (N = fascicolo dell'azienda)
    /elaborazione/fuori-catalogo/   etichette raccolte ma non significative, da promuovere

Testo ed entità si vedono solo se si può vedere il file da cui vengono: ogni
pagina parte dai fascicoli visibili all'utente, come nell'archivio.
"""
import collections
import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.http import Http404
from django.shortcuts import redirect, render

from archivio import caricamento
from archivio import models as archivio
from archivio.models import Fascicolo, FileCaricato
from soggetti import servizi as anagrafica

from . import coda
from . import models
from .models import Documento, EntitaEstratta


def _file_visibile(request, numero):
    riga = (
        FileCaricato.objects.filter(pk=numero, fascicolo__in=Fascicolo.objects.visibili_a(request.user))
        .select_related("fascicolo__faldone").first()
    )
    if riga is None:
        raise Http404
    return riga


class DatiNonValidi(Exception):
    """Ciò che il revisore ha scritto per il documento non si può leggere."""


def _documento_dal_modulo(dati, documento):
    """Ciò che il revisore ha deciso sul documento, nella forma attesa da coda.chiudi_revisione."""
    scritta, totale = dati.get("documento_data", "").strip(), dati.get("documento_totale", "").strip()
    try:
        data = datetime.date.fromisoformat(scritta) if scritta else None
    except ValueError:
        raise DatiNonValidi("La data del documento non è valida.")
    importo = coda.importo_da_testo(totale) if totale else None
    if totale and importo is None:
        raise DatiNonValidi("L'importo totale del documento non è un numero.")
    parti = {}
    for parte in documento.parti.all():
        soggetto = dati.get(f"soggetto_{parte.pk}", "")
        parti[parte.pk] = (dati.get(f"ruolo_{parte.pk}", ""), int(soggetto) if soggetto.isdigit() else None)
    return {
        "valido": dati.get("documento_valido") == "si",
        "tipo": dati.get("documento_tipo", "").strip().upper(),
        "numero": dati.get("documento_numero", "").strip(),
        "data": data, "totale": importo, "parti": parti,
    }


@login_required
@permission_required("elaborazione.view_entitaestratta", raise_exception=True)
def file(request, numero):
    riga = _file_visibile(request, numero)
    puo_rivedere = request.user.has_perm("elaborazione.change_entitaestratta")
    documento = Documento.objects.filter(file=riga).first()
    if request.method == "POST" and puo_rivedere:
        if request.POST.get("ripristina", "").isdigit():
            coda.ripristina(riga, [int(request.POST["ripristina"])])
            return redirect("elaborazione:file", numero=riga.pk)
        if request.POST.get("azione") == "conserva":
            scelte = [int(n) for n in request.POST.getlist("entita") if n.isdigit()]
            try:
                da_decidere = documento is not None and riga.stato != archivio.FILE_ANNULLATO
                deciso = _documento_dal_modulo(request.POST, documento) if da_decidere else None
            except DatiNonValidi as problema:
                messages.error(request, f"{problema} Nulla è stato salvato.")
                return redirect("elaborazione:file", numero=riga.pk)
            conservate, scartate = coda.chiudi_revisione(riga, scelte, deciso)
            riga.refresh_from_db()
            esito = f"Revisione chiusa: {conservate} entità conservate, {scartate} scartate. "
            if deciso:
                esito += "Documento e ruoli confermati. " if deciso["valido"] else "Documento scartato. "
            if riga.stato == archivio.FILE_ELABORATO:
                esito += "Il file è ora «elaborato»."
            else:
                esito += f"Il file resta «{riga.stato}»: la sua lettura non è ancora completa."
            messages.success(request, esito)
            return redirect("archivio:file", numero=riga.pk)
        return redirect("elaborazione:file", numero=riga.pk)

    elaborazioni = list(riga.elaborazioni.order_by("-iniziata_il"))
    ultima = next((e for e in elaborazioni if e.esito != "errore"), None)
    entita = list(
        EntitaEstratta.objects.filter(file=riga).select_related("voce", "soggetto").order_by("pagina", "pk")
    )
    return render(request, "elaborazione/file.html", {
        "file": riga,
        "fascicolo": riga.fascicolo,
        "elaborazioni": elaborazioni,
        "testi": ultima.testi.order_by("pagina") if ultima else [],
        "entita": entita,
        "in_attesa": sum(1 for e in entita if e.da_rivedere and not e.ritirata),
        "utilizzabili": sum(
            1 for e in entita
            if e.voce_id and (e.verificata or e.confermata) and e.soggetto_id and not e.da_rivedere and not e.ritirata
        ),
        "puo_rivedere": puo_rivedere,
        "documento": documento,
        "parti": list(documento.parti.select_related("soggetto").order_by("pk")) if documento else [],
        "soggetti_del_file": [(s.pk, anagrafica.etichetta(s)) for s in coda.soggetti_del_file(riga)],
        "ruoli": models.RUOLI,
        # L'originale accanto alle entità: "application/pdf", "image/..." oppure None (solo da scaricare)
        # la pagina su cui aprire l'originale, quando si arriva da un dato "non verificato"
        "pagina_iniziale": int(request.GET["pagina"]) if request.GET.get("pagina", "").isdigit() and request.GET["pagina"] != "1" else None,
        "originale": caricamento.tipo_in_pagina(riga) if request.user.has_perm("archivio.view_fascicolo") else None,
    })


@login_required
@permission_required("elaborazione.view_entitaestratta", raise_exception=True)
def soggetto(request, numero):
    """La scheda del soggetto a cui è intestato un fascicolo del faldone Aziende."""
    fascicolo = (
        Fascicolo.objects.visibili_a(request.user).filter(pk=numero, soggetto__isnull=False)
        .select_related("faldone", "soggetto").first()
    )
    if fascicolo is None:
        raise Http404
    scheda = coda.scheda_del_soggetto(fascicolo.soggetto, request.user)
    return render(request, "elaborazione/soggetto.html", {
        "fascicolo": fascicolo,
        "etichetta": anagrafica.etichetta(fascicolo.soggetto),
        "scheda": scheda,
        "documenti": coda.documenti_del_soggetto(fascicolo.soggetto, request.user),
        "altre": coda.altre_informazioni(fascicolo.soggetto, request.user),
        "note": sum(1 for riga in scheda if not riga["mancante"]),
        "mancanti": sum(1 for riga in scheda if riga["mancante"]),
    })


@login_required
@permission_required("elaborazione.change_vocecatalogo", raise_exception=True)
def fuori_catalogo(request):
    """
    Le etichette raccolte che nessuna voce del catalogo riconosce, con quante volte
    compaiono. Il Configuratore può riconoscerne una come altro nome di una voce:
    le entità già raccolte diventano significative senza rileggere i file.
    Si mostrano solo le etichette e i conteggi, mai i valori.
    """
    messaggio = None
    if request.method == "POST":
        numero = request.POST.get("voce", "")
        voce = coda.voci_valide().filter(pk=int(numero) if numero.isdigit() else 0).first()
        etichetta = request.POST.get("etichetta", "")
        if voce is not None and etichetta.strip():
            promosse = coda.promuovi(etichetta, voce)
            messaggio = f"«{etichetta}» riconosciuta come {voce.codice}: {promosse} entità ora significative."
    conteggi = collections.Counter(
        " ".join(etichetta.split()).lower()
        for etichetta in EntitaEstratta.objects.fuori_catalogo().values_list("etichetta", flat=True)
    )
    return render(request, "elaborazione/fuori_catalogo.html", {
        "etichette": conteggi.most_common(200),
        "voci": coda.voci_valide(),
        "messaggio": messaggio,
    })
