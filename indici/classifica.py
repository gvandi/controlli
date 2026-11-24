"""
LE AZIENDE PIÙ RISCHIOSE, PER CRITERIO (DECISIONI.md, n. 92).

Alla domanda "quali sono le aziende più rischiose?" non c'è una sola risposta: ci sono
più criteri, indipendenti fra loro, e la risposta deve dire quale criterio ha portato
a ciascun nome. Qui si raccolgono quelli che vengono dagli indici e dai rapporti:

    1. REGOLE          le regole di rischio che scattano per l'azienda (tutte quelle attive,
                       oppure la sola regola indicata); l'indice combina i loro pesi
    2. SCOSTAMENTO     l'azienda si discosta dalle aziende simili (z-score robusto del
                       fatturato rispetto al personale): vedi indici/spazio.py
    3. RAPPORTI        l'azienda ha documenti confermati con aziende segnalate dai criteri 1 o 2

Il quarto criterio, il punteggio della GNN sulla rete dei rapporti, lo aggiunge lo
strumento "classifica" del servizio MCP (grafo/servizio_mcp.py), che è l'unico a
leggere l'archivio dell'analisi di rete.

In testa alla risposta stanno le aziende segnalate da PIÙ criteri: sono quelle su cui
criteri diversi concordano.
"""
import collections

from . import spazio
from .models import RegolaDiRischio

REGOLE, SCOSTAMENTO, RAPPORTI = "regole", "scostamento", "rapporti con aziende segnalate"


def _indice(pesi):
    """Più regole si combinano senza superare 1: 1 - (1 - p1)(1 - p2)..."""
    resto = 1.0
    for peso in pesi:
        resto *= 1.0 - peso
    return round(1.0 - resto, 4)


def criteri(regola=None):
    """
    Per ogni criterio, le aziende che segnala, dalla più alla meno rilevante:
        {"punti": {soggetto: punto}, "fuori": {...}, "soglia_z": x, "regole": [RegolaDiRischio],
         "regole_scattate": [(soggetto, indice, [codici])], "scostamento": [(soggetto, z)],
         "rapporti": [(soggetto, [(altra, [criteri dell'altra], quanti, importo)], importo totale)]}
    regola: una sola regola al posto di tutte quelle attive.
    """
    dati = spazio.costruisci(regola)
    punti = {p["n"]: p for p in dati["punti"]}
    regole = [regola] if regola is not None else list(RegolaDiRischio.objects.filter(attiva=True))
    peso = {r.codice: float(r.peso) for r in regole}

    scattate = []
    for numero, punto in punti.items():
        codici = ([regola.codice] if punto["scatta"] else []) if regola is not None else punto["altre"]
        if codici:
            scattate.append((numero, _indice(peso[c] for c in codici), sorted(codici)))
    scattate.sort(key=lambda voce: (-voce[1], punti[voce[0]]["nome"]))

    discoste = [(numero, p["z"]) for numero, p in punti.items() if abs(p["z"]) >= dati["soglia_z"]]
    discoste.sort(key=lambda voce: (-abs(voce[1]), punti[voce[0]]["nome"]))

    # Chi ha rapporti con un'azienda segnalata dai primi due criteri
    segnalate = collections.defaultdict(list)
    for numero, _, _ in scattate:
        segnalate[numero].append(REGOLE)
    for numero, _ in discoste:
        segnalate[numero].append(SCOSTAMENTO)
    vicine = collections.defaultdict(list)
    for rapporto in dati["rapporti"]:
        for questa, altra in ((rapporto["da"], rapporto["a"]), (rapporto["a"], rapporto["da"])):
            if altra in segnalate:
                vicine[questa].append((altra, segnalate[altra], rapporto["quanti"], rapporto["importo"]))
    collegate = [(numero, elenco, round(sum(v[3] for v in elenco), 2)) for numero, elenco in vicine.items()]
    collegate.sort(key=lambda voce: (-len(voce[1]), -voce[2]))

    return {
        "punti": punti, "fuori": dati["fuori"], "soglia_z": dati["soglia_z"], "regole": regole,
        "regole_scattate": scattate, "scostamento": discoste, "rapporti": collegate,
    }


