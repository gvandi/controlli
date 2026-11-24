# >>> NOVITA (generato da aggiorna_intestazioni.py da NOVITA.md: non modificare a mano)
#
#   calcolo.py  -  app grafo, VERSIONE 33
#
#   NOVITÀ RISPETTO ALLA VERSIONE 12  ([NN] = versione che ha introdotto la novità)
#   Parte del registro: calcolo
#
#   [13] Etichette per TIPO di irregolarità: y passa da [N, 1] a [N, 4].
#   [13] Solo 150 aziende su 500 sono "ispezionate" e hanno un'etichetta (grafo.ha_etichetta);
#        le altre restano nel grafo ma fuori da train/val/test: non ispezionata != regolare.
#   [13] Gli archi conservano il verso venditore -> acquirente; GAT e GNNExplainer usano
#        l'edge_index simmetrico.
#   [13] ComplianceGAT restituisce i LOGIT (tolto il sigmoid dal forward) con un'uscita per
#        tipo; calcola_mappa_rischi() applica il sigmoid in inferenza.
#   [13] La BCEWithLogitsLoss pesata viene usata davvero, con un pos_weight per ogni tipo.
#   [13] Accuracy sostituita da PR-AUC, precision e recall per tipo (evaluate).
#   [13] Soglie di decisione scelte sul validation set (scegli_soglie) al posto di 0.5 fisso.
#   [13] GNNExplainer spiega un tipo di irregolarità alla volta (classe UscitaSingola), con
#        return_type='raw' coerente con i logit.
#   [14] GNNExplainer racchiuso nella funzione spiega_nodo(); dizionario_descrizioni.json
#        caricato prima della spiegazione.
#   [15] Ogni esecuzione viene registrata nel database con versione, data, soglie e metriche
#        (salva_dati_simulati, salva_esecuzione); le spiegazioni vengono salvate in tabella
#        (salva_spiegazione).
#   [16] Diviso in calcolo.py (PyTorch) e scrittura.py (senza PyTorch, riceve liste Python): il
#        cablaggio si può provare con un modello finto.
#   [16] Il codice è organizzato in funzioni (costruisci_grafo_simulato, addestra,
#        esegui_calcolo) invece che eseguito all'importazione.
#   [16] Pesi del modello e grafo salvati su file (modello_grafo.pt) con la versione
#        dell'esecuzione.
#   [16] Spiegazioni calcolate subito per l'irregolarità accertata con punteggio più alto e per
#        le prime 5 aziende non ispezionate della classifica.
#   [16] Nuovo comando "spiegazioni" (elabora_richieste): calcola le spiegazioni in coda senza
#        riaddestrare, e si rifiuta se modello su file e archivio sono di esecuzioni diverse.
#   [16] apri_in_scrittura() controlla la versione dello schema e rifiuta gli archivi creati da
#        versioni precedenti.
#   [16] Non contiene più report, mappa né domande di esempio; non usa più il generatore casuale
#        di numpy per date e importi (ora random.Random).
#   [18] Il dizionario delle descrizioni viene caricato nel database
#        (salva_dizionario_indicatori) a ogni calcolo.
#   [18] Ogni spiegazione conserva 10 indicatori invece di 3, per rendere utile la ricerca per
#        indicatore.
#   [18] Il messaggio per uno schema diverso dice di eliminare il file e rieseguire il calcolo.
#   [19] scrittura.py usa i modelli Django: registra_dati_simulati(), registra_esecuzione(),
#        salva_spiegazione(), richieste_pendenti(), esecuzione_piu_recente(),
#        nodi_dei_soggetti().
#   [19] Nulla viene più cancellato a ogni avvio: dati nuovi aggiungono una fotografia, dati
#        identici riusano quella esistente (impronta), e solo il ricalcolo della stessa coppia
#        calcolo/dati la sostituisce.
#   [19] Le spiegazioni si salvano come documenti auto-descrittivi che nominano i soggetti con
#        la chiave interna, non con l'indice del nodo (documento_spiegazione).
#   [19] Un file di modello per ogni coppia calcolo/dati, nella cartella dati_grafo insieme ai
#        file JSON in ingresso (calcolo_cartella.py).
#   [19] Si avvia con python manage.py grafo_calcolo (--spiegazioni per la sola coda).
#   [24] Nuovo modulo dati_reali.py e comando python manage.py grafo_dati_reali: fotografia dei
#        dati presa dall'archivio dell'applicativo (un nodo per ogni soggetto dell'anagrafica
#        mittente o destinatario di un documento confermato, un arco per documento), al posto
#        dei dati simulati.
#   [24] Anagrafica unica: il soggetto del grafo ricorda quello dell'anagrafica nel riferimento
#        ANAG-<numero>; i documenti di caricamenti riservati a un'indagine non entrano nella
#        fotografia; quelli senza data, importo o una delle due parti sono contati e riportati.
#   [25] registra_esecuzione() accetta la versione del calcolo: l'indice a regole (app indici)
#        si registra come esecuzione a sé, calcolo 1.0+regole, con le regole scattate come
#        spiegazione.
#   [25] La fotografia dei dati reali comprende anche le aziende che hanno dati per periodo
#        (soggetti.DatiPerPeriodo), pur senza documenti.
#   [32] Nuova funzione diagnosi() in dati_reali.py e comando python manage.py grafo_diagnosi
#        AZIENDA: per ogni file che riguarda un'azienda segue il documento fino alla mappa
#        (elaborato, riconosciuto, confermato, completo, non riservato, fotografato, calcolato,
#        in uso) e dice dove si ferma e che cosa fare.
#   [33] La diagnosi chiama il lavoro da lanciare con il suo nuovo nome, «Aggiorna il grafo e
#        calcola gli indici» (prima «Calcola gli indici»): è il passo che fotografa i rapporti,
#        applica le regole e mette il risultato in uso.
#
# <<< NOVITA
"""
PROCESSO DI CALCOLO: l'unica parte che usa PyTorch.

Costruisce il grafo, addestra la GNN, calcola i punteggi e li consegna a
scrittura.py, che li salva nel database dell'applicativo. Salva su file anche
pesi e grafo, per calcolare in seguito le spiegazioni richieste dalle interrogazioni.

    python manage.py grafo_calcolo                 calcolo completo (da eseguire di notte)
    python manage.py grafo_calcolo --spiegazioni   calcola solo le spiegazioni in coda

Ogni calcolo scrive una coppia (versione del calcolo, fotografia dei dati) e non
cancella le altre: vedi COMPATIBILITA.md.

Importa contratto.py e scrittura.py. NON importa interrogazione, server o mappa.
"""

