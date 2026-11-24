# >>> NOVITA (generato da aggiorna_intestazioni.py da NOVITA.md: non modificare a mano)
#
#   views.py  -  app grafo, VERSIONE 32
#
#   NOVITÀ RISPETTO ALLA VERSIONE 12  ([NN] = versione che ha introdotto la novità)
#   Parte del registro: server
#
#   [16] Nuovo server MCP (server_mcp.py) che registra i quattro strumenti della libreria, per
#        usare Unsloth Studio come chat.
#   [16] All'avvio apre l'archivio: se non combacia con il codice il server non parte.
#   [17] Compatibile con la libreria mcp 1.x (FastMCP) e 2.x (MCPServer): con la 2.x la versione
#        16 non partiva (ModuleNotFoundError).
#   [17] Strumenti registrati con add_tool() e trasporto stdio indicato in modo esplicito.
#   [18] Registra anche il quinto strumento, indicatore (nessuna modifica al codice: l'elenco
#        viene da contratto.py).
#   [19] Si avvia con python manage.py grafo_server_mcp, che carica le impostazioni
#        dell'applicativo.
#   [20] Nuovo servizio MCP su HTTP dentro l'applicativo (views.py, indirizzo /grafo/mcp/): la
#        chat si collega dalla rete e si presenta con un token personale; senza token valido la
#        risposta è 401.
#   [20] Il protocollo è scritto in protocollo_mcp.py (initialize, ping, tools/list,
#        tools/call), senza la libreria mcp, che resta solo per il trasporto stdio.
#   [20] Ogni chiamata passa da servizio_mcp.esegui_strumento(): la richiesta viene registrata
#        nella sessione prima dell'esecuzione e completata con esito, durata e coppia
#        calcolo/dati.
#   [20] Ogni strumento ha in più il parametro facoltativo domanda, in cui il modello della chat
#        ricopia la domanda dell'ispettore per il registro.
#   [20] Nuovo strumento mappa(societa): produce la mappa investigativa e restituisce il
#        collegamento alla pagina /grafo/mappe/N/, visibile dopo l'accesso solo a chi l'ha
#        chiesta.
#   [20] Nuove pagine: /grafo/collegamento/ (l'analista crea e revoca i propri token, ritrova le
#        proprie mappe) e /grafo/cruscotto/ (l'amministratore vede le quattro versioni, i
#        calcoli presenti, le sessioni, e modifica i parametri).
#   [20] Il server stdio (grafo_server_mcp) resta per le prove su un solo computer: non
#        riconosce l'utente e non registra sessioni.
#   [21] Accesso OAuth 2.0 dal browser: l'applicativo è il server di autorizzazione (libreria
#        django-oauth-toolkit 3.4, indirizzi sotto /o/); la chat si registra da sola, l'analista
#        accede e autorizza, il token non si copia più a mano.
#   [21] Il rifiuto 401 indica alla chat il documento da cui partire (intestazione WWW-
#        Authenticate con resource_metadata); i documenti di scoperta sono alla radice del sito
#        (/.well-known/...).
#   [21] views.py riconosce chi chiama in un solo punto (_identita_della_richiesta): token OAuth
#        verificato dalla libreria (scadenza, ambito, servizio a cui è destinato) oppure token
#        personale.
#   [21] Utente riconosciuto ma senza il diritto usa_chat: risposta 403, distinta dal 401 che fa
#        ripartire l'accesso.
#   [21] Nuova pagina di consenso in italiano (templates/oauth2_provider/authorize.html): mostra
#        il programma che chiede l'accesso e l'indirizzo a cui si viene rimandati.
#   [21] La pagina "Collegamento alla chat" indica l'accesso OAuth come via normale e i token
#        personali come ripiego; il cruscotto mostra per ogni sessione il tipo di accesso.
#   [21] La pagina di consenso si salta quando l'utente ha già autorizzato lo stesso programma e
#        il suo token non è scaduto (REQUEST_APPROVAL_PROMPT auto; con
#        CONTROLLI_OAUTH_CONSENSO=force torna a ogni accesso).
#   [22] Nuovo strumento calcola(espressione), nel modulo calcolatrice.py: aritmetica esatta per
#        la chat, valutata come albero sintattico senza eseguire codice; limiti su lunghezza,
#        esponente e dimensione del risultato.
#   [22] Le chiamate a calcola sono registrate nella sessione come le altre, senza coppia
#        calcolo/dati; lo strumento funziona anche se l'archivio non è utilizzabile.
#   [23] Nuovo strumento scheda(azienda): dice ciò che l'archivio sa di un'azienda (voci note
#        con il file di provenienza, voci non ancora arrivate, documenti confermati in cui
#        compare con il ruolo e le altre parti); l'azienda si indica con COE, partita IVA o
#        nome.
#   [23] scheda usa solo ciò che viene da file che l'utente della sessione può vedere (stessa
#        regola delle pagine); senza sessione (trasporto stdio) non risponde.
#   [26] Nuovo strumento spazio(regola, azienda): racconta lo spazio degli indici (per quali
#        aziende scatta una regola, quali si discostano dalle aziende simili, i rapporti di
#        un'azienda dai documenti confermati) e dà il collegamento alla pagina in tre
#        dimensioni, con regola e azienda già scelte.
#   [26] esegui_strumento() riceve l'indirizzo pubblico dell'applicativo, per i collegamenti
#        alle pagine che non sono mappe.
#   [27] Lo strumento classifica risponde per criteri distinti: 1) regole di rischio che
#        scattano (tutte quelle attive, o quella indicata nel nuovo parametro regola), 2)
#        scostamento dalle aziende simili, 3) rapporti con aziende segnalate, 4) punteggio
#        dell'analisi di rete; in testa le aziende segnalate da più criteri.
#   [27] Quando l'esecuzione in uso è l'indice a regole (dati reali), classifica non la presenta
#        come un quarto criterio: dichiara che la GNN non è calcolata su quei dati. Senza
#        sessione (stdio) classifica resta la sola analisi di rete.
#   [28] Lo strumento indicatore, se riceve come termine solo parole che indicano lo spazio
#        degli indici (indici, spazio, regole), passa la domanda allo strumento spazio; le
#        descrizioni dei due strumenti dicono esplicitamente quando usare l'uno e quando
#        l'altro.
#   [30] La pagina di una mappa che non si può mostrare resta 404 ma spiega che cosa fare: con
#        quale utente si è collegati e che la mappa si apre con l'utente che ha autorizzato la
#        chat, oppure che il file non c'è più e va richiesta di nuovo; il motivo preciso va nel
#        registro del server.
#   [31] Gli strumenti mappa e spazio dicono con quale utente va aperto il collegamento (quello
#        che ha autorizzato la chat); la pagina di collegamento elenca le chat autorizzate con
#        il proprio utente e permette di scollegarle.
#
# <<< NOVITA
"""
PAGINE E SERVIZIO HTTP dell'app grafo.

    /grafo/mcp/             servizio MCP per la chat (POST con accesso OAuth o token personale)
    /grafo/mappe/<n>/       mappa investigativa n, per chi ha fatto l'accesso
    /grafo/collegamento/    l'analista vede e scollega le chat autorizzate con il suo utente,
                            crea e revoca i propri token
    /grafo/cruscotto/       l'amministratore vede le versioni e cambia i parametri

Qui non c'è logica di interrogazione: il protocollo sta in protocollo_mcp.py,
l'esecuzione degli strumenti in servizio_mcp.py, sessioni e parametri in sessioni.py.
"""
import json
import logging
import pathlib

