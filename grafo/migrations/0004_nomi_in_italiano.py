"""
Nomi dei modelli in italiano (singolare e plurale) per le pagine di amministrazione.

Senza un nome dichiarato Django costruisce il plurale aggiungendo una "s"
("Faldones", "Soggettos"). Cambia solo le etichette: nessuna tabella è toccata.
Scritta a mano; la prova MigrazioniTest verifica che coincida con i modelli.
"""
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("grafo", "0003_accesso_oauth")]

    operations = [
        migrations.AlterModelOptions(
            name="infoarchivio",
            options={'verbose_name': "informazione sull'archivio", 'verbose_name_plural': "informazioni sull'archivio"},
        ),
        migrations.AlterModelOptions(
            name="soggetto",
            options={'verbose_name': 'soggetto del grafo', 'verbose_name_plural': 'soggetti del grafo'},
        ),
        migrations.AlterModelOptions(
            name="versionedati",
            options={'verbose_name': 'fotografia dei dati', 'verbose_name_plural': 'fotografie dei dati'},
        ),
        migrations.AlterModelOptions(
            name="datisoggetto",
            options={'verbose_name': 'dati di un soggetto', 'verbose_name_plural': 'dati dei soggetti'},
        ),
        migrations.AlterModelOptions(
            name="irregolaritaaccertata",
            options={'verbose_name': 'irregolarità accertata', 'verbose_name_plural': 'irregolarità accertate'},
        ),
        migrations.AlterModelOptions(
            name="relazione",
            options={'verbose_name': 'relazione', 'verbose_name_plural': 'relazioni'},
        ),
        migrations.AlterModelOptions(
            name="indicatore",
            options={'verbose_name': 'indicatore', 'verbose_name_plural': 'indicatori'},
        ),
        migrations.AlterModelOptions(
            name="esecuzione",
            options={'verbose_name': 'esecuzione', 'verbose_name_plural': 'esecuzioni'},
        ),
        migrations.AlterModelOptions(
            name="nodosoggetto",
            options={'verbose_name': 'nodo di un soggetto', 'verbose_name_plural': 'nodi dei soggetti'},
        ),
        migrations.AlterModelOptions(
            name="punteggiorischio",
            options={'verbose_name': 'punteggio di rischio', 'verbose_name_plural': 'punteggi di rischio'},
        ),
        migrations.AlterModelOptions(
            name="spiegazione",
            options={'verbose_name': 'spiegazione', 'verbose_name_plural': 'spiegazioni'},
        ),
        migrations.AlterModelOptions(
            name="richiestaspiegazione",
            options={'verbose_name': 'richiesta di spiegazione', 'verbose_name_plural': 'richieste di spiegazione'},
        ),
        migrations.AlterModelOptions(
            name="parametro",
            options={'verbose_name': 'parametro', 'verbose_name_plural': 'parametri'},
        ),
        migrations.AlterModelOptions(
            name="tokenaccesso",
            options={'verbose_name': 'token di accesso', 'verbose_name_plural': 'token di accesso'},
        ),
        migrations.AlterModelOptions(
            name="sessione",
            options={'permissions': [('usa_chat', "Può interrogare l'analisi di rete dalla chat")], 'verbose_name': 'sessione della chat', 'verbose_name_plural': 'sessioni della chat'},
        ),
        migrations.AlterModelOptions(
            name="richiesta",
            options={'verbose_name': 'richiesta della chat', 'verbose_name_plural': 'richieste della chat'},
        ),
        migrations.AlterModelOptions(
            name="mappaprodotta",
            options={'verbose_name': 'mappa prodotta', 'verbose_name_plural': 'mappe prodotte'},
        ),
    ]
