# Regole di compatibilità dell'app grafo

Scopo: permettere a versioni diverse di codice e di dati di coesistere, e modificare
il database senza fermare chi lo sta usando. Valgono per l'app `grafo`; sono scritte
per essere estese al resto dell'applicativo quando avrà dati reali.

## 1. Le quattro versioni

Ognuna risponde a una domanda diversa. Sono dichiarate in `contratto.py`.

| Versione | Domanda | Formato | Dove si legge |
|---|---|---|---|
| Progetto (`VERSIONE_CODICE`) | Quale rilascio è installato? | numero intero: `21`, `22` | `contratto.py`, `NOVITA.md` |
| Schema (`VERSIONE_SCHEMA`) | Questo lettore può aprire l'archivio? | due numeri: `4.2` | tabella `grafo_info`, scritta dalle migrazioni |
| Calcolo (`VERSIONE_CALCOLO`) | Questi punteggi sono confrontabili? | due numeri: `1.0` | tabella `grafo_esecuzione` |
| Dati | Su quale fotografia dei dati? | contatore: 1, 2, 3 | tabella `grafo_versione_dati` |

La versione del progetto è solo provenienza: **non blocca mai nulla**. Chi decide se si
può leggere è la versione dello schema; chi decide se i punteggi vanno ricalcolati è la
versione del calcolo. Per questo dalla versione 20 è un numero intero: non essendo mai
confrontata con un intervallo, il secondo numero non serviva.

### Quando sale quale numero

| Modifica | Versione | Numero |
|---|---|---|
| Nuova tabella, nuova colonna facoltativa o con valore predefinito, nuovo indice | schema | secondo (4.0 → 4.1) |
| Tabella o colonna tolta o rinominata, cambio di tipo o di significato | schema | primo (4.1 → 5.0) |
| Correzione che non altera i punteggi (messaggi, prestazioni) | calcolo | nessuno |
| Cambio che altera i punteggi restando confrontabili (iperparametri, epoche) | calcolo | secondo (1.0 → 1.1) |
| Cambio di modello, di features o dei tipi di irregolarità | calcolo | primo (1.1 → 2.0) |
| Campo aggiunto a un documento JSON | documento | secondo |
| Campo tolto o con significato diverso in un documento JSON | documento | primo |

### Chi legge dichiara cosa gli serve

Un lettore non pretende una versione identica alla sua: dichiara un intervallo con
l'operatore `~=` di PEP 440 ("rilascio compatibile").

```python
SCHEMA_RICHIESTO = "~=4.0"    # almeno 4.0, e comunque 4.x
```

Con questa riga il lettore accetta 4.0, 4.1, 4.7 e rifiuta 3.9 (gli manca qualcosa) e
5.0 (qualcosa è stato tolto). Se un lettore comincia a usare una colonna aggiunta nella
4.2, la sua dichiarazione diventa `~=4.2`.

### Restrizioni dell'amministratore

Gli intervalli scritti in `contratto.py` dicono ciò che il codice **sa** leggere: sono il
limite, e si spostano solo con un rilascio. Dal cruscotto (`/grafo/cruscotto/`)
l'amministratore può aggiungere una restrizione per ciascuno, salvata in `grafo_parametro`:

| Parametro | Si aggiunge a | Uso tipico |
|---|---|---|
| `restrizione_schema` | `SCHEMA_RICHIESTO` | di norma vuoto |
| `restrizione_calcolo` | `CALCOLO_ACCETTATO` | `==1.0` per restare sul calcolo 1.0 mentre si valuta l'1.1 |
| `restrizione_spiegazione` | `SPIEGAZIONE_ACCETTATA` | di norma vuoto |

Una versione è accettata se soddisfa **entrambe** le condizioni (`contratto.accettata()`).
Quindi una restrizione può restringere, mai allargare: nessuna impostazione fa leggere al
codice ciò che non conosce. Il cruscotto rifiuta una restrizione che escluderebbe lo schema
attuale o tutti i calcoli presenti; una restrizione scritta male (possibile solo
modificando la tabella a mano) viene ignorata.

## 2. Lettore tollerante

Dichiarare `~=4.0` è una promessa. Si mantiene così:

1. **Le colonne si nominano una per una.** Mai `SELECT *`: una colonna in più non deve
   cambiare ciò che il codice riceve.
2. **Tabelle e colonne sconosciute si ignorano.**
3. **Nei documenti JSON si leggono i campi conosciuti**, si ignorano quelli in più e si dà
   un valore predefinito a quelli facoltativi (`.get(campo, predefinito)`).
4. **Un documento di versione non accettata non si interpreta**: vale come mancante.
5. **Valori sconosciuti in un campo a elenco chiuso** (per esempio un nuovo tipo di
   irregolarità) si saltano, non fanno fallire la lettura.

In `interrogazione.py` tutte le letture passano da `_righe()` e tutte le spiegazioni da
`_normalizza_spiegazione()`: sono i due punti in cui queste regole sono applicate.

## 3. Documenti JSON auto-descrittivi

Ogni documento salvato in un campo JSON dichiara tipo e versione nel campo `schema`:

```json
{"schema": "spiegazione/1.0", "soggetto": 1012, "tipo_irregolarita": "triangolazione", "features": [], "relazioni": []}
```

Chi scrive rifiuta di salvare un documento che non si dichiara. Chi legge accetta
`~=1.0`. I dati estratti dai documenti con il modello linguistico (passi 6-8 del
progetto) dovranno seguire la stessa regola fin dal primo giorno, perché resteranno
nell'archivio per anni.

Forma di `spiegazione/1.0`:

