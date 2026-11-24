"""
Nomi dei modelli in italiano (singolare e plurale) per le pagine di amministrazione.

Senza un nome dichiarato Django costruisce il plurale aggiungendo una "s"
("Faldones", "Soggettos"). Cambia solo le etichette: nessuna tabella è toccata.
Scritta a mano; la prova MigrazioniTest verifica che coincida con i modelli.
"""
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("archivio", "0004_diritto_di_cancellazione")]

    operations = [
        migrations.AlterModelOptions(
            name="faldone",
            options={'verbose_name': 'faldone', 'verbose_name_plural': 'faldoni'},
        ),
        migrations.AlterModelOptions(
            name="fascicolo",
            options={'permissions': [('apre_indagini', "Può aprire fascicoli d'indagine")], 'verbose_name': 'fascicolo', 'verbose_name_plural': 'fascicoli'},
        ),
        migrations.AlterModelOptions(
            name="assegnazione",
            options={'verbose_name': 'assegnazione', 'verbose_name_plural': 'assegnazioni'},
        ),
        migrations.AlterModelOptions(
            name="soggettoinindagine",
            options={'verbose_name': 'soggetto in indagine', 'verbose_name_plural': 'soggetti in indagine'},
        ),
        migrations.AlterModelOptions(
            name="caricamento",
            options={'verbose_name': 'caricamento', 'verbose_name_plural': 'caricamenti'},
        ),
        migrations.AlterModelOptions(
            name="filecaricato",
            options={'permissions': [('cancella_definitivamente', 'Può cancellare definitivamente un file e i dati che ne derivano')], 'verbose_name': 'file caricato', 'verbose_name_plural': 'file caricati'},
        ),
        migrations.AlterModelOptions(
            name="soggettodichiarato",
            options={'verbose_name': 'soggetto dichiarato', 'verbose_name_plural': 'soggetti dichiarati'},
        ),
        migrations.AlterModelOptions(
            name="evento",
            options={'verbose_name': 'evento del registro', 'verbose_name_plural': 'eventi del registro'},
        ),
        migrations.AlterModelOptions(
            name="collegamentofile",
            options={'verbose_name': 'collegamento di un file', 'verbose_name_plural': 'collegamenti dei file'},
        ),
    ]