import json
import sys
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from sklearn.metrics import (
    average_precision_score,
    precision_recall_curve,
    precision_score,
    recall_score,
)
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import RobustScaler
from torch_geometric.data import Data
from torch_geometric.explain import Explainer, GNNExplainer
from torch_geometric.nn import GATConv
from torch_geometric.utils import remove_self_loops, to_undirected


from . import contratto, scrittura
from .calcolo_cartella import cartella_dati
from .contratto import DIM_STRUTTURATI, DIM_TESTO, DIM_TOTALI, NUM_TIPI, TIPI_IRREGOLARITA

# Parametri della simulazione
NUM_NODI = 500
NUM_ISPEZIONATI = 150  # aziende con verbale ispettivo confermato dall'analista
NUM_CON_IRREGOLARITA = 32  # fra le ispezionate, quelle con almeno un rilievo accertato

# Quante aziende non ispezionate in cima alla classifica ricevono subito la
# spiegazione (le altre vengono spiegate su richiesta, tramite la coda)
SPIEGAZIONI_PRECALCOLATE = 5


# =====================================================================
# 1. PREPARAZIONE DATI E FEATURE FUSION (SIMULAZIONE)
# =====================================================================
def costruisci_grafo_simulato():
    """
    NOTA: questa funzione verrà sostituita dalla lettura dei dati reali dal database.
    La simulazione riproduce però la FORMA dei dati reali:
     - archi con un verso (venditore -> acquirente);
     - etichette solo per le aziende con verbale ispettivo confermato;
     - aziende non ispezionate SENZA etichetta (non equivalgono a "regolari").
    Restituisce (grafo, archi_orientati).
    """
    # Simulazione Feature Fusion (Testo + Strutturati Normalizzati)
    text_embeddings = np.random.uniform(-1, 1, size=(NUM_NODI, DIM_TESTO))
    dati_strutturati_grezzi = np.random.exponential(scale=10000, size=(NUM_NODI, DIM_STRUTTURATI))
    dati_strutturati_norm = RobustScaler().fit_transform(dati_strutturati_grezzi)
    x_nodi = torch.tensor(
        np.hstack((text_embeddings, dati_strutturati_norm)), dtype=torch.float32
    )

    # Archi: nei dati reali fatture e DDT hanno un verso (venditore -> acquirente)
    archi_orientati = torch.randint(0, NUM_NODI, (2, 1500), dtype=torch.long)
    archi_orientati, _ = remove_self_loops(archi_orientati)

    # CONVENZIONE UNICA: GAT e GNNExplainer usano l'edge_index simmetrico (ogni
    # arco ha anche il suo inverso), così l'informazione scorre in entrambi i
    # versi. È la stessa nozione di "vicino" usata dalle query sul database.
    edge_index = to_undirected(archi_orientati, num_nodes=NUM_NODI)

    # Etichette per tipo di irregolarità, solo per le aziende ispezionate
    indici_ispezionati = np.random.choice(NUM_NODI, size=NUM_ISPEZIONATI, replace=False)
    indici_irregolari = indici_ispezionati[:NUM_CON_IRREGOLARITA]

    y_target = np.zeros((NUM_NODI, NUM_TIPI), dtype=np.float32)
    # Classe usata SOLO per stratificare: 0 = verificata senza rilievi, k+1 = tipo principale k
    classe_stratificazione = np.zeros(NUM_NODI, dtype=int)
    for i, nodo in enumerate(indici_irregolari):
        tipo_principale = i % NUM_TIPI  # distribuzione uniforme fra i tipi
        y_target[nodo, tipo_principale] = 1
        classe_stratificazione[nodo] = tipo_principale + 1
        if np.random.rand() < 0.25:  # una parte ha anche una seconda irregolarità
            y_target[nodo, np.random.randint(NUM_TIPI)] = 1

    ha_etichetta = torch.zeros(NUM_NODI, dtype=torch.bool)
    ha_etichetta[indici_ispezionati] = True

    # Maschere stratificate (Train 60%, Val 20%, Test 20%) SOLO sui nodi ispezionati:
    # gli altri restano nel grafo per il passaggio dei messaggi ma non entrano mai
    # nel calcolo della loss né delle metriche.
    indici_train_val, indici_test = train_test_split(
        indici_ispezionati,
        test_size=0.20,
        stratify=classe_stratificazione[indici_ispezionati],
        random_state=42,
    )
    indici_train, indici_val = train_test_split(
        indici_train_val,
        test_size=0.25,
        stratify=classe_stratificazione[indici_train_val],
        random_state=42,
    )
    maschere = {}
    for nome, indici in (("train", indici_train), ("val", indici_val), ("test", indici_test)):
        maschera = torch.zeros(NUM_NODI, dtype=torch.bool)
        maschera[indici] = True
        maschere[nome] = maschera

    grafo = Data(
        x=x_nodi,
        edge_index=edge_index,
        y=torch.tensor(y_target, dtype=torch.float32),  # forma [NUM_NODI, NUM_TIPI]
        train_mask=maschere["train"],
        val_mask=maschere["val"],
        test_mask=maschere["test"],
        ha_etichetta=ha_etichetta,
    )
    return grafo, archi_orientati


