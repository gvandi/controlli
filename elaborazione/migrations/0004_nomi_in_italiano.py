"""
Nomi dei modelli in italiano (singolare e plurale) per le pagine di amministrazione.

Senza un nome dichiarato Django costruisce il plurale aggiungendo una "s"
("Faldones", "Soggettos"). Cambia solo le etichette: nessuna tabella è toccata.
Scritta a mano; la prova MigrazioniTest verifica che coincida con i modelli.
"""
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("elaborazione", "0003_documento_e_parti")]

    operations = [
        migrations.AlterModelOptions(
            name="vocecatalogo",
            options={'verbose_name': 'voce del catalogo', 'verbose_name_plural': 'voci del catalogo'},
        ),
        migrations.AlterModelOptions(
            name="elaborazione",
            options={'verbose_name': 'elaborazione', 'verbose_name_plural': 'elaborazioni'},
        ),
        migrations.AlterModelOptions(
            name="testopagina",
            options={'verbose_name': 'testo di una pagina', 'verbose_name_plural': 'testi delle pagine'},
        ),
        migrations.AlterModelOptions(
            name="entitaestratta",
            options={'verbose_name': 'entità estratta', 'verbose_name_plural': 'entità estratte'},
        ),
        migrations.AlterModelOptions(
            name="documento",
            options={'verbose_name': 'documento', 'verbose_name_plural': 'documenti'},
        ),
        migrations.AlterModelOptions(
            name="partedeldocumento",
            options={'verbose_name': 'parte del documento', 'verbose_name_plural': 'parti dei documenti'},
        ),
    ]
