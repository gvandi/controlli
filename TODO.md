# TODO

Elenco unico delle cose da fare. Ogni passo si chiude con questo file aggiornato.

## Subito, al primo avvio

- [ ] Eseguire `makemigrations`, verificare che l'applicazione parta e salvare
      nel repository le migrazioni generate (non sono state generate in fase di
      scrittura perché Django non era eseguibile in quell'ambiente)
- [ ] Eseguire `python manage.py test`

## Passi di sviluppo

- [x] 1. Scheletro: accesso, utenti, ruoli, amministratore, tabelle di decodifica
- [x] 1c. Tabelle di decodifica per soggetti e documenti: tipi di identificativo, tipi di documento, ruoli nel documento
- [ ] 2. Anagrafica unica dei soggetti e loro identificativi fiscali (DECISIONI.md, n. 13-14)
  - [x] versione minima (app `soggetti`): soggetto con chiave interna, identificativi con
        tipo e valore normalizzato, soggetti provvisori
  - [ ] dati dell'anagrafica ufficiale (attività, forma giuridica, dimensione), storia
        degli identificativi, unione di due soggetti che risultano lo stesso
- [x] 3. Faldoni, fascicoli e visibilità (app `archivio`; DECISIONI.md, n. 17-19 e 62-63):
      faldoni Caricamenti, Aziende, Indagini; indagini visibili solo alle persone assegnate
  - [ ] **Prima esecuzione**: `migrate`, `crea_ruoli`, `test soggetti archivio`. In fase di
        scrittura Django non era disponibile: modelli, migrazioni, pagine e prove non sono
        mai stati eseguiti
  - [ ] faldone Sanzioni, visibile a tutti (DECISIONI.md, n. 62): un fascicolo per sanzione,
        con tipo di irregolarità, data e verbale; è il dato che oggi l'analisi di rete simula
  - [ ] chiusura di un'indagine; registro di chi ha aperto quale fascicolo
- [ ] 4. Caricamento (DECISIONI.md, n. 64-68)
  - [x] parte 2: fascicolo di caricamento in bozza, scelta di file, di una cartella o di un
        file ZIP (con limiti), percorso originale e file omonimi, file salvati una volta sola
        per impronta, metadati sul fascicolo ereditati dai file, campi COE (principale e
        collegati), visibilità generale o legata a un'indagine, conferma, annullamento,
        scarico dell'originale, registro
  - [ ] **Prima esecuzione della parte 2**: `migrate`, `crea_ruoli`, `test archivio`, e una
        prova vera dal browser con una cartella e con uno ZIP. In fase di scrittura sono
        stati provati solo `deposito.py` e `ingresso.py` (senza Django); modelli, migrazione
        0002, regole, pagine e prove non sono mai stati eseguiti
  - [ ] verificare dal browser che la scelta di una cartella conservi i percorsi (dipende
        dal browser: provato solo il lato server)
  - [ ] limiti del server web davanti all'applicativo (dimensione massima di una richiesta)
        quando ci sarà; caricamenti molto grandi a pezzi, con ripresa
  - [ ] controllo antivirus dei file ricevuti
  - [x] parte 3 (app `elaborazione`; DECISIONI.md, n. 70-75): coda di elaborazione con
        priorità, tentativi e ripresa; riconoscimento del file; catalogo delle entità;
        testo per pagina; entità con file, pagina e citazione; entità fuori catalogo e
        loro promozione; revisione; collegamento dei file ai fascicoli delle aziende;
        scheda del soggetto
  - [ ] **Prima esecuzione della parte 3**: `migrate`, `crea_ruoli`, `carica_catalogo`,
        `test elaborazione archivio`, poi `elabora_coda` su un caricamento di prova. In
        fase di scrittura sono stati provati `riconoscimento.py`, `regole.py` e
        `lettura_modello.py` (con un modello finto); modelli, migrazioni, coda, pagine e
        prove Django non sono mai stati eseguiti
  - [ ] **Prima lettura vera di una scansione** con il modello locale
        (`pip install -r elaborazione/requirements-lettura.txt`, `poppler-utils`): non è
        mai stata provata. Da misurare: quanto sbaglia la trascrizione, quanto dura una
        pagina, se le risposte restano entro il limite di lunghezza
  - [ ] avvio notturno di `elabora_coda --minuti N` (cron o servizio), un solo processo alla volta
- [ ] 5. Generatore di dati sintetici (soggetti, transazioni ed elenchi di documenti finti,
      con anomalie inserite apposta)
- [ ] 6. Importazione degli estratti: soggetti, attività, dati economici, transazioni, con validazione
- [ ] 7. Importazione degli elenchi di documenti: documento, righe, soggetti con ruolo,
      collegamenti tra documenti, confronto tra copie dello stesso documento
- [ ] 8. Elaborazione fuori linea dei documenti (DECISIONI.md, n. 21-28 e 70-75):
  - [x] coda di elaborazione con limite di tempo, per la finestra notturna
  - [x] riconoscimento della natura del file dai primi byte: PDF, immagine, XML, testo
  - [x] testo completo per pagina, da scansione, con il modello visivo locale
  - [x] identificativi, date, importi, email e siti con regole fisse
  - [x] entità proposte dal modello, verificate contro il testo; revisione manuale
  - [x] risultati con motore, modello e versione del prompt
  - [x] file di testo: regole più entità proposte dal modello; lettura parziale se il modello manca
  - [ ] PDF che contengono già il testo: estrazione diretta, senza OCR (oggi passano dal modello)
  - [ ] fatture elettroniche in XML: lettura dei campi come dati (oggi solo le regole sul testo)
  - [ ] ricerca per parola nel testo delle pagine
  - [ ] divisione degli elenchi in documenti singoli
  - [ ] tag da vocabolario controllato
  - [ ] documenti in più lingue: almeno italiano e inglese (DECISIONI.md, n. 31)
  - [ ] unione di due soggetti che risultano lo stesso (oggi il COE e la partita IVA della
        stessa azienda creano due soggetti distinti)
  - [ ] verbali ispettivi: dall'evento "accertamento" all'irregolarità accertata (faldone Sanzioni)
  - [x] documento commerciale e parti con ruolo (mittente, destinatario, vettore, luogo di
        destinazione), numero, data e totale; ruoli confermati da una persona (DECISIONI.md, n. 80)
  - [ ] **prima esecuzione** di documento e parti: `migrate`, `test elaborazione archivio`,
        poi un DDT vero dalla coda (il prompt è alla versione 2 e chiede più cose al modello)
  - [ ] righe dei documenti (merci, servizi, quantità, prezzi)
  - [ ] aggiungere a mano un documento o una parte che il modello non ha visto
  - [x] fotografia dei dati reali per l'analisi di rete: soggetti dell'anagrafica e rapporti dai
        documenti confermati (`grafo_dati_reali`, DECISIONI.md n. 85)
  - [ ] **prima esecuzione** di `grafo_dati_reali`
  - [x] dati dell'azienda per periodo, importati da CSV (`importa_anagrafica`, DECISIONI.md n. 86)
  - [x] indice di rischio a regole come calcolo a sé sui dati reali (`calcola_indici`, n. 87)
  - [ ] **prima esecuzione**: `migrate`, `crea_ruoli`, `carica_regole`, `importa_anagrafica`,
        `calcola_indici`, `grafo_versioni`, poi gli strumenti della chat
  - [x] spazio degli indici: aziende in tre dimensioni, indice a regole e z-score robusto (`/indici/spazio/`, n. 89)
  - [x] spazio degli indici provato in Chrome senza interfaccia su una copia statica della pagina (500 aziende
        simulate, rapporti inventati): disegno, ricerca del COE, linee dei rapporti, rotazione
  - [ ] **prima esecuzione** dello spazio degli indici dentro l'applicativo (pagina resa da Django)
  - [x] rapporti fra aziende nello spazio degli indici e strumento `spazio` della chat (DECISIONI.md n. 91)
  - [x] classifica delle aziende più rischiose per criteri distinti: regole, scostamento, rapporti, GNN (n. 92)
  - [ ] importazione di documenti da CSV, per avere abbastanza rapporti da provare (oggi c'è un solo DDT)
  - [ ] **definire i quattro tipi di irregolarità**: che cosa sono, come si accertano, riferimento normativo
        (oggi sono solo nomi: DECISIONI.md n. 90); poi una tabella gestita dal Configuratore
  - [ ] importazione dell'anagrafica dall'interfaccia (oggi solo da comando)
  - [ ] CSV con COE e partita IVA insieme: oggi vale il COE, la partita IVA non viene aggiunta al soggetto
  - [ ] regole su altri dati (forma giuridica, età dell'azienda, rapporti nel grafo)
  - [ ] tipo di relazione nello schema del grafo: vettore, persone e recapiti in comune
  - [ ] irregolarità accertate reali (etichette per l'addestramento)
  - [ ] cancellazione di un file: i dati già fotografati restano nelle fotografie precedenti
  - [ ] rielaborazione esplicita di un gruppo di file quando il modello migliora (mai automatica)
  - [x] cancellazione definitiva di un file e dei dati che ne derivano, con diritto apposito
        (ruolo "Responsabile dei dati"; DECISIONI.md, n. 77)
  - [ ] **Prima esecuzione della cancellazione**: `migrate`, `crea_ruoli`, `test elaborazione archivio`;
        scritta senza poterla eseguire
  - [ ] cancellazione e analisi di rete: oggi il grafo usa dati simulati e non contiene nulla
        dei file; quando userà le entità, iscrivere in `archivio.cancellazione.ALLA_CANCELLAZIONE`
        il ritiro dei dati e segnare da ricalcolare le esecuzioni che li contenevano
  - [ ] dopo una cancellazione, le entità di altri file segnate "da rivedere" per un conflitto con
        il file cancellato restano in attesa: farle tornare a posto da sole
  - [ ] cancellazione definitiva di un intero caricamento in un solo passo
- [ ] 9. Primo calcolo: due o tre indici, gruppi con la regola versione 1, Z-score robusto
- [ ] 10. Schermata di analisi: elenco ordinato e scheda dell'azienda con la spiegazione
- [ ] 11. Configurazione: regole e soglie versionate, modificabili dall'interfaccia
- [ ] Più avanti: risoluzione delle identità, controlli sui documenti, analisi di rete e GNN

## App grafo (`grafo/`, versione 22)

- [x] Prototipo su dati simulati: GNN con punteggi per tipo di irregolarità, libreria di
      interrogazione, server MCP per la chat, report e mappa
- [x] Società indicate per nome, ricerca per indicatore
- [x] Portato nell'applicativo come app Django su PostgreSQL, con chiave interna del
      soggetto (DECISIONI.md, n. 14) e migrazione nel repository
- [x] Regole di compatibilità (grafo/COMPATIBILITA.md): quattro versioni, lettore
      tollerante, documenti JSON auto-descrittivi, coesistenza di calcoli e dati
- [ ] **Prima esecuzione della versione 19**: `migrate`, `test grafo`, `grafo_calcolo`,
      `grafo_server_mcp`. In fase di scrittura Django e psycopg non erano disponibili:
      le query sono state provate su PostgreSQL 16, modelli, migrazione, scrittura e
      comandi non sono mai stati eseguiti
- [ ] Verificare con `makemigrations grafo --check` che la migrazione scritta a mano
      coincida con i modelli (lo fa anche la prova MigrazioniTest)
- [ ] Fissare le versioni in `grafo/requirements-calcolo.txt`
- [ ] Misurare quante volte il modello della chat sceglie lo strumento giusto
      (30-50 domande con risposta attesa)
- [ ] Decidere se le spiegazioni restano in coda o vanno calcolate al momento della domanda
- [ ] Ricerca delle società per nome: con i dati reali va rivista (decine di migliaia di
      nomi, ragioni sociali simili)
- [ ] Ricerca per indicatore: oggi guarda solo le società con spiegazione già calcolata
- [ ] Fondere `grafo.Soggetto` con il modello dei soggetti dell'applicativo quando arriverà
      la gestione documentale
- [ ] Riservatezza: le interrogazioni riconoscono l'utente ma non applicano ancora i
      fascicoli (DECISIONI.md, n. 17-19): chi ha il diritto usa_chat vede tutte le società
- [x] Sessioni di più analisti (versione 20): servizio MCP su HTTP con token personale,
      sessioni numerate, registro delle richieste, mappe separate per sessione e visibili
      solo a chi le ha chieste, cruscotto dell'amministratore
- [ ] **Prima esecuzione della versione 20**: `migrate`, `crea_ruoli`, `test grafo`,
      collegamento di Studio via HTTP. In fase di scrittura Django non era disponibile:
      sono stati provati il protocollo (senza Django) e le query delle restrizioni su
      PostgreSQL 16; modelli, migrazione 0002, sessioni, viste, pagine e prove nuove non
      sono mai stati eseguiti
- [ ] Verificare che Unsloth Studio parli con il servizio (versione del protocollo,
      intestazione Mcp-Session-Id, risposta JSON senza flusso SSE)
- [x] Versione 21: accesso OAuth 2.0 dal browser (django-oauth-toolkit 3.4), con
      registrazione automatica della chat; token personali come ripiego disattivabile
- [ ] **Prima esecuzione della versione 21**: `pip install -r requirements.txt`, `migrate`,
      `test grafo`, collegamento di Studio con "Use OAuth sign-in". In fase di scrittura
      né Django né la libreria OAuth erano disponibili: la configurazione è stata scritta
      leggendo il sorgente della libreria 3.4.0 e non è mai stata eseguita
- [ ] Verificare che Studio completi il percorso (scoperta, registrazione, ritorno dal
      browser, rinnovo del token) e con quale indirizzo di ritorno si registra
- [ ] Registrazione dei client oggi aperta a chiunque raggiunga il server: restringerla
      (rete, token iniziale o elenco degli indirizzi di ritorno ammessi) prima dell'uso reale,
      e ripulire periodicamente i client mai usati
- [ ] Pagina in cui l'analista vede e revoca le proprie autorizzazioni OAuth (oggi solo
      dall'amministrazione)
- [ ] Spegnere i token personali (`token_personali_ammessi = no`) quando OAuth è collaudato,
      poi togliere codice e tabella in un rilascio successivo (Contract)
- [ ] `python manage.py cleartokens` periodico per eliminare i token OAuth scaduti
- [ ] Installazione in rete: HTTPS davanti all'applicativo (il token viaggia a ogni
      richiesta), `CONTROLLI_ALLOWED_HOSTS`, `CONTROLLI_URL_PUBBLICO`
- [ ] Misurare quante volte il modello ricopia la domanda dell'ispettore nel parametro
      `domanda`; se poche, il registro resta fatto di strumento e parametri
- [ ] Conservazione di sessioni, richieste e file delle mappe: per quanto tenerli, e chi
      può leggere il registro (vedi "Punti aperti sulla riservatezza")
- [ ] Funzioni in prova per pochi utenti (Feature Flags) e ambiente di prova
- [ ] Conservazione delle fotografie dei dati: per quanto tenerle
- [ ] Sostituire i dati simulati con quelli estratti dai documenti (dopo i passi 6-8),
      con documenti JSON auto-descrittivi e schemi versionati nel repository
- [ ] Etichette dai verbali ispettivi: estrazione proposta dal modello, con citazione del
      testo, e conferma dell'analista prima dell'uso in addestramento
- [ ] Punteggio non supervisionato su tutta la popolazione (passo 9) come feature della GNN
## Da fare sullo scheletro

- [ ] Caricare la classificazione delle attività economiche dal file ufficiale
      (ora ci sono solo poche voci di esempio)
- [ ] Rivedere le classi di dipendenti e di fatturato sui dati reali
- [ ] Secondo fattore di autenticazione
- [ ] Registro degli accessi e delle operazioni
- [ ] Decidere se l'amministratore degli utenti può vedere i dati delle aziende
- [ ] Cifra di controllo della partita IVA italiana (ora si verifica solo la lunghezza)
- [x] Testi dell'interfaccia marcati come traducibili; traduzione automatica del browser disattivata
- [ ] Ogni nuova pagina: `{% load i18n %}` e testi dentro `{% translate %}`; nel codice Python, `gettext_lazy`

## Punti aperti sulla riservatezza

- [ ] Se un analista lascia l'ufficio, chi prende in carico i suoi fascicoli?
- [ ] Due analisti che lavorano sullo stesso soggetto senza saperlo: va segnalato, e come,
      senza rivelare il contenuto dei fascicoli?
- [ ] Chi può leggere il registro degli accessi?

## Domande aperte per l'amministrazione

- [ ] Quale ufficio è il destinatario e con quale base giuridica accede ai dati?
- [ ] Con quali criteri si selezionano i gruppi di operazioni (periodo, azienda,
      settore, strumento) e con quali limiti di volume?
- [ ] Quante aziende attive conta il Paese e quanti settori superano le 30 aziende?
- [ ] Qual è la soglia di controllo oggi in vigore e come è cambiata negli ultimi anni?
- [ ] Esiste un archivio di casi confermati utilizzabile per la verifica?
- [ ] Qual è il formato esatto del COE e con quali prefissi compare nei file?
- [ ] In che formato arrivano gli elenchi di documenti (CSV, XML della fattura elettronica, altro)?
- [ ] Quanti documenti al giorno e di quante pagine? Decide macchina e tempi dell'elaborazione
- [ ] Quale macchina è disponibile per OCR e modello locale (scheda grafica, memoria)?
- [ ] Quale regola definisce la popolazione analizzata (per esempio: tutte le aziende con COE attivo)?
- [ ] Quale classificazione delle attività economiche è in uso (NACE o variante nazionale)?
- [ ] Il codice e l'installazione devono stare su infrastruttura dell'amministrazione?
