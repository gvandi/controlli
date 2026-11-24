# Legenda dei comandi (`python manage.py ...`)

Tutti i comandi si lanciano dalla cartella del progetto, con l'ambiente attivo:

```
cd ~/Documenti/controlli
source .venv/bin/activate
```

Per l'aiuto di un comando: `python manage.py NOME --help`.

## Dopo ogni `git pull`

| Che cosa voglio fare | Comando |
|---|---|
| Aggiornare le tabelle del database | `python manage.py migrate` |
| Aggiornare ruoli e diritti (quando cambiano) | `python manage.py crea_ruoli` |
| Eseguire le prove | `python manage.py test` oppure, per alcune app, `python manage.py test elaborazione archivio` |
| Avviare l'applicativo | `python manage.py runserver` |
| Avviare l'applicativo insieme al processo che esegue i lavori lanciati dall'interfaccia | `./avvia.sh` |
| Avviare solo il processo dei lavori (per esempio su un'altra macchina) | `python manage.py esegui_lavori --tipi elabora_file` |

## Prima installazione

| Che cosa voglio fare | Comando |
|---|---|
| Creare l'utente amministratore | `python manage.py createsuperuser` |
| Caricare le decodifiche (classi ISTAT, tipi di identificativo, attività) | `python manage.py carica_decodifiche` |
| Caricare il catalogo delle entità da estrarre | `python manage.py carica_catalogo` |
| Caricare le regole di rischio di partenza | `python manage.py carica_regole` |

Questi tre "carica" si possono rilanciare: non toccano ciò che è già stato modificato a mano.

## File caricati: lettura ed estrazione

| Che cosa voglio fare | Comando |
|---|---|
| Elaborare tutti i file in attesa | `python manage.py elabora_coda` |
| Elaborarne al massimo N (per le prove) | `python manage.py elabora_coda --massimo 1` |
| Lavorare per un tempo limitato (processo notturno) | `python manage.py elabora_coda --minuti 240` |

Serve il modello locale avviato in Unsloth Studio e la chiave nella variabile
`UNSLOTH_STUDIO_AUTH_TOKEN` (o nel file `.env`). Senza modello i file di testo passano
dalle sole regole e restano da elaborare; le scansioni aspettano.

## Anagrafica delle aziende e indice a regole

| Che cosa voglio fare | Comando |
|---|---|
| Importare attività, dipendenti e fatturato per periodo da un CSV | `python manage.py importa_anagrafica percorso/file.csv --fonte "da dove viene"` |
| Calcolare l'indice di rischio a regole sui dati reali | `python manage.py calcola_indici` |
| Rimettere in ordine i nomi delle aziende (prevale l'anagrafica ufficiale) | `python manage.py allinea_denominazioni` |

`calcola_indici` aggiorna da solo la fotografia dei dati reali: dopo, la chat usa i dati reali.
Un file di esempio con dati inventati è in `indici/esempio_anagrafica.csv`.

## Analisi di rete (app grafo)

| Che cosa voglio fare | Comando |
|---|---|
| Vedere versioni di codice, schema e calcolo, e quale coppia calcolo/dati è in uso | `python manage.py grafo_versioni` |
| Prendere la fotografia dei dati reali senza calcolare nulla | `python manage.py grafo_dati_reali` |
| Addestrare la GNN e calcolare i punteggi (oggi sui dati simulati) | `python manage.py grafo_calcolo` |
| Calcolare le spiegazioni richieste dalla chat e rimaste in coda | `python manage.py grafo_calcolo --spiegazioni` |
| Fare una domanda senza la chat (prova degli strumenti) | `python manage.py grafo_consulta "quali sono le aziende più rischiose?"` |
| Produrre la mappa investigativa di una società | `python manage.py grafo_mappa --soggetto "nome o numero"` |

`grafo_calcolo` richiede le librerie di `grafo/requirements-calcolo.txt` (torch e simili).

## Chat (Unsloth Studio)

| Che cosa voglio fare | Comando |
|---|---|
| Creare un token personale per un utente (ripiego: la via normale è l'accesso OAuth dal browser) | `python manage.py grafo_token NOME_UTENTE --etichetta "pc ufficio"` |
| Avviare il server MCP su un solo computer, senza rete (solo prove) | `python manage.py grafo_server_mcp` |

Il servizio MCP vero non ha un comando: è una pagina dell'applicativo
(`/grafo/mcp/`) ed è attivo quando gira `runserver`.

## Sequenze tipiche

Provare un documento dall'inizio alla fine:

```
python manage.py runserver            # in un terminale; caricare e confermare il file dall'interfaccia
python manage.py elabora_coda --massimo 1     # in un altro terminale
# dall'interfaccia: "Testo ed entità estratte", controllare ruoli ed entità, chiudere la revisione
python manage.py calcola_indici       # porta documenti e aziende nell'analisi di rete
python manage.py grafo_versioni       # controlla quale coppia calcolo/dati è in uso
```

Aggiornare i dati delle aziende:

```
python manage.py importa_anagrafica nuovo_file.csv --fonte "Camera di Commercio 2026"
python manage.py calcola_indici
```

## Lo stesso, dall'interfaccia

L'Amministratore può lanciare dalla pagina iniziale (o da `/lavori/`) l'elaborazione dei file,
l'importazione dell'anagrafica da CSV, il calcolo degli indici, il riallineamento delle denominazioni,
la fotografia dei dati reali, il calcolo della GNN e delle spiegazioni. I pulsanti registrano la
richiesta: la esegue il processo `esegui_lavori`, che deve essere acceso.

## Che cosa NON si fa con un comando

- Caricare file, rivedere entità e ruoli, cancellare un file: dall'interfaccia (`/archivio/`).
- Modificare regole di rischio, catalogo delle entità, decodifiche, utenti e ruoli: dall'amministrazione (`/admin/`).
- Parametri e restrizioni dell'analisi di rete: dal cruscotto (`/grafo/cruscotto/`).
- Vedere le aziende in tre dimensioni, con indice a regole e scostamenti: dalla pagina `/indici/spazio/`.
