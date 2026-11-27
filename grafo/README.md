# App grafo - versione 22

Analisi di rete del progetto controlli UAE: una GNN assegna a ogni società un punteggio di
rischio per tipo di irregolarità; i risultati si interrogano da una chat.

**Stato: prototipo su dati simulati.** Dalla versione 19 è un'app Django dell'applicativo e
usa il suo database PostgreSQL. Dalla versione 20 la chat si collega dalla rete, riconosce
l'utente e registra sessioni, richieste e mappe; dalla 21 l'utente si riconosce con
l'accesso OAuth 2.0 dal browser. Non applica ancora i fascicoli: cosa manca è
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
| `dati_reali.py` | calcolo | Fotografia dei dati reali dall'archivio (soggetti e rapporti dai documenti confermati) | - |
| `interrogazione.py` | interrogazione | Query, testi di contesto, cinque strumenti | - |
| `sessioni.py` | sessioni | Parametri dell'amministratore, token, sessioni, registro | - |
| `protocollo_mcp.py` | server | Regole del protocollo MCP (JSON-RPC), senza Django | - |
| `servizio_mcp.py` | server | Esegue uno strumento e lo registra; strumenti `mappa`, `scheda` e `spazio` | - |
| `calcolatrice.py` | server | Strumento `calcola`: aritmetica esatta, senza Django né database | - |
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
python manage.py grafo_consulta "Quali sono le 3 società più rischiose?"
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
| `/o/authorize/`, `/o/token/`, `/o/register/` | la chat e il browser | Accesso OAuth 2.0 (django-oauth-toolkit) |
| `/.well-known/oauth-...` | la chat | Documenti con cui la chat scopre dove chiedere l'accesso |
| `/grafo/collegamento/` | Analista | Istruzioni per la chat, token personali di ripiego, elenco delle proprie mappe |
| `/grafo/mappe/N/` | chi ha chiesto la mappa N | Mostra la mappa, dopo l'accesso all'applicativo |
| `/grafo/cruscotto/` | Amministratore | Versioni, calcoli presenti, sessioni, parametri |

Dopo l'aggiornamento: `pip install -r requirements.txt` (la versione 21 aggiunge
`django-oauth-toolkit`), `python manage.py migrate` e `python manage.py crea_ruoli`.

## Collegare la chat (Unsloth Studio)

1. In Studio aggiungere un server MCP di tipo HTTP con l'indirizzo
   `https://NOME-DEL-SERVER/grafo/mcp/`, attivare **Use OAuth sign-in** e non aggiungere
   intestazioni personalizzate.
2. Al primo collegamento si apre il browser: l'analista accede all'applicativo con il proprio
   utente e preme **Autorizza**. Da quel momento la chat lavora a suo nome.
3. Incollare `grafo/prompt_di_sistema.txt` come prompt di sistema della chat.

### Cosa succede dietro (OAuth 2.0)

```
chat --POST /grafo/mcp/ senza accesso-->  401 + indirizzo del documento della risorsa
chat --GET /.well-known/oauth-protected-resource/grafo/mcp-->  quale server autorizza
chat --GET /.well-known/oauth-authorization-server/o-->  indirizzi di accesso, token, registrazione
chat --POST /o/register/-->  la chat si registra come client
browser --/o/authorize/-->  accesso con l'utente dell'applicativo + consenso
chat --POST /o/token/ (codice + PKCE)-->  token legato all'utente e al servizio MCP
chat --POST /grafo/mcp/ con il token-->  sessione a nome dell'utente
```

- Il token vale per il solo ambito `grafo` e per il solo servizio MCP; dura 8 ore e la chat
  lo rinnova da sola per 7 giorni (`CONTROLLI_OAUTH_ORE_TOKEN`, `CONTROLLI_OAUTH_GIORNI_RINNOVO`
  nel file `.env`).
- Client registrati, autorizzazioni e token si vedono e si revocano dall'amministrazione
  (sezione della libreria OAuth).
- L'accesso non basta: serve il diritto `usa_chat` (ruolo Analista), altrimenti la risposta è 403.

**Fuori dalle prove il servizio va raggiunto solo in HTTPS.** Se gli analisti raggiungono
l'applicativo con un nome diverso da quello che il server vede (proxy), impostare
`CONTROLLI_URL_PUBBLICO` e gli header del proxy (`SECURE_PROXY_SSL_HEADER`): il token è legato
all'indirizzo del servizio e un indirizzo visto in modo diverso lo fa rifiutare.

### Ripiego: token personale

Se la chat non riesce a usare l'accesso OAuth: pagina **Collegamento alla chat**, creare un
token, e in Studio usare l'intestazione `Authorization: Bearer IL-TOKEN` con l'accesso OAuth
disattivato. L'amministratore può spegnere questa via dal cruscotto
(`token_personali_ammessi = no`).

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
