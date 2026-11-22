"""Caricamento dei file: metadati del caricamento, file, soggetti dichiarati, registro.

Scritta a mano (in fase di scrittura Django non era disponibile): la prova
archivio.tests.MigrazioniTest verifica che coincida con models.py.
"""
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

CASCADE = django.db.models.deletion.CASCADE
PROTECT = django.db.models.deletion.PROTECT
SET_NULL = django.db.models.deletion.SET_NULL
UTENTE = settings.AUTH_USER_MODEL


def _id():
    return ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID"))


def _utente_facoltativo():
    return models.ForeignKey(blank=True, null=True, on_delete=SET_NULL, related_name="+", to=UTENTE)


def _tipo_documento():
    return models.ForeignKey(
        blank=True, null=True, on_delete=PROTECT, related_name="+", to="decodifiche.tipodocumento"
    )


class Migration(migrations.Migration):

    # "__latest__": i tipi di documento e di identificativo sono arrivati in
    # decodifiche dopo la sua prima migrazione.
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("decodifiche", "__latest__"),
        ("soggetti", "0001_iniziale"),
        ("archivio", "0001_iniziale"),
    ]

    operations = [
        migrations.CreateModel(
            name="Caricamento",
            fields=[
                (
                    "fascicolo",
                    models.OneToOneField(
                        on_delete=CASCADE, primary_key=True, related_name="caricamento", serialize=False,
                        to="archivio.fascicolo",
                    ),
                ),
                ("provenienza", models.CharField(blank=True, default="", max_length=200)),
                ("natura", models.CharField(blank=True, default="", max_length=20)),
                ("periodo_dal", models.DateField(blank=True, null=True)),
                ("periodo_al", models.DateField(blank=True, null=True)),
                ("note", models.TextField(blank=True, default="")),
                ("tipo_documento", _tipo_documento()),
            ],
        ),
        migrations.CreateModel(
            name="FileCaricato",
            fields=[
                _id(),
                ("percorso_originale", models.CharField(max_length=500)),
                ("impronta", models.CharField(db_index=True, max_length=64)),
                ("dimensione", models.BigIntegerField()),
                ("tipo_mime", models.CharField(blank=True, default="", max_length=100)),
                ("stato", models.CharField(default="bozza", max_length=20)),
                ("priorita", models.SmallIntegerField(default=0)),
                ("tentativi", models.PositiveSmallIntegerField(default=0)),
                ("ultimo_errore", models.TextField(blank=True, default="")),
                ("caricato_il", models.DateTimeField(auto_now_add=True)),
                ("provenienza", models.CharField(blank=True, default="", max_length=200)),
                ("natura", models.CharField(blank=True, default="", max_length=20)),
                ("periodo_dal", models.DateField(blank=True, null=True)),
                ("periodo_al", models.DateField(blank=True, null=True)),
                ("caricato_da", _utente_facoltativo()),
                ("fascicolo", models.ForeignKey(on_delete=CASCADE, related_name="file", to="archivio.fascicolo")),
                ("tipo_documento", _tipo_documento()),
            ],
            options={
                "constraints": [
                    models.UniqueConstraint(
                        fields=("fascicolo", "percorso_originale"), name="file_unico_per_percorso"
                    )
                ],
            },
        ),
        migrations.CreateModel(
            name="SoggettoDichiarato",
            fields=[
                _id(),
                ("valore_originale", models.CharField(max_length=60)),
                ("valore_normalizzato", models.CharField(max_length=60)),
                ("principale", models.BooleanField(default=False)),
                (
                    "fascicolo",
                    models.ForeignKey(
                        blank=True, null=True, on_delete=CASCADE, related_name="soggetti_dichiarati",
                        to="archivio.fascicolo",
                    ),
                ),
                (
                    "file",
                    models.ForeignKey(
                        blank=True, null=True, on_delete=CASCADE, related_name="soggetti_dichiarati",
                        to="archivio.filecaricato",
                    ),
                ),
                ("soggetto", models.ForeignKey(on_delete=PROTECT, related_name="+", to="soggetti.soggetto")),
                (
                    "tipo",
                    models.ForeignKey(on_delete=PROTECT, related_name="+", to="decodifiche.tipoidentificativo"),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Evento",
            fields=[
                _id(),
                ("quando", models.DateTimeField(auto_now_add=True)),
                ("azione", models.CharField(max_length=30)),
                ("dettaglio", models.CharField(blank=True, default="", max_length=500)),
                (
                    "fascicolo",
                    models.ForeignKey(
                        blank=True, null=True, on_delete=SET_NULL, related_name="eventi", to="archivio.fascicolo"
                    ),
                ),
                ("utente", _utente_facoltativo()),
            ],
        ),
    ]
