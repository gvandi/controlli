# >>> NOVITA (generato da aggiorna_intestazioni.py da NOVITA.md: non modificare a mano)
#
#   sessioni.py  -  app grafo, VERSIONE 38
#
#   NOVITÀ RISPETTO ALLA VERSIONE 12  ([NN] = versione che ha introdotto la novità)
#   Parte del registro: sessioni
#
#   [20] Nuovo modulo sessioni.py: parametri dell'amministratore, token personali, sessioni,
#        registro delle richieste e delle mappe.
#   [20] Il numero di sessione è assegnato dal database quando la chat si collega; la sessione
#        si chiude dopo i minuti di inattività scelti dall'amministratore (parametro
#        minuti_inattivita_sessione, predefinito 30).
#   [20] Conta come attività solo la chiamata a uno strumento; una richiesta che arriva a
#        sessione scaduta ne apre una nuova sulla stessa connessione.
#   [20] Del token si conserva solo l'impronta SHA-256: il testo in chiaro è mostrato una volta
#        a chi lo crea; revocarlo chiude le sessioni aperte.
#   [20] Un parametro viene controllato prima del salvataggio: una restrizione che escluderebbe
#        lo schema attuale o tutti i calcoli presenti è rifiutata.
#   [20] Nuovo diritto grafo.usa_chat (ruolo Analista); cruscotto e registro sono del ruolo
#        Amministratore.
#   [20] Nuovo comando python manage.py grafo_token UTENTE.
#   [21] Le sessioni ricevono un'identità già verificata (Identita: utente, tipo di accesso,
#        token o programma della chat) e non sanno più nulla di token: identita_da_token(),
#        identita_oauth(), puo_usare_la_chat().
#   [21] Ogni sessione registra come è stato fatto l'accesso (token oppure oauth) e, per OAuth,
#        il nome con cui la chat si è registrata.
#   [21] I token personali diventano un ripiego che l'amministratore può spegnere dal cruscotto
#        (parametro token_personali_ammessi: si / no).
#   [31] Nuove funzioni chat_autorizzate() e scollega_chat(): l'utente vede quali programmi di
#        chat agiscono a suo nome con l'accesso OAuth e può revocarli; scollegare chiude le
#        sessioni aperte, e la chat deve rifare l'accesso dal browser.
#
# <<< NOVITA
"""
SESSIONI DELLA CHAT: chi sta interrogando, da quando, cosa ha chiesto e quali
mappe ha prodotto. Tutto finisce nel database (schema 4.1).

  PARAMETRI   impostazioni che l'amministratore modifica dal cruscotto
  TOKEN       token personali copiati a mano: dalla versione 21 sono un ripiego,
              che l'amministratore può spegnere
  IDENTITÀ    chi sta chiamando, con token personale o con accesso OAuth
  SESSIONI    nascono alla connessione della chat, si chiudono per inattività
  REGISTRO    richieste dell'ispettore e mappe prodotte

Usa i modelli Django. Importa contratto.py e models.py; non importa
interrogazione.py: non sa nulla di aziende e punteggi.
"""
import collections
import datetime
import hashlib
import secrets

from django.utils import timezone

from . import contratto
from .models import MappaProdotta, Parametro, Richiesta, Sessione, TokenAccesso

PREFISSO_TOKEN = "ctrl_"
CHIUSA_PER_INATTIVITA = "inattivita"
CHIUSA_DAL_CLIENT = "client"
CHIUSA_PER_REVOCA = "revoca"


# =====================================================================
# 1. PARAMETRI DELL'AMMINISTRATORE
# =====================================================================
def leggi_parametri():
    """{nome: valore} per tutti i parametri del contratto; chi manca ha il valore predefinito."""
    salvati = dict(Parametro.objects.filter(nome__in=contratto.PARAMETRI).values_list("nome", "valore"))
    return {
        nome: (salvati.get(nome, predefinito) or "").strip()
        for nome, (predefinito, _) in contratto.PARAMETRI.items()
    }


def minuti_di_inattivita():
    """Minuti dopo i quali una sessione ferma viene chiusa. Un valore illeggibile vale il predefinito."""
    try:
        minuti = int(leggi_parametri()[contratto.PARAMETRO_INATTIVITA])
    except (TypeError, ValueError):
        return contratto.MINUTI_INATTIVITA_PREDEFINITI
    return minuti if 1 <= minuti <= 1440 else contratto.MINUTI_INATTIVITA_PREDEFINITI


