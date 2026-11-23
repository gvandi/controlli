"""Diritto di cancellare definitivamente un file e i dati che ne derivano.

Scritta a mano (in fase di scrittura Django non era disponibile): la prova
archivio.tests.MigrazioniTest verifica che coincida con models.py.
"""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("archivio", "0003_collegamento"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="filecaricato",
            options={
                "permissions": [
                    ("cancella_definitivamente", "Può cancellare definitivamente un file e i dati che ne derivano")
                ],
            },
        ),
    ]
