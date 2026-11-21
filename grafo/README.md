# App grafo - versione 19.0

Analisi di rete del progetto controlli UAE: una GNN assegna a ogni azienda un punteggio di
rischio per tipo di irregolarità; i risultati si interrogano da una chat.

**Stato: prototipo su dati simulati.** Dalla versione 19 è un'app Django dell'applicativo e
usa il suo database PostgreSQL. Non applica ancora utenti, ruoli e fascicoli: cosa manca è in
[TODO.md](../TODO.md).

Le regole per far coesistere versioni diverse di codice e dati, e per modificare lo schema,
sono in [COMPATIBILITA.md](COMPATIBILITA.md).

## Le parti

```
calcolo.py + scrittura.py  -->  PostgreSQL  <--  interrogazione.py  <--  server_mcp.py  <--  chat
        (PyTorch)             (models.py)        (senza PyTorch)     <--  mappa.py
```

| File | Parte | Cosa fa | Dipendenze oltre a Django |
|---|---|---|---|
| `contratto.py` | contratto | Versioni, regole di compatibilità, valori ammessi | packaging |
| `models.py`, `migrations/` | contratto | Schema del database | - |
| `calcolo.py` | calcolo | Grafo, addestramento, punteggi, GNNExplainer | torch, torch_geometric, scikit-learn |
| `scrittura.py` | calcolo | Scrive nel database ciò che il calcolo produce | - |
| `interrogazione.py` | interrogazione | Query, testi di contesto, cinque strumenti | - |
| `server_mcp.py` | server | Espone gli strumenti alla chat | mcp |
| `mappa.py` | mappa | Report e mappa investigativa in HTML | networkx, pyvis |

Le dipendenze di calcolo, mappa e server sono in `requirements-calcolo.txt`: non servono
all'applicativo web né alle prove.

## Comandi (dalla cartella del repository)

```
python manage.py migrate                          crea o aggiorna le tabelle
python manage.py grafo_calcolo                    calcolo completo (richiede PyTorch)
python manage.py grafo_calcolo --spiegazioni      calcola le spiegazioni in coda
python manage.py grafo_versioni                   versioni, esecuzioni presenti e quale è in uso
python manage.py grafo_consulta "Quali sono le 3 aziende più rischiose?"
python manage.py grafo_mappa --soggetto "Rossi Costruzioni"
python manage.py grafo_server_mcp                 avvia il server per la chat
python manage.py test grafo                       prova di cablaggio (senza PyTorch)
python grafo/aggiorna_intestazioni.py             ricopia le novità in testa ai file
```

## File fuori dal repository

La cartella `dati_grafo/` (creata al primo uso, esclusa da git) contiene:

- `elenco_aziende.json` e `dizionario_descrizioni.json`, da copiarci **prima** del calcolo;
- i modelli salvati, uno per ogni coppia calcolo/dati;
- le mappe generate.

Senza i due file JSON il prototipo funziona con nomi generici e senza ricerca per indicatore.

## Collegare la chat (Unsloth Studio)

1. `pip install -r grafo/requirements-calcolo.txt` (per la sola chat basta `mcp[cli]`).
2. Creare uno script di avvio, per esempio `avvia_server_mcp.sh` fuori dal repository:

   ```bash
   #!/bin/bash
   cd /percorso/del/repository
   exec .venv/bin/python manage.py grafo_server_mcp
   ```

3. In Studio: server MCP con comando = percorso dello script. Serve
   `UNSLOTH_STUDIO_ALLOW_STDIO_MCP=1` nell'ambiente in cui parte Studio.
4. Incollare `grafo/prompt_di_sistema.txt` come prompt di sistema della chat.

## Regole per le modifiche

1. Ciò che serve a più parti si scrive solo in `contratto.py` (valori) o `models.py` (schema).
2. Le dipendenze vanno in una sola direzione (vedi schema). Solo `calcolo.py` usa PyTorch.
3. Ogni modifica di schema segue la lista di controllo di `COMPATIBILITA.md`.
4. Ogni novità si scrive in `NOVITA.md` con la sigla della versione, poi si lancia
   `aggiorna_intestazioni.py`. Le intestazioni dei file non si toccano a mano.
5. Prima di consegnare: `python manage.py test grafo`.
