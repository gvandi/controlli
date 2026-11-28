"""
CHE COSA ENTRA NEI CALCOLI E NELLA DESCRIZIONE DI UNA SOCIETÀ (DECISIONI.md, n. 100).

Fino alla versione precedente entrava solo ciò che una persona aveva confermato. Ora lo
decidono cinque CRITERI, ognuno un sì o un no:

    documenti_non_confermati   i documenti letti dal modello e non ancora confermati,
                               con i ruoli proposti (diventano rapporti nel grafo)
    letture_incomplete         fra quelli, anche i documenti dei file la cui lettura ha un avviso
    entita_non_verificate      le entità il cui valore non è stato ritrovato nel testo
    entita_da_rivedere         le entità che aspettano la revisione di una persona
    entita_fuori_catalogo      le entità senza una voce del catalogo (date, importi, nomi...)

Con tutti i criteri a "no" vale la regola di prima (decisioni 74, 79, 80). In fase di prova
sono tutti a "sì": impostazione CALCOLO_AMMETTE. L'amministratore li sceglie ogni volta che
lancia un calcolo; le pagine (scheda di una società) usano quelli dell'impostazione.

Restano SEMPRE fuori, qualunque sia la scelta: ciò che una persona ha scartato, le entità
senza una società, e (lo decide grafo/dati_reali.py) i caricamenti riservati a un'indagine.

Ciò che entra senza conferma resta riconoscibile: verificato() lo dice per un'entità o un
documento, e chi mostra il dato deve dirlo. "Verificato" vuol dire confermato da una persona:
il controllo automatico sul testo non conta (n. 103).

Questo è l'UNICO posto in cui si decide che cosa è ammesso.
"""
import collections

from django.conf import settings
from django.db.models import Q

from archivio import models as archivio

from .models import Documento, EntitaEstratta

# codice -> (come si chiama nella pagina, che cosa aggiunge)
CRITERI = collections.OrderedDict([
    ("documenti_non_confermati", ("Documenti non ancora confermati",
                                  "Fatture e DDT letti dal modello, con i ruoli che ha proposto: diventano rapporti nel grafo.")),
    ("letture_incomplete", ("Anche da file con lettura incompleta",
                            "Fra i documenti non confermati, anche quelli dei file che hanno un avviso di lettura.")),
    ("entita_non_verificate", ("Entità non ritrovate nel testo",
                               "Valori che il controllo automatico non ha ritrovato nel testo del file.")),
    ("entita_da_rivedere", ("Entità in attesa di revisione",
                            "Per esempio identificativi e importi letti da una scansione.")),
    ("entita_fuori_catalogo", ("Entità fuori catalogo",
                               "Date, importi, nomi e altre informazioni lette che non corrispondono a una voce del catalogo.")),
])
Criteri = collections.namedtuple("Criteri", list(CRITERI))
SOLO_VERIFICATI = Criteri(*[False] * len(CRITERI))


def predefiniti():
    """I criteri dell'impostazione CALCOLO_AMMETTE; un criterio non indicato vale "sì"."""
    scelti = getattr(settings, "CALCOLO_AMMETTE", {}) or {}
    return Criteri(*[bool(scelti.get(codice, True)) for codice in CRITERI])


def da_parametri(parametri):
    """
    I criteri scelti per un calcolo: {codice: vero/falso}; None o vuoto = quelli predefiniti.
    Un criterio che manca in un dizionario non vuoto vale "no" (una casella non spuntata).
    """
    if not parametri:
        return predefiniti()
    return Criteri(*[bool(parametri.get(codice)) for codice in CRITERI])


def come_parametri(criteri):
    return dict(criteri._asdict())


def descrivi(criteri, solo_documenti=False):
    """
    In parole, per la descrizione di una fotografia e per gli esiti: che cosa è compreso oltre
    al verificato. solo_documenti: i soli criteri che cambiano i rapporti del grafo.
    """
    codici = [codice for codice in CRITERI if not solo_documenti or not codice.startswith("entita")]
    compresi = [CRITERI[codice][0].lower() for codice in codici if getattr(criteri, codice)]
    return "compresi: " + ", ".join(compresi) if compresi else "solo dati verificati"


def documenti(criteri=None):
    """I documenti commerciali ammessi: mai quelli scartati; i non confermati secondo i criteri."""
    criteri = criteri or predefiniti()
    ammessi = Documento.objects.filter(ritirato=False)
    if not criteri.documenti_non_confermati:
        return ammessi.filter(confermato=True)
    if not criteri.letture_incomplete:
        incompleta = Q(file__stato=archivio.FILE_DA_RIVEDERE) & ~Q(file__ultimo_errore="")
        ammessi = ammessi.filter(Q(confermato=True) | ~incompleta)
    # un file annullato o in errore non dà documenti, confermati o no
    return ammessi.exclude(confermato=False, file__stato__in=[archivio.FILE_ANNULLATO, archivio.FILE_ERRORE, archivio.FILE_BOZZA])


def entita(criteri=None):
    """Le entità ammesse a descrivere una società: mai quelle scartate o senza società."""
    criteri = criteri or predefiniti()
    ammesse = EntitaEstratta.objects.filter(ritirata=False, soggetto__isnull=False)
    if not criteri.entita_fuori_catalogo:
        ammesse = ammesse.filter(voce__isnull=False)
    if not criteri.entita_non_verificate:
        ammesse = ammesse.filter(Q(verificata=True) | Q(confermata=True))
    if not criteri.entita_da_rivedere:
        ammesse = ammesse.filter(da_rivedere=False)
    if criteri.entita_non_verificate or criteri.entita_da_rivedere or criteri.entita_fuori_catalogo:
        # ciò che nessuno ha confermato non si prende da un caricamento annullato
        ammesse = ammesse.exclude(Q(file__stato=archivio.FILE_ANNULLATO) & Q(confermata=False))
    return ammesse


def verificato(oggetto):
    """
    Vero solo se UNA PERSONA ha confermato il dato: un documento confermato, un'entità confermata.

    Il controllo automatico (EntitaEstratta.verificata: "il valore si ritrova nel testo") NON basta:
    dice che quella scritta nel file c'è, non che sia la risposta giusta. Il modello può leggere
    "€ 25.500,00" in un verbale e chiamarlo ricavi, o indicare come amministratore il socio
    sbagliato: sono valori presenti nel testo, e sbagliati. Per questo un dato che nessuno ha
    guardato resta "non verificato", qualunque cosa dica il controllo automatico (n. 103).
    """
    if isinstance(oggetto, Documento):
        return oggetto.confermato
    return bool(oggetto.confermata)
