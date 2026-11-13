# controlli
applicativo controlli per UAE

Applicazione web multiutente per l'analisi AML delle transazioni commerciali:
confronta ogni azienda con le aziende che svolgono la stessa attività e segnala
quelle che se ne discostano.

Stato: **passo 1, scheletro** (accesso, utenti, ruoli, tabelle di decodifica).
I passi successivi sono in [TODO.md](TODO.md); le scelte fatte finora in
[DECISIONI.md](DECISIONI.md); ambienti e lista di controllo dei rilasci in
[RILASCIO.md](RILASCIO.md).

## Requisiti

- Python 3.12 o successivo
- PostgreSQL 15 o successivo

## Primo avvio

```bash
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env                 # poi modificare i valori
createdb controlli                   # o crearlo da pgAdmin

python manage.py makemigrations utenti decodifiche
python manage.py migrate
python manage.py crea_ruoli
python manage.py carica_decodifiche
python manage.py createsuperuser
python manage.py runserver
```

Poi aprire http://127.0.0.1:8000/ e accedere con l'utente appena creato.
Utenti, ruoli e tabelle di decodifica si gestiscono da http://127.0.0.1:8000/admin/.

Per ogni nuovo utente: assegnare uno o più ruoli (campo "Gruppi") e, se deve
entrare nell'area di amministrazione, spuntare "Privilegi di staff".

`makemigrations` serve solo la prima volta: le migrazioni generate vanno poi
salvate nel repository (vedi TODO.md).

## Test

```bash
python manage.py test
```

## Struttura

| Cartella | Contenuto |
| --- | --- |
| `config/` | Impostazioni del progetto Django |
| `utenti/` | Utente, ruoli e diritti |
| `decodifiche/` | Tabelle di decodifica (attività, classi dimensionali, forma giuridica, modello di business) |
| `templates/` | Pagine HTML |
| `dati_caricati/` | File caricati dagli utenti. **Esclusa dal repository** |

## Regole del repository

- Solo codice: nessun dato reale, nessun file caricato per l'analisi.
- Nessuna credenziale: password e chiavi stanno in `.env`, escluso dal repository.
