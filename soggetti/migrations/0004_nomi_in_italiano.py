"""
Nomi dei modelli in italiano (singolare e plurale) per le pagine di amministrazione.

Senza un nome dichiarato Django costruisce il plurale aggiungendo una "s"
("Faldones", "Soggettos"). Cambia solo le etichette: nessuna tabella è toccata.
Scritta a mano; la prova MigrazioniTest verifica che coincida con i modelli.
"""
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("soggetti", "0003_classi_dalla_fonte")]

    operations = [
        migrations.AlterModelOptions(
            name="soggetto",
            options={'verbose_name': 'soggetto', 'verbose_name_plural': 'soggetti'},
        ),
        migrations.AlterModelOptions(
            name="identificativosoggetto",
            options={'verbose_name': 'identificativo', 'verbose_name_plural': 'identificativi'},
        ),
        migrations.AlterModelOptions(
            name="datiperperiodo",
            options={'verbose_name': 'dati per periodo', 'verbose_name_plural': 'dati per periodo'},
        ),
    ]
