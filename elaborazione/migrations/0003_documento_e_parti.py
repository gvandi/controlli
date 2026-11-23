"""
Documento e parti del documento (mittente, destinatario, vettore, luogo di destinazione).
Scritta a mano: vedi DECISIONI.md, n. 69 e 80.
"""
import django.db.models.deletion
from django.db import migrations, models

CASCADE = django.db.models.deletion.CASCADE
PROTECT = django.db.models.deletion.PROTECT


def _id():
    return ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID"))


class Migration(migrations.Migration):

    dependencies = [
        ("elaborazione", "0002_conferma_di_una_persona"),
    ]

    operations = [
        migrations.CreateModel(
            name="Documento",
            fields=[
                _id(),
                ("pagina", models.PositiveIntegerField(blank=True, null=True)),
                ("tipo", models.CharField(blank=True, default="", max_length=40)),
                ("numero", models.CharField(blank=True, default="", max_length=60)),
                ("data", models.DateField(blank=True, null=True)),
                ("totale", models.DecimalField(blank=True, decimal_places=2, max_digits=14, null=True)),
                ("data_scritta", models.CharField(blank=True, default="", max_length=60)),
                ("totale_scritto", models.CharField(blank=True, default="", max_length=60)),
                ("confermato", models.BooleanField(default=False)),
                ("ritirato", models.BooleanField(default=False)),
                ("estratto_il", models.DateTimeField(auto_now_add=True)),
                (
                    "elaborazione",
                    models.ForeignKey(on_delete=CASCADE, related_name="documenti", to="elaborazione.elaborazione"),
                ),
                (
                    "file",
                    models.ForeignKey(on_delete=CASCADE, related_name="documenti", to="archivio.filecaricato"),
                ),
            ],
        ),
        migrations.CreateModel(
            name="ParteDelDocumento",
            fields=[
                _id(),
                ("ruolo", models.CharField(blank=True, default="", max_length=30)),
                ("ruolo_proposto", models.CharField(blank=True, default="", max_length=60)),
                ("denominazione", models.CharField(blank=True, default="", max_length=300)),
                ("identificativo", models.CharField(blank=True, default="", max_length=60)),
                ("ritirata", models.BooleanField(default=False)),
                (
                    "documento",
                    models.ForeignKey(on_delete=CASCADE, related_name="parti", to="elaborazione.documento"),
                ),
                (
                    "soggetto",
                    models.ForeignKey(
                        blank=True, null=True, on_delete=PROTECT, related_name="+", to="soggetti.soggetto"
                    ),
                ),
            ],
        ),
    ]
