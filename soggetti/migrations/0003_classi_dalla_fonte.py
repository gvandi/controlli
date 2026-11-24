"""Dati per periodo: la classe di dipendenti e di fatturato, quando la fonte dà la classe e non il valore.
Scritta a mano: DECISIONI.md, n. 69 e 88."""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("soggetti", "0002_dati_per_periodo"),
    ]

    operations = [
        migrations.AddField(
            model_name="datiperperiodo",
            name="classe_dipendenti",
            field=models.CharField(blank=True, default="", max_length=20),
        ),
        migrations.AddField(
            model_name="datiperperiodo",
            name="classe_fatturato",
            field=models.CharField(blank=True, default="", max_length=20),
        ),
    ]
