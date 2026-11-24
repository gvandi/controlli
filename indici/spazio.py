"""
LO SPAZIO DEGLI INDICI (DECISIONI.md, n. 89): le aziende come punti in tre dimensioni.

Le tre dimensioni sono quelle su cui lavorano le regole:

    asse X   classe di dipendenti      (ordinata: D0, D1, ...)
    asse Y   classe di fatturato       (ordinata: F0, F1, ...)
    asse Z   attività economica        (divisione: le prime due cifre del codice)

Di ogni azienda si dicono due cose DIVERSE, che la pagina mostra con colori diversi:

  1. se per lei SCATTA LA REGOLA scelta fra quelle definite (indici/calcolo.py): è ciò
     che una persona ha dichiarato sospetto scrivendo quella regola. Si sceglie una
     regola e non un tipo di irregolarità perché i tipi non hanno ancora una
     definizione scritta, mentre una regola dice esattamente che cosa guarda (n. 90);

  2. se si discosta dalle aziende simili, con lo z-score robusto: è ciò che è
     insolito nei dati, anche se nessuna regola lo prevede.
     Si confronta il "fatturato rispetto al personale" (posizione della classe di
     fatturato meno posizione della classe di dipendenti) con quello delle aziende
     della stessa divisione di attività; se la divisione ha meno di MINIMO_GRUPPO
     aziende, con tutte le aziende.

I RAPPORTI (n. 91). Fra le aziende si mostrano anche i rapporti che risultano dai
documenti confermati (mittente -> destinatario), gli stessi che entrano nella
fotografia dei dati reali dell'analisi di rete: per ogni coppia il numero di documenti
e la somma degli importi. Nella pagina compaiono come linee quando si seleziona
un'azienda; racconta() dice le stesse cose in parole, per lo strumento "spazio" della chat.

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
from elaborazione import coda as elaborazione
from grafo import dati_reali
from soggetti import servizi as anagrafica
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


def _dentro_la_regola(regola, dipendenti, fatturato, divisioni):
    """Le posizioni dei tre assi che la regola richiede: servono a evidenziarle nel disegno."""
    classi_d, classi_f = calcolo._valori(regola.classi_dipendenti), calcolo._valori(regola.classi_fatturato)
    prefissi = calcolo._valori(regola.prefissi_attivita)
    return {
        "dipendenti": [i for i, (codice, _) in enumerate(dipendenti) if codice.upper() in classi_d],
        "fatturato": [i for i, (codice, _) in enumerate(fatturato) if codice.upper() in classi_f],
        # una divisione è toccata dalla regola se un prefisso la contiene o ne è contenuto
        "attivita": [
            i for i, divisione in enumerate(divisioni)
            if any(p.startswith(divisione) or divisione.startswith(p) for p in prefissi)
        ],
    }


def rapporti():
    """
    I rapporti fra aziende dai documenti confermati e non riservati, sommati per coppia e verso:
        [{"da": soggetto che vende, "a": soggetto che compra, "quanti": n, "importo": somma}], {soggetto: nome}
    """
    per_coppia, nomi = {}, {}
    for mittente, destinatario, documento in dati_reali.archi_dall_archivio()[0]:
        voce = per_coppia.setdefault((mittente.pk, destinatario.pk), [0, 0.0])
        voce[0] += 1
        voce[1] += float(documento.totale)
        nomi[mittente.pk] = anagrafica.nome_vero(mittente.denominazione) or "senza denominazione"
        nomi[destinatario.pk] = anagrafica.nome_vero(destinatario.denominazione) or "senza denominazione"
    elenco = [
        {"da": da, "a": a, "quanti": quanti, "importo": round(importo, 2)}
        for (da, a), (quanti, importo) in sorted(per_coppia.items())
    ]
    return elenco, nomi


def costruisci(regola=None):
    """
    I dati della pagina per una regola (una RegolaDiRischio, anche non attiva; None = nessuna):
        {"regola": {...} o None, "soglia_z", "assi": {"dipendenti", "fatturato", "attivita"},
         "punti": [...], "esclusi": n, "rapporti": [...], "fuori": {soggetto: nome}}
    "rapporti" è l'elenco di rapporti(); "fuori" dà il nome delle aziende che hanno un
    rapporto ma non sono collocate nello spazio (non hanno dati per periodo).
    Un punto: {"n" soggetto, "nome", "codice", "ateco", "periodo", "d", "f", "a" (posizioni
    sui tre assi), "scatta" (la regola scelta), "altre" (le altre regole attive che scattano),
    "z", "gruppo", "fascicolo"}.
    Per ogni azienda valgono i dati del periodo più recente. Un'azienda a cui manca una
    delle tre coordinate non si può collocare: è contata in "esclusi".
    """
    attive = [r for r in RegolaDiRischio.objects.filter(attiva=True) if regola is None or r.pk != regola.pk]
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
        collocati.append({
            "dato": dato, "d": d, "f": f, "divisione": caratteristiche["attivita"][:2],
            "scatta": regola is not None and calcolo.scatta(regola, caratteristiche),
            "altre": [r.codice for r in attive if calcolo.scatta(r, caratteristiche)],
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
            "nome": anagrafica.nome_vero(dato.soggetto.denominazione) or anagrafica.nome_vero(dato.denominazione)
            or "senza denominazione",
            "codice": str(identificativi[0]) if identificativi else "",
            "ateco": dato.codice_attivita, "periodo": dato.periodo,
            "d": punto["d"], "f": punto["f"], "a": posto_a[punto["divisione"]],
            "scatta": punto["scatta"], "altre": punto["altre"],
            "z": round(punto["z"], 2), "gruppo": punto["gruppo"],
            "fascicolo": fascicoli.get(dato.soggetto_id),
        })
    elenco, nomi = rapporti()
    collocate = {punto["n"] for punto in punti}
    return {
        "rapporti": elenco,
        "fuori": {str(numero): nome for numero, nome in nomi.items() if numero not in collocate},
        "regola": None if regola is None else {
            "codice": regola.codice, "descrizione": regola.descrizione, "tipo": regola.tipo,
            "peso": float(regola.peso), "attiva": regola.attiva,
            "dentro": _dentro_la_regola(regola, dipendenti, fatturato, divisioni),
        },
        "soglia_z": SOGLIA_Z,
        "assi": {
            "dipendenti": [{"codice": c, "descrizione": d} for c, d in dipendenti],
            "fatturato": [{"codice": c, "descrizione": d} for c, d in fatturato],
            "attivita": [{"codice": divisione, "descrizione": f"attività {divisione}"} for divisione in divisioni],
        },
        "punti": punti, "esclusi": esclusi,
    }


# =====================================================================
# IN PAROLE, PER LA CHAT
# =====================================================================
MASSIMO_IN_ELENCO = 10


def trova_regola(cercata):
    """
    La regola indicata con il codice o con parole del codice o della descrizione.
    Vuoto = la prima regola attiva. Restituisce (regola, "") oppure (None, messaggio).
    """
    regole = list(RegolaDiRischio.objects.order_by("-attiva", "codice"))
    if not regole:
        return None, "Non è definita nessuna regola di rischio."
    cercata = " ".join(str(cercata or "").split()).lower()
    if not cercata:
        return regole[0], ""
    esatte = [r for r in regole if r.codice.lower() == cercata]
    simili = esatte or [r for r in regole if cercata in r.codice.lower() or cercata in r.descrizione.lower()]
    if len(simili) == 1:
        return simili[0], ""
    elenco = "\n".join(f"- {r.codice}: {r.descrizione}" for r in (simili or regole))
    quale = "Più regole corrispondono" if simili else "Nessuna regola corrisponde"
    return None, f"{quale} a «{cercata}». Regole definite:\n{elenco}"


def _segni(punto, soglia_z):
    segni = []
    if punto["scatta"]:
        segni.append("la regola scatta")
    if abs(punto["z"]) >= soglia_z:
        segni.append(f"si discosta dalle aziende simili (z {punto['z']:+.2f})")
    return ", ".join(segni) or "nessuna segnalazione"


def racconta(utente, regola="", azienda=""):
    """
    Lo spazio degli indici in parole. Restituisce (testo, parametri del collegamento alla
    pagina o None): senza azienda il quadro della regola, con un'azienda la sua posizione,
    se la regola scatta, quanto si discosta e i suoi rapporti con le altre aziende.
    """
    if not utente.has_perm("indici.view_regoladirischio"):
        return "L'utente non ha il diritto di consultare gli indici di rischio.", None
    scelta, messaggio = trova_regola(regola)
    if scelta is None:
        return messaggio, None
    dati = costruisci(scelta)
    punti, soglia_z = {p["n"]: p for p in dati["punti"]}, dati["soglia_z"]
    parametri = {"regola": scelta.codice}
    righe = [
        f"Regola {scelta.codice}: {scelta.descrizione}" + ("" if scelta.attiva else " (non attiva)"),
        f"Condizioni: attività che comincia per {scelta.prefissi_attivita or 'qualsiasi'}; "
        f"classe di dipendenti {scelta.classi_dipendenti or 'qualsiasi'}; "
        f"classe di fatturato {scelta.classi_fatturato or 'qualsiasi'}.",
    ]

    if str(azienda or "").strip():
        soggetto, messaggio = elaborazione.trova_azienda(azienda)
        if soggetto is None:
            return messaggio, None
        nome = anagrafica.nome_vero(soggetto.denominazione) or "senza denominazione"
        punto = punti.get(soggetto.pk)
        if punto is None:
            righe.append(f"\n{nome}: non è collocata nello spazio, perché non ha dati per periodo completi "
                         "(attività, dipendenti, fatturato).")
        else:
            parametri["azienda"] = soggetto.pk
            assi = dati["assi"]
            righe.append(
                f"\n{punto['nome']} ({punto['codice']}), dati del periodo {punto['periodo']}: attività {punto['ateco']}; "
                f"{assi['dipendenti'][punto['d']]['descrizione']}; {assi['fatturato'][punto['f']]['descrizione']}."
            )
            righe.append(f"La regola {'SCATTA' if punto['scatta'] else 'non scatta'}.")
            if punto["altre"]:
                righe.append("Altre regole attive che scattano: " + ", ".join(punto["altre"]) + ".")
            righe.append(
                f"z-score robusto del fatturato rispetto al personale: {punto['z']:+.2f} "
                f"(confronto con {punto['gruppo']}; soglia {soglia_z}): "
                + ("si discosta dalle aziende simili." if abs(punto["z"]) >= soglia_z else "nella norma.")
            )
        suoi = [r for r in dati["rapporti"] if soggetto.pk in (r["da"], r["a"])]
        righe.append(f"\nRapporti dai documenti confermati ({len(suoi)}):" if suoi else "\nNessun rapporto dai documenti confermati.")
        for rapporto in sorted(suoi, key=lambda r: -r["importo"]):
            altra = rapporto["a"] if rapporto["da"] == soggetto.pk else rapporto["da"]
            verso = "vende a" if rapporto["da"] == soggetto.pk else "compra da"
            if altra in punti:
                chi = f"{punti[altra]['nome']} ({_segni(punti[altra], soglia_z)})"
            else:
                chi = f"{dati['fuori'].get(str(altra), 'azienda')} (non collocata nello spazio)"
            righe.append(f"- {verso} {chi}: {rapporto['quanti']} documenti, importo totale {rapporto['importo']:.2f}")
    else:
        scattano = [p for p in dati["punti"] if p["scatta"]]
        discoste = [p for p in dati["punti"] if abs(p["z"]) >= soglia_z]
        entrambe = [p for p in scattano if abs(p["z"]) >= soglia_z]
        righe.append(
            f"\nAziende collocate: {len(dati['punti'])} (non collocate per dati mancanti: {dati['esclusi']}). "
            f"La regola scatta per {len(scattano)}; si discostano dalle aziende simili {len(discoste)} "
            f"(soglia z {soglia_z}); entrambe le cose {len(entrambe)}. Rapporti fra aziende: {len(dati['rapporti'])}."
        )
        for titolo, elenco in (("La regola scatta e si discostano", entrambe),
                               ("La regola scatta", [p for p in scattano if p not in entrambe]),
                               ("Si discostano senza che la regola scatti", [p for p in discoste if p not in entrambe])):
            if elenco:
                elenco = sorted(elenco, key=lambda p: -abs(p["z"]))
                righe.append(f"\n{titolo} ({len(elenco)}" + (f", le prime {MASSIMO_IN_ELENCO}" if len(elenco) > MASSIMO_IN_ELENCO else "") + "):")
                righe += [
                    f"- {p['nome']} ({p['codice']}): attività {p['ateco']}, z {p['z']:+.2f}"
                    for p in elenco[:MASSIMO_IN_ELENCO]
                ]
    righe.append(
        "\nLa regola dice ciò che una persona ha dichiarato sospetto; lo scostamento ciò che è insolito nei dati. "
        "Nessuno dei due è un'irregolarità accertata."
    )
    return "\n".join(righe), parametri
