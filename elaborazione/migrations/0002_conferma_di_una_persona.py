"""
Entità: il campo "confermata" (un revisore l'ha conservata; la sua conferma prevale
sul controllo contro il testo). Scritta a mano: vedi DECISIONI.md, n. 69 e 79.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("elaborazione", "0001_iniziale"),
    ]

    operations = [
        migrations.AddField(
            model_name="entitaestratta",
            name="confermata",
            field=models.BooleanField(default=False),
        ),
    ]
