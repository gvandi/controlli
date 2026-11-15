# TODO

Elenco unico delle cose da fare. Ogni passo si chiude con questo file aggiornato.

## Subito, al primo avvio

- [ ] Eseguire `makemigrations`, verificare che l'applicazione parta e salvare
      nel repository le migrazioni generate (non sono state generate in fase di
      scrittura perché Django non era eseguibile in quell'ambiente)
- [ ] Eseguire `python manage.py test`

## Passi di sviluppo

L'analisi lavora su due livelli (DECISIONI.md, n. 46-47). Il livello 1 usa dati
disponibili per tutte le aziende e si costruisce per primo.

- [x] 1. Scheletro: accesso, utenti, ruoli, amministratore, tabelle di decodifica
- [x] 1c. Tabelle di decodifica per soggetti e documenti: tipi di identificativo, tipi di
      documento, ruoli nel documento

### Livello 1: selezione, su tutte le aziende

- [ ] 2. Anagrafica unica dei soggetti e loro identificativi fiscali (DECISIONI.md, n. 13-14)
- [ ] 3. Importazione dei dati della Camera di Commercio: soggetti, ATECO, oggetto sociale,
      soci, amministratori e cariche, dipendenti, bilanci XBRL, verbali di assemblea
- [ ] 4. Importazione di import ed export: per azienda, trimestre, verso, paese, importo,
      classe di merce da 0 a 9; tabella di decodifica delle classi di merce e loro
      corrispondenza con i settori ATECO (DECISIONI.md, n. 51)
- [ ] 5. Generatore di dati sintetici di livello 1: aziende, bilanci, import ed export, con
      profili di triangolazione e di false fatturazioni inseriti apposta
- [ ] 6. Indici di livello 1 (margine, export su import, struttura rispetto ai volumi, scarti
      tra fonti, paesi, cambi societari), gruppi con la regola versione 1, Z-score robusto
- [ ] 7. Elenco delle segnalazioni e scheda dell'azienda con gruppo, indici e spiegazione
- [ ] 8. Verifica dell'attendibilità della classe di merce: quota nella classe residuale,
      stabilità nel tempo, coerenza con l'ATECO (DECISIONI.md, n. 52). Il confronto con le
      fatture arriva dopo il passo 15
- [ ] 9. Configurazione: regole, soglie e classificazioni versionate, modificabili
      dall'interfaccia

### Livello 2: approfondimento, sulle aziende prese in carico

- [ ] 10. Fascicoli d'indagine e visibilità; valutazione della segnalazione; origine del
      controllo all'apertura; esito con tipo di irregolarità (DECISIONI.md, n. 17-19, 42, 50)
- [ ] 11. Caricamento, sempre dentro un fascicolo: invio del file, salvataggio sul server,
      scheda del file, natura del file, stato di elaborazione (DECISIONI.md, n. 48)
- [ ] 12. Importazione degli elenchi di documenti: documento, righe, soggetti con ruolo,
      collegamenti tra documenti, confronto tra copie dello stesso documento
- [ ] 13. Elaborazione fuori linea dei documenti (DECISIONI.md, n. 21-28):
  - [ ] coda di elaborazione continua a bassa priorità, con finestra notturna per i carichi grossi
  - [ ] riconoscimento della natura del file: XML, PDF con testo, immagine
  - [ ] divisione degli elenchi in documenti singoli
  - [ ] testo completo: estrazione diretta o OCR, e ricerca per parola
  - [ ] campi strutturati con regole (identificativi, date, importi) e modello locale
  - [ ] verifica: ogni valore estratto deve comparire nel testo; sotto soglia, revisione manuale
  - [ ] tag da vocabolario controllato, più tag proposti da promuovere
  - [ ] risultati versionati per motore OCR, modello e versione
  - [ ] documenti in più lingue: almeno italiano e inglese (DECISIONI.md, n. 31)
- [ ] 14. Classificazione dei prodotti (DECISIONI.md, n. 40-41): tabella gerarchica delle
      categorie, corrispondenza con ATECO e licenze, classificazione delle righe, revisione
      manuale che diventa regola, paniere dell'azienda
- [ ] 15. Indici di livello 2 sui documenti: ricarico, bilancio delle quantità, catena
      DDT-fattura, destinazione della merce, vendite fuori licenza. Si confrontano con il
      dichiarato, con i riferimenti e con i rilievi, non con le aziende simili
- [ ] 16. Rilievi degli ufficiali: verbale firmato conservato intatto, dati del rilievo,
      documenti raccolti, confronto tra rilevato, dichiarato e pubblicizzato (DECISIONI.md, n. 43)

### Tra i due livelli

- [ ] 17. Proiezione degli esiti sul livello 1 e indicazione dei settori su cui dirigere gli
      approfondimenti (DECISIONI.md, n. 49-50). Richiede origine del controllo, esiti anche
      negativi e una quota di controlli casuali
- [ ] Più avanti: risoluzione delle identità, rete degli scambi, Isolation Forest, GNN

## Ambienti e rilasci (RILASCIO.md, DECISIONI.md n. 32-37)

- [ ] Nome dell'ambiente in `.env` (`CONTROLLI_AMBIENTE`) e fascia colorata sulle pagine
      di sviluppo e collaudo
- [ ] Numero di versione dell'applicazione, mostrato nella pagina di accesso
- [ ] Avviso di aggiornamento in testa alle pagine, gestito dall'amministratore
- [ ] Pagina di manutenzione
- [ ] Elenco degli utenti collegati con ultimo accesso e chiusura della sessione
- [ ] Diritto per le funzioni in prova
- [ ] Copia di sicurezza di database e file caricati, con prova di ripristino
- [ ] Preparare l'ambiente di collaudo
- [ ] Fermare e riavviare in modo ordinato la coda dei documenti (dipende dal passo 8)

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
- [ ] In che formato e con quale frequenza la Camera di Commercio espone i dati?
- [x] I documenti disponibili coprono tutte le aziende o solo quelle già oggetto di controllo?
      Risposta: Camera di Commercio e import-export per tutte; fatture, DDT e rilievi solo
      per quelle prese in carico
- [ ] I dati di import ed export comprendono gli scambi con l'Italia?
- [ ] Quale classificazione è il codice di merce da 0 a 9, e chi lo assegna?
- [ ] Esiste un archivio dei controlli passati con il loro esito, da caricare come base per
      la proiezione?
- [ ] L'ufficio può riservare una quota di controlli a settori scelti a caso?
- [ ] Le fatture riportano la modalità di pagamento?
- [ ] Per i prodotti si adotta una nomenclatura esistente o una tabella propria?
- [ ] Chi definisce quali categorie di prodotto sono ammesse da ciascuna licenza?
- [ ] Come si registra in un rilievo ciò che viene pubblicizzato in rete?
- [ ] Con quale strumento sono firmati i verbali, e la firma va verificata dal sistema?
- [ ] Quale regola definisce la popolazione analizzata (per esempio: tutte le aziende con COE attivo)?
- [ ] Quale classificazione delle attività economiche è in uso (NACE o variante nazionale)?
- [ ] Il codice e l'installazione devono stare su infrastruttura dell'amministrazione?
- [ ] Chi esegue i rilasci in produzione e chi prova le versioni in collaudo?
- [ ] Quanto preavviso serve agli utenti e in quali orari si può aggiornare?
