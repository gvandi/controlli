"""Lavori ed esecutori. Scritta a mano: DECISIONI.md, n. 69 e 94."""
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Esecutore",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nome", models.CharField(max_length=80, unique=True)),
                ("tipi", models.CharField(blank=True, default="", max_length=255)),
                ("ultimo_segnale", models.DateTimeField()),
            ],
        ),
        migrations.CreateModel(
            name="Lavoro",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("tipo", models.CharField(max_length=40)),
                ("stato", models.CharField(default="richiesto", max_length=20)),
                ("richiesto_il", models.DateTimeField(auto_now_add=True)),
                ("iniziato_il", models.DateTimeField(blank=True, null=True)),
                ("finito_il", models.DateTimeField(blank=True, null=True)),
                ("parametri", models.JSONField(blank=True, default=dict)),
                ("ingresso", models.TextField(blank=True, default="")),
                ("nome_ingresso", models.CharField(blank=True, default="", max_length=255)),
                ("esito", models.TextField(blank=True, default="")),
                (
                    "richiesto_da",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name_plural": "lavori",
                "ordering": ["-richiesto_il", "-pk"],
                "permissions": [("lancia_lavori", "Può lanciare elaborazioni e calcoli")],
            },
        ),
    ]
