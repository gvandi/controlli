# Registro delle decisioni

Una voce per ogni scelta fatta, soprattutto quelle prese al posto di una risposta
che ancora manca. Quando la risposta arriva, la voce si rivede.

| N. | Data | Decisione | Motivo | Da rivedere quando |
| --- | --- | --- | --- | --- |
| 1 | 2026-11-12 | Python, Django, PostgreSQL | Utenti, ruoli e caricamento file già pronti; librerie statistiche mature; buona gestione degli intervalli di validità | Solo se l'amministrazione impone altro |
| 2 | 2026-11-12 | Pagine generate dal server, senza frontend separato | Meno codice finché le schermate sono poche | Se le schermate di analisi richiedono molta interattività |
| 3 | 2026-11-12 | Modello utente proprio (`utenti.Utente`) fin dall'inizio | Cambiarlo a progetto avviato è costoso | - |
| 4 | 2026-11-12 | Ruoli come gruppi di Django: Amministratore, Caricatore dati, Analista, Configuratore, Lettore | Proposta iniziale della relazione, combinabili sullo stesso utente | Dopo il confronto con l'amministrazione |
| 5 | 2026-11-12 | Ogni tabella di decodifica ha codice, descrizione, ordine, valida dal, valida al | Un valore si ritira senza cancellarlo; la storia resta leggibile | - |
| 6 | 2026-11-12 | Forma giuridica e posizione nel gruppo sono due tabelle distinte | Una holding è quasi sempre una srl o una spa: sono informazioni indipendenti | - |
| 7 | 2026-11-12 | Il modello di business è fatto di quattro attributi separati (clientela, stagionalità, contanti, estero) | Un'azienda può essere B2C, stagionale e importatrice insieme | - |
| 8 | 2026-11-12 | Classi di dipendenti: 0, 1-2, 3-5, 6-9, 10-19, 20-49, 50-249, 250 e oltre | Soglie europee a 10, 50 e 250, con più dettaglio sotto 10 perché quasi tutte le aziende sono micro | Sui dati reali |
| 9 | 2026-11-12 | Classi di fatturato: fino a 100.000, 100-250.000, 250-500.000, 500.000-1 milione, 1-2, 2-10, 10-50, oltre 50 milioni | Come sopra, soglie europee a 2, 10 e 50 milioni | Sui dati reali |
| 10 | 2026-11-12 | Le classi dimensionali sono intervalli (minimo incluso, massimo escluso); la classe di un'azienda si calcola, non si inserisce | Le soglie possono cambiare senza toccare i dati delle aziende | - |
| 11 | 2026-11-12 | La tabella delle attività economiche ha gerarchia (codice padre) e versione della classificazione | Serve per allargare il gruppo di confronto e per gestire le revisioni | Quando è nota la classificazione in uso |
| 12 | 2026-11-12 | Sviluppo solo su dati sintetici; nessun dato reale e nessuna credenziale nel repository | Il repository è su un servizio esterno | - |
| 13 | 2026-11-12 | Anagrafica unica dei soggetti: aziende analizzate e controparti stanno nello stesso archivio | Una fattura lega un'azienda analizzata a una controparte; con due archivi lo stesso soggetto verrebbe registrato due volte | - |
| 14 | 2026-11-12 | L'identificativo fiscale non è la chiave del soggetto: chiave interna, più una tabella di identificativi con tipo, paese, valore originale, valore normalizzato e validità | Il formato dipende dal paese (COE a San Marino, partita IVA in Italia), un soggetto può averne più di uno e può cambiare | - |
| 15 | 2026-11-12 | Gestione documentale su tre livelli: file (oggetto caricato), documento (atto contenuto), legame documento-soggetto con ruolo | Un file può essere un elenco di documenti; un documento lega più soggetti; i documenti si collegano tra loro (DDT, fattura, pagamento) | - |
| 16 | 2026-11-12 | Lo stesso documento ricevuto da due fonti non è un doppione: le copie si confrontano | Una differenza tra la copia dell'emittente e quella del destinatario è un'anomalia | - |
| 17 | 2026-11-12 | Nessun attributo "sotto controllo" sul soggetto. La popolazione analizzata è definita da una regola generale versionata | Un'etichetta sull'anagrafica rivelerebbe a tutto il gruppo di lavoro quali soggetti sono oggetto di indagine | - |
| 18 | 2026-11-12 | Le indagini stanno in fascicoli separati, visibili solo alle persone assegnate. Ogni analista apre i propri fascicoli e decide chi vi è assegnato | Riservatezza delle indagini; scelta indicata dal committente | Se serve una figura di supervisione (vedi TODO.md) |
| 19 | 2026-11-12 | File e documenti hanno un livello di visibilità (generale o legato a un fascicolo); conteggi e ricerche mostrano solo ciò che l'utente può vedere; i punteggi si calcolano sempre per tutta la popolazione | Evitare che presenza di dati, totali o elaborazioni mirate rivelino l'interesse per un soggetto | - |
| 20 | 2026-11-12 | Il formato del COE è assunto di cinque cifre, con prefissi "COE" e "SM" tolti nella normalizzazione | Dedotto dall'esempio del committente; il controllo è un'espressione modificabile dalla configurazione | Alla conferma del formato |
| 21 | 2026-11-13 | I documenti si elaborano fuori linea, dopo il caricamento, con OCR e modello linguistico locale | Il caricamento resta immediato; i documenti non escono dall'infrastruttura; trattare tutti i file allo stesso modo non rivela quali interessano | - |
| 22 | 2026-11-13 | Da ogni documento si ricavano tre cose: testo completo per la ricerca, campi strutturati per i controlli, tag per la classificazione | I soli tag permettono di ritrovare un documento ma non di confrontarlo con le transazioni | - |
| 23 | 2026-11-13 | Ogni strumento per ciò che sa fare: XML letto come dati, PDF con testo estratto direttamente, OCR solo per le immagini, regole per identificativi, date e importi, modello per tipo, ruoli, descrizioni e tag | Meno errori e meno calcolo che affidare tutto al modello | - |
| 24 | 2026-11-13 | Tag scelti da un vocabolario controllato; i tag liberi sono "proposti" e li promuove un configuratore | Un modello lasciato libero produce più varianti dello stesso tag | - |
| 25 | 2026-11-13 | Ogni valore estratto dal modello deve comparire nel testo del documento; risposta vincolata a uno schema, con grado di affidabilità. Il testo del documento è trattato come dato, mai come istruzione, e il modello non ha strumenti | Contro i dati inventati e contro documenti confezionati per ingannare il modello | - |
| 26 | 2026-11-13 | I risultati dell'elaborazione sono versionati (motore OCR, modello, versione) e non si sovrascrivono; l'originale resta la prova | Rielaborare quando il modello migliora senza perdere ciò che si vedeva prima | - |
| 27 | 2026-11-13 | Testo, campi e tag ereditano la visibilità del file; la ricerca non rivela documenti non visibili all'utente | Coerenza con le decisioni 17-19 | - |
| 28 | 2026-11-13 | Coda continua a bassa priorità, con finestra notturna per i carichi grossi | Con il solo notturno un documento caricato al mattino si cerca il giorno dopo | Dopo aver misurato i volumi |
| 29 | 2026-11-13 | Interfaccia in sola lingua italiana, ma con i testi marcati come traducibili | La multilingua non è un requisito attuale; predisporla ora costa poco, aggiungerla dopo significa riscrivere le pagine | Se compaiono utenti che non lavorano in italiano |
| 30 | 2026-11-13 | La traduzione automatica del browser è disattivata su tutte le pagine | In alcuni browser invia il testo della pagina a server esterni; inoltre traduce anche ragioni sociali, descrizioni e tag | - |
| 31 | 2026-11-13 | La multilingua riguarda i documenti: OCR e modello devono leggere almeno italiano e inglese e ricondurre i campi agli stessi tipi e tag | Fatture e DDT dei fornitori esteri non sono in italiano | Quando sono note le lingue effettive dei documenti |
