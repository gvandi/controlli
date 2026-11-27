"""
CALCOLO DELL'INDICE A REGOLE (DECISIONI.md, n. 87).

    soggetti.DatiPerPeriodo  --+
    decodifiche (classi)     --+-->  regole che scattano  -->  grafo: un'esecuzione
    indici.RegolaDiRischio   --+                               "calcolo 1.0+regole / dati N"

Per ogni azienda della fotografia dei dati reali si prendono i dati del periodo più
recente, si calcolano le classi (di dipendenti e di fatturato) e si guarda quali
regole scattano. Il punteggio di un tipo di irregolarità combina i pesi delle regole
scattate: 1 - (1 - p1)(1 - p2)..., così due regole contano più di una e non si supera 1.

Il risultato è registrato come un'ESECUZIONE dell'analisi di rete con una versione
del calcolo propria (contratto.VERSIONE_CALCOLO_REGOLE), distinta da quella della
GNN: gli strumenti della chat la leggono come le altre, e resta sempre scritto con
quale calcolo è stata data una risposta. La spiegazione di un punteggio è l'elenco
delle regole scattate.

Un dato che manca non fa scattare nulla: mancante non è zero.
"""
import datetime

from django.db import transaction

from decodifiche.models import ClasseDipendenti, ClasseFatturato
from grafo import contratto, dati_reali, scrittura
from grafo.models import DatiSoggetto
from soggetti.models import DatiPerPeriodo

from .models import RegolaDiRischio

SOGLIA = 0.5


def _valori(testo):
    return [valore.strip().upper() for valore in testo.split(",") if valore.strip()]


def descrivi(dato):
    """
    Le caratteristiche su cui lavorano le regole, da una riga di DatiPerPeriodo:
        {"periodo", "attivita", "classe_dipendenti", "classe_fatturato"}   (codici, o "" se non noti)
    Se la fonte ha dato direttamente la classe si usa quella; altrimenti la classe si
    calcola dal valore, con le classi valide alla fine dell'anno del periodo.
    """
    giorno = datetime.date(int(dato.periodo[:4]), 12, 31)
    dipendenti = ClasseDipendenti.per_valore(dato.dipendenti, giorno) if dato.dipendenti is not None else None
    fatturato = ClasseFatturato.per_valore(dato.fatturato, giorno) if dato.fatturato is not None else None
    return {
        "periodo": dato.periodo,
        "attivita": dato.codice_attivita.strip().upper(),
        "classe_dipendenti": (dato.classe_dipendenti or (dipendenti.codice if dipendenti else "")).upper(),
        "classe_fatturato": (dato.classe_fatturato or (fatturato.codice if fatturato else "")).upper(),
    }


def scatta(regola, caratteristiche):
    """Vero se valgono TUTTE le condizioni compilate della regola. Una regola senza condizioni non scatta mai."""
    prefissi, dipendenti, fatturato = (
        _valori(regola.prefissi_attivita), _valori(regola.classi_dipendenti), _valori(regola.classi_fatturato)
    )
    if not (prefissi or dipendenti or fatturato):
        return False
    if prefissi and not any(caratteristiche["attivita"].startswith(p) for p in prefissi if caratteristiche["attivita"]):
        return False
    if dipendenti and caratteristiche["classe_dipendenti"] not in dipendenti:
        return False
    if fatturato and caratteristiche["classe_fatturato"] not in fatturato:
        return False
    return True


def punteggi(scattate):
    """Dalle regole scattate per un'azienda ai punteggi per tipo, nell'ordine della tassonomia."""
    restante = {tipo: 1.0 for tipo in contratto.TIPI_IRREGOLARITA}
    for regola in scattate:
        restante[regola.tipo] *= 1.0 - float(regola.peso)
    return [round(1.0 - restante[tipo], 4) for tipo in contratto.TIPI_IRREGOLARITA]


@transaction.atomic
def esegui(criteri=None):
    """
    criteri: che cosa è ammesso oltre ai documenti confermati (elaborazione/ammissione.py;
    None = quelli predefiniti). Il resoconto riporta anche "relazioni" e "non_verificate".

    Prende la fotografia dei dati reali (ne crea una nuova se l'archivio è cambiato),
    applica le regole attive e registra l'esecuzione. Restituisce un resoconto:
        {"versione_dati", "esecuzione", "aziende": n, "senza_dati": n, "segnalate": n, "regole": n}
    Senza dati reali "esecuzione" è None.
    """
    fotografia = dati_reali.fotografa(criteri=criteri)
    versione_dati = fotografia["versione_dati"]
    resoconto = {
        "versione_dati": versione_dati, "esecuzione": None, "aziende": 0, "senza_dati": 0, "segnalate": 0,
        "relazioni": fotografia["relazioni"], "non_verificate": fotografia["non_verificate"], "criteri": fotografia["criteri"],
    }
    regole = [
        regola for regola in RegolaDiRischio.objects.filter(attiva=True)
        if regola.tipo in contratto.TIPI_IRREGOLARITA
    ]
    resoconto["regole"] = len(regole)
    if versione_dati is None:
        return resoconto

    nodi = list(
        DatiSoggetto.objects.filter(versione_dati=versione_dati).select_related("soggetto").order_by("soggetto_id")
    )
    # Per ogni soggetto dell'anagrafica, i dati del periodo più recente
    numeri = {nodo.soggetto_id: dati_reali.soggetto_dell_anagrafica(nodo.soggetto.riferimento) for nodo in nodi}
    recenti = {}
    for dato in DatiPerPeriodo.objects.filter(soggetto__in=[n for n in numeri.values() if n]).order_by("periodo"):
        recenti[dato.soggetto_id] = dato

    soggetti_per_nodo, punteggi_nodi, spiegazioni = [], [], []
    for nodo in nodi:
        dato = recenti.get(numeri[nodo.soggetto_id])
        scattate = [r for r in regole if scatta(r, descrivi(dato))] if dato is not None else []
        valori = punteggi(scattate)
        soggetti_per_nodo.append(nodo.soggetto_id)
        punteggi_nodi.append(valori)
        resoconto["senza_dati"] += dato is None
        resoconto["segnalate"] += any(valore >= SOGLIA for valore in valori)
        for tipo in {regola.tipo for regola in scattate}:
            spiegazioni.append({
                "schema": contratto.SCHEMA_SPIEGAZIONE,
                "soggetto": nodo.soggetto_id,
                "tipo_irregolarita": tipo,
                "features": [
                    {
                        "indice": posizione, "tipo": "regola", "peso": float(regola.peso),
                        "descrizione": f"Regola {regola.codice}: {regola.descrizione} (dati del periodo {dato.periodo})",
                    }
                    for posizione, regola in enumerate(scattate) if regola.tipo == tipo
                ],
                "relazioni": [], "impatto_testo": 0.0, "impatto_strutturati": 1.0,
            })
    resoconto["aziende"] = len(nodi)
    esecuzione = scrittura.registra_esecuzione(
        versione_dati, soggetti_per_nodo, punteggi_nodi, [SOGLIA] * contratto.NUM_TIPI,
        {"metodo": "regole", "regole": sorted(regola.codice for regola in regole)},
        versione_calcolo=contratto.VERSIONE_CALCOLO_REGOLE,
    )
    for spiegazione in spiegazioni:
        scrittura.salva_spiegazione(esecuzione, spiegazione)
    resoconto["esecuzione"] = esecuzione
    return resoconto