from django.conf import settings
from django.contrib.auth.decorators import login_required, permission_required
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from oauth2_provider.oauth2_backends import get_oauthlib_core

from . import calcolo_cartella, contratto, interrogazione, protocollo_mcp, servizio_mcp, sessioni
from .models import Esecuzione, InfoArchivio, MappaProdotta, Richiesta, Sessione, TokenAccesso

registro = logging.getLogger(__name__)
INTESTAZIONE_CONNESSIONE = "Mcp-Session-Id"
ISTRUZIONI = (pathlib.Path(__file__).resolve().parent / "prompt_di_sistema.txt").read_text(encoding="utf-8")


def _indirizzo_pubblico(request):
    """Indirizzo dell'applicativo come lo vede l'analista (senza barra finale)."""
    configurato = getattr(settings, "GRAFO_URL_PUBBLICO", "")
    return (configurato or request.build_absolute_uri("/")).rstrip("/")


# =====================================================================
# 1. SERVIZIO MCP
# =====================================================================
def _metadati_della_risorsa(request):
    """
    Indirizzo del documento che dice alla chat dove chiedere l'accesso (RFC 9728),
    nella forma con il percorso del servizio: .../.well-known/oauth-protected-resource/grafo/mcp
    """
    return _indirizzo_pubblico(request) + "/.well-known/oauth-protected-resource" + reverse("grafo:mcp").rstrip("/")


