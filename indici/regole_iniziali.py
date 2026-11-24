"""
Una regola di partenza, da adattare con l'amministrazione.

(codice, descrizione, tipo, peso, prefissi dell'attività, classi di dipendenti, classi di fatturato)
"""
REGOLE = [
    (
        "COMMERCIO_SENZA_DIPENDENTI",
        "Commercio con fatturato da 100.000 euro in su e nessun dipendente",
        "falsa_fatturazione", "0.60", "46.1, 47", "D0", "F1, F2, F3, F4, F5, F6, F7",
    ),
]
