from django.apps import AppConfig


class ElaborazioneConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "elaborazione"
    verbose_name = "Elaborazione dei file: testo ed entità"

    def ready(self):
        # Quando un caricamento viene annullato, l'archivio avvisa chi ne ha derivato
        # dei dati: qui si ritirano le entità estratte dai suoi file.
        from archivio import caricamento

        from . import coda

        if coda.ritira_caricamento not in caricamento.AL_RITIRO:
            caricamento.AL_RITIRO.append(coda.ritira_caricamento)