def racconta(utente, n=3, regola=""):
    """
    Le aziende più rischiose secondo indici e rapporti, in parole, un criterio alla volta.
    Restituisce il testo; n = quante aziende per criterio; regola = "" per tutte le regole attive.
    """
    if not utente.has_perm("indici.view_regoladirischio"):
        return "Criteri degli indici (regole, scostamento, rapporti): l'utente non ha il diritto di consultarli."
    scelta = None
    if str(regola or "").strip():
        scelta, messaggio = spazio.trova_regola(regola)
        if scelta is None:
            return messaggio
    c = criteri(scelta)
    punti, fuori = c["punti"], c["fuori"]

    def nome(numero):
        if numero in punti:
            return f"{punti[numero]['nome']} ({punti[numero]['codice']})" if punti[numero]["codice"] else punti[numero]["nome"]
        return f"{fuori.get(str(numero), 'azienda')} (senza dati per periodo)"

    def titolo(testo, elenco):
        quante = f"{len(elenco)} aziende" if len(elenco) != 1 else "1 azienda"
        return f"\n{testo}: {quante}" + (f", le prime {n}" if len(elenco) > n else "") + ("." if not elenco else ":")

    per_azienda = collections.defaultdict(list)
    for numero, _, _ in c["regole_scattate"]:
        per_azienda[numero].append(REGOLE)
    for numero, _ in c["scostamento"]:
        per_azienda[numero].append(SCOSTAMENTO)
    for numero, _, _ in c["rapporti"]:
        per_azienda[numero].append(RAPPORTI)
    concordi = sorted(
        ((numero, elenco) for numero, elenco in per_azienda.items() if len(elenco) > 1),
        key=lambda voce: (-len(voce[1]), nome(voce[0])),
    )

    righe = [f"Aziende collocate con i dati per periodo: {len(punti)}."]
    righe.append(titolo("SEGNALATE DA PIÙ CRITERI", concordi))
    righe += [f"- {nome(numero)}: {' + '.join(elenco)}" for numero, elenco in concordi[:n]]

    if scelta is not None:
        quali = f"la sola regola {scelta.codice} ({scelta.descrizione})"
    elif c["regole"]:
        quali = "tutte le regole attive: " + ", ".join(sorted(r.codice for r in c["regole"]))
    else:
        quali = "nessuna regola attiva è definita"
    righe.append(titolo(f"CRITERIO 1 - REGOLE DI RISCHIO ({quali})", c["regole_scattate"]))
    for numero, indice, codici in c["regole_scattate"][:n]:
        p = punti[numero]
        righe.append(f"- {nome(numero)}: indice {indice:.2f}; regole scattate: {', '.join(codici)}; attività {p['ateco']}")

    righe.append(titolo(
        f"CRITERIO 2 - SCOSTAMENTO DALLE AZIENDE SIMILI (z-score robusto del fatturato rispetto al personale, soglia {c['soglia_z']})",
        c["scostamento"],
    ))
    for numero, z in c["scostamento"][:n]:
        righe.append(f"- {nome(numero)}: z {z:+.2f}, confronto con {punti[numero]['gruppo']}; attività {punti[numero]['ateco']}")

    righe.append(titolo("CRITERIO 3 - RAPPORTI CON AZIENDE SEGNALATE (dai documenti confermati)", c["rapporti"]))
    for numero, elenco, importo in c["rapporti"][:n]:
        altre = "; ".join(f"{nome(altra)} [{', '.join(perche)}], {quanti} documenti" for altra, perche, quanti, _ in elenco)
        righe.append(f"- {nome(numero)}: {altre}; importo totale {importo:.2f}")
    return "\n".join(righe)
