from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class DecodificheConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "decodifiche"
    verbose_name = _("Tabelle di decodifica")
