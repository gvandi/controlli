from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _


class Utente(AbstractUser):
    """Utente dell'applicazione.

    Per ora coincide con l'utente standard di Django. È definito qui fin
    dall'inizio perché sostituire il modello utente a progetto avviato è costoso
    (vedi DECISIONI.md, n. 3).
    """

    class Meta(AbstractUser.Meta):
        verbose_name = _("utente")
        verbose_name_plural = _("utenti")

    def nomi_ruoli(self):
        """Nomi dei ruoli (gruppi) assegnati all'utente, in ordine alfabetico."""
        return sorted(self.groups.values_list("name", flat=True))
