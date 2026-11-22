"""
Prime voci del catalogo delle entità: una bozza da adattare con l'amministrazione.

(codice, descrizione, tipo di valore, ha un periodo, ammette più valori, cambia nel tempo, sinonimi)
"""
VOCI = [
    ("COE", "Codice operatore economico", "identificativo", False, True, False, []),
    ("PARTITA_IVA", "Partita IVA", "identificativo", False, True, False, ["P.IVA", "partita iva"]),
    ("DENOMINAZIONE", "Denominazione o ragione sociale", "testo", False, False, True,
     ["ragione sociale", "nome azienda", "società"]),
    ("SEDE", "Sede legale", "luogo", False, False, True, ["sede legale", "indirizzo della sede"]),
    ("AMMINISTRATORE", "Amministratore", "testo", False, True, True,
     ["amministratore unico", "legale rappresentante", "nome amministratore"]),
    ("SOCIO", "Socio", "testo", False, True, True, ["soci", "nome socio"]),
    ("OGGETTO_SOCIALE", "Oggetto sociale", "testo", False, False, True, []),
    ("DIPENDENTI", "Numero di dipendenti nell'anno", "numero", True, False, False, ["numero dipendenti"]),
    ("RICAVI", "Ricavi dell'anno (bilancio)", "importo", True, False, False, ["fatturato", "ricavi delle vendite"]),
    ("UTILE", "Utile o perdita dell'anno (bilancio)", "importo", True, False, False, ["utile", "perdita", "risultato d'esercizio"]),
    ("TOTALE_ATTIVO", "Totale dell'attivo (bilancio)", "importo", True, False, False, ["totale attivo"]),
]