| Campo | Obbligatorio | Contenuto |
|---|---|---|
| `schema` | sì | `"spiegazione/1.0"` |
| `soggetto` | sì | chiave interna del soggetto (non l'indice del nodo) |
| `tipo_irregolarita` | sì | uno dei tipi di `contratto.TIPI_IRREGOLARITA` |
| `features` | no | elenco di `{indice, tipo, descrizione, peso}`; obbligatorio solo `indice` |
| `relazioni` | no | elenco di `[[soggetto_a, soggetto_b], importanza]` |
| `impatto_testo`, `impatto_strutturati` | no | peso medio delle due parti del vettore |

## 4. Coesistenza di calcoli e dati

- **Dati nuovi non cancellano i vecchi.** Si aggiunge una fotografia (`VersioneDati`).
  Dati identici a una fotografia esistente non ne creano una seconda.
- **Un calcolo è una coppia** (versione del calcolo, fotografia dei dati). Coppie diverse
  convivono: `calcolo 1.0 / dati 1`, `calcolo 1.0 / dati 2`, `calcolo 1.1 / dati 2`.
- **Ripetere il calcolo sulla stessa coppia la sostituisce**, con punteggi, spiegazioni e
  coda. È l'unico caso in cui dei risultati vengono eliminati.
- **I lettori usano** la fotografia più recente fra le esecuzioni di un calcolo che
  accettano (`CALCOLO_ACCETTATO`). Una coppia precisa si sceglie con le variabili
  d'ambiente `GRAFO_VERSIONE_CALCOLO` e `GRAFO_VERSIONE_DATI`, per i confronti.
- **Il soggetto ha una chiave interna stabile** fra una fotografia e l'altra: il numero
  di una società non cambia quando cambiano i dati o il calcolo.

`python manage.py grafo_versioni` mostra versioni ed esecuzioni presenti, e quale è in uso.

## 5. Modificare lo schema: Expand, Migrate, Contract

Lo strumento è quello di Django: una migrazione nel repository per ogni modifica. Mai
modificare le tabelle a mano, mai cancellare e ricreare il database.

Una modifica che toglie o rinomina si fa in **tre rilasci distinti**:

| Fase | Cosa si rilascia | Schema |
|---|---|---|
| 1. Expand | Migrazione che aggiunge il nuovo (colonna, tabella) accanto al vecchio. Il codice esistente continua a funzionare senza modifiche. | 4.0 → 4.1 |
| 2. Migrate | Chi scrive riempie il nuovo; i dati esistenti vengono copiati dal vecchio al nuovo con una migrazione di dati. I lettori passano al nuovo e dichiarano `~=4.1`. | 4.1 |
| 3. Contract | Solo quando nessun lettore usa più il vecchio: migrazione che lo toglie. | 4.1 → 5.0 |

Fra la fase 1 e la 3 codice vecchio e codice nuovo possono girare insieme. La scrittura
contemporanea su vecchio e nuovo (dual-write) serve solo se il rilascio di chi scrive e
quello di chi legge non possono essere coordinati: con un calcolo notturno e pochi
utenti di norma non occorre.

La versione 20 è il primo caso reale: la migrazione `0002_sessioni` aggiunge cinque tabelle
(4.0 → 4.1) senza toccare le esistenti, e il codice della versione 19 continua a funzionare
sul database aggiornato. La versione 21 fa lo stesso con `0003_accesso_oauth` (4.1 → 4.2): due
colonne con valore predefinito. Il parametro `token_personali_ammessi` è il primo
interruttore del sistema: permette di spegnere la via vecchia (token copiati a mano) solo
quando la nuova (OAuth) è collaudata, senza rilasciare codice.

### Lista di controllo per una modifica di schema

1. Stabilire se la modifica aggiunge o toglie (tabella del punto 1).
2. Se toglie: fermarsi e pianificare le tre fasi. Non si fa in un solo rilascio.
3. Modificare `models.py` ed eseguire `python manage.py makemigrations grafo`.
4. Nella migrazione generata aggiungere il passo che aggiorna `versione_schema`
   (come in `0001_iniziale.py`: costante `VERSIONE_SCHEMA` e `RunPython`).
5. Aggiornare `VERSIONE_SCHEMA` in `contratto.py` con lo stesso valore.
6. Aggiornare `SCHEMA_RICHIESTO` solo se un lettore usa davvero il nuovo.
7. Scrivere la novità in `NOVITA.md` ed eseguire `python grafo/aggiorna_intestazioni.py`.
8. Eseguire `python manage.py test grafo`: controlla che migrazioni e modelli
   coincidano, che lo schema scritto sia quello dichiarato e che il lettore lo accetti.
9. Salvare la migrazione nel repository insieme al codice.

## 6. Rilasci

- **Ordine**: prima le migrazioni di espansione, poi il codice. Mai il contrario.
- **Funzioni in prova** (Feature Flags): una funzione nuova si rilascia spenta e si
  accende per pochi utenti. Non è ancora realizzato. La tabella `grafo_parametro` e il
  cruscotto (versione 20) sono il posto in cui andranno gli interruttori (vedi TODO.md).
- **Tornare indietro**: una migrazione di espansione si può lasciare applicata anche
  tornando al codice precedente, proprio perché il codice vecchio la tollera.

## 7. Cosa non è coperto

- **Schema Registry**: non c'è un servizio dedicato. Gli schemi dei documenti JSON sono
  descritti in questo file e controllati da `contratto.documento_leggibile()`. Un
  registro di schemi JSON nel repository andrà introdotto con l'estrazione dai documenti.
- **Conservazione**: le fotografie dei dati non vengono mai eliminate. Con dati reali va
  deciso per quanto tenerle e come gestire un documento corretto o ritirato.
- **Resto dell'applicativo**: `utenti` e `decodifiche` non hanno ancora le migrazioni nel
  repository (vedi TODO.md): finché mancano, queste regole per loro non sono applicabili.