# =====================================================================
# 2. ARCHITETTURA GNN
# =====================================================================
class ComplianceGAT(nn.Module):

    def __init__(self, in_channels=DIM_TOTALI, hidden_channels=256, out_channels=128, num_tipi=NUM_TIPI):
        super().__init__()

        # Layer Convoluzionali di Grafo
        self.conv1 = GATConv(in_channels, hidden_channels, heads=4, dropout=0.2)
        self.conv2 = GATConv(hidden_channels * 4, out_channels, heads=1, concat=False, dropout=0.2)

        # Classificatore Lineare (MLP)
        self.fc1 = nn.Linear(out_channels, 64)
        self.fc2 = nn.Linear(64, 32)
        self.output_layer = nn.Linear(32, num_tipi)  # un'uscita per tipo

        self.dropout = nn.Dropout(p=0.3)

    def forward(self, x, edge_index):
        x = self.dropout(F.elu(self.conv1(x, edge_index)))
        x = self.dropout(F.elu(self.conv2(x, edge_index)))
        x = self.dropout(self.fc1(x).relu())
        x = self.dropout(self.fc2(x).relu())
        # Restituiamo i LOGIT (nessun sigmoid): la BCEWithLogitsLoss lo applica
        # internamente. Le probabilità si ottengono con torch.sigmoid in inferenza.
        return self.output_layer(x)


