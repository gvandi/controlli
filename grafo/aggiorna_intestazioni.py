"""
Ricopia in testa a ogni file del pacchetto le novità della sua parte, lette da NOVITA.md.

    python grafo/aggiorna_intestazioni.py             riscrive le intestazioni
    python grafo/aggiorna_intestazioni.py --verifica  controlla soltanto (esce con 1 se non coincidono)

Le intestazioni stanno fra le righe "# >>> NOVITA" e "# <<< NOVITA" e non vanno
modificate a mano: si modifica NOVITA.md e si rilancia questo script.
"""

import pathlib
import re
import sys
import textwrap

RADICE = pathlib.Path(__file__).resolve().parent
REGISTRO = RADICE / "NOVITA.md"
PACCHETTO = RADICE

# A quale parte del registro appartiene ogni file
PARTE_DEL_FILE = {
    "contratto.py": "contratto",
    "calcolo.py": "calcolo",
    "scrittura.py": "calcolo",
    "dati_reali.py": "calcolo",
    "interrogazione.py": "interrogazione",
    "server_mcp.py": "server",
    "protocollo_mcp.py": "server",
    "servizio_mcp.py": "server",
    "calcolatrice.py": "server",
    "views.py": "server",
    "sessioni.py": "sessioni",
    "mappa.py": "mappa",
}

INIZIO, FINE = "# >>> NOVITA", "# <<< NOVITA"
VOCE = re.compile(r"^- \[(\d+)\] \((\w+)\) (.+)$")


def leggi_registro():
    """Restituisce (versione corrente, {parte: [(versione, testo), ...]})."""
    versione, voci = None, {}
    for riga in REGISTRO.read_text(encoding="utf-8").splitlines():
        if riga.startswith("Versione corrente:"):
            versione = riga.split(":", 1)[1].strip()
        trovata = VOCE.match(riga)
        if trovata:
            voci.setdefault(trovata.group(2), []).append((trovata.group(1), trovata.group(3)))
        elif riga.startswith("- ["):
            raise SystemExit(f"Voce del registro non riconosciuta: {riga}")
    if versione is None:
        raise SystemExit("Nel registro manca la riga 'Versione corrente: NN'")
    sconosciute = set(voci) - set(PARTE_DEL_FILE.values())
    if sconosciute:
        raise SystemExit(f"Parti non previste nel registro: {sorted(sconosciute)}")
    return versione, voci


def intestazione(nome_file, versione, voci_parte):
    righe = [
        INIZIO + " (generato da aggiorna_intestazioni.py da NOVITA.md: non modificare a mano)",
        "#",
        f"#   {nome_file}  -  app grafo, VERSIONE {versione}",
        "#",
        "#   NOVITÀ RISPETTO ALLA VERSIONE 12  ([NN] = versione che ha introdotto la novità)",
        f"#   Parte del registro: {PARTE_DEL_FILE[nome_file]}",
        "#",
    ]
    for sigla, testo in voci_parte:
        righe += textwrap.wrap(
            testo, width=96, initial_indent=f"#   [{sigla}] ", subsequent_indent="#        "
        )
    righe += ["#", FINE]
    return "\n".join(righe)


def nuovo_contenuto(percorso, versione, voci):
    testo = percorso.read_text(encoding="utf-8")
    blocco = intestazione(percorso.name, versione, voci.get(PARTE_DEL_FILE[percorso.name], []))
    if INIZIO not in testo or FINE not in testo:
        raise SystemExit(f"{percorso.name}: mancano le righe {INIZIO} / {FINE}")
    prima, resto = testo.split(INIZIO, 1)
    _, dopo = resto.split(FINE, 1)
    return testo, prima + blocco + dopo


def esegui(solo_verifica=False):
    """Restituisce l'elenco dei file la cui intestazione non coincide con il registro."""
    versione, voci = leggi_registro()
    diversi = []
    for nome_file in PARTE_DEL_FILE:
        percorso = PACCHETTO / nome_file
        attuale, atteso = nuovo_contenuto(percorso, versione, voci)
        if attuale != atteso:
            diversi.append(nome_file)
            if not solo_verifica:
                percorso.write_text(atteso, encoding="utf-8")
    return diversi


if __name__ == "__main__":
    solo_verifica = "--verifica" in sys.argv
    diversi = esegui(solo_verifica)
    if solo_verifica:
        print("Intestazioni NON allineate: " + ", ".join(diversi) if diversi else "Intestazioni allineate al registro.")
        sys.exit(1 if diversi else 0)
    print("Intestazioni aggiornate: " + (", ".join(diversi) if diversi else "nessuna modifica necessaria"))
