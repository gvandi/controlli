"""
Etichetta di pagina  {% avviso_di_lettura file %}: mostra, in parole dell'utente, l'errore o
l'avviso dell'ultima lettura di un file (elaborazione/messaggi.py). Il testo tecnico compare,
ripiegato, solo a chi amministra (può vedere i lavori) o è del personale tecnico.
"""
from django import template

from elaborazione import coda, messaggi

register = template.Library()


@register.inclusion_tag("elaborazione/_avviso_di_lettura.html", takes_context=True)
def avviso_di_lettura(context, file):
    utente = getattr(context.get("request"), "user", None)
    return {
        "avviso": messaggi.in_chiaro(file.ultimo_errore, file.stato, file.tentativi, coda.massimo_tentativi()),
        "grave": file.stato == messaggi.ERRORE,
        "mostra_tecnico": bool(utente and (utente.is_staff or utente.has_perm("lavori.view_lavoro"))),
    }
