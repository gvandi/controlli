"""
ERRORI E AVVISI DI LETTURA IN PAROLE DELL'UTENTE (DECISIONI.md, n. 98).

Il programma registra ciò che è andato storto con le parole di chi lo ha scritto
("Pagina 1, entità: Risposta tagliata: il modello ha raggiunto il limite di lunghezza").
All'ispettore serve altro: che cosa è successo al SUO file e che cosa deve fare.

    in_chiaro(testo tecnico, stato del file, tentativi fatti, tentativi massimi)
        -> {"titolo", "righe": [...], "fare", "tecnico"}  oppure None se non c'è nulla da dire

Il testo tecnico NON viene toccato: resta nel database (FileCaricato.ultimo_errore,
Elaborazione.errore) e le pagine lo mostrano, ripiegato, a chi amministra. Qui lo si
traduce soltanto, al momento di mostrarlo: una frase migliore non richiede di rileggere i file.

Per aggiungere un caso: una riga in CASI. Il primo che corrisponde vince; ciò che nessun
caso riconosce diventa "un errore che il programma non sa descrivere", mai il testo tecnico.

Questo modulo non usa Django né il database: si prova da solo.
"""
import re

ERRORE, DA_RIVEDERE = "errore", "da rivedere"   # come archivio.models.FILE_ERRORE e FILE_DA_RIVEDERE

CONFRONTA = "Confronta l'elenco delle entità con il documento originale prima di confermare."
SEGNALA = "Segnalalo all'amministratore, indicando il numero del file."

# (espressione sul testo tecnico, che cosa è successo, che cosa fare)
# In "che cosa è successo" {0}, {1}... sono i gruppi dell'espressione.
CASI = (
    (r"entità è stata tagliata", "la lettura delle entità è incompleta: qualcuna può mancare", CONFRONTA),
    (r"ha proposto più di (\d+) entità", "ci sono più entità di quante il programma ne tiene per pagina ({0}): le altre sono state ignorate", CONFRONTA),
    (r"ha ripetuto \d+ volte", "alcune entità comparivano più volte e sono state contate una volta sola", ""),
    (r"trascrizione: risposta tagliata", "il testo è troppo lungo per essere trascritto in una volta sola", ""),
    (r"risposta tagliata", "la lettura si è interrotta prima della fine", ""),
    (r"server del modello non ha risposto|connection|timed? ?out|non configurato",
     "il modello che legge i documenti non ha risposto", ""),
    (r"risposta vuota|forma non prevista|json|manca l'elenco", "il modello ha dato una risposta che il programma non può usare", ""),
    (r"tipo di file non gestito \(([^)]*)\)", "questo tipo di file ({0}) non può essere letto dal programma",
     "Convertilo in PDF e caricalo di nuovo."),
)
SCONOSCIUTO = "si è verificato un errore che il programma non sa descrivere"

_PAGINA = re.compile(r"(?<!\w)pagina (\d+)\s*[,:]", re.IGNORECASE)


def _pezzi(tecnico):
    """Divide il testo tecnico in [(numero di pagina o None, testo)]: ogni "Pagina N:" apre un pezzo."""
    inizi = [m.start() for m in _PAGINA.finditer(tecnico)]
    if not inizi or inizi[0] > 0:
        inizi = [0] + inizi
    pezzi = []
    for inizio, fine in zip(inizi, inizi[1:] + [len(tecnico)]):
        testo = tecnico[inizio:fine].strip()
        pagina = _PAGINA.match(testo)
        if testo:
            pezzi.append((int(pagina.group(1)) if pagina else None, testo))
    return pezzi


def _riconosci(testo):
    for espressione, successo, fare in CASI:
        trovato = re.search(espressione, testo, re.IGNORECASE)
        if trovato:
            return successo.format(*trovato.groups()), fare
    return SCONOSCIUTO, SEGNALA


def _pagine(numeri):
    numeri = sorted(set(numeri))
    if len(numeri) == 1:
        return f"Pagina {numeri[0]}"
    return "Pagine " + ", ".join(str(n) for n in numeri[:-1]) + f" e {numeri[-1]}"


def in_chiaro(tecnico, stato="", tentativi=0, massimo=0):
    """
    Traduce il testo tecnico di un errore o di un avviso di lettura.
        titolo   una frase su che cosa è successo al file
        righe    che cosa è successo, pagina per pagina (le pagine con lo stesso problema insieme)
        fare     che cosa deve fare chi legge; può essere "non devi fare nulla"
        tecnico  il testo originale, per chi amministra
    """
    tecnico = " ".join(str(tecnico or "").split())
    if not tecnico:
        return None
    raccolti, ordine = {}, []          # (che cosa è successo, che cosa fare) -> pagine
    for pagina, testo in _pezzi(tecnico):
        chiave = _riconosci(testo)
        if chiave not in raccolti:
            raccolti[chiave] = []
            ordine.append(chiave)
        if pagina is not None:
            raccolti[chiave].append(pagina)
    righe, consigli = [], []
    for successo, fare in ordine:
        pagine = raccolti[(successo, fare)]
        righe.append((f"{_pagine(pagine)}: {successo}" if pagine else successo[:1].upper() + successo[1:]) + ".")
        if fare and fare not in consigli:
            consigli.append(fare)

    if stato == ERRORE:
        titolo = "La lettura di questo file non è riuscita."
        if not consigli:           # un guasto passeggero: dire se il programma riproverà
            if massimo and tentativi >= massimo:
                consigli.append(f"Il programma ha provato {massimo} volte e non riproverà da solo. {SEGNALA}")
            elif massimo:
                consigli.append(
                    f"Non devi fare nulla: il file verrà riletto alla prossima elaborazione (tentativo {tentativi} di {massimo})."
                )
            else:
                consigli.append("Non devi fare nulla: il file verrà riletto alla prossima elaborazione.")
    elif stato == DA_RIVEDERE:
        titolo = "La lettura di questo file è incompleta: va controllata prima di confermare."
    else:
        titolo = "Durante la lettura di questo file è successo qualcosa da sapere."
    return {"titolo": titolo, "righe": righe, "fare": " ".join(consigli), "tecnico": tecnico}
