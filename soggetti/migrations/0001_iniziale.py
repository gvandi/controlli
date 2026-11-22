"""Anagrafica dei soggetti e loro identificativi.

Scritta a mano (in fase di scrittura Django non era disponibile): la prova
soggetti.tests.MigrazioniTest verifica che coincida con models.py.
"""
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("decodifiche", "__first__"),
    ]

    operations = [
        migrations.CreateModel(
            name="Soggetto",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("denominazione", models.CharField(blank=True, default="", max_length=255)),
                ("provvisorio", models.BooleanField(default=True)),
                ("creato_il", models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name="IdentificativoSoggetto",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("valore_originale", models.CharField(max_length=60)),
                ("valore_normalizzato", models.CharField(max_length=60)),
                ("valido_dal", models.DateField(blank=True, null=True)),
                ("valido_al", models.DateField(blank=True, null=True)),
                (
                    "soggetto",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, related_name="identificativi",
                        to="soggetti.soggetto",
                    ),
                ),
                (
                    "tipo",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT, related_name="+",
                        to="decodifiche.tipoidentificativo",
                    ),
                ),
            ],
            options={
                "constraints": [
                    models.UniqueConstraint(fields=("tipo", "valore_normalizzato"), name="identificativo_unico")
                ],
            },
        ),
    ]
