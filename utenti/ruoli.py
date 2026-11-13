"""Ruoli dell'applicazione e diritti associati.

Un ruolo è un gruppo di Django. I diritti sono quelli standard di Django
(add, change, delete, view) sui modelli indicati. I ruoli si possono combinare
sullo stesso utente; l'amministratore può crearne altri dall'interfaccia.

Caricatore dati e Analista non hanno ancora diritti: le loro funzioni arrivano
con i passi successivi (vedi TODO.md).
"""

AMMINISTRATORE = "Amministratore"
CARICATORE_DATI = "Caricatore dati"
ANALISTA = "Analista"
CONFIGURATORE = "Configuratore"
LETTORE = "Lettore"

TUTTE = ("add", "change", "delete", "view")
SOLO_LETTURA = ("view",)

# ruolo -> elenco di (app, modello o None per tutti i modelli dell'app, azioni)
DIRITTI = {
    AMMINISTRATORE: [
        ("utenti", "utente", TUTTE),
        ("auth", "group", TUTTE),
    ],
    CARICATORE_DATI: [],
    ANALISTA: [
        ("decodifiche", None, SOLO_LETTURA),
    ],
    CONFIGURATORE: [
        ("decodifiche", None, TUTTE),
    ],
    LETTORE: [
        ("decodifiche", None, SOLO_LETTURA),
    ],
}
