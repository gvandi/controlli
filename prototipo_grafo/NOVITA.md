# Registro delle novità

Versione corrente: 18

Elenco completo delle novità rispetto alla versione 12 (ultimo file unico di partenza).
È l'UNICO posto in cui le novità si scrivono a mano: `aggiorna_intestazioni.py` ricopia
in testa a ogni file le voci della sua parte.

Formato di una voce: `- [versione] (parte) testo`, su una sola riga.
Parti: `contratto`, `calcolo`, `interrogazione`, `server`, `mappa`.
Fino alla versione 15 il programma era un solo file (`fac_simile_addestramento_gat_ver.NN.py`):
le voci 13-15 sono assegnate alla parte in cui quel codice si trova oggi.

## contratto

- [13] (contratto) Tassonomia TIPI_IRREGOLARITA: un'uscita della GNN per ogni tipo di irregolarità.
- [15] (contratto) Schema del database: azienda, irregolarita_accertata, relazione (un documento per arco, con data e importo), esecuzione_modello, nodo_azienda, punteggio_rischio, spiegazione.
- [15] (contratto) Le tabelle usano l'identificativo fiscale dell'azienda; nodo_azienda conserva la corrispondenza con l'indice del nodo per ogni esecuzione.
- [16] (contratto) Nuovo modulo contratto.py: unico posto per tassonomia, popolazioni, nomi degli strumenti, dimensioni delle features, percorsi dei file e schema del database.
- [16] (contratto) Un solo numero di versione per tutto il progetto (VERSIONE_CODICE) e versione dello schema (VERSIONE_SCHEMA, ora 2).
- [16] (contratto) Nuova tabella info_archivio con la versione dello schema; esecuzione_modello registra anche versione del codice e tassonomia usate nel calcolo.
- [16] (contratto) Nuova tabella richiesta_spiegazione: coda delle spiegazioni chieste dalle interrogazioni.
- [16] (contratto) Eccezione ArchivioIncompatibile e forma documentata della spiegazione.
- [16] (contratto) Percorsi dei file modificabili con le variabili d'ambiente CONTROLLI_DB e CONTROLLI_MODELLO.
- [17] (contratto) connetti() apre la connessione con check_same_thread=False, perché il server esegue gli strumenti in un thread diverso da quello che ha aperto l'archivio.

## calcolo

- [13] (calcolo) Etichette per TIPO di irregolarità: y passa da [N, 1] a [N, 4].
- [13] (calcolo) Solo 150 aziende su 500 sono "ispezionate" e hanno un'etichetta (grafo.ha_etichetta); le altre restano nel grafo ma fuori da train/val/test: non ispezionata != regolare.
- [13] (calcolo) Gli archi conservano il verso venditore -> acquirente; GAT e GNNExplainer usano l'edge_index simmetrico.
- [13] (calcolo) ComplianceGAT restituisce i LOGIT (tolto il sigmoid dal forward) con un'uscita per tipo; calcola_mappa_rischi() applica il sigmoid in inferenza.
- [13] (calcolo) La BCEWithLogitsLoss pesata viene usata davvero, con un pos_weight per ogni tipo.
- [13] (calcolo) Accuracy sostituita da PR-AUC, precision e recall per tipo (evaluate).
- [13] (calcolo) Soglie di decisione scelte sul validation set (scegli_soglie) al posto di 0.5 fisso.
- [13] (calcolo) GNNExplainer spiega un tipo di irregolarità alla volta (classe UscitaSingola), con return_type='raw' coerente con i logit.
- [14] (calcolo) GNNExplainer racchiuso nella funzione spiega_nodo(); dizionario_descrizioni.json caricato prima della spiegazione.
- [15] (calcolo) Ogni esecuzione viene registrata nel database con versione, data, soglie e metriche (salva_dati_simulati, salva_esecuzione); le spiegazioni vengono salvate in tabella (salva_spiegazione).
- [16] (calcolo) Diviso in calcolo.py (PyTorch) e scrittura.py (senza PyTorch, riceve liste Python): il cablaggio si può provare con un modello finto.
- [16] (calcolo) Il codice è organizzato in funzioni (costruisci_grafo_simulato, addestra, esegui_calcolo) invece che eseguito all'importazione.
- [16] (calcolo) Pesi del modello e grafo salvati su file (modello_grafo.pt) con la versione dell'esecuzione.
- [16] (calcolo) Spiegazioni calcolate subito per l'irregolarità accertata con punteggio più alto e per le prime 5 aziende non ispezionate della classifica.
- [16] (calcolo) Nuovo comando "spiegazioni" (elabora_richieste): calcola le spiegazioni in coda senza riaddestrare, e si rifiuta se modello su file e archivio sono di esecuzioni diverse.
- [16] (calcolo) apri_in_scrittura() controlla la versione dello schema e rifiuta gli archivi creati da versioni precedenti.
- [16] (calcolo) Non contiene più report, mappa né domande di esempio; non usa più il generatore casuale di numpy per date e importi (ora random.Random).

## interrogazione