def errore_parametro(nome, valore, schema_attuale=None, calcoli_presenti=()):
    """
    Controlla un valore prima di salvarlo. Restituisce None se va bene, altrimenti
    il motivo in chiaro. Una restrizione che spegnerebbe il servizio (esclude lo
    schema attuale o tutti i calcoli presenti) viene rifiutata.
    """
    valore = (valore or "").strip()
    if nome not in contratto.PARAMETRI:
        return f"Parametro sconosciuto: {nome}."
    if nome == contratto.PARAMETRO_TOKEN_PERSONALI:
        return None if valore.lower() in ("si", "no") else "Scrivere si oppure no."
    if nome == contratto.PARAMETRO_INATTIVITA:
        if not valore.isdigit() or not 1 <= int(valore) <= 1440:
            return "Indicare un numero intero di minuti fra 1 e 1440."
        return None
    if not contratto.restrizione_valida(valore):
        return f"'{valore}' non è un intervallo di versioni valido. Esempi: ==1.0   ~=1.0   >=1.0,<1.2"
    if not valore:
        return None
    if nome == contratto.PARAMETRO_SCHEMA and schema_attuale:
        if not contratto.accettata(schema_attuale, contratto.SCHEMA_RICHIESTO, valore):
            return (
                f"'{valore}' escluderebbe lo schema attuale del database ({schema_attuale}): "
                "le interrogazioni smetterebbero di funzionare."
            )
    if nome == contratto.PARAMETRO_CALCOLO and calcoli_presenti:
        if not any(contratto.accettata(c, contratto.CALCOLO_ACCETTATO, valore) for c in calcoli_presenti):
            return (
                f"'{valore}' escluderebbe tutti i calcoli presenti ({', '.join(sorted(set(calcoli_presenti)))}): "
                "le interrogazioni smetterebbero di funzionare."
            )
    return None


def salva_parametro(nome, valore, utente=None):
    """Salva un valore già controllato con errore_parametro()."""
    predefinito, descrizione = contratto.PARAMETRI[nome]
    Parametro.objects.update_or_create(
        nome=nome,
        defaults={"valore": (valore or "").strip(), "descrizione": descrizione, "modificato_da": utente},
    )


# =====================================================================
# 2. TOKEN PERSONALI
# =====================================================================
def impronta(token_in_chiaro):
    return hashlib.sha256(token_in_chiaro.encode("utf-8")).hexdigest()


def crea_token(utente, etichetta=""):
    """
    Crea un token per l'utente. Restituisce (riga, token in chiaro): il testo in
    chiaro non è salvato da nessuna parte e non si può più recuperare.
    """
    in_chiaro = PREFISSO_TOKEN + secrets.token_urlsafe(32)
    riga = TokenAccesso.objects.create(utente=utente, impronta=impronta(in_chiaro), etichetta=etichetta[:80])
    return riga, in_chiaro


def token_valido(token_in_chiaro):
    """
    La riga del token se esiste, non è revocato e appartiene a un utente attivo
    che ha il diritto di usare la chat; altrimenti None.
    """
    if not token_in_chiaro or not token_in_chiaro.startswith(PREFISSO_TOKEN):
        return None
    riga = (
        TokenAccesso.objects.select_related("utente")
        .filter(impronta=impronta(token_in_chiaro), revocato_il__isnull=True)
        .first()
    )
    if riga is None or not riga.utente.is_active or not riga.utente.has_perm("grafo.usa_chat"):
        return None
    if not token_personali_ammessi():
        return None
    adesso = timezone.now()
    # Una scrittura al minuto basta per sapere se un token è ancora usato
    if riga.ultimo_uso is None or adesso - riga.ultimo_uso > datetime.timedelta(minutes=1):
        TokenAccesso.objects.filter(pk=riga.pk).update(ultimo_uso=adesso)
    return riga


def revoca_token(riga):
    """Revoca il token e chiude le sessioni aperte con quel token."""
    adesso = timezone.now()
    TokenAccesso.objects.filter(pk=riga.pk, revocato_il__isnull=True).update(revocato_il=adesso)
    Sessione.objects.filter(token=riga, chiusa_il__isnull=True).update(
        chiusa_il=adesso, motivo_chiusura=CHIUSA_PER_REVOCA
    )


