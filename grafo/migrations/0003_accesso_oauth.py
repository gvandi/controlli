"""Schema 4.2: per ogni sessione, come è stato fatto l'accesso e da quale programma.

ESPANSIONE: due colonne con valore predefinito su grafo_sessione e un parametro
in più per l'amministratore. Il codice della versione 20 continua a funzionare su
questo schema; le sessioni esistenti risultano aperte con il token personale,
com'era vero.

Scritta a mano (in fase di scrittura Django non era disponibile): la prova
grafo.tests.MigrazioniTest verifica che coincida con models.py.
"""
from django.db import migrations, models

VERSIONE_SCHEMA = "4.2"
VERSIONE_PRECEDENTE = "4.1"

PARAMETRO = (
    "token_personali_ammessi",
    "si",
    "Accettare anche i token personali copiati a mano (si / no). Con 'no' la chat entra "
    "solo con l'accesso OAuth dal browser.",
)


def avanti(apps, schema_editor):
    apps.get_model("grafo", "InfoArchivio").objects.update_or_create(
        chiave="versione_schema", defaults={"valore": VERSIONE_SCHEMA}
    )
    nome, valore, descrizione = PARAMETRO
    apps.get_model("grafo", "Parametro").objects.get_or_create(
        nome=nome, defaults={"valore": valore, "descrizione": descrizione}
    )


def indietro(apps, schema_editor):
    apps.get_model("grafo", "InfoArchivio").objects.update_or_create(
        chiave="versione_schema", defaults={"valore": VERSIONE_PRECEDENTE}
    )


class Migration(migrations.Migration):

    dependencies = [
        ("grafo", "0002_sessioni"),
    ]

    operations = [
        migrations.AddField(
            model_name="sessione",
            name="accesso",
            field=models.CharField(blank=True, default="token", max_length=10),
        ),
        migrations.AddField(
            model_name="sessione",
            name="client_oauth",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
        migrations.RunPython(avanti, indietro),
    ]
