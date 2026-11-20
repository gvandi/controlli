# controlli_grafo - versione 17

Componente grafo del progetto controlli UAE: una GNN assegna a ogni azienda un punteggio
di rischio per tipo di irregolarità; i risultati si interrogano da una chat.

Fino alla versione 15 era un solo file. Dalla 16 è un solo progetto con più punti di avvio.

**Stato: prototipo su dati simulati.** Non è ancora un'app Django: ha un proprio database
SQLite e non conosce utenti, ruoli né fascicoli dell'applicativo. Cosa manca per integrarlo
è in [TODO.md](../TODO.md); le scelte fatte sono in [DECISIONI.md](../DECISIONI.md), n. 32-39.

## Le parti

```
calcolo.py + scrittura.py  -->  database  <--  interrogazione.py  <--  server_mcp.py  <--  chat
        (PyTorch)                (SQLite)        (senza PyTorch)   <--  mappa.py
```

| File | Parte | Cosa fa | Dipendenze esterne |
|---|---|---|---|
| `controlli_grafo/contratto.py` | contratto | Tassonomia, valori ammessi, schema del database, versioni | nessuna |
| `controlli_grafo/calcolo.py` | calcolo | Grafo, addestramento, punteggi, GNNExplainer | torch, torch_geometric, scikit-learn |
| `controlli_grafo/scrittura.py` | calcolo | Scrive nel database ciò che il calcolo produce | nessuna |
| `controlli_grafo/interrogazione.py` | interrogazione | Query, testi di contesto, quattro strumenti | nessuna |
| `controlli_grafo/server_mcp.py` | server | Espone gli strumenti alla chat | mcp |
| `controlli_grafo/mappa.py` | mappa | Report e mappa investigativa in HTML | networkx, pyvis |

## Installazione

```
pip install -r requirements.txt       (dalla cartella prototipo_grafo)
```

PyTorch e PyTorch Geometric servono solo al calcolo: chi usa soltanto interrogazione,
server o prove può installare le sole righe corrispondenti del file.

## Comandi (dalla cartella prototipo_grafo)

```
python -m controlli_grafo.calcolo                  calcolo completo: scrive database e modello
python -m controlli_grafo.calcolo spiegazioni      calcola le spiegazioni in coda
python -m controlli_grafo.interrogazione "Quali sono le 3 aziende più rischiose?"
python -m controlli_grafo.mappa                    scrive mappa_investigativa.html
python -m controlli_grafo.server_mcp               avvia il server per la chat
python -m unittest prove.prova_cablaggio -v        prova di cablaggio (senza PyTorch)
python aggiorna_intestazioni.py                    ricopia le novità in testa ai file
```

File prodotti nella cartella di lavoro: `controlli_grafo.sqlite`, `modello_grafo.pt`,
`mappa_investigativa.html`. I primi due si spostano con le variabili d'ambiente
`CONTROLLI_DB` e `CONTROLLI_MODELLO`.

## Collegare la chat (Unsloth Studio)

1. Installare la libreria: `pip install "mcp[cli]"` (versione 1 o 2).
2. Nelle impostazioni MCP di Studio aggiungere un server con comando
   `python -m controlli_grafo.server_mcp`, cartella di lavoro = `prototipo_grafo`.
3. Incollare `prompt_di_sistema.txt` come prompt di sistema della chat.
4. Spuntare il server nel menu MCP della chat.

## I contratti: cosa tiene cablate le parti

| Contratto | Dove è scritto | Chi lo scrive | Chi lo legge |
|---|---|---|---|
| Schema del database | `contratto.SCHEMA_DB` | calcolo | interrogazione |
| Tassonomia, popolazioni | `contratto.py` | - | tutti |
| Forma della spiegazione | commento in `contratto.py` | calcolo | interrogazione, mappa |
| Nomi degli strumenti | `contratto.NOMI_STRUMENTI` | interrogazione | server, chat |
| Coda delle spiegazioni | tabella `richiesta_spiegazione` | interrogazione | calcolo |

## Regole per le modifiche

1. Ciò che serve a più parti si scrive solo in `contratto.py`, mai copiato.
2. Le dipendenze vanno in una sola direzione (vedi schema). Solo `calcolo.py` usa PyTorch.
3. Se cambia `SCHEMA_DB`, aumentare `VERSIONE_SCHEMA`: la libreria rifiuta gli archivi vecchi.
4. Ogni novità si scrive in `NOVITA.md` con la sigla della versione, poi si lancia
   `aggiorna_intestazioni.py`. Le intestazioni dei file non si toccano a mano.
5. A ogni nuova versione: aggiornare `VERSIONE_CODICE` e la riga "Versione corrente" del registro.
6. Prima di consegnare: `python -m unittest prove.prova_cablaggio`. Controlla letture, strumenti,
   coda, compatibilità, direzione delle dipendenze e allineamento fra registro e intestazioni.
