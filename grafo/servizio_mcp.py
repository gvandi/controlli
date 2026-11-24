# >>> NOVITA (generato da aggiorna_intestazioni.py da NOVITA.md: non modificare a mano)
#
#   servizio_mcp.py  -  app grafo, VERSIONE 31
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
SERVIZIO DEGLI STRUMENTI: il punto in cui una chiamata della chat diventa una
richiesta registrata nella sessione di un utente.

    views.py (HTTP, con token)  --+
                                  +-->  esegui_strumento()  -->  interrogazione.py / mappa.py
    server_mcp.py (stdio)  -------+              |
                                                 +-->  sessioni.py (registro)

Contiene anche il sesto strumento, "mappa": sta qui e non in interrogazione.py
perché scrive un file e lo registra nella sessione. Il settimo, "calcola", è in
calcolatrice.py e qui viene solo aggiunto all'elenco. L'ottavo, "scheda", legge
dall'archivio dei file caricati (app elaborazione) ciò che si sa di un'azienda,
con la visibilità dell'utente della sessione. Il nono, "spazio", racconta lo
spazio degli indici (app indici) e dà il collegamento alla sua pagina.
Dalla versione 27 "classifica" è qui e non più solo in interrogazione.py: unisce
ai punteggi dell'analisi di rete i criteri degli indici (regole, scostamento,
rapporti con aziende segnalate), tenendoli distinti.

