# >>> NOVITA (generato da aggiorna_intestazioni.py da NOVITA.md: non modificare a mano)
#
#   servizio_mcp.py  -  app grafo, VERSIONE 25
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
con la visibilità dell'utente della sessione.

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

# Chi sta chiamando lo strumento in questo thread: {sessione, richiesta, indirizzo_mappa}.
# Vuoto quando gli strumenti sono usati senza sessione (trasporto stdio, prove).
_chiamata = threading.local()


@interrogazione.in_esclusiva
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
        + "Per aprirla l'ispettore deve accedere all'applicativo controlli con il proprio utente.\n"
        + f"Sessione n. {sessione.pk}, file {prodotta['nome_file']}.\n"
        + interrogazione.intestazione_dati()
    )


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


# Tutti gli strumenti esposti alla chat, nell'ordine del contratto
STRUMENTI = {**interrogazione.STRUMENTI, "mappa": mappa, "calcola": calcolatrice.calcola, "scheda": scheda}


def esegui_strumento(nome, parametri, domanda="", sessione=None, indirizzo_mappa=None):
    """
    Esegue uno strumento e restituisce (testo, e_errore). Con una sessione, la
    richiesta viene scritta nel registro prima dell'esecuzione e completata dopo
    con esito, durata e coppia calcolo/dati usata per la risposta.

    Uno strumento non fa mai fallire il servizio: qualsiasi errore diventa un
    testo per la chat, e il dettaglio finisce nel registro del server.
    """
    richiesta = sessioni.registra_richiesta(sessione, nome, parametri, domanda) if sessione else None
    _chiamata.sessione, _chiamata.richiesta, _chiamata.indirizzo_mappa = sessione, richiesta, indirizzo_mappa
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