def _non_autorizzato(request, errore=None):
    """
    401: manca un accesso valido. L'intestazione WWW-Authenticate indica alla chat
    il documento da cui partire per l'accesso OAuth dal browser.
    """
    risposta = JsonResponse(
        {"errore": "Accesso mancante, scaduto o revocato: collegare la chat con l'accesso OAuth."}, status=401
    )
    parti = ['realm="controlli"']
    if errore:
        parti.append(f'error="{errore}"')
    parti.append(f'resource_metadata="{_metadati_della_risorsa(request)}"')
    risposta["WWW-Authenticate"] = "Bearer " + ", ".join(parti)
    return risposta


def _vietato():
    """403: l'utente è stato riconosciuto ma non ha il diritto di usare la chat. Rifare l'accesso non serve."""
    return JsonResponse(
        {"errore": "L'utente non ha il diritto di interrogare l'analisi di rete (ruolo Analista)."}, status=403
    )


def _identita_della_richiesta(request):
    """
    Restituisce (identità, None) oppure (None, risposta di rifiuto).

    Due modi di presentarsi, entrambi nell'intestazione "Authorization: Bearer ...":
      - token personale (comincia con ctrl_): ripiego della versione 20, se l'amministratore lo ammette;
      - token OAuth rilasciato dall'applicativo dopo l'accesso dal browser: lo
        verifica la libreria (validità, scadenza, ambito, servizio a cui è destinato).
    """
    schema, _, valore = request.headers.get("Authorization", "").partition(" ")
    valore = valore.strip()
    if schema.lower() != "bearer" or not valore:
        return None, _non_autorizzato(request)

    if valore.startswith(sessioni.PREFISSO_TOKEN):
        riga = sessioni.token_valido(valore)
        return (sessioni.identita_da_token(riga), None) if riga else (None, _non_autorizzato(request, "invalid_token"))

    request.body  # letto ora: resta disponibile dopo la verifica della libreria
    valido, richiesta_oauth = get_oauthlib_core().verify_request(request, scopes=[contratto.AMBITO_OAUTH])
    utente = getattr(richiesta_oauth, "user", None) if valido else None
    if utente is None:
        return None, _non_autorizzato(request, "invalid_token")
    if not sessioni.puo_usare_la_chat(utente):
        return None, _vietato()
    client = getattr(richiesta_oauth, "client", None)
    return sessioni.identita_oauth(utente, getattr(client, "name", "") or getattr(client, "client_id", "")), None


