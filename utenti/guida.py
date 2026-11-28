"""
"CHE COSA VUOI FARE?": le azioni dell'applicativo dette con le parole di chi lo usa, per la
ricerca della scheda "Da fare" (DECISIONI.md, n. 102).

Ogni voce dice che cosa si può fare, in una riga come si fa, e dove: una pagina o una scheda
della pagina iniziale. Una voce compare solo a chi ha il diritto di farla. La ricerca è nella
pagina (nessuna richiesta al server): confronta le parole scritte con titolo, testo e PAROLE,
che raccoglie i modi diversi di chiamare la stessa cosa.

Per aggiungere una voce: una riga in VOCI. "dove" è il nome di un indirizzo (con i suoi
argomenti) oppure "#nome" per una scheda della pagina iniziale. "diritto" vuoto = tutti.

    suggerimenti(...)  è l'altra metà: non ciò che si può fare, ma ciò che conviene fare ORA,
                       ricavato dallo stato dell'archivio. Al più tre, il più urgente per primo.
"""
from django.urls import NoReverseMatch, reverse

# (titolo, come si fa, parole per la ricerca, dove, argomenti, diritto, solo personale tecnico)
VOCI = (
    ("Caricare fatture, DDT o altri documenti",
     "Apri un caricamento, aggiungi i file (anche una cartella o uno ZIP) e alla fine conferma.",
     "carica caricare upload inviare file fattura fatture ddt documento documenti pdf scansione zip cartella nuovo caricamento",
     "archivio:faldone", ("CARICAMENTI",), "archivio.add_filecaricato", False),
    ("Rivedere un file letto dal programma",
     "Nell'elenco qui sotto apri il file: a sinistra l'originale, a destra entità, mittente e destinatario da controllare.",
     "rivedere revisione controllare confermare conferma entità mittente destinatario ruoli verificare da rivedere",
     "#da-fare", (), "archivio.view_fascicolo", False),
    ("Capire perché un file è in errore",
     "Apri il file dall'elenco qui sotto: trovi che cosa è successo e che cosa fare. Spesso non devi fare nulla.",
     "errore errori non letto fallito lettura tagliata problema file rotto non riuscito",
     "#da-fare", (), "archivio.view_fascicolo", False),
    ("Sapere che cosa si sa di una società",
     "Nella scheda «Società e analisi» cerca per COE, partita IVA o nome.",
     "società azienda ditta impresa soggetto coe partita iva scheda cerca cercare trovare informazioni dati anagrafica",
     "#societa", (), "elaborazione.view_entitaestratta", False),
    ("Vedere con chi commercia una società",
     "Cerca la società e apri «Nello spazio degli indici»: selezionata, compaiono le linee verso le società con cui ha documenti. "
     "Oppure chiedi in chat: «con chi commercia il COE …».",
     "rapporti relazioni commercia clienti fornitori vende compra collegamenti linee controparti",
     "#societa", (), "elaborazione.view_entitaestratta", False),
    ("Ottenere la mappa di rete di una società",
     "Si chiede in chat: «mostrami la mappa di rete del COE …». Le mappe già chieste sono nella scheda «Società e analisi», cercando la società.",
     "mappa rete grafo triangolazione triangolazioni circuito investigativa disegno nodi",
     "grafo:collegamento", (), "grafo.usa_chat", False),
    ("Trovare le società più a rischio",
     "In chat: «quali sono le società più rischiose». La risposta tiene distinti i criteri: regole, scostamenti, rapporti, rete.",
     "rischio rischiose classifica sospette segnalate controlli priorità dove controllare indice punteggio",
     "grafo:collegamento", (), "grafo.usa_chat", False),
    ("Vedere le società che si discostano dalle simili",
     "Lo spazio degli indici mostra le società in tre dimensioni: quelle per cui scatta una regola e quelle insolite.",
     "spazio indici scostamento anomale anomalie insolite z-score regola regole tre dimensioni sfere grafico",
     "indici:spazio", (), "indici.view_regoladirischio", False),
    ("Collegare la chat all'applicativo",
     "La pagina di collegamento dà l'indirizzo da inserire nel programma di chat e l'elenco delle chat autorizzate.",
     "chat collegare collegamento unsloth mcp server autorizzare token assistente domande",
     "grafo:collegamento", (), "grafo.usa_chat", False),
    ("Aprire un'indagine riservata",
     "Nel faldone Indagini: il fascicolo sarà visibile solo a te e alle persone che vi assegni.",
     "indagine indagini riservata riservato fascicolo assegnare segreto caso",
     "archivio:faldone", ("INDAGINI",), "archivio.apre_indagini", False),
    ("Togliere un file caricato per errore",
     "Dalla pagina del file: «Cancella definitivamente» toglie il file e tutto ciò che ne è stato ricavato. Serve una motivazione.",
     "cancellare cancella eliminare togliere rimuovere sbagliato errore file doppio annullare",
     "archivio:faldone", ("CARICAMENTI",), "archivio.cancella_definitivamente", False),
    ("Far leggere al programma i file caricati",
     "Scheda «Aggiornamento dati», passo 2: «Elabora i file in attesa». Serve il modello locale acceso.",
     "elaborare elabora leggere lettura modello coda file in attesa ocr trascrivere estrarre",
     "#aggiornamento", (), "lavori.lancia_lavori", False),
    ("Importare l'anagrafica delle società da CSV",
     "Scheda «Aggiornamento dati», passo 4. Colonne: coe;piva;periodo;denominazione;ateco;dipendenti;fatturato.",
     "importare importa csv anagrafica camera di commercio ateco dipendenti fatturato elenco società periodo",
     "#aggiornamento", (), "lavori.lancia_lavori", False),
    ("Aggiornare grafo e indici dopo nuovi documenti",
     "Scheda «Aggiornamento dati», passo 5. Va rilanciato ogni volta che si caricano documenti o si importa un'anagrafica.",
     "aggiornare aggiorna grafo indici calcolo calcolare ricalcolare dati non aggiornati non vedo mappa vuota mancano rapporti",
     "#aggiornamento", (), "lavori.lancia_lavori", False),
    ("Vedere l'esito di elaborazioni e calcoli",
     "Lo storico dei lavori: chi li ha chiesti, quanto sono durati, come sono finiti.",
     "lavori storico esito esiti fallito finito durata log registro",
     "lavori:elenco", (), "lavori.view_lavoro", False),
    ("Cambiare le regole di rischio",
     "Le regole stanno in una tabella: attività, classe di dipendenti e di fatturato, peso. Dopo una modifica va rilanciato il calcolo.",
     "regola regole rischio soglia peso modificare aggiungere configurare indicatore",
     "admin:indici_regoladirischio_changelist", (), "indici.change_regoladirischio", True),
    ("Riconoscere una nuova informazione letta nei file",
     "«Entità fuori catalogo» elenca ciò che il modello legge e nessuna voce riconosce: da lì la si aggiunge a una voce.",
     "catalogo voce voci entità fuori catalogo sinonimo etichetta nuova informazione",
     "elaborazione:fuori_catalogo", (), "elaborazione.change_vocecatalogo", False),
    ("Creare un utente o cambiargli il ruolo",
     "Dall'amministrazione degli utenti: i diritti si assegnano per ruolo.",
     "utente utenti ruolo ruoli diritti permessi password accesso creare ispettore amministratore",
     "admin:app_list", ("utenti",), "utenti.change_utente", True),
)