def chat_autorizzate(utente):
    """
    I programmi di chat che oggi possono agire a nome dell'utente con l'accesso OAuth:
        [{"applicazione": numero, "nome": ..., "dal": data della prima autorizzazione ancora valida}]
    Servono all'utente per sapere con quale utente la chat sta lavorando, e per scollegarla.
    """
    from oauth2_provider.models import get_access_token_model, get_refresh_token_model

    trovate = {}
    righe = list(get_refresh_token_model().objects.filter(user=utente, revoked__isnull=True).select_related("application"))
    righe += list(get_access_token_model().objects.filter(user=utente).select_related("application"))
    for riga in righe:
        applicazione = riga.application
        if applicazione is None:
            continue
        voce = trovate.setdefault(applicazione.pk, {
            "applicazione": applicazione.pk, "nome": applicazione.name or applicazione.client_id, "dal": riga.created,
        })
        voce["dal"] = min(voce["dal"], riga.created)
    return sorted(trovate.values(), key=lambda voce: voce["dal"])


def scollega_chat(utente, applicazione):
    """
    Toglie a un programma di chat il permesso di agire a nome dell'utente: revoca i suoi
    accessi OAuth e chiude le sessioni aperte. Alla richiesta successiva la chat riceve
    401 e deve rifare l'accesso dal browser, con l'utente collegato in quel momento.
    Restituisce quanti accessi ha tolto.
    """
    from oauth2_provider.models import get_access_token_model, get_refresh_token_model

    tolti = 0
    for rinnovo in get_refresh_token_model().objects.filter(user=utente, application_id=applicazione, revoked__isnull=True):
        rinnovo.revoke()  # revoca anche l'accesso a cui è legato
        tolti += 1
    tolti += get_access_token_model().objects.filter(user=utente, application_id=applicazione).delete()[0]
    Sessione.objects.filter(utente=utente, accesso=contratto.ACCESSO_OAUTH, chiusa_il__isnull=True).update(
        chiusa_il=timezone.now(), motivo_chiusura=CHIUSA_PER_REVOCA
    )
    return tolti


def token_personali_ammessi():
    """Falso se l'amministratore ha scelto di accettare solo l'accesso OAuth."""
    return leggi_parametri()[contratto.PARAMETRO_TOKEN_PERSONALI].lower() != "no"


# =====================================================================
# 3. IDENTITÀ E SESSIONI
# =====================================================================
# Chi sta chiamando, comunque abbia dimostrato di esserlo. Le sessioni non
# sanno nulla di token e di OAuth: ricevono un'identità già verificata.
#   utente        l'utente dell'applicativo
#   accesso       contratto.ACCESSO_TOKEN oppure contratto.ACCESSO_OAUTH
#   token         la riga del token personale (solo per ACCESSO_TOKEN)
#   client_oauth  il nome del programma della chat (solo per ACCESSO_OAUTH)
Identita = collections.namedtuple("Identita", "utente accesso token client_oauth")


def identita_da_token(riga):
    """Identità di chi si presenta con un token personale valido (vedi token_valido)."""
    return Identita(riga.utente, contratto.ACCESSO_TOKEN, riga, "")


def identita_oauth(utente, client_oauth=""):
    """Identità di chi ha fatto l'accesso dal browser: il token l'ha già verificato chi chiama."""
    return Identita(utente, contratto.ACCESSO_OAUTH, None, (client_oauth or "")[:255])


def puo_usare_la_chat(utente):
    return bool(utente and utente.is_active and utente.has_perm("grafo.usa_chat"))


def _scaduta(sessione, adesso, minuti):
    return adesso - sessione.ultima_attivita > datetime.timedelta(minutes=minuti)


def chiudi_scadute():
    """Chiude tutte le sessioni ferme da più del tempo consentito. Restituisce quante."""
    minuti = datetime.timedelta(minutes=minuti_di_inattivita())
    chiuse = 0
    for sessione in Sessione.objects.filter(chiusa_il__isnull=True, ultima_attivita__lt=timezone.now() - minuti):
        # La chiusura porta l'ora in cui il tempo è scaduto, non quella del controllo
        Sessione.objects.filter(pk=sessione.pk, chiusa_il__isnull=True).update(
            chiusa_il=sessione.ultima_attivita + minuti, motivo_chiusura=CHIUSA_PER_INATTIVITA
        )
        chiuse += 1
    return chiuse


def apri_sessione(identita, client="", indirizzo=None, id_connessione=None):
    """Nuova sessione per l'utente. Il numero di sessione è sessione.pk."""
    return Sessione.objects.create(
        utente=identita.utente,
        token=identita.token,
        accesso=identita.accesso,
        client_oauth=identita.client_oauth,
        id_connessione=id_connessione or secrets.token_urlsafe(24),
        ultima_attivita=timezone.now(),
        client=(client or "")[:200],
        indirizzo=indirizzo or None,
        versione_codice=contratto.VERSIONE_CODICE,
    )


