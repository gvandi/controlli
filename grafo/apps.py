from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class GrafoConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "grafo"
    verbose_name = _("Analisi di rete (prototipo)")