class UscitaSingola(nn.Module):
    """
    Espone UNA sola uscita del modello (un tipo di irregolarità) come logit [N, 1].
    GNNExplainer spiega così una irregolarità alla volta, in classificazione binaria.
    """

    def __init__(self, modello, indice_tipo):
        super().__init__()
        self.modello = modello
        self.indice_tipo = indice_tipo

    def forward(self, x, edge_index):
        return self.modello(x, edge_index)[:, [self.indice_tipo]]


@torch.no_grad()
def calcola_mappa_rischi(modello, grafo):
    """Probabilità di rischio [NUM_NODI, NUM_TIPI] in modalità valutazione."""
    modello.eval()
    return torch.sigmoid(modello(grafo.x, grafo.edge_index))


# =====================================================================
# 3. ADDESTRAMENTO E VALUTAZIONE
# =====================================================================
def train(model, data, optimizer, criterion):
    model.train()
    optimizer.zero_grad()
    out = model(data.x, data.edge_index)  # la GAT processa sempre l'INTERO grafo
    # Loss pesata SOLO sui nodi etichettati della maschera di addestramento
    loss = criterion(out[data.train_mask], data.y[data.train_mask])
    loss.backward()
    optimizer.step()
    return loss.item()


@torch.no_grad()
def evaluate(model, data, mask, criterion, soglie=None):
    """
    Restituisce la loss e, per ogni tipo di irregolarità, PR-AUC, precision e
    recall. L'accuracy non viene calcolata: con classi sbilanciate è ingannevole.
    """
    model.eval()
    logits = model(data.x, data.edge_index)[mask]
    reali = data.y[mask]
    loss = criterion(logits, reali).item()

    probabilita = torch.sigmoid(logits).cpu().numpy()
    reali_np = reali.cpu().numpy()
    if soglie is None:
        soglie = [0.5] * NUM_TIPI

    metriche = {}
    for i, tipo in enumerate(TIPI_IRREGOLARITA):
        r, p = reali_np[:, i], probabilita[:, i]
        predetti = (p >= soglie[i]).astype(int)
        metriche[tipo] = {
            "positivi": int(r.sum()),
            "pr_auc": average_precision_score(r, p) if r.sum() > 0 else float("nan"),
            "precision": precision_score(r, predetti, zero_division=0),
            "recall": recall_score(r, predetti, zero_division=0),
        }
    return loss, metriche


@torch.no_grad()
def scegli_soglie(model, data, mask):
    """Sceglie per ogni tipo la soglia che massimizza l'F1 sul validation set."""
    model.eval()
    probabilita = torch.sigmoid(model(data.x, data.edge_index)[mask]).cpu().numpy()
    reali_np = data.y[mask].cpu().numpy()

    soglie = []
    for i in range(NUM_TIPI):
        r = reali_np[:, i]
        if r.sum() == 0:
            soglie.append(0.5)  # nessun positivo in validazione: soglia neutra
            continue
        precision, recall, valori_soglia = precision_recall_curve(r, probabilita[:, i])
        f1 = 2 * precision * recall / (precision + recall + 1e-12)
        soglie.append(float(valori_soglia[np.argmax(f1[:-1])]))
    return soglie


def pr_auc_media(metriche):
    valori = [m["pr_auc"] for m in metriche.values() if not np.isnan(m["pr_auc"])]
    return float(np.mean(valori)) if valori else float("nan")


