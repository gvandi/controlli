# Ambienti e rilasci

Regole e lista di controllo per portare una versione in produzione mentre gli
utenti lavorano. Corrisponde al capitolo 10 della relazione; le scelte sono in
[DECISIONI.md](DECISIONI.md), voci 32-37.

## Ambienti

| Ambiente | Dove | Dati | Chi lo usa |
| --- | --- | --- | --- |
| Sviluppo | Macchina dello sviluppatore | Sintetici | Chi scrive il codice |
| Collaudo | Server, configurato come la produzione | Sintetici | Chi prova le versioni nuove |
| Produzione | Server dell'amministrazione | Reali | Gli utenti |

## Regole

1. **Nessuna prova in produzione.** Una versione arriva in produzione solo dopo
   essere stata installata e provata in collaudo.
2. **Ambienti isolati.** Ogni ambiente ha database, cartella dei file caricati,
   file `.env` e chiave segreta propri. Una sessione aperta in un ambiente non
   vale negli altri.
3. **Nessun dato reale fuori dalla produzione.** La produzione non si copia in
   collaudo né in sviluppo.
4. **Ambiente sempre visibile.** Ogni pagina di sviluppo e collaudo mostra una
   fascia colorata con il nome dell'ambiente.
5. **Le sessioni sopravvivono agli aggiornamenti.** Sono conservate nel database:
   un riavvio dell'applicazione non disconnette nessuno.
6. **Modifiche al database in due tempi.** Una versione aggiunge tabelle e campi;
   ciò che non serve più si toglie in una versione successiva.
7. **Aggiornamenti annunciati.** Un avviso in testa alle pagine precede ogni
   rilascio. Se serve un fermo, pagina di manutenzione e non un errore.
8. **Utenti collegati sotto controllo.** L'amministratore vede chi è collegato e
   da quanto è inattivo, e può chiudere una sessione.
9. **Elaborazioni fermate in modo ordinato.** Un file a metà elaborazione torna in
   coda, non resta in errore.
10. **Funzioni in prova solo per chi è autorizzato**, tramite un diritto apposito.
11. **Nessun accesso a nome di un altro utente.**
12. **Ogni rilascio è registrato** in fondo a questo file.

## Lista di controllo del rilascio

Va seguita per intero. Un punto non soddisfatto ferma il rilascio.

### Prima, in collaudo

- [ ] La versione ha un numero ed è unita in `main`
- [ ] I test automatici terminano con `OK`
- [ ] Le migrazioni sono generate e salvate nel repository
- [ ] Le migrazioni solo aggiungono: nessuna tabella o campo usato dalla versione
      in esecuzione viene tolto o rinominato
- [ ] La versione è installata in collaudo con la stessa procedura della produzione
- [ ] È stata provata in collaudo da una persona diversa da chi l'ha scritta
- [ ] In collaudo ci sono solo dati sintetici
- [ ] Nel repository non ci sono credenziali né file caricati
- [ ] `TODO.md` e `DECISIONI.md` sono aggiornati

### Preparazione in produzione

- [ ] Copia di sicurezza del database e dei file caricati eseguita
- [ ] Ripristino della copia provato almeno una volta fuori dalla produzione
- [ ] Procedura di ritorno alla versione precedente scritta e a portata di mano
- [ ] Momento scelto guardando l'elenco degli utenti collegati
- [ ] Avviso pubblicato con almeno un giorno lavorativo di anticipo
- [ ] Se serve un fermo, durata comunicata nell'avviso

### Durante il rilascio

- [ ] Coda dei documenti fermata in modo ordinato
- [ ] Pagina di manutenzione attivata, se è previsto un fermo
- [ ] Codice portato alla versione stabilita: `git fetch && git checkout <versione>`
- [ ] Dipendenze aggiornate: `pip install -r requirements.txt`
- [ ] Migrazioni applicate: `python manage.py migrate`
- [ ] Ruoli e decodifiche allineati: `python manage.py crea_ruoli` e
      `python manage.py carica_decodifiche`
- [ ] Applicazione riavviata
- [ ] Coda dei documenti riavviata
- [ ] Pagina di manutenzione tolta

### Subito dopo

- [ ] La pagina di accesso si apre e mostra la nuova versione
- [ ] Un utente già collegato prima del rilascio continua a lavorare senza rifare
      l'accesso
- [ ] Le pagine principali si aprono senza errori
- [ ] I file rimasti in coda riprendono l'elaborazione
- [ ] Registro degli errori controllato per la prima mezz'ora
- [ ] Avviso di aggiornamento rimosso
- [ ] Rilascio annotato nel registro qui sotto

### Se qualcosa va storto

- [ ] Errore che blocca il lavoro degli utenti: si torna alla versione precedente,
      senza tentare correzioni in produzione
- [ ] Il ritorno indietro riguarda solo il codice, perché le migrazioni hanno solo
      aggiunto
- [ ] Il ripristino della copia di sicurezza è l'ultima risorsa e richiede una
      decisione esplicita: fa perdere il lavoro svolto dopo la copia
- [ ] Utenti avvisati dell'accaduto
- [ ] Causa annotata nel registro prima di riprovare

## Funzione in prova in produzione

- [ ] La funzione è già stata provata in collaudo
- [ ] È legata a un diritto apposito, spento per tutti all'inizio
- [ ] Non modifica né cancella dati esistenti
- [ ] Gli utenti che la provano sono stati scelti e avvisati
- [ ] È fissata una data entro cui la funzione viene estesa a tutti oppure tolta

## Stato attuale

Molti punti della lista presuppongono funzioni non ancora scritte: fascia
dell'ambiente, avviso di aggiornamento, pagina di manutenzione, elenco degli
utenti collegati, numero di versione, coda dei documenti. Sono in
[TODO.md](TODO.md). Finché non esistono, i punti corrispondenti si eseguono a
mano o si annotano come "non applicabile".

## Registro dei rilasci

| Data | Versione | Ambiente | Eseguito da | Esito | Note |
| --- | --- | --- | --- | --- | --- |
