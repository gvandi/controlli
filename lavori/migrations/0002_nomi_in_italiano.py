"""
Nomi dei modelli in italiano (singolare e plurale) per le pagine di amministrazione.

Senza un nome dichiarato Django costruisce il plurale aggiungendo una "s"
("Faldones", "Soggettos"). Cambia solo le etichette: nessuna tabella è toccata.
Scritta a mano; la prova MigrazioniTest verifica che coincida con i modelli.
"""
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("lavori", "0001_iniziale")]

    operations = [
        migrations.AlterModelOptions(
            name="lavoro",
            options={'ordering': ['-richiesto_il', '-pk'], 'permissions': [('lancia_lavori', 'Può lanciare elaborazioni e calcoli')], 'verbose_name': 'lavoro', 'verbose_name_plural': 'lavori'},
        ),
        migrations.AlterModelOptions(
            name="esecutore",
            options={'verbose_name': 'esecutore', 'verbose_name_plural': 'esecutori'},
        ),
    ]