def addestra(grafo, epoche=100):
    """Addestra il modello e restituisce (modello, soglie, metriche sul test set)."""
    model = ComplianceGAT()

    # pos_weight: un peso per ogni tipo, calcolato solo sui nodi etichettati del training
    y_train = grafo.y[grafo.train_mask]
    num_positivi = y_train.sum(dim=0)
    peso_classe_positiva = (y_train.shape[0] - num_positivi) / num_positivi.clamp(min=1)

    criterion = nn.BCEWithLogitsLoss(pos_weight=peso_classe_positiva)
    optimizer = torch.optim.Adam(model.parameters(), lr=0.005, weight_decay=5e-4)

    print("--- AVVIO ADDESTRAMENTO DELLA GNN ---")
    for epoch in range(1, epoche + 1):
        loss_train = train(model, grafo, optimizer, criterion)
        loss_val, metriche_val = evaluate(model, grafo, grafo.val_mask, criterion)
        if epoch % 10 == 0 or epoch == 1:
            print(
                f"Epoca: {epoch:03d} | Train Loss: {loss_train:.4f} | "
                f"Val Loss: {loss_val:.4f} | Val PR-AUC media: {pr_auc_media(metriche_val):.4f}"
            )

    # Soglie di decisione scelte sul validation set (non 0.5 fisso)
    soglie = scegli_soglie(model, grafo, grafo.val_mask)

    loss_test, metriche_test = evaluate(model, grafo, grafo.test_mask, criterion, soglie=soglie)
    print("\n--- VALUTAZIONE FINALE SUL TEST SET ---")
    print(f"Test Loss: {loss_test:.4f} | PR-AUC media: {pr_auc_media(metriche_test):.4f}")
    for i, tipo in enumerate(TIPI_IRREGOLARITA):
        m = metriche_test[tipo]
        print(
            f"  {tipo:<36} positivi: {m['positivi']:2d} | soglia: {soglie[i]:.3f} | "
            f"PR-AUC: {m['pr_auc']:.3f} | Precision: {m['precision']:.3f} | Recall: {m['recall']:.3f}"
        )
    return model, soglie, metriche_test


# =====================================================================
# 4. SPIEGABILITÀ (GNNExplainer)
# =====================================================================
def spiega_nodo(model, grafo, nodo, indice_tipo, dizionario_descrizioni,
                soglia_archi=0.4, num_features=contratto.FEATURES_PER_SPIEGAZIONE):
    """
    Esegue GNNExplainer su un nodo per UN tipo di irregolarità. Restituisce una
    spiegazione nella forma descritta in contratto.py (200 epoche: qualche secondo).
    """
    nodo, indice_tipo = int(nodo), int(indice_tipo)
    model.eval()
    explainer = Explainer(
        model=UscitaSingola(model, indice_tipo),  # modello addestrato, un solo tipo
        algorithm=GNNExplainer(epochs=200, lr=0.01),  # Ottimizzazione dei mascheramenti
        explanation_type="model",  # Spiega il comportamento del modello
        node_mask_type="attributes",  # Isola l'importanza delle singole features
        edge_mask_type="object",  # Isola l'importanza dei singoli archi
        model_config=dict(
            mode="binary_classification",  # Irregolarità presente vs assente
            task_level="node",  # Analisi a livello di singolo nodo/soggetto
            return_type="raw",  # Coerente: il modello restituisce logit
        ),
    )
    spiegazione = explainer(grafo.x, grafo.edge_index, index=nodo)

    # --- Relazioni: 'edge_mask' ha un punteggio da 0 a 1 per ciascun arco ---
    punteggi_archi = spiegazione.edge_mask
    archi_rilevanti = (punteggi_archi > soglia_archi).nonzero(as_tuple=True)[0]

    # L'edge_index è simmetrico: ogni relazione compare due volte (A->B e B->A).
    # Le riuniamo in una sola coppia tenendo l'importanza più alta.
    importanza_coppie = {}
    for idx_arco in archi_rilevanti:
        a = grafo.edge_index[0, idx_arco].item()
        b = grafo.edge_index[1, idx_arco].item()
        coppia = (min(a, b), max(a, b))
        importanza_coppie[coppia] = max(
            importanza_coppie.get(coppia, 0.0), punteggi_archi[idx_arco].item()
        )
    relazioni = sorted(importanza_coppie.items(), key=lambda voce: voce[1], reverse=True)

    # --- Features: 'node_mask' ha dimensione [NUM_NODI, DIM_TOTALI] ---
    punteggi_features = spiegazione.node_mask.mean(dim=0)  # Media lungo il sotto-grafo
    valori_top, indici_top = torch.topk(punteggi_features, k=num_features)

    features = []
    for i in range(num_features):
        idx_feat = indici_top[i].item()
        features.append(
            {
                "indice": idx_feat,
                "tipo": (
                    "Testuale (NLP)"
                    if idx_feat < DIM_TESTO
                    else f"Strutturata Numerica (Indice Posizionale: {idx_feat - DIM_TESTO})"
                ),
                # L'indice va convertito in stringa (requisito del formato JSON)
                "descrizione": dizionario_descrizioni.get(
                    str(idx_feat), f"Descrizione non mappata per l'indice {idx_feat}"
                ),
                "peso": valori_top[i].item(),
            }
        )

    return {
        "nodo": nodo,
        "indice_tipo": indice_tipo,
        "tipo_irregolarita": TIPI_IRREGOLARITA[indice_tipo],
        "features": features,
        "relazioni": relazioni,  # [((nodo_a, nodo_b), importanza)]
        "impatto_testo": punteggi_features[:DIM_TESTO].mean().item(),
        "impatto_strutturati": punteggi_features[DIM_TESTO:].mean().item(),
    }


