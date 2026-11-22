"""Collegamento di un file ai fascicoli delle aziende che riguarda.

Scritta a mano (in fase di scrittura Django non era disponibile): la prova
archivio.tests.MigrazioniTest verifica che coincida con models.py.
"""
import django.db.models.deletion
from django.db import migrations, models

CASCADE = django.db.models.deletion.CASCADE


class Migration(migrations.Migration):

    dependencies = [
        ("archivio", "0002_caricamento"),
    ]

    operations = [
        migrations.CreateModel(
            name="CollegamentoFile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("origine", models.CharField(blank=True, default="", max_length=20)),
                ("collegato_il", models.DateTimeField(auto_now_add=True)),
                (
                    "fascicolo",
                    models.ForeignKey(on_delete=CASCADE, related_name="file_collegati", to="archivio.fascicolo"),
                ),
                ("file", models.ForeignKey(on_delete=CASCADE, related_name="collegamenti", to="archivio.filecaricato")),
            ],
            options={
                "constraints": [models.UniqueConstraint(fields=("file", "fascicolo"), name="collegamento_unico")],
            },
        ),
    ]
