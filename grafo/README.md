# App grafo - versione 20

Analisi di rete del progetto controlli UAE: una GNN assegna a ogni azienda un punteggio di
rischio per tipo di irregolarità; i risultati si interrogano da una chat.

**Stato: prototipo su dati simulati.** Dalla versione 19 è un'app Django dell'applicativo e
usa il suo database PostgreSQL. Dalla versione 20 la chat si collega dalla rete, riconosce
l'utente e registra sessioni, richieste e mappe. Non applica ancora i fascicoli: cosa manca è
in [TODO.md](../TODO.md).

Le regole per far coesistere versioni diverse di codice e dati, e per modificare lo schema,
sono in [COMPATIBILITA.md](COMPATIBILITA.md).

## Le parti

```
calcolo.py + scrittura.py  -->  PostgreSQL  <--  interrogazione.py  <--  mappa.py
        (PyTorch)             (models.py)               ^                   ^
                                   ^                    |                   |
                              sessioni.py  <------  servizio_mcp.py  -------+
                                                        ^
                              protocollo_mcp.py  <--  views.py  <--  chat (HTTP, con token)
                                                      server_mcp.py  <--  chat (stdio, solo prove)
```

| File | Parte | Cosa fa | Dipendenze oltre a Django |
|---|---|---|---|
| `contratto.py` | contratto | Versioni, regole di compatibilità, valori ammessi | packaging |
| `models.py`, `migrations/` | contratto | Schema del database | - |
| `calcolo.py` | calcolo | Grafo, addestramento, punteggi, GNNExplainer | torch, torch_geometric, scikit-learn |
| `scrittura.py` | calcolo | Scrive nel database ciò che il calcolo produce | - |
| `interrogazione.py` | interrogazione | Query, testi di contesto, cinque strumenti | - |
| `sessioni.py` | sessioni | Parametri dell'amministratore, token, sessioni, registro | - |
| `protocollo_mcp.py` | server | Regole del protocollo MCP (JSON-RPC), senza Django | - |
| `servizio_mcp.py` | server | Esegue uno strumento e lo registra; strumento `mappa` | - |
| `views.py`, `urls.py`, `templates/` | server | Servizio HTTP, pagina della mappa, collegamento, cruscotto | - |
| `server_mcp.py` | server | Trasporto stdio per le prove su un solo computer | mcp |
| `mappa.py` | mappa | Report e mappa investigativa in HTML | networkx, pyvis |

Le dipendenze di calcolo, mappa e server stdio sono in `requirements-calcolo.txt`: non servono
alle prove. **Sul computer dove gira l'applicativo web servono `networkx` e `pyvis`**, perché
è lì che lo strumento `mappa` scrive il file.

## Comandi (dalla cartella del repository)

```
python manage.py migrate                          crea o aggiorna le tabelle
python manage.py grafo_calcolo                    calcolo completo (richiede PyTorch)
python manage.py grafo_calcolo --spiegazioni      calcola le spiegazioni in coda
python manage.py grafo_versioni                   versioni, esecuzioni presenti e quale è in uso
python manage.py grafo_consulta "Quali sono le 3 aziende più rischiose?"
python manage.py grafo_mappa --soggetto "Rossi Costruzioni"
python manage.py grafo_token UTENTE               crea un token per la chat (mostrato una volta)
python manage.py grafo_server_mcp                 server stdio, solo per prove su un computer
python manage.py test grafo                       prova di cablaggio (senza PyTorch)
python grafo/aggiorna_intestazioni.py             ricopia le novità in testa ai file
```

## File fuori dal repository

La cartella `dati_grafo/` (creata al primo uso, esclusa da git) contiene:

- `elenco_aziende.json` e `dizionario_descrizioni.json`, da copiarci **prima** del calcolo;
- i modelli salvati, uno per ogni coppia calcolo/dati;
- le mappe generate.

Senza i due file JSON il prototipo funziona con nomi generici e senza ricerca per indicatore.

## Indirizzi dell'applicativo

| Indirizzo | Per chi | Cosa fa |
|---|---|---|
| `/grafo/mcp/` | la chat | Servizio MCP: una POST per messaggio, con il token nell'intestazione |
| `/grafo/collegamento/` | Analista | Crea e revoca i propri token; elenco delle proprie mappe |
| `/grafo/mappe/N/` | chi ha chiesto la mappa N | Mostra la mappa, dopo l'accesso all'applicativo |
| `/grafo/cruscotto/` | Amministratore | Versioni, calcoli presenti, sessioni, parametri |

Dopo l'aggiornamento: `python manage.py migrate` e `python manage.py crea_ruoli` (assegna i
nuovi diritti ai ruoli Analista e Amministratore).

## Collegare la chat (Unsloth Studio)

1. L'analista accede all'applicativo, apre **Collegamento alla chat** e crea un token. Il
   token viene mostrato una volta sola.
2. In Studio aggiunge un server MCP di tipo HTTP con l'indirizzo indicato nella pagina
   (`https://NOME-DEL-SERVER/grafo/mcp/`) e l'intestazione `Authorization: Bearer IL-TOKEN`.
3. Incolla `grafo/prompt_di_sistema.txt` come prompt di sistema della chat.

Il token viaggia a ogni richiesta: **fuori dalle prove il servizio va raggiunto solo in
HTTPS**. Con `CONTROLLI_DEBUG=0` l'applicativo rifiuta già le richieste in chiaro. Se gli
analisti raggiungono l'applicativo con un nome diverso da quello che il server vede (proxy),
impostare `CONTROLLI_URL_PUBBLICO` nel file `.env`: è l'indirizzo usato nei collegamenti alle
mappe.

### Sessioni

- Una sessione nasce quando la chat si collega; il **numero di sessione** è assegnato dal
  database (tabella `grafo_sessione`).
- Ogni chiamata a uno strumento è una riga di `grafo_richiesta`: strumento, parametri, esito,
  coppia calcolo/dati e, quando il modello la ricopia, la domanda dell'ispettore.
- Dopo il periodo di inattività scelto dall'amministratore la sessione viene chiusa; la
  richiesta successiva ne apre una nuova senza che l'analista debba ricollegarsi.
- Ogni mappa prodotta è una riga di `grafo_mappa` con il nome del file, che contiene il numero
  di sessione.

### Prova su un solo computer, senza token

Resta disponibile il trasporto stdio (`python manage.py grafo_server_mcp`, con
`UNSLOTH_STUDIO_ALLOW_STDIO_MCP=1`): non riconosce l'utente e non registra nulla.

## Regole per le modifiche

1. Ciò che serve a più parti si scrive solo in `contratto.py` (valori) o `models.py` (schema).
2. Le dipendenze vanno in una sola direzione (vedi schema). Solo `calcolo.py` usa PyTorch.
3. Ogni modifica di schema segue la lista di controllo di `COMPATIBILITA.md`.
4. Ogni novità si scrive in `NOVITA.md` con la sigla della versione, poi si lancia
   `aggiorna_intestazioni.py`. Le intestazioni dei file non si toccano a mano.
5. Prima di consegnare: `python manage.py test grafo`.