@csrf_exempt  # non usa i cookie dell'applicativo: l'identità è nell'intestazione Authorization
@require_http_methods(["POST", "DELETE"])
def mcp(request):
    """Punto di ingresso della chat: un messaggio JSON-RPC (o un elenco) per ogni POST."""
    identita, rifiuto = _identita_della_richiesta(request)
    if rifiuto is not None:
        return rifiuto
    id_connessione = request.headers.get(INTESTAZIONE_CONNESSIONE, "")

    if request.method == "DELETE":
        # La chat dichiara di aver finito: la sessione si chiude subito
        if id_connessione:
            sessioni.chiudi_connessione(identita, id_connessione)
        return HttpResponse(status=204)

    try:
        corpo = json.loads(request.body.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        return JsonResponse(
            {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "JSON non valido."}}, status=400
        )
    messaggi = corpo if isinstance(corpo, list) else [corpo]
    client = request.headers.get("User-Agent", "")
    indirizzo = request.META.get("REMOTE_ADDR")

    # La sessione nasce quando la chat si collega (messaggio "initialize")
    nuova = None
    iniziali = [m for m in messaggi if protocollo_mcp.metodo(m) == "initialize"]
    if iniziali:
        sessioni.chiudi_scadute()
        info = (iniziali[0].get("params") or {}).get("clientInfo") or {}
        descrizione = " ".join(str(info.get(campo, "")) for campo in ("name", "version")).strip()
        nuova = sessioni.apri_sessione(identita, descrizione or client, indirizzo)
        id_connessione = nuova.id_connessione
    elif id_connessione and not sessioni.connessione_nota(identita, id_connessione):
        # Per il protocollo: 404 significa "sessione terminata, ricollegarsi"
        return JsonResponse(
            {"jsonrpc": "2.0", "id": None, "error": {"code": -32001, "message": "Sessione terminata: ricollegarsi."}},
            status=404,
        )

    indirizzo_pubblico = _indirizzo_pubblico(request)

    def esegui(nome, parametri, domanda):
        sessione = sessioni.sessione_per_richiesta(identita, id_connessione, client, indirizzo)
        if sessione is None:
            return "Sessione terminata: ricollegare il server MCP nella chat.", True
        return servizio_mcp.esegui_strumento(
            nome, parametri, domanda, sessione,
            lambda numero: indirizzo_pubblico + reverse("grafo:mappa", args=[numero]),
            indirizzo_pubblico,
        )

    risposte = [
        risposta for risposta in (
            protocollo_mcp.rispondi(m, servizio_mcp.STRUMENTI, esegui, ISTRUZIONI) for m in messaggi
        )
        if risposta is not None
    ]
    if not risposte:
        return HttpResponse(status=202)  # solo avvisi: nessuna risposta da dare
    risposta = JsonResponse(risposte if isinstance(corpo, list) else risposte[0], safe=False)
    if nuova is not None:
        risposta[INTESTAZIONE_CONNESSIONE] = nuova.id_connessione
    return risposta


# =====================================================================
# 2. MAPPA INVESTIGATIVA
# =====================================================================
@login_required
def mappa(request, numero):
    """
    Mostra una mappa a chi l'ha prodotta, o a chi può vedere le mappe di tutti.

    Quando non si può mostrare, la risposta resta 404 ma dice che cosa fare, senza
    rivelare nulla: "non esiste" e "non è tua" hanno lo stesso identico testo. Il
    motivo preciso va nel registro del server, per chi amministra.
    """
    riga = MappaProdotta.objects.select_related("sessione__utente").filter(pk=numero).first()
    if riga is None or not (
        riga.sessione.utente_id == request.user.pk or request.user.has_perm("grafo.view_mappaprodotta")
    ):
        registro.warning(
            "Mappa %s negata all'utente %s: %s", numero, request.user.get_username(),
            "non esiste" if riga is None else f"è dell'utente {riga.sessione.utente.get_username()}",
        )
        return render(request, "grafo/mappa_non_disponibile.html", {"motivo": "altro_utente"}, status=404)
    # Il nome viene dal database, ma si usa comunque solo l'ultima parte del percorso
    percorso = calcolo_cartella.cartella_dati() / pathlib.Path(riga.nome_file).name
    if not percorso.is_file():
        registro.warning("Mappa %s: il file %s non è nella cartella %s", numero, percorso.name, percorso.parent)
        return render(request, "grafo/mappa_non_disponibile.html", {"motivo": "file_mancante"}, status=404)
    return HttpResponse(percorso.read_bytes(), content_type="text/html; charset=utf-8")


# =====================================================================
# 3. COLLEGAMENTO ALLA CHAT (token dell'analista)
# =====================================================================
@login_required
@permission_required("grafo.usa_chat", raise_exception=True)
def collegamento(request):
    token_appena_creato = None
    if request.method == "POST":
        if request.POST.get("azione") == "crea":
            _, token_appena_creato = sessioni.crea_token(request.user, request.POST.get("etichetta", "").strip())
        elif request.POST.get("azione") == "revoca":
            numero = request.POST.get("token", "")
            riga = TokenAccesso.objects.filter(pk=int(numero) if numero.isdigit() else 0, utente=request.user).first()
            if riga is not None:
                sessioni.revoca_token(riga)
        elif request.POST.get("azione") == "scollega" and request.POST.get("applicazione", "").isdigit():
            # solo le proprie autorizzazioni: l'utente è sempre quello della richiesta
            sessioni.scollega_chat(request.user, int(request.POST["applicazione"]))
    return render(request, "grafo/collegamento.html", {
        "chat_autorizzate": sessioni.chat_autorizzate(request.user),
        "token_appena_creato": token_appena_creato,
        "token": TokenAccesso.objects.filter(utente=request.user).order_by("-creato_il"),
        "indirizzo_servizio": _indirizzo_pubblico(request) + reverse("grafo:mcp"),
        "token_personali_ammessi": sessioni.token_personali_ammessi(),
        "mappe": MappaProdotta.objects.filter(sessione__utente=request.user)
        .select_related("sessione").order_by("-prodotta_il")[:20],
    })