def voci(utente):
    """Le voci che questo utente può usare: [{"titolo", "testo", "parole", "indirizzo", "scheda"}]."""
    elenco = []
    for titolo, testo, parole, dove, argomenti, diritto, solo_personale in VOCI:
        if (diritto and not utente.has_perm(diritto)) or (solo_personale and not utente.is_staff):
            continue
        if dove.startswith("#"):
            indirizzo, scheda = dove, dove[1:]
        else:
            try:
                indirizzo, scheda = reverse(dove, args=argomenti), ""
            except NoReverseMatch:
                continue
        elenco.append({"titolo": titolo, "testo": testo, "parole": parole, "indirizzo": indirizzo, "scheda": scheda})
    return elenco


def suggerimenti(utente, da_fare, stato_dei_dati, esecutore_acceso):
    """
    Ciò che conviene fare ora, dallo stato dell'archivio: [{"testo", "indirizzo", "azione", "conta"}], al più tre.
    "conta" è vero per ciò che aspetta davvero qualcuno (non per "niente ti aspetta") e non è già
    contato fra file da rivedere, file non letti e bozze: serve al numero sul bottone "Da fare".
    da_fare è quello della pagina iniziale (o None), stato_dei_dati quello di grafo.dati_reali (o None).
    """
    puo_lanciare, voci_utili = utente.has_perm("lavori.lancia_lavori"), []

    def aggiungi(testo, indirizzo="", azione="", conta=False):
        voci_utili.append({"testo": testo, "indirizzo": indirizzo, "azione": azione, "conta": conta})

    if puo_lanciare and not esecutore_acceso:
        aggiungi("Nessun processo sta eseguendo i lavori: ciò che lanci resta in attesa. Avvia «./avvia.sh» "
                 "oppure «python manage.py esegui_lavori».", reverse("lavori:elenco"), "Apri i lavori", conta=True)
    if da_fare:
        rivedere = da_fare["da_rivedere"]
        if rivedere["quanti"]:
            primo = rivedere["primi"][0]
            pagina = "elaborazione:file" if utente.has_perm("elaborazione.view_entitaestratta") else "archivio:file"
            aggiungi(
                ("C'è un file da rivedere" if rivedere["quanti"] == 1 else f"Ci sono {rivedere['quanti']} file da rivedere")
                + f": comincia dal più vecchio, «{primo.percorso_originale}».",
                reverse(pagina, args=[primo.pk]), "Apri la revisione",
            )
        if da_fare["bozze"]["quanti"]:
            bozza = da_fare["bozze"]["primi"][0]
            aggiungi(f"Il caricamento «{bozza.titolo}» è ancora in bozza: finché non lo confermi i suoi file non vengono letti.",
                     reverse("archivio:fascicolo", args=[bozza.pk]), "Apri il caricamento")
        if puo_lanciare and da_fare["in_attesa"]:
            aggiungi(f"{da_fare['in_attesa']} file aspettano di essere letti dal programma.", "#aggiornamento", "Vai al passo 2", conta=True)
    if stato_dei_dati and not stato_dei_dati["vuoto"] and not stato_dei_dati["aggiornati"]:
        if puo_lanciare:
            aggiungi("Chat, mappa e classifica non vedono gli ultimi dati caricati.", "#aggiornamento", "Vai al passo 5", conta=True)
    elif stato_dei_dati and stato_dei_dati["vuoto"] and puo_lanciare:
        aggiungi("Non ci sono ancora dati da analizzare: importa un'anagrafica (passo 4) o fai leggere i file caricati (passo 2).",
                 "#aggiornamento", "Vai all'aggiornamento dei dati")
    if not voci_utili and da_fare and da_fare["nulla"] and utente.has_perm("archivio.add_filecaricato"):
        aggiungi("Niente ti aspetta. Se hai nuovi documenti, puoi caricarli.", reverse("archivio:faldone", args=["CARICAMENTI"]),
                 "Nuovo caricamento")
    return voci_utili[:3]
