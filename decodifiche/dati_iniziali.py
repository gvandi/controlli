"""Valori iniziali delle tabelle di decodifica.

Sono una prima bozza (vedi DECISIONI.md, n. 6-9): si caricano con
    python manage.py carica_decodifiche
e poi si modificano dall'interfaccia di amministrazione.
"""

# (codice, descrizione, minimo incluso, massimo escluso o None)
CLASSI_DIPENDENTI = [
    ("D0", "Nessun dipendente", 0, 1),
    ("D1", "1-2 dipendenti", 1, 3),
    ("D2", "3-5 dipendenti", 3, 6),
    ("D3", "6-9 dipendenti", 6, 10),
    ("D4", "10-19 dipendenti", 10, 20),
    ("D5", "20-49 dipendenti", 20, 50),
    ("D6", "50-249 dipendenti", 50, 250),
    ("D7", "250 dipendenti e oltre", 250, None),
]

CLASSI_FATTURATO = [
    ("F0", "Fino a 100.000 euro", 0, 100_000),
    ("F1", "Da 100.000 a 250.000 euro", 100_000, 250_000),
    ("F2", "Da 250.000 a 500.000 euro", 250_000, 500_000),
    ("F3", "Da 500.000 a 1 milione di euro", 500_000, 1_000_000),
    ("F4", "Da 1 a 2 milioni di euro", 1_000_000, 2_000_000),
    ("F5", "Da 2 a 10 milioni di euro", 2_000_000, 10_000_000),
    ("F6", "Da 10 a 50 milioni di euro", 10_000_000, 50_000_000),
    ("F7", "Oltre 50 milioni di euro", 50_000_000, None),
]

# (codice, descrizione)
FORME_GIURIDICHE = [
    ("DI", "Ditta individuale"),
    ("SP", "Società di persone"),
    ("SRL", "Società a responsabilità limitata"),
    ("SPA", "Società per azioni"),
    ("COOP", "Cooperativa"),
    ("ENTE", "Associazione o fondazione"),
    ("SEDE_EST", "Sede secondaria di società estera"),
    ("ALTRO", "Altra forma"),
]

POSIZIONI_GRUPPO = [
    ("IND", "Indipendente"),
    ("CAPO", "Capogruppo (holding)"),
    ("CTRL", "Controllata"),
    ("CTRL_EST", "Controllata da soggetto estero"),
]

CLIENTELA = [
    ("B2B", "Vendita a imprese"),
    ("B2C", "Vendita a consumatori"),
    ("MISTA", "Mista"),
]

STAGIONALITA = [
    ("STAG", "Attività stagionale"),
    ("NON_STAG", "Attività non stagionale"),
]

USO_CONTANTE = [
    ("CONT", "Incasso in contanti per natura"),
    ("NO_CONT", "Senza incasso in contanti per natura"),
]

OPERATIVITA_ESTERO = [
    ("NESSUNO", "Nessuna operatività con l'estero"),
    ("IMPORT", "Importazione"),
    ("EXPORT", "Esportazione"),
    ("ENTRAMBI", "Importazione ed esportazione"),
]

# (codice, descrizione, paese ISO, prefissi da togliere, espressione di controllo)
# Il formato del COE (cinque cifre) è da confermare: vedi TODO.md.
TIPI_IDENTIFICATIVO = [
    ("COE", "Codice operatore economico (San Marino)", "SM", "COE,SM", r"\d{5}"),
    ("PIVA_IT", "Partita IVA (Italia)", "IT", "IT", r"\d{11}"),
    ("CF_IT", "Codice fiscale (Italia)", "IT", "", r"[A-Z0-9]{16}|\d{11}"),
    ("VAT_UE", "Partita IVA di altro paese dell'Unione europea", "", "", r"[A-Z]{2}[A-Z0-9]{2,12}"),
    ("ALTRO", "Altro identificativo", "", "", ""),
]

TIPI_DOCUMENTO = [
    ("FATTURA", "Fattura"),
    ("NOTA_CREDITO", "Nota di credito"),
    ("DDT", "Documento di trasporto"),
    ("CONTRATTO", "Contratto"),
    ("DOGANA", "Dichiarazione doganale"),
    ("ALTRO", "Altro documento"),
]

RUOLI_NEL_DOCUMENTO = [
    ("EMITTENTE", "Emittente o cedente"),
    ("DESTINATARIO", "Destinatario o cessionario"),
    ("MITTENTE", "Mittente della merce"),
    ("VETTORE", "Vettore"),
    ("DESTINAZIONE", "Luogo di destinazione della merce"),
    ("INTERMEDIARIO", "Intermediario"),
]

# Poche voci di esempio per provare la gerarchia. La classificazione completa va
# caricata dal file ufficiale (TODO.md).
# (codice, descrizione, livello, codice padre, contanti per natura, stagionale per natura)
VERSIONE_ATTIVITA_ESEMPIO = "ESEMPIO"
ATTIVITA_ESEMPIO = [
    ("47", "Commercio al dettaglio", "divisione", None, False, False),
    ("47.2", "Commercio al dettaglio di alimentari, bevande e tabacco", "gruppo", "47", True, False),
    ("47.26", "Commercio al dettaglio di prodotti del tabacco", "classe", "47.2", True, False),
    ("56", "Servizi di ristorazione", "divisione", None, True, False),
    ("56.1", "Ristoranti e ristorazione mobile", "gruppo", "56", True, False),
    ("56.3", "Bar e altri esercizi simili senza cucina", "gruppo", "56", True, False),
    ("71", "Studi di architettura e di ingegneria", "divisione", None, False, False),
    ("71.1", "Attività degli studi di architettura e di ingegneria", "gruppo", "71", False, False),
]
