"""
LA PAGINA INIZIALE, A SCHEDE (DECISIONI.md, n. 101).

    Da fare               ciò che aspetta l'utente: file da rivedere, file non letti, caricamenti in bozza
    Caricamento           inviare file e consultare l'archivio
    Società e analisi     cercare una società e vedere ciò che se ne sa, le sue mappe, gli strumenti di analisi
    Aggiornamento dati    elaborazioni e calcoli, nell'ordine in cui vanno fatti (chi può lanciarli)
    Configurazione        decodifiche, catalogo, utenti, cruscotto (chi ne ha i diritti)

"Da fare" ha in testa la ricerca "Che cosa vuoi fare?" (utenti/guida.py), i suggerimenti ricavati
dallo stato dell'archivio e l'avviso quando i dati dell'analisi non sono aggiornati (n. 102).

Una scheda compare solo a chi può usarne almeno una funzione. Ogni scheda ha un indirizzo
(/#caricamento, /#societa ...): un collegamento porta direttamente lì.
"""
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.http import urlencode

from archivio import models as archivio
from archivio.models import Fascicolo, FileCaricato
from lavori import servizi as lavori

from . import guida

IN_ELENCO = 8
CHIAVE_DI_SESSIONE = "da_fare_aperte"   # le righe di "Da dove cominciare" già aperte in questo accesso


def _da_fare(utente):
    """Ciò che aspetta questo utente, fra i fascicoli che può vedere: conteggi e i primi di ogni elenco."""
    visibili = Fascicolo.objects.visibili_a(utente)
    file = FileCaricato.objects.filter(fascicolo__in=visibili).select_related("fascicolo")
    da_rivedere = file.filter(stato=archivio.FILE_DA_RIVEDERE).order_by("caricato_il", "pk")
    in_errore = file.filter(stato=archivio.FILE_ERRORE).order_by("-caricato_il", "-pk")
    bozze = visibili.filter(faldone__codice=archivio.CARICAMENTI, stato=archivio.BOZZA, creato_da=utente).order_by("-creato_il")
    in_attesa = file.filter(stato__in=[archivio.FILE_RICEVUTO, archivio.FILE_IN_ELABORAZIONE]).count()
    voci = {
        "da_rivedere": {"quanti": da_rivedere.count(), "primi": list(da_rivedere[:IN_ELENCO])},
        "in_errore": {"quanti": in_errore.count(), "primi": list(in_errore[:IN_ELENCO])},
        "bozze": {"quanti": bozze.count(), "primi": list(bozze[:IN_ELENCO])},
        "in_attesa": in_attesa,
    }
    voci["nulla"] = not (voci["da_rivedere"]["quanti"] or voci["in_errore"]["quanti"] or voci["bozze"]["quanti"])
    return voci


def _societa(cercata, utente):
    """
    La società cercata (COE, partita IVA o nome) con ciò che se ne sa, per la scheda "Società e analisi":
        {"cercata", "messaggio"}                       se non è stata trovata, o ne corrispondono più d'una
        {"cercata", "soggetto", "etichetta", ...}      altrimenti
    Usa le stesse funzioni della scheda completa e della chat: stessa visibilità, stessi criteri.
    """
    from elaborazione import coda
    from grafo.dati_reali import riferimento
    from grafo.models import MappaProdotta
    from soggetti import servizi as anagrafica

    soggetto, messaggio = coda.trova_azienda(cercata)
    if soggetto is None:
        return {"cercata": cercata, "messaggio": messaggio}
    scheda = coda.scheda_del_soggetto(soggetto, utente)
    fascicolo = Fascicolo.objects.visibili_a(utente).filter(faldone__codice=archivio.AZIENDE, soggetto=soggetto).first()
    return {
        "cercata": cercata, "soggetto": soggetto, "etichetta": anagrafica.etichetta(soggetto), "fascicolo": fascicolo,
        "note": [riga for riga in scheda if not riga["mancante"]],
        "mancanti": sum(1 for riga in scheda if riga["mancante"]),
        "documenti": coda.documenti_del_soggetto(soggetto, utente)[:IN_ELENCO],
        "altre": len(coda.altre_informazioni(soggetto, utente)),
        "periodi": list(soggetto.dati_per_periodo.order_by("-periodo")[:3]),
        # le mappe di rete che questo utente ha chiesto in chat per questa società
        "mappe": list(
            MappaProdotta.objects.filter(sessione__utente=utente, soggetto__riferimento=riferimento(soggetto))
            .order_by("-prodotta_il")[:IN_ELENCO]
        ),
    }


