"""Ruoli dell'applicazione e diritti associati.

Un ruolo è un gruppo di Django. I diritti sono quelli standard di Django
(add, change, delete, view) sui modelli indicati. I ruoli si possono combinare
sullo stesso utente; l'amministratore può crearne altri dall'interfaccia.

Il Caricatore dati non ha ancora diritti: le sue funzioni arrivano con i passi
successivi (vedi TODO.md).

Analisi di rete (app grafo): l'Analista può interrogarla dalla chat (diritto
"usa_chat"); l'Amministratore ne modifica i parametri dal cruscotto e consulta
il registro di sessioni, richieste e mappe, ma non interroga i dati.
"""

AMMINISTRATORE = "Amministratore"
CARICATORE_DATI = "Caricatore dati"
ANALISTA = "Analista"
CONFIGURATORE = "Configuratore"
LETTORE = "Lettore"

TUTTE = ("add", "change", "delete", "view")
SOLO_LETTURA = ("view",)
# Diritto proprio dell'app grafo (grafo.usa_chat, definito sul modello Sessione)
USA_CHAT = ("usa",)

# ruolo -> elenco di (app, modello o None per tutti i modelli dell'app, azioni)
DIRITTI = {
    AMMINISTRATORE: [
        ("utenti", "utente", TUTTE),
        ("auth", "group", TUTTE),
        ("grafo", "parametro", TUTTE),
        ("grafo", "tokenaccesso", ("change", "view")),
        ("grafo", "sessione", SOLO_LETTURA),
        ("grafo", "richiesta", SOLO_LETTURA),
        ("grafo", "mappaprodotta", SOLO_LETTURA),
    ],
    CARICATORE_DATI: [],
    ANALISTA: [
        ("decodifiche", None, SOLO_LETTURA),
        ("grafo", "sessione", USA_CHAT),
    ],
    CONFIGURATORE: [
        ("decodifiche", None, TUTTE),
    ],
    LETTORE: [
        ("decodifiche", None, SOLO_LETTURA),
    ],
}
