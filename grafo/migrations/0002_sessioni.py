"""Schema 4.1: parametri dell'amministratore, token, sessioni, richieste e mappe.

ESPANSIONE (fase 1 di Expand/Migrate/Contract): aggiunge cinque tabelle e non
tocca quelle esistenti. Il codice della versione 19 continua a funzionare su
questo schema, perché il suo lettore accetta "~=4.0".

Scritta a mano (in fase di scrittura Django non era disponibile): la prova
grafo.tests.MigrazioniTest verifica che coincida con models.py.
"""
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

VERSIONE_SCHEMA = "4.1"
VERSIONE_PRECEDENTE = "4.0"

# Copia di contratto.PARAMETRI al momento di questa migrazione: una migrazione non
# importa il codice dell'app, che nel frattempo può cambiare.
PARAMETRI = {
    "minuti_inattivita_sessione": (
        "30",
        "Minuti senza richieste dopo i quali una sessione della chat viene chiusa (da 1 a 1440).",
    ),
    "restrizione_schema": (
        "",
        "Restrizione sulle versioni dello schema accettate, in aggiunta a quella del codice. "
        "Vuoto = nessuna. Esempio: ==4.1",
    ),
    "restrizione_calcolo": (
        "",
        "Restrizione sulle versioni del calcolo usate dalle interrogazioni, in aggiunta a quella "
        "del codice. Vuoto = nessuna. Esempio: ==1.0",
    ),
    "restrizione_spiegazione": (
        "",
        "Restrizione sulle versioni dei documenti di spiegazione accettate, in aggiunta a quella "
        "del codice. Vuoto = nessuna. Esempio: ==1.0",
    ),
}


def avanti(apps, schema_editor):
    apps.get_model("grafo", "InfoArchivio").objects.update_or_create(
        chiave="versione_schema", defaults={"valore": VERSIONE_SCHEMA}
    )
    Parametro = apps.get_model("grafo", "Parametro")
    for nome, (valore, descrizione) in PARAMETRI.items():
        Parametro.objects.get_or_create(nome=nome, defaults={"valore": valore, "descrizione": descrizione})


def indietro(apps, schema_editor):
    apps.get_model("grafo", "InfoArchivio").objects.update_or_create(
        chiave="versione_schema", defaults={"valore": VERSIONE_PRECEDENTE}
    )


CASCADE = django.db.models.deletion.CASCADE
PROTECT = django.db.models.deletion.PROTECT
SET_NULL = django.db.models.deletion.SET_NULL
UTENTE = settings.AUTH_USER_MODEL


def _id():
    return ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID"))


def _fk(modello, alla_cancellazione):
    return models.ForeignKey(on_delete=alla_cancellazione, related_name="+", to=modello)


def _fk_facoltativa(modello):
    return models.ForeignKey(blank=True, null=True, on_delete=SET_NULL, related_name="+", to=modello)


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("grafo", "0001_iniziale"),
    ]

    operations = [
        migrations.CreateModel(
            name="Parametro",
            fields=[
                ("nome", models.CharField(max_length=60, primary_key=True, serialize=False)),
                ("valore", models.CharField(blank=True, default="", max_length=255)),
                ("descrizione", models.TextField(blank=True, default="")),
                ("modificato_il", models.DateTimeField(auto_now=True)),
                ("modificato_da", _fk_facoltativa(UTENTE)),
            ],
            options={"db_table": "grafo_parametro"},
        ),
        migrations.CreateModel(
            name="TokenAccesso",
            fields=[
                _id(),
                ("impronta", models.CharField(max_length=64, unique=True)),
                ("etichetta", models.CharField(blank=True, default="", max_length=80)),
                ("creato_il", models.DateTimeField(auto_now_add=True)),
                ("ultimo_uso", models.DateTimeField(blank=True, null=True)),
                ("revocato_il", models.DateTimeField(blank=True, null=True)),
                ("utente", _fk(UTENTE, CASCADE)),
            ],
            options={"db_table": "grafo_token"},
        ),
        migrations.CreateModel(
            name="Sessione",
            fields=[
                _id(),
                ("id_connessione", models.CharField(blank=True, db_index=True, default="", max_length=120)),
                ("iniziata_il", models.DateTimeField(auto_now_add=True)),
                ("ultima_attivita", models.DateTimeField()),
                ("chiusa_il", models.DateTimeField(blank=True, null=True)),
                ("motivo_chiusura", models.CharField(blank=True, default="", max_length=20)),
                ("client", models.CharField(blank=True, default="", max_length=200)),
                ("indirizzo", models.GenericIPAddressField(blank=True, null=True)),
                ("versione_codice", models.CharField(blank=True, default="", max_length=20)),
                ("token", _fk_facoltativa("grafo.tokenaccesso")),
                ("utente", _fk(UTENTE, PROTECT)),
            ],
            options={
                "db_table": "grafo_sessione",
                "permissions": [("usa_chat", "Può interrogare l'analisi di rete dalla chat")],
            },
        ),
        migrations.CreateModel(
            name="Richiesta",
            fields=[
                _id(),
                ("ricevuta_il", models.DateTimeField(auto_now_add=True)),
                ("strumento", models.CharField(max_length=40)),
                ("parametri", models.JSONField(default=dict)),
                ("domanda", models.TextField(blank=True, default="")),
                ("esito", models.CharField(blank=True, default="", max_length=20)),
                ("durata_ms", models.PositiveIntegerField(blank=True, null=True)),
                ("versione_calcolo", models.CharField(blank=True, default="", max_length=20)),
                ("numero_dati", models.PositiveIntegerField(blank=True, null=True)),
                ("sessione", _fk("grafo.sessione", PROTECT)),
            ],
            options={
                "db_table": "grafo_richiesta",
                "indexes": [
                    models.Index(fields=["sessione", "ricevuta_il"], name="grafo_richiesta_sessione")
                ],
            },
        ),
        migrations.CreateModel(
            name="MappaProdotta",
            fields=[
                _id(),
                ("nome_file", models.CharField(max_length=255)),
                ("prodotta_il", models.DateTimeField(auto_now=True)),
                ("versione_calcolo", models.CharField(blank=True, default="", max_length=20)),
                ("numero_dati", models.PositiveIntegerField(blank=True, null=True)),
                ("richiesta", _fk_facoltativa("grafo.richiesta")),
                ("sessione", _fk("grafo.sessione", PROTECT)),
                ("soggetto", _fk("grafo.soggetto", PROTECT)),
            ],
            options={
                "db_table": "grafo_mappa",
                "constraints": [
                    models.UniqueConstraint(fields=("sessione", "nome_file"), name="grafo_mappa_unica")
                ],
            },
        ),
        migrations.RunPython(avanti, indietro),
    ]