- [13] (interrogazione) stato_compliance(): irregolarità accertate, verificato senza rilievi o non ispezionato.
- [13] (interrogazione) Il contesto usa gli indicatori REALI di GNNExplainer (prima: una frase fissa) e riporta stato noto e punteggi per tipo di ogni soggetto.
- [13] (interrogazione) Domande e istruzioni neutre: si chiede di valutare l'ipotesi, non di giustificarla.
- [13] (interrogazione) Fino alla versione 15: client del modello creato solo quando serve, eccezioni del client OpenAI gestite, risposta restituita come testo.
- [14] (interrogazione) Quattro intenti: classifica, relazione, spiegazione, vicinato; smistamento a parole chiave (smista_con_regole).
- [14] (interrogazione) Fino alla versione 15: smistamento proposto dall'LLM in JSON e validato campo per campo (smista_domanda, valida_smistamento).
- [14] (interrogazione) classifica_rischio(): prime N aziende per punteggio, per tipo e per popolazione (non ispezionate / ispezionate / tutte), con percentile e soglia.
- [14] (interrogazione) Funzioni di contesto: contesto_classifica(), genera_contesto_investigativo(), contesto_spiegazione(), contesto_vicinato().
- [15] (interrogazione) Riscritte come query sul database: classifica_rischio(), vicini_diretti(), stato_compliance(); nuove vicini_a_due_passi(), documenti_relazione(), punteggi_nodo(), irregolarita_accertate(), leggi_esecuzione().
- [15] (interrogazione) Ogni contesto dichiara data e versione del calcolo (intestazione_dati) e, per le relazioni, i documenti scambiati (descrivi_documenti).
- [16] (interrogazione) Nuovo modulo interrogazione.py, senza PyTorch: letture, contesti e strumenti.
- [16] (interrogazione) apri() si aggancia all'esecuzione più recente e solleva ArchivioIncompatibile se schema o tassonomia non combaciano con il codice; avvisa se la versione del codice è diversa.
- [16] (interrogazione) Quattro strumenti per la chat (classifica, relazione, spiegazione, vicinato) con controllo dei parametri: un valore non ammesso produce un messaggio in chiaro.
- [16] (interrogazione) Spiegazione non ancora calcolata: la richiesta viene messa in coda (richiedi_spiegazione) e il contesto lo dichiara; la libreria non esegue più GNNExplainer.
- [16] (interrogazione) verso_relazione() legge dal database; nuove dati_azienda(), relazioni_fra(), soggetto_principale().
- [16] (interrogazione) genera_contesto_investigativo() riceve il tipo di irregolarità al posto degli indicatori e li legge da sé.
- [16] (interrogazione) consulta(domanda) e uso da riga di comando, con smistamento a parole chiave.
- [16] (interrogazione) Rimossi chiama_llm, smista_domanda, estrai_json, valida_smistamento, interroga_graph_rag e i relativi prompt: scelta dello strumento e stesura della risposta passano alla chat (istruzioni in prompt_di_sistema.txt).
- [17] (interrogazione) Gli strumenti vengono eseguiti uno alla volta (_in_esclusiva): con mcp 2.x le funzioni sono chiamate da thread di lavoro e la connessione al database è una sola.
- [18] (interrogazione) L'ispettore può indicare una società per nome, anche parziale, per numero o per numero di iscrizione: nuova risolvi_societa(), con normalizza_nome() e nucleo_nome() (maiuscole, accenti, punteggiatura e forma giuridica non contano).
- [18] (interrogazione) Un nome che corrisponde a più società, o a nessuna, non viene mai indovinato: lo strumento restituisce l'elenco dei candidati o dei nomi simili, e decide l'ispettore.
- [18] (interrogazione) Gli strumenti relazione, spiegazione e vicinato ricevono la società come testo (nome o numero) invece che come numero intero.
- [18] (interrogazione) Tutti i testi indicano ogni società con numero, nome e numero di iscrizione (nuova etichetta()); una nota chiede alla chat di citarli nella risposta.
- [18] (interrogazione) I nomi si leggono dalla tabella azienda, riempita dal calcolo a partire da elenco_aziende.json: il file non viene letto durante le interrogazioni.
- [18] (interrogazione) consulta() riconosce nella domanda anche i nomi completi delle società, nell'ordine in cui compaiono (estrai_nodi_dalla_domanda).

## server

- [16] (server) Nuovo server MCP (server_mcp.py) che registra i quattro strumenti della libreria, per usare Unsloth Studio come chat.
- [16] (server) All'avvio apre l'archivio: se non combacia con il codice il server non parte.
- [17] (server) Compatibile con la libreria mcp 1.x (FastMCP) e 2.x (MCPServer): con la 2.x la versione 16 non partiva (ModuleNotFoundError).
- [17] (server) Strumenti registrati con add_tool() e trasporto stdio indicato in modo esplicito.

## mappa

- [13] (mappa) report_html inizializzato prima dei messaggi sui file mancanti (prima: NameError).
- [13] (mappa) Il soggetto analizzato è la coppia (nodo, tipo) accertata con punteggio più alto.
- [13] (mappa) Relazioni rilevanti riunite per coppia e distinte in dirette / indirette, con il verso.
- [13] (mappa) html.escape su nomi azienda, descrizioni delle features e tooltip.
- [13] (mappa) "HIGH RISK" fisso sostituito dallo stato reale del soggetto; i complici indiretti sono solo i soggetti con irregolarità ACCERTATE.
- [13] (mappa) Inserimento del report nella mappa con str.replace (re.sub interpretava le "\").
- [16] (mappa) Report e mappa spostati in mappa.py: leggono solo dal database tramite la libreria, senza PyTorch.
- [16] (mappa) Nomi delle aziende letti dalla tabella azienda (prima: da elenco_aziende.json); vicinato a 1 e 2 passi calcolato con le query.
- [16] (mappa) Il tooltip degli archi riporta verso commerciale e documenti scambiati; il report dichiara la data dei punteggi.
- [16] (mappa) Se la spiegazione del soggetto manca, il report lo segnala e la mette in coda.
