"""
DEPOSITO DEI FILE: dove sta fisicamente il contenuto dei file caricati.

Ogni contenuto è salvato UNA volta sola, sotto un nome ricavato dalla sua
impronta SHA-256 (DECISIONI.md, n. 64):

    <deposito>/ab/abcdef...        (le prime due cifre fanno da sottocartella)

Conseguenze: due file omonimi non si scontrano; lo stesso contenuto caricato due
volte occupa spazio una volta; un file non si sposta e non si riscrive mai, quindi
l'impronta prova che è quello ricevuto. I nomi e i percorsi con cui i file sono
arrivati stanno nel database (FileCaricato), non qui.

Non usa Django né il database: riceve la cartella del deposito da chi lo chiama.
Per questo si prova da solo.
"""
import hashlib
import os
import pathlib
import tempfile


class TroppoGrande(Exception):
    """Il contenuto supera il limite indicato: nulla è stato salvato."""


def percorso(cartella, impronta):
    """Dove sta (o starà) il contenuto con quell'impronta."""
    return pathlib.Path(cartella) / impronta[:2] / impronta


def salva(cartella, blocchi, limite=None):
    """
    Scrive nel deposito il contenuto ricevuto a blocchi (bytes).
    Restituisce (impronta, dimensione). Se il contenuto c'è già non lo riscrive.
    Con un limite, solleva TroppoGrande appena lo si supera.
    """
    cartella = pathlib.Path(cartella)
    cartella.mkdir(parents=True, exist_ok=True)
    calcolo, dimensione = hashlib.sha256(), 0
    # Si scrive in un file temporaneo nella stessa cartella: lo spostamento finale è
    # istantaneo, e un'interruzione a metà non lascia nel deposito un file monco.
    numero, provvisorio = tempfile.mkstemp(dir=cartella, prefix="in-arrivo-")
    try:
        with os.fdopen(numero, "wb") as uscita:
            for blocco in blocchi:
                dimensione += len(blocco)
                if limite is not None and dimensione > limite:
                    raise TroppoGrande()
                calcolo.update(blocco)
                uscita.write(blocco)
        impronta = calcolo.hexdigest()
        destinazione = percorso(cartella, impronta)
        if destinazione.exists():
            os.unlink(provvisorio)
        else:
            destinazione.parent.mkdir(parents=True, exist_ok=True)
            os.replace(provvisorio, destinazione)
            os.chmod(destinazione, 0o440)  # sola lettura: l'originale non si modifica
    except BaseException:
        if os.path.exists(provvisorio):
            os.unlink(provvisorio)
        raise
    return impronta, dimensione


def elimina(cartella, impronta):
    """Toglie un contenuto dal deposito. Chi chiama ha già verificato che nessun file lo usa."""
    destinazione = percorso(cartella, impronta)
    if destinazione.exists():
        os.chmod(destinazione, 0o640)
        destinazione.unlink()
