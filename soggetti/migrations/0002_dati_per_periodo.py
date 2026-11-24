"""Dati di un soggetto per periodo (anno, in futuro anno e mese). Scritta a mano: DECISIONI.md, n. 69 e 86."""
import django.db.models.deletion
from django.db import migrations, models

import soggetti.models


class Migration(migrations.Migration):

    dependencies = [
        ("soggetti", "0001_iniziale"),
    ]

    operations = [
        migrations.CreateModel(
            name="DatiPerPeriodo",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("periodo", models.CharField(max_length=7, validators=[soggetti.models.periodo_valido])),
                ("denominazione", models.CharField(blank=True, default="", max_length=255)),
                ("codice_attivita", models.CharField(blank=True, default="", max_length=20)),
                ("dipendenti", models.PositiveIntegerField(blank=True, null=True)),
                ("fatturato", models.DecimalField(blank=True, decimal_places=2, max_digits=16, null=True)),
                ("fonte", models.CharField(blank=True, default="", max_length=120)),
                ("importato_il", models.DateTimeField(auto_now=True)),
                (
                    "soggetto",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="dati_per_periodo",
                        to="soggetti.soggetto",
                    ),
                ),
            ],
            options={
                "constraints": [
                    models.UniqueConstraint(fields=("soggetto", "periodo"), name="dati_per_periodo_unici"),
                ],
            },
        ),
    ]
