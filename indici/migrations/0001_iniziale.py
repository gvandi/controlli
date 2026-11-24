"""Regole di rischio. Scritta a mano: DECISIONI.md, n. 69 e 87."""
import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="RegolaDiRischio",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("codice", models.CharField(max_length=40, unique=True)),
                ("descrizione", models.CharField(max_length=255)),
                ("tipo", models.CharField(max_length=60)),
                (
                    "peso",
                    models.DecimalField(
                        decimal_places=2,
                        max_digits=3,
                        validators=[
                            django.core.validators.MinValueValidator(0),
                            django.core.validators.MaxValueValidator(1),
                        ],
                    ),
                ),
                (
                    "prefissi_attivita",
                    models.CharField(
                        blank=True, default="", max_length=255,
                        help_text="Inizio del codice dell'attività economica. Esempio: 46.1, 47",
                    ),
                ),
                (
                    "classi_dipendenti",
                    models.CharField(
                        blank=True, default="", max_length=255,
                        help_text="Codici delle classi di dipendenti. Esempio: D0",
                    ),
                ),
                (
                    "classi_fatturato",
                    models.CharField(
                        blank=True, default="", max_length=255,
                        help_text="Codici delle classi di fatturato. Esempio: F1, F2, F3",
                    ),
                ),
                ("attiva", models.BooleanField(default=True)),
                ("note", models.TextField(blank=True, default="")),
            ],
            options={
                "verbose_name": "regola di rischio",
                "verbose_name_plural": "regole di rischio",
                "ordering": ["codice"],
            },
        ),
    ]
