"""
Un solo nome: "società" al posto di azienda e soggetto (DECISIONI.md, n. 97).

Cambia le etichette dei modelli e il nome del faldone "Aziende", che diventa "Società"
(il codice del faldone resta AZIENDE; un nome già cambiato a mano non viene toccato).
Nessuna tabella cambia struttura: nel codice e nel database i nomi restano quelli di prima (Soggetto, soggetti).
Scritta a mano; la prova MigrazioniTest verifica che coincida con i modelli.
"""
from django.db import migrations


def rinomina(apps, schema_editor, prima="Aziende", dopo="Società"):
    apps.get_model("archivio", "Faldone").objects.filter(codice="AZIENDE", nome=prima).update(nome=dopo)


def ripristina(apps, schema_editor):
    rinomina(apps, schema_editor, prima="Società", dopo="Aziende")


class Migration(migrations.Migration):
    dependencies = [("archivio", "0005_nomi_in_italiano")]

    operations = [
        migrations.AlterModelOptions(
            name="soggettoinindagine",
            options={"verbose_name": "società in indagine", "verbose_name_plural": "società in indagine"},
        ),
        migrations.AlterModelOptions(
            name="soggettodichiarato",
            options={"verbose_name": "società dichiarata", "verbose_name_plural": "società dichiarate"},
        ),
        migrations.RunPython(rinomina, ripristina),
    ]
