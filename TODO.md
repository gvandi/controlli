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
- [ ] 3. Fascicoli d'indagine e visibilità: va fatto prima del caricamento, perché ogni
      pagina che elenca file o documenti deve già rispettarla (DECISIONI.md, n. 17-19)
- [ ] 4. Caricamento: invio del file, salvataggio sul server, scheda del file, natura del
      file (estratto di dati o documenti), visibilità
- [ ] 5. Generatore di dati sintetici (soggetti, transazioni ed elenchi di documenti finti,
      con anomalie inserite apposta)
- [ ] 6. Importazione degli estratti: soggetti, attività, dati economici, transazioni, con validazione
- [ ] 7. Importazione degli elenchi di documenti: documento, righe, soggetti con ruolo,
      collegamenti tra documenti, confronto tra copie dello stesso documento
- [ ] 8. Primo calcolo: due o tre indici, gruppi con la regola versione 1, Z-score robusto
- [ ] 9. Schermata di analisi: elenco ordinato e scheda dell'azienda con la spiegazione
- [ ] 10. Configurazione: regole e soglie versionate, modificabili dall'interfaccia
- [ ] Più avanti: risoluzione delle identità, lettura dei documenti, analisi di rete e GNN

## Da fare sullo scheletro

- [ ] Caricare la classificazione delle attività economiche dal file ufficiale
      (ora ci sono solo poche voci di esempio)
- [ ] Rivedere le classi di dipendenti e di fatturato sui dati reali
- [ ] Secondo fattore di autenticazione
- [ ] Registro degli accessi e delle operazioni
- [ ] Decidere se l'amministratore degli utenti può vedere i dati delle aziende
- [ ] Cifra di controllo della partita IVA italiana (ora si verifica solo la lunghezza)

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
- [ ] Quale regola definisce la popolazione analizzata (per esempio: tutte le aziende con COE attivo)?
- [ ] Quale classificazione delle attività economiche è in uso (NACE o variante nazionale)?
- [ ] Il codice e l'installazione devono stare su infrastruttura dell'amministrazione?