# =====================================================================
# 4. CRUSCOTTO DELL'AMMINISTRATORE
# =====================================================================
LIMITE_DEL_CODICE = {
    contratto.PARAMETRO_SCHEMA: contratto.SCHEMA_RICHIESTO,
    contratto.PARAMETRO_CALCOLO: contratto.CALCOLO_ACCETTATO,
    contratto.PARAMETRO_SPIEGAZIONE: contratto.SPIEGAZIONE_ACCETTATA,
}


@login_required
@permission_required("grafo.change_parametro", raise_exception=True)
def cruscotto(request):
    info = InfoArchivio.objects.filter(chiave="versione_schema").first()
    schema_database = info.valore if info else None
    esecuzioni = list(
        Esecuzione.objects.select_related("versione_dati").order_by("-versione_dati__numero", "-calcolata_il")
    )
    calcoli_presenti = [e.versione_calcolo for e in esecuzioni]

    errori, salvato = {}, False
    proposti = sessioni.leggi_parametri()
    if request.method == "POST":
        for nome in contratto.PARAMETRI:
            proposti[nome] = request.POST.get(nome, "").strip()
            errore = sessioni.errore_parametro(nome, proposti[nome], schema_database, calcoli_presenti)
            if errore:
                errori[nome] = errore
        if not errori:
            for nome, valore in proposti.items():
                sessioni.salva_parametro(nome, valore, request.user)
            salvato = True

    in_vigore = sessioni.leggi_parametri()
    try:
        in_uso, errore_archivio = interrogazione.apri(), None
    except contratto.ArchivioIncompatibile as errore:
        in_uso, errore_archivio = None, str(errore)

    sessioni.chiudi_scadute()
    ultime = list(Sessione.objects.select_related("utente").order_by("-pk")[:15])
    for sessione in ultime:
        sessione.numero_richieste = Richiesta.objects.filter(sessione=sessione).count()

    return render(request, "grafo/cruscotto.html", {
        "versione_codice": contratto.VERSIONE_CODICE,
        "schema_del_codice": contratto.VERSIONE_SCHEMA,
        "schema_database": schema_database,
        "schema_allineato": schema_database == contratto.VERSIONE_SCHEMA,
        "versione_calcolo": contratto.VERSIONE_CALCOLO,
        "schema_spiegazione": contratto.SCHEMA_SPIEGAZIONE,
        "limiti": {
            "schema": contratto.SCHEMA_RICHIESTO,
            "calcolo": contratto.CALCOLO_ACCETTATO,
            "spiegazione": contratto.SPIEGAZIONE_ACCETTATA,
        },
        "esecuzioni": [
            {
                "etichetta": f"calcolo {e.versione_calcolo} / dati {e.versione_dati.numero}",
                "calcolata_il": e.calcolata_il,
                "versione_codice": e.versione_codice,
                "accettata": contratto.accettata(
                    e.versione_calcolo, contratto.CALCOLO_ACCETTATO, in_vigore[contratto.PARAMETRO_CALCOLO]
                ),
            }
            for e in esecuzioni
        ],
        "in_uso": in_uso,
        "errore_archivio": errore_archivio,
        "parametri": [
            {
                "nome": nome,
                "valore": proposti[nome],
                "descrizione": descrizione,
                "limite_del_codice": LIMITE_DEL_CODICE.get(nome),
                "errore": errori.get(nome),
            }
            for nome, (_, descrizione) in contratto.PARAMETRI.items()
        ],
        "salvato": salvato,
        "sessioni_aperte": Sessione.objects.filter(chiusa_il__isnull=True).count(),
        "ultime_sessioni": ultime,
        "minuti_inattivita": sessioni.minuti_di_inattivita(),
    })