# =====================================================================
# 5. I DUE COMANDI (avviati da: python manage.py grafo_calcolo)
# =====================================================================
def percorso_modello(esecuzione):
    """Un file per ogni coppia calcolo/dati: le esecuzioni non si sovrascrivono fra loro."""
    return cartella_dati() / (
        f"modello_calcolo-{esecuzione.versione_calcolo}_dati-{esecuzione.versione_dati.numero}.pt"
    )


def carica_json(nome_file):
    """Legge un file JSON dalla cartella dei dati; dizionario vuoto (con avviso) se manca."""
    percorso = cartella_dati() / nome_file
    if percorso.exists():
        with open(percorso, "r", encoding="utf-8") as f:
            return json.load(f)
    print(f"Attenzione: file {percorso} non trovato, si prosegue senza.", file=sys.stderr)
    return {}


def documento_spiegazione(risultato, soggetti_per_nodo):
    """
    Trasforma l'output di spiega_nodo() nel documento da salvare: auto-descrittivo
    (campo "schema") e con le chiavi interne dei soggetti al posto degli indici
    di nodo, che fuori dal calcolo non significano nulla.
    """
    return {
        "schema": contratto.SCHEMA_SPIEGAZIONE,
        "soggetto": soggetti_per_nodo[risultato["nodo"]],
        "tipo_irregolarita": risultato["tipo_irregolarita"],
        "features": risultato["features"],
        "relazioni": [
            [[soggetti_per_nodo[a], soggetti_per_nodo[b]], importanza]
            for (a, b), importanza in risultato["relazioni"]
        ],
        "impatto_testo": risultato["impatto_testo"],
        "impatto_strutturati": risultato["impatto_strutturati"],
    }


