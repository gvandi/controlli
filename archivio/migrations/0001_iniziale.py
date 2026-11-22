"""Faldoni, fascicoli, assegnazioni e soggetti delle indagini; crea i tre faldoni.

Scritta a mano (in fase di scrittura Django non era disponibile): la prova
archivio.tests.MigrazioniTest verifica che coincida con models.py.
"""
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

# (codice, nome, ordine, riservato, creato dal sistema, legato a)
FALDONI = [
    ("CARICAMENTI", "Caricamenti", 1, False, False, "caricamento"),
    ("AZIENDE", "Aziende", 2, False, True, "soggetto"),
    ("INDAGINI", "Indagini", 3, True, False, "indagine"),
]


def crea_faldoni(apps, schema_editor):
    Faldone = apps.get_model("archivio", "Faldone")
    for codice, nome, ordine, riservato, dal_sistema, legato_a in FALDONI:
        Faldone.objects.get_or_create(
            codice=codice,
            defaults={
                "nome": nome, "ordine": ordine, "riservato": riservato,
                "creato_dal_sistema": dal_sistema, "legato_a": legato_a,
            },
        )


CASCADE = django.db.models.deletion.CASCADE
PROTECT = django.db.models.deletion.PROTECT
SET_NULL = django.db.models.deletion.SET_NULL
UTENTE = settings.AUTH_USER_MODEL


def _id():
    return ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID"))


def _utente_facoltativo():
    return models.ForeignKey(blank=True, null=True, on_delete=SET_NULL, related_name="+", to=UTENTE)


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("soggetti", "0001_iniziale"),
    ]

    operations = [
        migrations.CreateModel(
            name="Faldone",
            fields=[
                _id(),
                ("codice", models.CharField(max_length=20, unique=True)),
                ("nome", models.CharField(max_length=80)),
                ("ordine", models.PositiveSmallIntegerField(default=0)),
                ("riservato", models.BooleanField(default=False)),
                ("creato_dal_sistema", models.BooleanField(default=False)),
                ("legato_a", models.CharField(blank=True, default="", max_length=20)),
            ],
        ),
        migrations.CreateModel(
            name="Fascicolo",
            fields=[
                _id(),
                ("titolo", models.CharField(max_length=200)),
                ("descrizione", models.TextField(blank=True, default="")),
                ("stato", models.CharField(default="aperto", max_length=20)),
                ("creato_il", models.DateTimeField(auto_now_add=True)),
                ("creato_da", _utente_facoltativo()),
                (
                    "faldone",
                    models.ForeignKey(on_delete=PROTECT, related_name="fascicoli", to="archivio.faldone"),
                ),
                (
                    "riservato_a",
                    models.ForeignKey(
                        blank=True, null=True, on_delete=PROTECT, related_name="riservati", to="archivio.fascicolo"
                    ),
                ),
                (
                    "soggetto",
                    models.ForeignKey(
                        blank=True, null=True, on_delete=PROTECT, related_name="+", to="soggetti.soggetto"
                    ),
                ),
            ],
            options={
                "permissions": [("apre_indagini", "Può aprire fascicoli d'indagine")],
                "constraints": [
                    models.UniqueConstraint(fields=("faldone", "soggetto"), name="fascicolo_unico_per_soggetto")
                ],
            },
        ),
        migrations.CreateModel(
            name="Assegnazione",
            fields=[
                _id(),
                ("assegnato_il", models.DateTimeField(auto_now_add=True)),
                ("assegnato_da", _utente_facoltativo()),
                (
                    "fascicolo",
                    models.ForeignKey(on_delete=CASCADE, related_name="assegnazioni", to="archivio.fascicolo"),
                ),
                ("utente", models.ForeignKey(on_delete=CASCADE, related_name="+", to=UTENTE)),
            ],
            options={
                "constraints": [
                    models.UniqueConstraint(fields=("fascicolo", "utente"), name="assegnazione_unica")
                ],
            },
        ),
        migrations.CreateModel(
            name="SoggettoInIndagine",
            fields=[
                _id(),
                ("nota", models.CharField(blank=True, default="", max_length=255)),
                ("aggiunto_il", models.DateTimeField(auto_now_add=True)),
                ("aggiunto_da", _utente_facoltativo()),
                (
                    "fascicolo",
                    models.ForeignKey(
                        on_delete=CASCADE, related_name="soggetti_in_indagine", to="archivio.fascicolo"
                    ),
                ),
                ("soggetto", models.ForeignKey(on_delete=PROTECT, related_name="+", to="soggetti.soggetto")),
            ],
            options={
                "constraints": [
                    models.UniqueConstraint(fields=("fascicolo", "soggetto"), name="soggetto_in_indagine_unico")
                ],
            },
        ),
        migrations.RunPython(crea_faldoni, migrations.RunPython.noop),
    ]