Importa contratto.py, interrogazione.py, mappa.py, sessioni.py, calcolo_cartella.py,
calcolatrice.py.
"""
import logging
import threading
import time
from typing import Union

from . import calcolatrice, calcolo_cartella, contratto, interrogazione, sessioni
from . import mappa as modulo_mappa

registro = logging.getLogger("grafo.servizio_mcp")

# Chi sta chiamando lo strumento in questo thread: {sessione, richiesta, indirizzo_mappa, indirizzo_pubblico}.
# Vuoto quando gli strumenti sono usati senza sessione (trasporto stdio, prove).
_chiamata = threading.local()


@interrogazione.in_esclusiva
def _con_quale_utente(sessione):
    """
    La chat lavora a nome dell'utente che l'ha autorizzata, e le pagine che produce si aprono
    solo con lui: lo si dice per nome, perché nel browser si può essere entrati con un altro.
    """
    return (
        f"Per aprirla bisogna essere entrati nell'applicativo controlli con l'utente «{sessione.utente.get_username()}», "
        "quello con cui questa chat è stata autorizzata: con un altro utente la pagina risponde che non è disponibile.\n"
    )


def mappa(societa: Union[int, str] = "") -> str:
    """Produce la mappa investigativa di una società: il grafo dei suoi rapporti a uno e due
    passi con il report sugli indicatori di rischio, in una pagina HTML. Da usare per domande
    come "fammi la mappa della società Rossi" o "mostrami la rete di Beta Legnami".
    societa: nome (anche parziale), numero di iscrizione o numero identificativo della società,
    così come l'ha scritto l'ispettore. Lasciare vuoto per la società con l'irregolarità
    accertata a punteggio più alto.
    La risposta contiene il collegamento alla pagina: va riportato all'ispettore così com'è."""
    soggetto = None
    if str(societa).strip():
        soggetto, errore = interrogazione.risolvi_societa(societa)
        if errore:
            return errore

    sessione = getattr(_chiamata, "sessione", None)
    try:
        prodotta = modulo_mappa.produci(
            calcolo_cartella.cartella_dati(), soggetto, sessione.pk if sessione else None
        )
    except ModuleNotFoundError as errore:
        return (
            f"La mappa non può essere prodotta: sul server manca la libreria '{errore.name}' "
            "(servono networkx e pyvis). Segnalarlo all'amministratore."
        )
    if prodotta is None:
        return "Nessuna irregolarità accertata nell'archivio: indicare la società di cui si vuole la mappa."

    esecuzione = interrogazione.leggi_esecuzione()
    testo = f"Mappa investigativa prodotta per {interrogazione.etichetta(prodotta['soggetto'])}.\n"
    if sessione is None:
        # Senza sessione (stdio) non c'è una pagina protetta a cui rimandare
        return testo + f"File: {prodotta['percorso']}\n{interrogazione.intestazione_dati()}"

    riga = sessioni.registra_mappa(
        sessione, getattr(_chiamata, "richiesta", None), prodotta["soggetto"], prodotta["nome_file"],
        esecuzione["versione_calcolo"], esecuzione["numero_dati"],
    )
    return (
        testo
        + f"Collegamento alla mappa: {_chiamata.indirizzo_mappa(riga.pk)}\n"
        + _con_quale_utente(sessione)
        + f"Sessione n. {sessione.pk}, file {prodotta['nome_file']}.\n"
        + interrogazione.intestazione_dati()
    )


# Parole con cui il modello della chat scambia lo spazio degli indici per un "indicatore"
_PAROLE_DELLO_SPAZIO = ("spazio", "indici", "indice", "regola", "regole")


def indicatore(termine: str, societa: Union[int, str] = "") -> str:
    """Cerca un INDICATORE della GNN (una caratteristica usata dal modello di rete) partendo da una
    parola della sua descrizione, e dice per quali società pesa di più. Da usare per domande come
    "quali aziende hanno l'indicatore sui paesi offshore" o "per la società Rossi conta il fatturato?".
    NON è lo strumento per lo "spazio degli indici", per gli indici di rischio o per le regole di
    rischio: per quelli usare lo strumento spazio.
    termine: una o più parole della descrizione dell'indicatore, oppure il suo numero.
    societa: lasciare vuoto per cercare fra tutte le società, oppure indicarne una per nome o numero."""
    parole = "".join(c if c.isalnum() else " " for c in str(termine).lower()).split()
    # Rete di sicurezza: "indici" somiglia a "indicatore", e il modello a volte sbaglia strumento.
    # Se il termine parla solo dello spazio degli indici, risponde lo strumento giusto.
    if parole and any(p in _PAROLE_DELLO_SPAZIO for p in parole) and all(
        p in _PAROLE_DELLO_SPAZIO or p in ("degli", "di", "dello", "lo", "gli", "le", "rischio", "mostra", "mostrami")
        for p in parole
    ):
        return spazio("", societa)
    return interrogazione.indicatore(termine, societa)


ERRORI_DI_CLASSIFICA = ("Tipo di irregolarità non riconosciuto", "Popolazione non riconosciuta", "Il numero di aziende")


def classifica(n: int = 3, tipo: str = "", popolazione: str = "non_ispezionate", regola: str = "") -> str:
    """Elenca le aziende più rischiose, distinguendo il CRITERIO che ha portato a ciascuna. Da
    usare per domande come "quali sono le aziende più rischiose" o "dove conviene dirigere i
    controlli". I criteri sono indipendenti: 1) regole di rischio che scattano (tutte quelle
    attive, se l'ispettore non ne indica una); 2) scostamento dalle aziende simili (z-score
    robusto); 3) rapporti con aziende segnalate; 4) punteggio dell'analisi di rete (GNN). In testa
    stanno le aziende segnalate da più criteri. Nella risposta all'ispettore i criteri vanno
    tenuti distinti, dicendo per ogni azienda quale criterio l'ha segnalata.
    n: quante aziende elencare per ogni criterio (da 1 a 50).
    regola: lasciare vuoto per tutte le regole attive, oppure il codice o il nome di una regola.
    tipo: riguarda solo il criterio 4; lasciare vuoto per qualsiasi irregolarità, oppure uno fra
    triangolazione, falsa_fatturazione, fuori_oggetto_licenza, prodotti_diversi_dal_pubblicizzato.
    popolazione: riguarda solo il criterio 4; non_ispezionate (predefinito), ispezionate oppure tutte."""
    # Il criterio 4 legge l'archivio dell'analisi di rete; i suoi controlli sui parametri valgono per tutti
    try:
        rete = interrogazione.classifica(n, tipo, popolazione)
    except contratto.ArchivioIncompatibile as errore:
        rete = None
        nota = f"non disponibile ({errore})"
    if rete is not None and rete.startswith(ERRORI_DI_CLASSIFICA):
        return rete
    sessione = getattr(_chiamata, "sessione", None)
    if sessione is None:
        # Senza sapere chi chiede (trasporto stdio) resta la sola analisi di rete, come prima
        return rete if rete is not None else f"Archivio non utilizzabile: {nota}"

    if rete is not None and interrogazione.leggi_esecuzione()["versione_calcolo"] == contratto.VERSIONE_CALCOLO_REGOLE:
        # Sui dati reali l'archivio contiene l'indice a regole: è il criterio 1, non un altro criterio
        rete, nota = None, (
            "non calcolato sui dati reali: la GNN lavora ancora sui dati simulati e ha bisogno di "
            "irregolarità accertate per essere addestrata. I punteggi presenti nell'archivio dell'analisi "
            "di rete sono quelli delle regole del criterio 1"
        )
    # Importato qui: l'app grafo resta utilizzabile anche senza l'app indici
    from indici import classifica as classifica_degli_indici

    try:
        quante = max(1, min(contratto.MAX_AZIENDE_IN_CLASSIFICA, int(n)))
    except (TypeError, ValueError):
        quante = 3

    parti = [
        "AZIENDE PIÙ RISCHIOSE, PER CRITERIO. I criteri sono indipendenti e nessuno è un'irregolarità "
        "accertata: per ogni azienda va detto quale criterio l'ha segnalata.",
        classifica_degli_indici.racconta(sessione.utente, quante, regola),
        "\nCRITERIO 4 - ANALISI DI RETE (GNN): " + (nota + "." if rete is None else "\n" + rete),
    ]
    return "\n".join(parti)


def scheda(azienda: Union[int, str]) -> str:
    """Dice quali informazioni l'archivio conosce di un'azienda: le voci della sua scheda
    (denominazione, sede, amministratore, soci, dati di bilancio...) con il file da cui vengono,
    le voci non ancora arrivate, e i documenti (DDT, fatture) in cui compare con il suo ruolo
    (mittente, destinatario, vettore) e le altre parti. Da usare per domande come "che cosa
    sappiamo dell'azienda 10000?", "chi è l'amministratore della Alfa?", "in quali documenti
    compare il COE 54321?".
    azienda: COE, partita IVA oppure nome (anche parziale), così come l'ha scritto l'ispettore.
    Questi dati vengono dai file caricati, non dall'analisi di rete: non sono punteggi di rischio."""
    sessione = getattr(_chiamata, "sessione", None)
    if sessione is None:
        # Senza sapere chi chiede non si può decidere che cosa può vedere
        return "La scheda di un'azienda si può chiedere solo da una sessione con accesso (servizio HTTP)."
    # Importato qui: l'app grafo resta utilizzabile anche senza l'app elaborazione
    from elaborazione import coda

    return coda.descrivi_azienda(azienda, sessione.utente)


