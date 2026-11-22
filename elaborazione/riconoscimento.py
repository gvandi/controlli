"""
RICONOSCIMENTO: che cos'è un file, guardando i suoi primi byte.

Il nome e l'estensione li sceglie chi carica e possono essere sbagliati; i primi
byte no. La natura decide quale lettore può occuparsi del file.

Non usa Django né il database: si prova da solo.
"""
PDF = "pdf"
IMMAGINE = "immagine"
XML = "xml"
TESTO = "testo"
ALTRO = "altro"

_FIRME_IMMAGINE = (b"\xff\xd8\xff", b"\x89PNG\r\n\x1a\n", b"II*\x00", b"MM\x00*", b"BM")


def natura(primi_byte):
    """La natura del file dai suoi primi byte (ne bastano un migliaio)."""
    inizio = bytes(primi_byte[:2048])
    if inizio.lstrip()[:5] == b"%PDF-":
        return PDF
    if inizio.startswith(_FIRME_IMMAGINE):
        return IMMAGINE
    senza_bom = inizio.lstrip(b"\xef\xbb\xbf").lstrip()
    if senza_bom.startswith(b"<?xml") or senza_bom.startswith(b"<"):
        return XML
    if not inizio:
        return ALTRO
    try:
        testo = inizio.decode("utf-8")
    except UnicodeDecodeError:
        # un carattere a più byte può essere stato tagliato in fondo: si riprova senza la coda
        try:
            testo = inizio[:-3].decode("utf-8")
        except UnicodeDecodeError:
            return ALTRO
    stampabili = sum(1 for c in testo if c.isprintable() or c in "\r\n\t")
    return TESTO if testo and stampabili / len(testo) > 0.95 else ALTRO
