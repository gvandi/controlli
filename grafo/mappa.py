# >>> NOVITA (generato da aggiorna_intestazioni.py da NOVITA.md: non modificare a mano)
#
#   mappa.py  -  app grafo, VERSIONE 32
#
#   NOVITÀ RISPETTO ALLA VERSIONE 12  ([NN] = versione che ha introdotto la novità)
#   Parte del registro: mappa
#
#   [13] report_html inizializzato prima dei messaggi sui file mancanti (prima: NameError).
#   [13] Il soggetto analizzato è la coppia (nodo, tipo) accertata con punteggio più alto.
#   [13] Relazioni rilevanti riunite per coppia e distinte in dirette / indirette, con il verso.
#   [13] html.escape su nomi azienda, descrizioni delle features e tooltip.
#   [13] "HIGH RISK" fisso sostituito dallo stato reale del soggetto; i complici indiretti sono
#        solo i soggetti con irregolarità ACCERTATE.
#   [13] Inserimento del report nella mappa con str.replace (re.sub interpretava le "\").
#   [16] Report e mappa spostati in mappa.py: leggono solo dal database tramite la libreria,
#        senza PyTorch.
#   [16] Nomi delle aziende letti dalla tabella azienda (prima: da elenco_aziende.json);
#        vicinato a 1 e 2 passi calcolato con le query.
#   [16] Il tooltip degli archi riporta verso commerciale e documenti scambiati; il report
#        dichiara la data dei punteggi.
#   [16] Se la spiegazione del soggetto manca, il report lo segnala e la mette in coda.
#   [18] Il report mostra i primi 3 indicatori dei 10 ora conservati in ogni spiegazione.
#   [19] Il file della mappa porta nel nome soggetto e coppia calcolo/dati e viene scritto in
#        dati_grafo: mappe diverse non si sovrascrivono.
#   [19] Si può scegliere il soggetto: python manage.py grafo_mappa --soggetto "nome o numero".
#   [20] Nuova produci(): restituisce percorso, nome del file e soggetto; chiesta dalla chat, la
#        mappa porta nel nome anche il numero di sessione, così analisti diversi non si
#        sovrascrivono.
#
# <<< NOVITA
"""
REPORT E MAPPA INVESTIGATIVA di un soggetto, in un file HTML.

È un secondo utilizzatore della libreria di interrogazione, come il server MCP:
legge solo dal database, non usa PyTorch e non ricalcola nulla.

    python manage.py grafo_mappa                  soggetto con l'irregolarità accertata più evidente
    python manage.py grafo_mappa --soggetto 12    un soggetto a scelta

Importa contratto.py e interrogazione.py.
"""

import html
import re
from pathlib import Path

from . import interrogazione
from .contratto import DIM_TOTALI, TIPI_IRREGOLARITA

SCRIPT_TOGGLE = """
<script>
function toggleDescrizione(elemento) {
    const idOriginale = elemento.getAttribute('data-id');
    const descrizione = elemento.getAttribute('data-descrizione');
    if (elemento.innerText === idOriginale) {
        elemento.innerText = descrizione;
        elemento.style.color = "#0275d8";
    } else {
        elemento.innerText = idOriginale;
        elemento.style.color = "";
    }
}
</script>
"""


def genera_nodi_interattivi_html(lista_nodi):
    """
    Genera un elenco HTML di nodi interattivi. Al click sul numero del nodo,
    mostra il nome dell'azienda e il numero di iscrizione societaria.
    """
    elementi_html = []
    for nodo in lista_nodi:
        dati = interrogazione.dati_azienda(nodo)
        descrizione = f"{dati['nome']} ({dati['nr_iscrizione'] or dati['id_fiscale']})"
        # html.escape protegge l'attributo: un apostrofo o un "<" nella ragione
        # sociale non può rompere il report
        elementi_html.append(
            f"<b onclick='toggleDescrizione(this)' data-id='#{nodo}' "
            f"data-descrizione='{html.escape(descrizione, quote=True)}' "
            f"style='cursor: pointer; text-decoration: underline;'>#{nodo}</b>"
        )
    return ", ".join(elementi_html)


def _soggetto_da_analizzare(soggetto=None):
    """Il soggetto indicato (sul suo tipo più rischioso), oppure quello principale."""
    if soggetto is None:
        return interrogazione.soggetto_principale()
    migliore = max(interrogazione.punteggi_nodo(soggetto), key=lambda voce: voce["punteggio"])
    return {
        "nodo": int(soggetto),
        "tipo": migliore["tipo"],
        "indice_tipo": TIPI_IRREGOLARITA.index(migliore["tipo"]),
        "punteggio": migliore["punteggio"],
        "soglia": interrogazione.leggi_esecuzione()["soglie"][migliore["tipo"]],
    }