def spazio(regola: str = "", azienda: Union[int, str] = "") -> str:
    """Mostra lo SPAZIO DEGLI INDICI e ne dà il collegamento: è lo strumento da usare ogni volta che
    l'ispettore chiede di mostrare, aprire o vedere lo spazio degli indici, gli indici di rischio o
    le regole di rischio ("mostrami lo spazio degli indici", "apri lo spazio degli indici per il
    COE 10000"). Le aziende sono collocate per classe di dipendenti, classe di fatturato e
    attività, con due segnalazioni distinte: per quali scatta una regola di rischio e quali si
    discostano dalle aziende simili (z-score robusto del fatturato rispetto al personale).
    Dà anche i rapporti fra aziende che risultano dai documenti confermati, con numero di documenti
    e importi. Da usare per domande come "per quali aziende scatta la regola sul commercio senza
    dipendenti?", "la Alfa si discosta dalle aziende simili?", "con chi ha rapporti il COE 10000 e
    sono aziende segnalate?".
    regola: codice della regola, o parole del suo nome; lasciare vuoto per la prima regola attiva.
    azienda: COE, partita IVA o nome; lasciare vuoto per il quadro generale della regola.
    La risposta contiene il collegamento alla pagina in tre dimensioni: va riportato così com'è."""
    sessione = getattr(_chiamata, "sessione", None)
    if sessione is None:
        return "Lo spazio degli indici si può chiedere solo da una sessione con accesso (servizio HTTP)."
    # Importati qui: l'app grafo resta utilizzabile anche senza l'app indici
    from django.urls import reverse
    from django.utils.http import urlencode

    from indici import spazio as spazio_degli_indici

    testo, parametri = spazio_degli_indici.racconta(sessione.utente, regola, azienda)
    if parametri is None:
        return testo
    indirizzo = (getattr(_chiamata, "indirizzo_pubblico", "") or "") + reverse("indici:spazio") + "?" + urlencode(parametri)
    return (
        testo
        + f"\n\nCollegamento alla pagina in tre dimensioni: {indirizzo}\n"
        + _con_quale_utente(sessione).rstrip("\n")
    )


