# TODO

Elenco unico delle cose da fare. Ogni passo si chiude con questo file aggiornato.

## Subito, al primo avvio

- [ ] Eseguire `makemigrations`, verificare che l'applicazione parta e salvare
      nel repository le migrazioni generate (non sono state generate in fase di
      scrittura perché Django non era eseguibile in quell'ambiente)
- [ ] Eseguire `python manage.py test`

## Passi di sviluppo

- [x] 1. Scheletro: accesso, utenti, ruoli, amministratore, tabelle di decodifica
- [ ] 1b. Generatore di dati sintetici (aziende e transazioni finte, con anomalie inserite apposta)
- [ ] 2. Caricamento: invio del file, salvataggio sul server, scheda del file
- [ ] 3. Importazione: viste azienda, attività, dati economici, transazioni, con validazione
- [ ] 4. Primo calcolo: due o tre indici, gruppi con la regola versione 1, Z-score robusto
- [ ] 5. Schermata di analisi: elenco ordinato e scheda dell'azienda con la spiegazione
- [ ] 6. Configurazione: regole e soglie versionate, modificabili dall'interfaccia
- [ ] Più avanti: risoluzione delle identità, lettura dei documenti, analisi di rete e GNN

## Da fare sullo scheletro

- [ ] Caricare la classificazione delle attività economiche dal file ufficiale
      (ora ci sono solo poche voci di esempio)
- [ ] Rivedere le classi di dipendenti e di fatturato sui dati reali
- [ ] Secondo fattore di autenticazione
- [ ] Registro degli accessi e delle operazioni
- [ ] Decidere se l'amministratore degli utenti può vedere i dati delle aziende

## Domande aperte per l'amministrazione

- [ ] Quale ufficio è il destinatario e con quale base giuridica accede ai dati?
- [ ] Con quali criteri si selezionano i gruppi di operazioni (periodo, azienda,
      settore, strumento) e con quali limiti di volume?
- [ ] Quante aziende attive conta il Paese e quanti settori superano le 30 aziende?
- [ ] Qual è la soglia di controllo oggi in vigore e come è cambiata negli ultimi anni?
- [ ] Esiste un archivio di casi confermati utilizzabile per la verifica?
- [ ] Quale classificazione delle attività economiche è in uso (NACE o variante nazionale)?
- [ ] Il codice e l'installazione devono stare su infrastruttura dell'amministrazione?
