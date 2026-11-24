"""
IMPORTAZIONE DELL'ANAGRAFICA PER PERIODO da un file CSV (DECISIONI.md, n. 86).

Colonne (la prima riga porta i nomi; l'ordine non conta; separatore ; oppure ,):

    coe            codice operatore economico            } almeno uno dei due;
    piva           partita IVA italiana                  } se ci sono entrambi vale il COE
    periodo        anno (2025) oppure anno e mese (2025-03)
    denominazione  facoltativa
    ateco          codice dell'attività economica, facoltativo
    dipendenti     numero intero, facoltativo (vuoto = non noto)
    fatturato      importo, facoltativo: 350.000,00 oppure 350000.00

La chiave di una riga è identificativo + periodo: reimportare lo stesso soggetto
per lo stesso periodo AGGIORNA la riga, un periodo nuovo ne aggiunge una.
Una riga sbagliata non ferma l'importazione: viene saltata e riportata con il motivo.
Il soggetto che non esiste viene creato, con il suo fascicolo nel faldone Aziende;
un soggetto che arriva dall'anagrafica non è più provvisorio.
"""
import csv
import decimal
import io
import re

from django.core.exceptions import ValidationError
from django.db import transaction

from archivio import servizi as archivio
from decodifiche.models import TipoIdentificativo
from soggetti import servizi as anagrafica
from soggetti.models import DatiPerPeriodo, Soggetto, periodo_valido

COLONNE = ("coe", "piva", "periodo", "denominazione", "ateco", "dipendenti", "fatturato")
TIPO_PER_COLONNA = (("coe", "COE"), ("piva", "PIVA_IT"))


class RigaNonValida(Exception):
    pass


def _importo(testo):
    cifre = re.sub(r"[^\d.,-]", "", testo)
    if "," in cifre:
        cifre = cifre.replace(".", "").replace(",", ".")
    elif re.fullmatch(r"-?\d{1,3}(\.\d{3})+", cifre):
        cifre = cifre.replace(".", "")
    try:
        importo = decimal.Decimal(cifre).quantize(decimal.Decimal("0.01"))
    except decimal.InvalidOperation:
        raise RigaNonValida(f"fatturato non leggibile: {testo!r}")
    if importo < 0 or importo >= 10 ** 14:
        raise RigaNonValida(f"fatturato fuori misura: {testo!r}")
    return importo


def _una_riga(riga, tipi, fonte):
    """Scrive una riga del file. Restituisce True se ha creato, False se ha aggiornato."""
    periodo = riga["periodo"]
    try:
        periodo_valido(periodo)
    except ValidationError:
        raise RigaNonValida(f"periodo non valido: {periodo!r} (atteso 2025 oppure 2025-03)")
    colonna, tipo = next(((c, tipi.get(t)) for c, t in TIPO_PER_COLONNA if riga[c]), (None, None))
    if colonna is None:
        raise RigaNonValida("manca l'identificativo (coe oppure piva)")
    if tipo is None:
        raise RigaNonValida(f"tipo di identificativo non presente nelle decodifiche per la colonna {colonna}")
    dipendenti = None
    if riga["dipendenti"]:
        if not riga["dipendenti"].isdigit():
            raise RigaNonValida(f"dipendenti non è un numero intero: {riga['dipendenti']!r}")
        dipendenti = int(riga["dipendenti"])
    fatturato = _importo(riga["fatturato"]) if riga["fatturato"] else None
    try:
        fascicolo = archivio.acquisisci_azienda(tipo, riga[colonna], riga["denominazione"])
    except anagrafica.IdentificativoNonValido as problema:
        raise RigaNonValida(str(problema))
    Soggetto.objects.filter(pk=fascicolo.soggetto_id, provvisorio=True).update(provvisorio=False)
    _, creata = DatiPerPeriodo.objects.update_or_create(
        soggetto_id=fascicolo.soggetto_id, periodo=periodo,
        defaults={
            "denominazione": riga["denominazione"][:255], "codice_attivita": riga["ateco"][:20],
            "dipendenti": dipendenti, "fatturato": fatturato, "fonte": fonte[:120],
        },
    )
    return creata


def importa(testo, fonte=""):
    """
    Importa il contenuto di un file CSV. Restituisce
        {"create": n, "aggiornate": n, "rifiutate": [(numero di riga, motivo)]}
    Solleva RigaNonValida se manca la riga dei nomi o una colonna obbligatoria.
    """
    testo = testo.lstrip("\ufeff")
    prima = testo.splitlines()[0] if testo.strip() else ""
    lettore = csv.DictReader(io.StringIO(testo), delimiter=";" if prima.count(";") >= prima.count(",") else ",")
    nomi = {(nome or "").strip().lower(): nome for nome in (lettore.fieldnames or [])}
    if "periodo" not in nomi or not ({"coe", "piva"} & set(nomi)):
        raise RigaNonValida("La prima riga deve nominare le colonne: servono 'periodo' e almeno una fra 'coe' e 'piva'.")
    tipi = {t.codice: t for t in TipoIdentificativo.objects.filter(codice__in=[t for _, t in TIPO_PER_COLONNA])}
    resoconto = {"create": 0, "aggiornate": 0, "rifiutate": []}
    for numero, grezza in enumerate(lettore, start=2):
        riga = {c: " ".join(str(grezza.get(nomi.get(c, "")) or "").split()) for c in COLONNE}
        if not any(riga.values()):
            continue
        try:
            with transaction.atomic():
                creata = _una_riga(riga, tipi, fonte)
            resoconto["create" if creata else "aggiornate"] += 1
        except RigaNonValida as problema:
            resoconto["rifiutate"].append((numero, str(problema)))
    return resoconto
