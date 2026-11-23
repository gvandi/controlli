"""
ESTRAZIONE CON REGOLE FISSE: ciò che un'espressione regolare legge senza errori
non si chiede al modello (DECISIONI.md, n. 23).

    estrai(testo)             identificativi, date, importi, email, siti
    compare_nel_testo()       la verifica della decisione 25: un valore estratto
                              (da una regola o dal modello) vale solo se si
                              ritrova nel testo del documento

Ogni entità è un dizionario:
    etichetta   come si chiama ciò che è stato trovato (es. "COE")
    valore      come compare nel documento
    normalizzato  forma confrontabile (COE senza prefissi, data AAAA-MM-GG, importo con il punto)
    citazione   il pezzo di testo attorno al valore

Le etichette prodotte qui si collegano alle voci del catalogo per codice: "COE" e
"PARTITA_IVA" sono voci significative; date, importi, email e siti trovati senza
contesto non lo sono, ma si raccolgono comunque (vedi coda.py).

Non usa Django né il database: si prova da solo.
"""
import re

COE = "COE"
PARTITA_IVA = "PARTITA_IVA"
DATA = "DATA"
IMPORTO = "IMPORTO"
EMAIL = "EMAIL"
SITO = "SITO"

_MESI = {
    "gennaio": 1, "febbraio": 2, "marzo": 3, "aprile": 4, "maggio": 5, "giugno": 6, "luglio": 7,
    "agosto": 8, "settembre": 9, "ottobre": 10, "novembre": 11, "dicembre": 12,
}

# Il COE si riconosce solo se introdotto dalla sigla: cinque cifre da sole sono troppo comuni
_COE = re.compile(r"\b(?:C\.?\s?O\.?\s?E\.?|SM)\s*[:.\-]?\s*(?:SM\s*)?(\d{5})\b", re.IGNORECASE)
_PIVA = re.compile(r"\b(?:P\.?\s?IVA|partita\s+iva|VAT)\s*[:.\-]?\s*(?:IT\s*)?(\d{11})\b", re.IGNORECASE)
_DATA_NUMERI = re.compile(r"\b(\d{1,2})[/.\-](\d{1,2})[/.\-](\d{4})\b")
_DATA_ISO = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")
_DATA_MESE = re.compile(r"\b(\d{1,2})°?\s+(" + "|".join(_MESI) + r")\s+(\d{4})\b", re.IGNORECASE)
_IMPORTO = re.compile(
    r"(?:(?:€|EUR|euro)\s*(\d{1,3}(?:\.\d{3})*(?:,\d{2})?|\d+(?:,\d{2})?))"
    r"|(?:(\d{1,3}(?:\.\d{3})*(?:,\d{2})?|\d+(?:,\d{2})?)\s*(?:€|EUR|euro)\b)",
    re.IGNORECASE,
)
_EMAIL = re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")
_SITO = re.compile(r"\b(?:https?://|www\.)[A-Za-z0-9.\-]+\.[A-Za-z]{2,}(?:/[^\s<>\"']*)?", re.IGNORECASE)


def _citazione(testo, inizio, fine, margine=40):
    return " ".join(testo[max(0, inizio - margine):fine + margine].split())


def _data(anno, mese, giorno):
    """AAAA-MM-GG se è una data possibile, altrimenti None."""
    anno, mese, giorno = int(anno), int(mese), int(giorno)
    if not (1900 <= anno <= 2100 and 1 <= mese <= 12 and 1 <= giorno <= 31):
        return None
    return f"{anno:04d}-{mese:02d}-{giorno:02d}"


def estrai(testo):
    """Le entità che le regole riconoscono nel testo, senza ripetizioni, nell'ordine in cui compaiono."""
    trovate, viste = [], set()

    def aggiungi(etichetta, valore, normalizzato, corrispondenza):
        if normalizzato and (etichetta, normalizzato) not in viste:
            viste.add((etichetta, normalizzato))
            trovate.append({
                "etichetta": etichetta, "valore": valore.strip(), "normalizzato": normalizzato,
                "citazione": _citazione(testo, corrispondenza.start(), corrispondenza.end()),
                "posizione": corrispondenza.start(),
            })

    for c in _COE.finditer(testo):
        aggiungi(COE, c.group(0), c.group(1), c)
    for c in _PIVA.finditer(testo):
        aggiungi(PARTITA_IVA, c.group(0), c.group(1), c)
    for c in _DATA_NUMERI.finditer(testo):
        aggiungi(DATA, c.group(0), _data(c.group(3), c.group(2), c.group(1)), c)
    for c in _DATA_ISO.finditer(testo):
        aggiungi(DATA, c.group(0), _data(c.group(1), c.group(2), c.group(3)), c)
    for c in _DATA_MESE.finditer(testo):
        aggiungi(DATA, c.group(0), _data(c.group(3), _MESI[c.group(2).lower()], c.group(1)), c)
    for c in _IMPORTO.finditer(testo):
        cifre = c.group(1) or c.group(2)
        aggiungi(IMPORTO, c.group(0), cifre.replace(".", "").replace(",", "."), c)
    for c in _EMAIL.finditer(testo):
        aggiungi(EMAIL, c.group(0), c.group(0).lower(), c)
    for c in _SITO.finditer(testo):
        aggiungi(SITO, c.group(0), c.group(0).lower().rstrip(".,;"), c)

    trovate.sort(key=lambda e: e.pop("posizione"))
    return trovate


def citazione_dal_testo(valore, testo):
    """Il punto del testo in cui compare il valore, con un po' di contesto; "" se non compare alla lettera."""
    inizio = testo.lower().find(valore.strip().lower()) if valore.strip() else -1
    return _citazione(testo, inizio, inizio + len(valore.strip())) if inizio >= 0 else ""


def _compatto(testo):
    """Minuscolo e senza spazi né punteggiatura: 'S.r.l.' e 'SRL', '1.234,56' e '1234,56' coincidono."""
    return re.sub(r"[\W_]+", "", str(testo).lower())


def compare_nel_testo(valore, testo):
    """
    Vero se il valore si ritrova nel testo, a meno di maiuscole, spazi e punteggiatura.
    È il controllo contro i valori inventati: ciò che non compare nel documento non
    entra nei dati (DECISIONI.md, n. 25).
    """
    cercato = _compatto(valore)
    return len(cercato) >= 2 and cercato in _compatto(testo)
