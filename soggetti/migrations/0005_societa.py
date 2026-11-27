"""
Un solo nome: "società" al posto di azienda e soggetto (DECISIONI.md, n. 97).

Cambia le etichette dei modelli. Nessuna tabella è toccata: nel codice
e nel database i nomi restano quelli di prima (Soggetto, soggetti).
Scritta a mano; la prova MigrazioniTest verifica che coincida con i modelli.
"""
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("soggetti", "0004_nomi_in_italiano")]

    operations = [
        migrations.AlterModelOptions(
            name="soggetto",
            options={"verbose_name": "società", "verbose_name_plural": "società"},
        ),
    ]
