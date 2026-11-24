"""Ruoli dell'applicazione e diritti associati.

Un ruolo è un gruppo di Django. I diritti sono quelli standard di Django
(add, change, delete, view) sui modelli indicati. I ruoli si possono combinare
sullo stesso utente; l'amministratore può crearne altri dall'interfaccia.

Archivio (app archivio e soggetti): Caricatore dati, Analista e Lettore
consultano faldoni e fascicoli; Caricatore dati e Analista possono aggiungere
soggetti e caricare file; solo l'Analista apre indagini (diritto "apre_indagini"). Avere il
diritto di consultare non basta per vedere un'indagine: bisogna esservi assegnati.
L'Amministratore non ha diritti sull'archivio.

Elaborazione (app elaborazione): chi consulta l'archivio vede testo ed entità dei
file che può vedere; l'Analista conferma o scarta le entità da rivedere; il
Configuratore gestisce il catalogo delle entità.

Analisi di rete (app grafo): l'Analista può interrogarla dalla chat (diritto
"usa_chat"); l'Amministratore ne modifica i parametri dal cruscotto e consulta
il registro di sessioni, richieste e mappe, ma non interroga i dati.
"""

AMMINISTRATORE = "Amministratore"
CARICATORE_DATI = "Caricatore dati"
ANALISTA = "Analista"
CONFIGURATORE = "Configuratore"
LETTORE = "Lettore"
RESPONSABILE_DEI_DATI = "Responsabile dei dati"

TUTTE = ("add", "change", "delete", "view")
SOLO_LETTURA = ("view",)
# Diritto proprio dell'app grafo (grafo.usa_chat, definito sul modello Sessione)
USA_CHAT = ("usa",)
# Diritto proprio dell'archivio (archivio.apre_indagini, definito sul modello Fascicolo)
APRE_INDAGINI = ("apre",)
AGGIUNGE_E_LEGGE = ("add", "view")
# Caricare file: il diritto che conta è archivio.add_filecaricato
CARICA = ("add", "change", "delete")
# Rivedere le entità estratte: confermarle o scartarle (elaborazione.change_entitaestratta)
RIVEDE = ("change",)
# Cancellare definitivamente un file e i dati che ne derivano (archivio.cancella_definitivamente)
CANCELLA = ("cancella",)

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
        ("archivio", "filecaricato", CARICA),
        ("soggetti", None, AGGIUNGE_E_LEGGE),
        ("elaborazione", None, SOLO_LETTURA),
    ],
    ANALISTA: [
        ("decodifiche", None, SOLO_LETTURA),
        ("grafo", "sessione", USA_CHAT),
        ("archivio", None, SOLO_LETTURA),
        ("archivio", "fascicolo", APRE_INDAGINI),
        ("archivio", "filecaricato", CARICA),
        ("soggetti", None, AGGIUNGE_E_LEGGE),
        ("elaborazione", None, SOLO_LETTURA),
        ("elaborazione", "entitaestratta", RIVEDE),
    ],
    CONFIGURATORE: [
        ("decodifiche", None, TUTTE),
        ("elaborazione", "vocecatalogo", TUTTE),
        ("indici", "regoladirischio", TUTTE),
        ("soggetti", "datiperperiodo", TUTTE),
    ],
    LETTORE: [
        ("indici", None, SOLO_LETTURA),
        ("decodifiche", None, SOLO_LETTURA),
        ("archivio", None, SOLO_LETTURA),
        ("soggetti", None, SOLO_LETTURA),
        ("elaborazione", None, SOLO_LETTURA),
    ],
    # Ruolo a parte, da dare a pochi: nessun altro ruolo può cancellare definitivamente.
    # Vede l'archivio come un Lettore; per un file riservato deve essere assegnato all'indagine.
    RESPONSABILE_DEI_DATI: [
        ("archivio", None, SOLO_LETTURA),
        ("archivio", "filecaricato", CANCELLA),
        ("soggetti", None, SOLO_LETTURA),
        ("elaborazione", None, SOLO_LETTURA),
    ],
}
