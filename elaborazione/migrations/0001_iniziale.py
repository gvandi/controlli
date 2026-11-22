"""Catalogo delle entità, elaborazioni, testo delle pagine, entità estratte.

Scritta a mano (in fase di scrittura Django non era disponibile): la prova
elaborazione.tests.MigrazioniTest verifica che coincida con models.py.
"""
import django.db.models.deletion
from django.db import migrations, models

CASCADE = django.db.models.deletion.CASCADE
PROTECT = django.db.models.deletion.PROTECT


def _id():
    return ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID"))


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("archivio", "0003_collegamento"),
        ("soggetti", "0001_iniziale"),
    ]

    operations = [
        migrations.CreateModel(
            name="VoceCatalogo",
            fields=[
                _id(),
                ("codice", models.CharField(max_length=30, unique=True)),
                ("descrizione", models.CharField(max_length=200)),
                ("tipo_valore", models.CharField(default="testo", max_length=20)),
                ("ha_periodo", models.BooleanField(default=False)),
                ("multipla", models.BooleanField(default=False)),
                ("cambia_nel_tempo", models.BooleanField(default=False)),
                ("sinonimi", models.TextField(blank=True, default="")),
                ("ordine", models.PositiveSmallIntegerField(default=0)),
                ("valida_dal", models.DateField(blank=True, null=True)),
                ("valida_al", models.DateField(blank=True, null=True)),
            ],
        ),
        migrations.CreateModel(
            name="Elaborazione",
            fields=[
                _id(),
                ("iniziata_il", models.DateTimeField(auto_now_add=True)),
                ("finita_il", models.DateTimeField(blank=True, null=True)),
                ("esito", models.CharField(blank=True, default="", max_length=20)),
                ("natura", models.CharField(blank=True, default="", max_length=20)),
                ("motore", models.CharField(blank=True, default="", max_length=60)),
                ("modello", models.CharField(blank=True, default="", max_length=120)),
                ("versione_prompt", models.CharField(blank=True, default="", max_length=20)),
                ("pagine", models.PositiveIntegerField(default=0)),
                ("errore", models.TextField(blank=True, default="")),
                (
                    "file",
                    models.ForeignKey(on_delete=CASCADE, related_name="elaborazioni", to="archivio.filecaricato"),
                ),
            ],
        ),
        migrations.CreateModel(
            name="TestoPagina",
            fields=[
                _id(),
                ("pagina", models.PositiveIntegerField()),
                ("testo", models.TextField(blank=True, default="")),
                ("origine", models.CharField(blank=True, default="", max_length=20)),
                (
                    "elaborazione",
                    models.ForeignKey(on_delete=CASCADE, related_name="testi", to="elaborazione.elaborazione"),
                ),
            ],
            options={
                "constraints": [
                    models.UniqueConstraint(fields=("elaborazione", "pagina"), name="testo_unico_per_pagina")
                ],
            },
        ),
        migrations.CreateModel(
            name="EntitaEstratta",
            fields=[
                _id(),
                ("etichetta", models.CharField(max_length=120)),
                ("valore", models.CharField(max_length=500)),
                ("valore_normalizzato", models.CharField(blank=True, default="", max_length=500)),
                ("pagina", models.PositiveIntegerField(blank=True, null=True)),
                ("citazione", models.TextField(blank=True, default="")),
                ("evento", models.CharField(blank=True, default="", max_length=200)),
                ("periodo", models.CharField(blank=True, default="", max_length=20)),
                ("fonte", models.CharField(blank=True, default="", max_length=20)),
                ("verificata", models.BooleanField(default=False)),
                ("da_rivedere", models.BooleanField(default=False)),
                ("motivo_revisione", models.CharField(blank=True, default="", max_length=200)),
                ("ritirata", models.BooleanField(default=False)),
                ("estratta_il", models.DateTimeField(auto_now_add=True)),
                (
                    "elaborazione",
                    models.ForeignKey(on_delete=CASCADE, related_name="entita", to="elaborazione.elaborazione"),
                ),
                ("file", models.ForeignKey(on_delete=CASCADE, related_name="entita", to="archivio.filecaricato")),
                (
                    "soggetto",
                    models.ForeignKey(
                        blank=True, null=True, on_delete=PROTECT, related_name="+", to="soggetti.soggetto"
                    ),
                ),
                (
                    "voce",
                    models.ForeignKey(
                        blank=True, null=True, on_delete=PROTECT, related_name="+", to="elaborazione.vocecatalogo"
                    ),
                ),
            ],
            options={
                "indexes": [models.Index(fields=["soggetto", "voce"], name="entita_soggetto_voce")],
            },
        ),
    ]
