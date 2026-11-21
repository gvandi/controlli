"""Schema 4.0: prima migrazione dell'app grafo.

Scritta a mano (in fase di scrittura Django non era disponibile): la prova
grafo.tests.MigrazioniTest verifica che coincida con models.py.

Ogni migrazione che modifica lo schema aggiorna anche 'versione_schema' in
grafo_info, come fa questa: vedi grafo/COMPATIBILITA.md.
"""
import django.db.models.deletion
from django.db import migrations, models

VERSIONE_SCHEMA = "4.0"


def scrivi_versione_schema(apps, schema_editor):
    InfoArchivio = apps.get_model("grafo", "InfoArchivio")
    InfoArchivio.objects.update_or_create(
        chiave="versione_schema", defaults={"valore": VERSIONE_SCHEMA}
    )


def togli_versione_schema(apps, schema_editor):
    apps.get_model("grafo", "InfoArchivio").objects.filter(chiave="versione_schema").delete()


def _fk(modello, alla_cancellazione):
    return models.ForeignKey(on_delete=alla_cancellazione, related_name="+", to=modello)


CASCADE = django.db.models.deletion.CASCADE
PROTECT = django.db.models.deletion.PROTECT


def _id():
    return ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID"))


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="InfoArchivio",
            fields=[
                ("chiave", models.CharField(max_length=50, primary_key=True, serialize=False)),
                ("valore", models.CharField(max_length=255)),
            ],
            options={"db_table": "grafo_info"},
        ),
        migrations.CreateModel(
            name="Soggetto",
            fields=[
                _id(),
                ("riferimento", models.CharField(max_length=80, unique=True)),
                ("creato_il", models.DateTimeField(auto_now_add=True)),
            ],
            options={"db_table": "grafo_soggetto"},
        ),
        migrations.CreateModel(
            name="VersioneDati",
            fields=[
                _id(),
                ("numero", models.PositiveIntegerField(unique=True)),
                ("creata_il", models.DateTimeField(auto_now_add=True)),
                ("descrizione", models.CharField(blank=True, default="", max_length=255)),
                ("impronta", models.CharField(max_length=64, unique=True)),
            ],
            options={"db_table": "grafo_versione_dati"},
        ),
        migrations.CreateModel(
            name="Esecuzione",
            fields=[
                _id(),
                ("versione_calcolo", models.CharField(max_length=20)),
                ("versione_codice", models.CharField(max_length=20)),
                ("calcolata_il", models.DateTimeField(auto_now_add=True)),
                ("tassonomia", models.JSONField()),
                ("soglie", models.JSONField()),
                ("metriche", models.JSONField()),
                ("versione_dati", _fk("grafo.versionedati", PROTECT)),
            ],
            options={
                "db_table": "grafo_esecuzione",
                "constraints": [
                    models.UniqueConstraint(
                        fields=("versione_calcolo", "versione_dati"), name="grafo_esecuzione_unica"
                    )
                ],
            },
        ),
        migrations.CreateModel(
            name="DatiSoggetto",
            fields=[
                _id(),
                ("nome", models.CharField(max_length=255)),
                ("nr_iscrizione", models.CharField(blank=True, default="", max_length=80)),
                ("id_fiscale", models.CharField(blank=True, default="", max_length=80)),
                ("ispezionata", models.BooleanField(default=False)),
                ("soggetto", _fk("grafo.soggetto", PROTECT)),
                ("versione_dati", _fk("grafo.versionedati", CASCADE)),
            ],
            options={
                "db_table": "grafo_dati_soggetto",
                "constraints": [
                    models.UniqueConstraint(
                        fields=("versione_dati", "soggetto"), name="grafo_dati_soggetto_unico"
                    )
                ],
            },
        ),
        migrations.CreateModel(
            name="IrregolaritaAccertata",
            fields=[
                _id(),
                ("tipo", models.CharField(max_length=60)),
                ("soggetto", _fk("grafo.soggetto", PROTECT)),
                ("versione_dati", _fk("grafo.versionedati", CASCADE)),
            ],
            options={
                "db_table": "grafo_irregolarita",
                "constraints": [
                    models.UniqueConstraint(
                        fields=("versione_dati", "soggetto", "tipo"), name="grafo_irregolarita_unica"
                    )
                ],
            },
        ),
        migrations.CreateModel(
            name="Relazione",
            fields=[
                _id(),
                ("documento", models.CharField(max_length=80)),
                ("data", models.DateField()),
                ("importo", models.DecimalField(decimal_places=2, max_digits=14)),
                ("acquirente", _fk("grafo.soggetto", PROTECT)),
                ("venditore", _fk("grafo.soggetto", PROTECT)),
                ("versione_dati", _fk("grafo.versionedati", CASCADE)),
            ],
            options={
                "db_table": "grafo_relazione",
                "indexes": [
                    models.Index(fields=["versione_dati", "venditore"], name="grafo_rel_venditore"),
                    models.Index(fields=["versione_dati", "acquirente"], name="grafo_rel_acquirente"),
                ],
            },
        ),
        migrations.CreateModel(
            name="Indicatore",
            fields=[
                _id(),
                ("indice", models.PositiveIntegerField()),
                ("descrizione", models.TextField()),
                ("versione_dati", _fk("grafo.versionedati", CASCADE)),
            ],
            options={
                "db_table": "grafo_indicatore",
                "constraints": [
                    models.UniqueConstraint(
                        fields=("versione_dati", "indice"), name="grafo_indicatore_unico"
                    )
                ],
            },
        ),
        migrations.CreateModel(
            name="NodoSoggetto",
            fields=[
                _id(),
                ("indice_nodo", models.PositiveIntegerField()),
                ("esecuzione", _fk("grafo.esecuzione", CASCADE)),
                ("soggetto", _fk("grafo.soggetto", PROTECT)),
            ],
            options={
                "db_table": "grafo_nodo",
                "constraints": [
                    models.UniqueConstraint(fields=("esecuzione", "indice_nodo"), name="grafo_nodo_unico"),
                    models.UniqueConstraint(
                        fields=("esecuzione", "soggetto"), name="grafo_nodo_soggetto_unico"
                    ),
                ],
            },
        ),
        migrations.CreateModel(
            name="PunteggioRischio",
            fields=[
                _id(),
                ("tipo", models.CharField(max_length=60)),
                ("punteggio", models.FloatField()),
                ("sopra_soglia", models.BooleanField()),
                ("esecuzione", _fk("grafo.esecuzione", CASCADE)),
                ("soggetto", _fk("grafo.soggetto", PROTECT)),
            ],
            options={
                "db_table": "grafo_punteggio",
                "constraints": [
                    models.UniqueConstraint(
                        fields=("esecuzione", "soggetto", "tipo"), name="grafo_punteggio_unico"
                    )
                ],
            },
        ),
        migrations.CreateModel(
            name="Spiegazione",
            fields=[
                _id(),
                ("tipo", models.CharField(max_length=60)),
                ("calcolata_il", models.DateTimeField(auto_now=True)),
                ("dati", models.JSONField()),
                ("esecuzione", _fk("grafo.esecuzione", CASCADE)),
                ("soggetto", _fk("grafo.soggetto", PROTECT)),
            ],
            options={
                "db_table": "grafo_spiegazione",
                "constraints": [
                    models.UniqueConstraint(
                        fields=("esecuzione", "soggetto", "tipo"), name="grafo_spiegazione_unica"
                    )
                ],
            },
        ),
        migrations.CreateModel(
            name="RichiestaSpiegazione",
            fields=[
                _id(),
                ("tipo", models.CharField(max_length=60)),
                ("richiesta_il", models.DateTimeField(auto_now_add=True)),
                ("esecuzione", _fk("grafo.esecuzione", CASCADE)),
                ("soggetto", _fk("grafo.soggetto", PROTECT)),
            ],
            options={
                "db_table": "grafo_richiesta_spiegazione",
                "constraints": [
                    models.UniqueConstraint(
                        fields=("esecuzione", "soggetto", "tipo"), name="grafo_richiesta_unica"
                    )
                ],
            },
        ),
        migrations.RunPython(scrivi_versione_schema, togli_versione_schema),
    ]