def costruisci_report(soggetto=None):
    """
    Compone il report HTML sul soggetto principale. Restituisce (report_html, bolla)
    dove bolla = {"target", "vicini_1", "vicini_2"} serve a disegnare la mappa.
    Restituisce (messaggio, None) se nell'archivio non c'è nessuna irregolarità accertata.
    """
    soggetto = _soggetto_da_analizzare(soggetto)
    if soggetto is None:
        return "<p>Nessuna irregolarità accertata nell'archivio: nessun soggetto da analizzare.</p>", None

    nodo_target = soggetto["nodo"]
    html_nodo_target = genera_nodi_interattivi_html([nodo_target])
    sopra_soglia = soggetto["punteggio"] >= soggetto["soglia"]

    report = SCRIPT_TOGGLE
    report += "<h3>--- FASE ISPETTIVA ---</h3>\n"
    report += f"<i>{html.escape(interrogazione.intestazione_dati())}</i><br>\n"
    report += f"<b>Soggetto Sospetto Identificato:</b> <span style='color: #d9534f;'>Nodo {html_nodo_target}</span><br>\n"
    report += f"<b>Irregolarità analizzata:</b> <code>{html.escape(soggetto['tipo'])}</code><br>\n"
    report += (
        f"<b>Punteggio di Rischio Assegnato dalla GNN:</b> <code>{soggetto['punteggio']*100:.2f}%</code> "
        f"(soglia di decisione: <code>{soggetto['soglia']*100:.2f}%</code>, "
        f"{'superata' if sopra_soglia else 'NON superata'})<br><br>\n"
    )

    # --- Spiegazione di GNNExplainer (calcolata dal processo di calcolo) ---
    indicatori = interrogazione.leggi_spiegazione(nodo_target, soggetto["indice_tipo"])
    if indicatori is None:
        interrogazione.richiedi_spiegazione(nodo_target, soggetto["indice_tipo"])
        report += (
            "<p style='color: #d9534f;'><i>Spiegazione GNNExplainer non ancora calcolata: "
            "la richiesta è stata messa in coda per il processo di calcolo.</i></p>\n"
        )
    else:
        report += "<h3>--- 1. RELAZIONI E SOGGETTI RESPONSABILI DELL'ANOMALIA ---</h3>\n"
        relazioni = indicatori["relazioni"]
        report += f"Nel raggio d'azione della GAT, sono state isolate <b>{len(relazioni)}</b> relazioni critiche:<br>\n"
        for (a, b), importanza in relazioni:
            verso = html.escape(interrogazione.verso_relazione(a, b))
            if nodo_target in (a, b):
                altro = b if a == nodo_target else a
                descrizione = f"Connessione diretta con <b>Nodo {genera_nodi_interattivi_html([altro])}</b>"
            else:
                # Relazione fra due nodi del vicinato che NON coinvolge direttamente il target
                descrizione = f"Relazione indiretta fra i <b>Nodi {genera_nodi_interattivi_html([a, b])}</b>"
            report += (
                f" ➔ {descrizione} (<i>{verso}</i>) | Impatto sul Rischio: "
                f"<span style='font-weight: bold; color: #f0ad4e;'>{importanza*100:5.2f}%</span><br>\n"
            )

        report += "<br><h3>--- 2. CARATTERISTICHE (FEATURES) CHE HANNO COSTRUITO IL RISCHIO ---</h3>\n"
        report += f"Analisi dei pesi delle <u>{DIM_TOTALI} features</u> del super-vettore:<br>\n"
        report += f" ➔ Peso medio della componente <b>Testuale</b> (Semantica dei JSON): <code>{indicatori['impatto_testo']*100:.2f}%</code><br>\n"
        report += f" ➔ Peso medio della componente <b>Strutturata</b> (Dati Finanziari/Bilanci): <code>{indicatori['impatto_strutturati']*100:.2f}%</code><br><br>\n"
        report += f"<b>Top 3 indicatori specifici</b> isolati da GNNExplainer per il <b>Nodo {nodo_target}</b> (Clicca sull'ID per la descrizione):<br>\n"
        for i, feat in enumerate(indicatori["features"][:3], start=1):
            report += (
                f"  {i}. Feature <b onclick='toggleDescrizione(this)' data-id='#{feat['indice']}' "
                f"data-descrizione='{html.escape(str(feat['descrizione']), quote=True)}' style='cursor: pointer; text-decoration: underline;'>#{feat['indice']}</b> "
                f"[<i>{html.escape(feat['tipo'])}</i>] ➔ Peso: <span style='color: #5cb85c; font-weight: bold;'>{feat['peso']*100:.2f}%</span><br>\n"
            )

    # --- Triangolazioni: vicinato a 1 e 2 passi ---
    vicini_1 = sorted(interrogazione.vicini_diretti(nodo_target))
    vicini_2 = sorted(interrogazione.vicini_a_due_passi(nodo_target))

    report += "<p></p>\n"
    report += f"<h3>--- ANALISI DELLE TRIANGOLAZIONI SUL SOGGETTO {html_nodo_target} ---</h3>\n"
    report += (
        f"<b>Stato noto del soggetto:</b> <span style='color: #d9534f; font-weight: bold;'>"
        f"{html.escape(interrogazione.stato_compliance(nodo_target))}</span><br><br>\n"
    )
    report += f"<b>[LIVELLO 1-HOP]</b> - Canali di Transito Diretti (<code>{len(vicini_1)}</code> nodi):<br>\n"
    report += f" ➔ Nodi connessi direttamente: <code>{genera_nodi_interattivi_html(vicini_1)}</code><br><br>\n"
    report += f"<b>[LIVELLO 2-HOP]</b> - Beneficiari Occulti / Destinatari Finali (<code>{len(vicini_2)}</code> nodi):<br>\n"
    report += f" ➔ Nodi connessi indirettamente: <code>{genera_nodi_interattivi_html(vicini_2)}</code><br><br>\n"

    # Fra i vicini a 2 passi, solo i soggetti con irregolarità ACCERTATE: i non
    # ispezionati non contano né come rischiosi né come regolari
    report += "<h3>--- VERIFICA CIRCUITI CHIUSI ---</h3>\n"
    complici_indiretti = [v for v in vicini_2 if interrogazione.irregolarita_accertate(v)]
    if complici_indiretti:
        report += (
            f"<span style='color: #d9534f; font-weight: bold;'>⚠️ ALLERTA TRIANGOLAZIONE:</span> "
            f"Il soggetto a rischio <b>{nodo_target}</b> è collegato indirettamente "
            f"(tramite i nodi del circuito 1-hop) ad altri soggetti con <b>IRREGOLARITÀ ACCERTATE</b>: "
            f"<code>{genera_nodi_interattivi_html(complici_indiretti)}</code><br>\n"
        )
    else:
        report += "<span style='color: #5cb85c; font-weight: bold;'>✅ Nessun circuito chiuso</span> o triangolazione con altri soggetti con irregolarità accertate nel raggio di 2-hop.<br>\n"

    return report, {"target": nodo_target, "vicini_1": vicini_1, "vicini_2": vicini_2}