def connessione_nota(identita, id_connessione):
    """
    Vero se l'identificativo di connessione appartiene a questo utente e la chat
    può continuare a usarlo. Falso se è sconosciuto, oppure se la sessione è stata
    chiusa dalla chat o per revoca del token: la chat deve ricollegarsi.
    """
    sessione = (
        Sessione.objects.filter(id_connessione=id_connessione, utente=identita.utente)
        .order_by("-pk")
        .first()
    )
    return sessione is not None and (
        sessione.chiusa_il is None or sessione.motivo_chiusura == CHIUSA_PER_INATTIVITA
    )


def sessione_per_richiesta(identita, id_connessione="", client="", indirizzo=None):
    """
    La sessione su cui registrare una richiesta dell'ispettore, aggiornando l'ora
    dell'ultima attività. Conta come attività solo la chiamata a uno strumento:
    i messaggi di servizio della chat (elenco degli strumenti, ping) no,
    altrimenti una chat lasciata aperta terrebbe viva la sessione per sempre.

    Se la sessione è scaduta per inattività la chiude e ne apre una nuova sulla
    stessa connessione: l'ispettore che torna dopo una pausa continua a lavorare,
    ma con un nuovo numero di sessione. Restituisce None solo se la connessione
    non è più valida (vedi connessione_nota).
    """
    sessioni_utente = Sessione.objects.filter(utente=identita.utente)
    if id_connessione:
        sessione = sessioni_utente.filter(id_connessione=id_connessione).order_by("-pk").first()
        if sessione is None:
            return None
    else:
        # Chat che non rimanda l'identificativo: vale l'ultima sessione aperta dallo
        # stesso utente con lo stesso tipo di accesso (e lo stesso token, se personale)
        sessione = (
            sessioni_utente.filter(accesso=identita.accesso, token=identita.token, chiusa_il__isnull=True)
            .order_by("-pk").first()
        )
        if sessione is None:
            return apri_sessione(identita, client, indirizzo)
    adesso, minuti = timezone.now(), minuti_di_inattivita()
    if sessione.chiusa_il is None and not _scaduta(sessione, adesso, minuti):
        Sessione.objects.filter(pk=sessione.pk).update(ultima_attivita=adesso)
        sessione.ultima_attivita = adesso
        return sessione
    if sessione.chiusa_il is None:
        Sessione.objects.filter(pk=sessione.pk).update(
            chiusa_il=sessione.ultima_attivita + datetime.timedelta(minutes=minuti),
            motivo_chiusura=CHIUSA_PER_INATTIVITA,
        )
    elif sessione.motivo_chiusura != CHIUSA_PER_INATTIVITA:
        return None
    return apri_sessione(identita, client or sessione.client, indirizzo, sessione.id_connessione)


def chiudi_connessione(identita, id_connessione, motivo=CHIUSA_DAL_CLIENT):
    """Chiude la sessione aperta su una connessione (la chat ha terminato)."""
    return Sessione.objects.filter(
        id_connessione=id_connessione, utente=identita.utente, chiusa_il__isnull=True
    ).update(chiusa_il=timezone.now(), motivo_chiusura=motivo)


# =====================================================================
# 4. REGISTRO DELLE RICHIESTE E DELLE MAPPE
# =====================================================================
def registra_richiesta(sessione, strumento, parametri, domanda=""):
    """Scrive la richiesta PRIMA di eseguirla: resta traccia anche se lo strumento fallisce."""
    return Richiesta.objects.create(
        sessione=sessione, strumento=strumento[:40], parametri=parametri, domanda=domanda or "",
        esito="in corso",
    )


def chiudi_richiesta(richiesta, esito, durata_ms=None, versione_calcolo="", numero_dati=None):
    Richiesta.objects.filter(pk=richiesta.pk).update(
        esito=esito[:20], durata_ms=durata_ms, versione_calcolo=versione_calcolo or "",
        numero_dati=numero_dati,
    )


def registra_mappa(sessione, richiesta, soggetto, nome_file, versione_calcolo="", numero_dati=None):
    """Registra il file della mappa. Rifare la stessa mappa nella stessa sessione aggiorna la riga."""
    mappa, _ = MappaProdotta.objects.update_or_create(
        sessione=sessione,
        nome_file=nome_file,
        defaults={
            "richiesta": richiesta, "soggetto_id": soggetto,
            "versione_calcolo": versione_calcolo or "", "numero_dati": numero_dati,
        },
    )
    return mappa
