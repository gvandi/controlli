"""
INGRESSO DEI FILE: controlli su ciò che arriva da fuori, prima di salvarlo.

  pulisci_percorso()   il percorso con cui un file è arrivato, reso innocuo
  apri_zip()           le voci di un archivio ZIP, una alla volta, con i limiti
                       della decisione 68

Un nome di file e un archivio caricati da un utente sono dati non fidati: un
percorso può tentare di uscire dalla cartella ("../../etc"), un archivio può
dichiarare dimensioni false o contenere milioni di file.

Non usa Django né il database: si prova da solo.
"""
import zipfile

MASSIMO_PERCORSO = 500
# Archivi dentro l'archivio: non si aprono e non si accettano
ESTENSIONI_ARCHIVIO = (".zip", ".7z", ".rar", ".tar", ".gz", ".tgz", ".bz2", ".xz")
BLOCCO = 1024 * 1024


class ArchivioNonValido(Exception):
    """Il file ZIP non si può aprire o supera i limiti: non ne viene accettato nulla."""


def pulisci_percorso(testo):
    """
    Riduce un percorso ricevuto a una forma innocua: barre in avanti, niente
    cartelle vuote o ".", nessuna barra iniziale. Restituisce None se il percorso
    non è accettabile (vuoto, con "..", con caratteri di controllo, troppo lungo).
    """
    testo = str(testo or "").replace("\\", "/")
    if any(ord(carattere) < 32 for carattere in testo):
        return None
    parti = [parte.strip() for parte in testo.split("/")]
    parti = [parte for parte in parti if parte not in ("", ".")]
    if not parti or ".." in parti or ":" in parti[0]:
        return None
    pulito = "/".join(parti)
    return pulito if len(pulito) <= MASSIMO_PERCORSO else None


def e_un_archivio(percorso):
    return percorso.lower().endswith(ESTENSIONI_ARCHIVIO)


def apri_zip(file_zip, massimo_file, massimo_byte):
    """
    Apre un archivio ZIP e restituisce (voci, rifiutate):
      voci        elenco di (percorso pulito, funzione che restituisce i blocchi del contenuto)
      rifiutate   elenco di (nome nell'archivio, motivo) per le voci scartate una a una

    Solleva ArchivioNonValido, senza accettare nulla, se il file non è uno ZIP,
    se contiene troppe voci o se la dimensione dichiarata supera il limite.
    La dimensione dichiarata può mentire: chi legge i blocchi deve comunque
    contare i byte veri (deposito.salva con il suo limite).
    """
    try:
        archivio = zipfile.ZipFile(file_zip)
    except (zipfile.BadZipFile, OSError):
        raise ArchivioNonValido("Il file non è un archivio ZIP leggibile.")
    informazioni = [voce for voce in archivio.infolist() if not voce.is_dir()]
    if len(informazioni) > massimo_file:
        raise ArchivioNonValido(f"L'archivio contiene {len(informazioni)} file: il massimo è {massimo_file}.")
    if sum(voce.file_size for voce in informazioni) > massimo_byte:
        raise ArchivioNonValido("L'archivio, una volta aperto, supera la dimensione massima consentita.")

    voci, rifiutate, visti = [], [], set()
    for voce in informazioni:
        percorso = pulisci_percorso(voce.filename)
        if percorso is None:
            rifiutate.append((voce.filename, "percorso non ammesso"))
        elif voce.flag_bits & 0x1:
            rifiutate.append((voce.filename, "protetto da password"))
        elif e_un_archivio(percorso):
            rifiutate.append((voce.filename, "archivio dentro l'archivio"))
        elif percorso in visti:
            rifiutate.append((voce.filename, "percorso ripetuto nell'archivio"))
        else:
            visti.add(percorso)
            voci.append((percorso, _lettore(archivio, voce)))
    return voci, rifiutate


def _lettore(archivio, voce):
    def blocchi():
        with archivio.open(voce) as contenuto:
            while True:
                blocco = contenuto.read(BLOCCO)
                if not blocco:
                    return
                yield blocco
    return blocchi
