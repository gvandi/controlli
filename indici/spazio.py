"""
LO SPAZIO DEGLI INDICI (DECISIONI.md, n. 89): le aziende come punti in tre dimensioni.

Le tre dimensioni sono quelle su cui lavorano le regole:

    asse X   classe di dipendenti      (ordinata: D0, D1, ...)
    asse Y   classe di fatturato       (ordinata: F0, F1, ...)
    asse Z   attività economica        (divisione: le prime due cifre del codice)

Di ogni azienda si dicono due cose DIVERSE, che la pagina mostra con colori diversi:

  1. se supera l'indice a regole per il tipo di irregolarità scelto (indici/calcolo.py):
     è ciò che una persona ha dichiarato sospetto scrivendo una regola;

  2. se si discosta dalle aziende simili, con lo z-score robusto: è ciò che è
     insolito nei dati, anche se nessuna regola lo prevede.
     Si confronta il "fatturato rispetto al personale" (posizione della classe di
     fatturato meno posizione della classe di dipendenti) con quello delle aziende
     della stessa divisione di attività; se la divisione ha meno di MINIMO_GRUPPO
     aziende, con tutte le aziende.

Lo z-score robusto usa mediana e MAD al posto di media e scarto: pochi valori estremi
non spostano il termine di confronto (Iglewicz e Hoaglin):

    z = 0,6745 * (valore - mediana) / MAD
    se MAD = 0:   z = (valore - mediana) / (1,253314 * scarto assoluto medio)

Le classi sono poche e ordinate, quindi lo z-score prende pochi valori distinti: la
soglia è un parametro della pagina, non una verità. Un punto "insolito" è un invito a
guardare, non un'irregolarità.
"""
import collections
import statistics

from archivio import models as archivio
from archivio.models import Fascicolo
from decodifiche.models import ClasseDipendenti, ClasseFatturato
from grafo import contratto
from soggetti.models import DatiPerPeriodo

from . import calcolo
from .models import RegolaDiRischio

SOGLIA_Z = 2.5
MINIMO_GRUPPO = 8
TUTTE = "tutte le aziende"


def z_robusti(valori):
    """Lo z-score robusto di ogni valore rispetto agli altri della lista (stesso ordine)."""
    valori = [float(v) for v in valori]
    if len(valori) < 2:
        return [0.0] * len(valori)
    mediana = statistics.median(valori)
    scarti = [abs(v - mediana) for v in valori]
    mad = statistics.median(scarti)
    if mad > 0:
        return [0.6745 * (v - mediana) / mad for v in valori]
    medio = statistics.fmean(scarti)
    if medio > 0:
        return [(v - mediana) / (1.253314 * medio) for v in valori]
    return [0.0] * len(valori)


def _classi(modello):
    """Le classi in ordine crescente: [(codice, descrizione)]."""
    return [(c.codice, c.descrizione) for c in modello.objects.order_by("minimo", "codice")]


def costruisci(tipo):
    """
    I dati della pagina per un tipo di irregolarità:
        {"tipo", "soglia", "soglia_z", "assi": {"dipendenti", "fatturato", "attivita"},
         "punti": [...], "esclusi": n, "regole": [codice, ...]}
    Un punto: {"n" soggetto, "nome", "codice", "ateco", "periodo", "d", "f", "a" (posizioni
    sui tre assi), "punteggio", "sopra", "regole", "z", "gruppo", "fascicolo"}.
    Per ogni azienda valgono i dati del periodo più recente. Un'azienda a cui manca una
    delle tre coordinate non si può collocare: è contata in "esclusi".
    """
    indice_tipo = contratto.TIPI_IRREGOLARITA.index(tipo)
    regole = [r for r in RegolaDiRischio.objects.filter(attiva=True) if r.tipo in contratto.TIPI_IRREGOLARITA]
    dipendenti, fatturato = _classi(ClasseDipendenti), _classi(ClasseFatturato)
    posto_d = {codice.upper(): i for i, (codice, _) in enumerate(dipendenti)}
    posto_f = {codice.upper(): i for i, (codice, _) in enumerate(fatturato)}

    recenti = {}
    righe = DatiPerPeriodo.objects.select_related("soggetto").prefetch_related("soggetto__identificativi__tipo")
    for dato in righe.order_by("periodo"):
        recenti[dato.soggetto_id] = dato

    collocati, esclusi = [], 0
    for dato in recenti.values():
        caratteristiche = calcolo.descrivi(dato)
        d, f = posto_d.get(caratteristiche["classe_dipendenti"]), posto_f.get(caratteristiche["classe_fatturato"])
        if d is None or f is None or len(caratteristiche["attivita"]) < 2:
            esclusi += 1
            continue
        scattate = [r for r in regole if calcolo.scatta(r, caratteristiche)]
        collocati.append({
            "dato": dato, "d": d, "f": f, "divisione": caratteristiche["attivita"][:2],
            "punteggio": calcolo.punteggi(scattate)[indice_tipo],
            "regole": [r.codice for r in scattate if r.tipo == tipo],
        })

    # Lo scostamento dalle aziende simili: fatturato rispetto al personale
    per_divisione = collections.defaultdict(list)
    for punto in collocati:
        per_divisione[punto["divisione"]].append(punto)
    for punto, z in zip(collocati, z_robusti([p["f"] - p["d"] for p in collocati])):
        punto["z"], punto["gruppo"] = z, TUTTE
    for divisione, gruppo in per_divisione.items():
        if len(gruppo) >= MINIMO_GRUPPO:
            for punto, z in zip(gruppo, z_robusti([p["f"] - p["d"] for p in gruppo])):
                punto["z"], punto["gruppo"] = z, f"attività {divisione}"

    divisioni = sorted(per_divisione)
    posto_a = {divisione: i for i, divisione in enumerate(divisioni)}
    fascicoli = dict(
        Fascicolo.objects.filter(
            faldone__codice=archivio.AZIENDE, soggetto__in=[p["dato"].soggetto_id for p in collocati]
        ).values_list("soggetto_id", "pk")
    )
    punti = []
    for punto in sorted(collocati, key=lambda p: p["dato"].soggetto_id):
        dato = punto["dato"]
        identificativi = list(dato.soggetto.identificativi.all())
        punti.append({
            "n": dato.soggetto_id,
            "nome": dato.soggetto.denominazione or dato.denominazione or "senza denominazione",
            "codice": str(identificativi[0]) if identificativi else "",
            "ateco": dato.codice_attivita, "periodo": dato.periodo,
            "d": punto["d"], "f": punto["f"], "a": posto_a[punto["divisione"]],
            "punteggio": punto["punteggio"], "sopra": punto["punteggio"] >= calcolo.SOGLIA,
            "regole": punto["regole"], "z": round(punto["z"], 2), "gruppo": punto["gruppo"],
            "fascicolo": fascicoli.get(dato.soggetto_id),
        })
    return {
        "tipo": tipo, "soglia": calcolo.SOGLIA, "soglia_z": SOGLIA_Z,
        "assi": {
            "dipendenti": [{"codice": c, "descrizione": d} for c, d in dipendenti],
            "fatturato": [{"codice": c, "descrizione": d} for c, d in fatturato],
            "attivita": [{"codice": divisione, "descrizione": f"attività {divisione}"} for divisione in divisioni],
        },
        "punti": punti, "esclusi": esclusi,
        "regole": sorted(r.codice for r in regole if r.tipo == tipo),
    }