@login_required
def home(request):
    """Pagina iniziale a schede: ogni scheda mostra ciò che l'utente può fare con i suoi diritti."""
    utente = request.user
    puo_vedere_l_archivio = utente.has_perm("archivio.view_fascicolo")
    puo_vedere_le_schede = puo_vedere_l_archivio and utente.has_perm("elaborazione.view_entitaestratta")
    puo_lanciare = utente.has_perm("lavori.lancia_lavori")
    cercata = " ".join(request.GET.get("societa", "").split())[:120]
    contesto = {
        "ruoli": utente.nomi_ruoli(),
        "puo_gestire_utenti": utente.has_perm("utenti.change_utente"),
        "puo_configurare": utente.has_module_perms("decodifiche"),
        "puo_entrare_in_admin": utente.is_staff,
        "puo_vedere_l_archivio": puo_vedere_l_archivio,
        "puo_caricare_file": utente.has_perm("archivio.add_filecaricato"),
        "puo_gestire_il_catalogo": utente.has_perm("elaborazione.change_vocecatalogo"),
        "puo_usare_la_chat": utente.has_perm("grafo.usa_chat"),
        "puo_amministrare_il_grafo": utente.has_perm("grafo.change_parametro"),
        "puo_vedere_i_lavori": utente.has_perm("lavori.view_lavoro"),
        "puo_vedere_le_schede": puo_vedere_le_schede,
        "puo_rivedere": utente.has_perm("elaborazione.change_entitaestratta"),
        # La sequenza di elaborazioni e calcoli con i pulsanti per lanciarli (solo per chi può)
        "lavori": lavori.per_le_pagine() if puo_lanciare else None,
        "ritorno_lavori": reverse("home") + "#aggiornamento",
        # Lo storico accanto alla sequenza, senza cambiare pagina
        "storico": None, "lavori_in_attivita": False,
        "da_fare": _da_fare(utente) if puo_vedere_l_archivio else None,
        "societa": _societa(cercata, utente) if cercata and puo_vedere_le_schede else None,
        "cercata": cercata,
    }
    if contesto["puo_vedere_i_lavori"]:
        contesto["storico"], contesto["lavori_in_attivita"] = lavori.storico(20)
    # L'avviso "dati non aggiornati", la ricerca "che cosa vuoi fare?" e i suggerimenti (n. 102)
    from grafo import dati_reali

    contesto["stato_dei_dati"] = dati_reali.stato_per_le_pagine() if puo_vedere_l_archivio else None
    contesto["puo_lanciare"] = puo_lanciare
    contesto["guida"] = guida.voci(utente)
    # "Da dove cominciare": una riga per cosa da fare. Il numero sul bottone "Da fare" conta le righe
    # che l'utente non ha ancora aperto; una riga aperta resta in elenco, spenta, finché la cosa
    # non è fatta, e torna a contare se la situazione cambia (n. 104).
    contesto["suggerimenti"] = guida.suggerimenti(
        utente, contesto["da_fare"], contesto["stato_dei_dati"], bool(lavori.tipi_serviti()) if puo_lanciare else True
    )
    aperte = set(request.session.get(CHIAVE_DI_SESSIONE, []))
    for voce in contesto["suggerimenti"]:
        voce["aperta"] = bool(voce["chiave"]) and voce["chiave"] in aperte
        # si passa da apri_da_fare, che ricorda l'apertura e porta alla pagina giusta
        voce["collegamento"] = (
            f"{reverse('apri_da_fare')}?{urlencode({'chiave': voce['chiave']})}" if voce["chiave"] else voce["indirizzo"]
        )
    contesto["quante_da_fare"] = sum(1 for voce in contesto["suggerimenti"] if voce["chiave"] and not voce["aperta"])
    contesto["mostra_configurazione"] = contesto["puo_entrare_in_admin"] and (
        contesto["puo_configurare"] or contesto["puo_gestire_utenti"]
    ) or contesto["puo_amministrare_il_grafo"]
    # La scheda aperta all'arrivo: quella della società se si è appena cercato, altrimenti "Da fare"
    contesto["scheda_iniziale"] = "societa" if cercata else "da-fare"
    return render(request, "home.html", contesto)


@login_required
def apri_da_fare(request):
    """
    Il collegamento di una riga di "Da dove cominciare": ricorda che l'utente l'ha aperta (così il
    numero sul bottone "Da fare" scala) e porta alla pagina della riga.

    L'indirizzo NON viene dalla richiesta: si ricalcolano le righe di questo utente e si usa
    quello della riga con la chiave indicata. Una chiave che non corrisponde più a nulla (la cosa
    è stata fatta, o la situazione è cambiata) riporta alla pagina iniziale.
    Il ricordo vale per questo accesso: al prossimo, ciò che è ancora da fare torna a contare.
    """
    from grafo import dati_reali

    utente, chiave = request.user, request.GET.get("chiave", "")
    puo_vedere_l_archivio, puo_lanciare = utente.has_perm("archivio.view_fascicolo"), utente.has_perm("lavori.lancia_lavori")
    righe = guida.suggerimenti(
        utente, _da_fare(utente) if puo_vedere_l_archivio else None,
        dati_reali.stato_per_le_pagine() if puo_vedere_l_archivio else None,
        bool(lavori.tipi_serviti()) if puo_lanciare else True,
    )
    riga = next((voce for voce in righe if chiave and voce["chiave"] == chiave), None)
    if riga is None:
        return redirect("home")
    aperte = [c for c in request.session.get(CHIAVE_DI_SESSIONE, []) if c != chiave] + [chiave]
    request.session[CHIAVE_DI_SESSIONE] = aperte[-50:]
    indirizzo = riga["indirizzo"]
    return redirect(reverse("home") + indirizzo if indirizzo.startswith("#") else indirizzo)
