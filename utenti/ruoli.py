"""Ruoli dell'applicazione e diritti associati.

Un ruolo è un gruppo di Django. I diritti sono quelli standard di Django
(add, change, delete, view) sui modelli indicati. I ruoli si possono combinare
sullo stesso utente; l'amministratore può crearne altri dall'interfaccia.

Archivio (app archivio e soggetti): Caricatore dati, Analista e Lettore
consultano faldoni e fascicoli; Caricatore dati e Analista possono aggiungere
soggetti; solo l'Analista apre indagini (diritto "apre_indagini"). Avere il
diritto di consultare non basta per vedere un'indagine: bisogna esservi assegnati.
L'Amministratore non ha diritti sull'archivio.

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
# Diritto proprio dell'archivio (archivio.apre_indagini, definito sul modello Fascicolo)
APRE_INDAGINI = ("apre",)
AGGIUNGE_E_LEGGE = ("add", "view")

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
    CARICATORE_DATI: [
        ("archivio", None, SOLO_LETTURA),
        ("soggetti", None, AGGIUNGE_E_LEGGE),
    ],
    ANALISTA: [
        ("decodifiche", None, SOLO_LETTURA),
        ("grafo", "sessione", USA_CHAT),
        ("archivio", None, SOLO_LETTURA),
        ("archivio", "fascicolo", APRE_INDAGINI),
        ("soggetti", None, AGGIUNGE_E_LEGGE),
    ],
    CONFIGURATORE: [
        ("decodifiche", None, TUTTE),
    ],
    LETTORE: [
        ("decodifiche", None, SOLO_LETTURA),
        ("archivio", None, SOLO_LETTURA),
        ("soggetti", None, SOLO_LETTURA),
    ],
}
