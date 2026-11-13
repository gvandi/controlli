from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class UtentiConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "utenti"
    verbose_name = _("Utenti e ruoli")