def scrivi_mappa(report_html, bolla, nome_file):
    """Disegna la bolla di influenza con PyVis e vi affianca il report."""
    import networkx as nx  # servono solo qui
    from pyvis.network import Network

    nodo_target = bolla["target"]
    set_1hop, set_2hop = set(bolla["vicini_1"]), set(bolla["vicini_2"])
    nodi_bolla = [nodo_target, *bolla["vicini_1"], *bolla["vicini_2"]]

    G_bolla = nx.Graph()
    G_bolla.add_nodes_from(nodi_bolla)
    G_bolla.add_edges_from(interrogazione.relazioni_fra(nodi_bolla))
    pos = nx.spring_layout(G_bolla, k=0.5, seed=42)

    net = Network(height="800px", width="100%", bgcolor="#ffffff", font_color="#000000",
                  cdn_resources="in_line")

    titolo_mappa = (
        "<b>Mappa Investigativa delle Triangolazioni</b><br>"
        "Legenda: Centro Rosso: Target | Giallo: 1-Hop (Transito) | Verde: 2-Hop (Destinatari)<br>"
        "Bordo Nero Spesso: Soggetto con irregolarità accertate"
    )

    for nodo in G_bolla.nodes():
        e_sospetto_storico = bool(interrogazione.irregolarita_accertate(nodo))

        colore_sfondo, dimensione, ruolo = "#90EE90", 20, "2-Hop (Destinatario)"
        colore_bordo = "#000000" if e_sospetto_storico else "gray"
        ampiezza_bordo = 3 if e_sospetto_storico else 1
        if nodo == nodo_target:
            colore_sfondo, dimensione, ruolo = "#FF4500", 35, "TARGET INVESTIGATIVO"
            colore_bordo, ampiezza_bordo = "#000000", 3
        elif nodo in set_1hop:
            colore_sfondo = "#D32F2F" if e_sospetto_storico else "#FFD700"
            dimensione, ruolo = 25, "1-Hop (Transito diretto)"
        elif nodo in set_2hop and e_sospetto_storico:
            colore_sfondo = "#D32F2F"

        dati = interrogazione.dati_azienda(nodo)
        tooltip = (
            f"Soggetto ID: {html.escape(dati['nome'])} {html.escape(dati['nr_iscrizione'] or dati['id_fiscale'])}\n"
            f"Ruolo nella Bolla: {ruolo}\n"
            f"Stato Compliance: {html.escape(interrogazione.stato_compliance(nodo))}"
        )
        net.add_node(
            int(nodo),
            label=str(nodo),
            title=tooltip,
            size=dimensione,
            color={"background": colore_sfondo, "border": colore_bordo},
            borderWidth=ampiezza_bordo,
            x=pos[nodo][0] * 1000,  # posizione iniziale dallo Spring Layout
            y=pos[nodo][1] * 1000,
            physics=True,
        )

    for a, b in G_bolla.edges():
        # Il tooltip dell'arco riporta il verso commerciale e i documenti
        net.add_edge(
            source=int(a), to=int(b), color="gray", opacity=0.4,
            title=f"{interrogazione.verso_relazione(a, b)} ({interrogazione.descrivi_documenti(a, b)})",
        )

    net.barnes_hut(gravity=-2000, central_gravity=0.3, spring_length=95, spring_strength=0.04)
    net.show_buttons(filter_=["physics"])
    net.write_html(nome_file)

    with open(nome_file, "r", encoding="utf-8") as file:
        html_content = file.read()

    # I testi inseriti passano per funzione o str.replace, così eventuali "\" nei
    # nomi azienda non vengono interpretati da re.sub
    html_content = re.sub(
        r"""<center>\s*          <h1></h1>""", lambda _: "<center>\n\t\t\t" + titolo_mappa, html_content
    )
    html_content = re.sub(
        r"""#mynetwork {\s*                 width: 100%;""",
        lambda _: "#mynetwork {\n\t\t\t\t width: 50%;",
        html_content,
    )
    blocco_card = """<div class="card" style="width: 100%">"""
    html_content = html_content.replace(
        blocco_card,
        blocco_card + "\n\t\t\t" + """<div class="card-body" style="display: flex; gap: 20px; align-items: flex-start;">""",
    )
    blocco_div = """<div id="mynetwork" class="card-body"></div>"""
    html_content = html_content.replace(
        blocco_div,
        "\t" + blocco_div
        + """\n\t\t\t\t<div id="descrizione" class="card-body" style="width: 50%; height: 600px;">"""
        + report_html + """</div>\n\t\t\t</div>""",
    )

    with open(nome_file, "w", encoding="utf-8") as file:
        file.write(html_content)
    return nome_file



def produci(cartella, soggetto=None, sessione=None):
    """
    Scrive la mappa di un soggetto. Restituisce {"percorso", "nome_file", "soggetto"}
    oppure None se non c'è nulla da analizzare.

    Il nome del file contiene soggetto e coppia calcolo/dati e, se la mappa è
    chiesta dalla chat, il numero di sessione: le mappe di analisti diversi non si
    sovrascrivono fra loro.
    """
    report, bolla = costruisci_report(soggetto)
    if bolla is None:
        return None
    esecuzione = interrogazione.leggi_esecuzione()
    nome = (
        f"mappa_{f'sessione-{sessione}_' if sessione else ''}soggetto-{bolla['target']}"
        f"_calcolo-{esecuzione['versione_calcolo']}_dati-{esecuzione['numero_dati']}.html"
    )
    Path(cartella).mkdir(parents=True, exist_ok=True)
    percorso = scrivi_mappa(report, bolla, str(Path(cartella) / nome))
    return {"percorso": percorso, "nome_file": nome, "soggetto": bolla["target"]}


def genera(cartella, soggetto=None):
    """Come produci(), ma restituisce solo il percorso del file (o None)."""
    prodotta = produci(cartella, soggetto)
    return prodotta["percorso"] if prodotta else None