# Tutti gli strumenti esposti alla chat, nell'ordine del contratto
STRUMENTI = {
    **interrogazione.STRUMENTI, "classifica": classifica, "indicatore": indicatore, "mappa": mappa, "calcola": calcolatrice.calcola, "scheda": scheda, "spazio": spazio,
}


def esegui_strumento(nome, parametri, domanda="", sessione=None, indirizzo_mappa=None, indirizzo_pubblico=""):
    """
    Esegue uno strumento e restituisce (testo, e_errore). Con una sessione, la
    richiesta viene scritta nel registro prima dell'esecuzione e completata dopo
    con esito, durata e coppia calcolo/dati usata per la risposta.

    Uno strumento non fa mai fallire il servizio: qualsiasi errore diventa un
    testo per la chat, e il dettaglio finisce nel registro del server.
    """
    richiesta = sessioni.registra_richiesta(sessione, nome, parametri, domanda) if sessione else None
    _chiamata.sessione, _chiamata.richiesta, _chiamata.indirizzo_mappa = sessione, richiesta, indirizzo_mappa
    _chiamata.indirizzo_pubblico = indirizzo_pubblico
    inizio = time.monotonic()
    try:
        testo, esito = STRUMENTI[nome](**parametri), "ok"
    except contratto.ArchivioIncompatibile as errore:
        testo, esito = f"Archivio non utilizzabile: {errore}", "archivio"
    except Exception:
        registro.exception("Errore nello strumento %s", nome)
        testo, esito = "Errore interno durante l'esecuzione dello strumento: segnalarlo all'amministratore.", "errore"
    finally:
        _chiamata.sessione = _chiamata.richiesta = _chiamata.indirizzo_mappa = None
        _chiamata.indirizzo_pubblico = ""

    if richiesta is not None:
        # La calcolatrice non usa punteggi né dati: per lei nessuna coppia da registrare
        coppia = ("", None) if nome in contratto.STRUMENTI_SENZA_ARCHIVIO else _coppia_in_uso()
        sessioni.chiudi_richiesta(richiesta, esito, int((time.monotonic() - inizio) * 1000), *coppia)
    return testo, esito != "ok"


def _coppia_in_uso():
    """Coppia calcolo/dati con cui è stata data la risposta, oppure ("", None) se non si può leggere."""
    try:
        esecuzione = interrogazione.leggi_esecuzione()
        return esecuzione["versione_calcolo"], esecuzione["numero_dati"]
    except Exception:
        return "", None