def esegui_calcolo():
    """Calcolo completo: dati, addestramento, punteggi, archivio, spiegazioni iniziali."""
    # Seed per la riproducibilità della simulazione
    torch.manual_seed(42)
    np.random.seed(42)

    grafo, archi_orientati = costruisci_grafo_simulato()

    # --- Fotografia dei dati in ingresso (scrittura.py non conosce PyTorch: riceve liste) ---
    # Dati identici a una fotografia esistente non ne creano una nuova.
    dizionario_descrizioni = carica_json("dizionario_descrizioni.json")
    versione_dati, soggetti_per_nodo = scrittura.registra_dati_simulati(
        archi_orientati.tolist(),
        grafo.ha_etichetta.tolist(),
        grafo.y.tolist(),
        carica_json("elenco_aziende.json"),
        dizionario_descrizioni,
    )

    model, soglie, metriche_test = addestra(grafo)
    mappa_rischi = calcola_mappa_rischi(model, grafo)

    # --- Risultati: coppia (versione del calcolo, fotografia dei dati) ---
    esecuzione = scrittura.registra_esecuzione(
        versione_dati, soggetti_per_nodo, mappa_rischi.tolist(), soglie, metriche_test
    )

    # --- Pesi e grafo su file: servono per calcolare in seguito le spiegazioni in coda ---
    torch.save(
        {
            "esecuzione_id": esecuzione.id,
            "stato_modello": model.state_dict(),
            "x": grafo.x,
            "edge_index": grafo.edge_index,
        },
        percorso_modello(esecuzione),
    )
    print(f"\nPunteggi salvati: {esecuzione} (codice {contratto.VERSIONE_CODICE})")

    # --- Spiegazioni calcolate subito ---
    # 1) l'irregolarità accertata con il punteggio più alto (esempio del report)
    punteggi_accertati = mappa_rischi.clone()
    punteggi_accertati[~(grafo.ha_etichetta.unsqueeze(1) & (grafo.y == 1))] = -1.0
    da_spiegare = [divmod(punteggi_accertati.argmax().item(), NUM_TIPI)]
    # 2) le prime aziende NON ispezionate della classifica, ciascuna sul suo tipo più alto
    punteggi_massimi, tipi_massimi = mappa_rischi.max(dim=1)
    punteggi_massimi[grafo.ha_etichetta] = -1.0
    for nodo in torch.argsort(punteggi_massimi, descending=True)[:SPIEGAZIONI_PRECALCOLATE].tolist():
        da_spiegare.append((nodo, tipi_massimi[nodo].item()))

    for nodo, indice_tipo in da_spiegare:
        print(f"Spiegazione: società {soggetti_per_nodo[nodo]}, {TIPI_IRREGOLARITA[indice_tipo]}")
        risultato = spiega_nodo(model, grafo, nodo, indice_tipo, dizionario_descrizioni)
        scrittura.salva_spiegazione(esecuzione, documento_spiegazione(risultato, soggetti_per_nodo))
    return esecuzione


def elabora_richieste():
    """Calcola le spiegazioni messe in coda dalle interrogazioni, senza riaddestrare."""
    esecuzione = scrittura.esecuzione_piu_recente()
    if esecuzione is None:
        sys.exit(f"Nessuna esecuzione del calcolo {contratto.VERSIONE_CALCOLO}: eseguire prima il calcolo completo.")
    percorso = percorso_modello(esecuzione)
    if not percorso.exists():
        sys.exit(f"File del modello non trovato ({percorso}): eseguire prima il calcolo completo.")
    salvato = torch.load(percorso)
    # Il file del modello e i punteggi nell'archivio devono venire dalla stessa esecuzione
    if salvato["esecuzione_id"] != esecuzione.id:
        sys.exit(f"Il modello su file non appartiene all'esecuzione {esecuzione}: rieseguire il calcolo completo.")

    model = ComplianceGAT()
    model.load_state_dict(salvato["stato_modello"])
    grafo = Data(x=salvato["x"], edge_index=salvato["edge_index"])

    nodo_del_soggetto = scrittura.nodi_dei_soggetti(esecuzione)
    soggetti_per_nodo = [None] * len(nodo_del_soggetto)
    for soggetto, nodo in nodo_del_soggetto.items():
        soggetti_per_nodo[nodo] = soggetto

    richieste = scrittura.richieste_pendenti(esecuzione)
    print(f"Esecuzione: {esecuzione}. Spiegazioni in coda: {len(richieste)}")
    dizionario_descrizioni = carica_json("dizionario_descrizioni.json")
    for soggetto, indice_tipo in richieste:
        print(f"Spiegazione: società {soggetto}, {TIPI_IRREGOLARITA[indice_tipo]}")
        risultato = spiega_nodo(model, grafo, nodo_del_soggetto[soggetto], indice_tipo, dizionario_descrizioni)
        scrittura.salva_spiegazione(esecuzione, documento_spiegazione(risultato, soggetti_per_nodo))
    return len(richieste)
