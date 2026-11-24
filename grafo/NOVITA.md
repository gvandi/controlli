# Registro delle novità

Versione corrente: 31

Elenco completo delle novità rispetto alla versione 12 (ultimo file unico di partenza).
È l'UNICO posto in cui le novità si scrivono a mano: `aggiorna_intestazioni.py` ricopia
in testa a ogni file le voci della sua parte.

Formato di una voce: `- [versione] (parte) testo`, su una sola riga.
Parti: `contratto`, `calcolo`, `interrogazione`, `server`, `mappa`, `sessioni`.
Fino alla versione 15 il programma era un solo file (`fac_simile_addestramento_gat_ver.NN.py`):
le voci 13-15 sono assegnate alla parte in cui quel codice si trova oggi.
Dalla 16 alla 18 era un prototipo autonomo su SQLite (cartella `prototipo_grafo`); dalla 19 è
l'app Django `grafo` dell'applicativo, su PostgreSQL.
Dalla 20 il numero di versione del codice è un intero.

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
- [18] (contratto) Nuova tabella feature con le descrizioni degli indicatori (da dizionario_descrizioni.json); VERSIONE_SCHEMA passa a 3: l'archivio va ricreato rieseguendo il calcolo.
- [18] (contratto) Nuovo strumento indicatore in NOMI_STRUMENTI; nuove costanti FEATURES_PER_SPIEGAZIONE (10) e FEATURES_NEL_CONTESTO (5).
- [19] (contratto) Lo schema del database non sta più qui: è in models.py e nelle migrazioni Django (PostgreSQL). Tolti SCHEMA_DB, connetti(), percorso_db(), percorso_modello().
- [19] (contratto) Quattro versioni distinte in formato PEP 440: progetto (VERSIONE_CODICE 19.0), schema (VERSIONE_SCHEMA 4.0), calcolo (VERSIONE_CALCOLO 1.0), dati (contatore nel database).
- [19] (contratto) I lettori dichiarano cosa gli serve invece di pretendere una versione identica: SCHEMA_RICHIESTO e CALCOLO_ACCETTATO con l'operatore ~= ; nuove funzioni compatibile() e documento_leggibile().
- [19] (contratto) Schema 4.0: chiave interna del soggetto (Soggetto), fotografie dei dati (VersioneDati) e risultati per coppia calcolo/dati (Esecuzione); la versione dello schema la scrivono le migrazioni nella tabella grafo_info.
- [19] (contratto) Documenti JSON auto-descrittivi: SCHEMA_SPIEGAZIONE "spiegazione/1.0" e SPIEGAZIONE_ACCETTATA.
- [19] (contratto) Le regole complete sono in COMPATIBILITA.md, con la lista di controllo per le modifiche di schema.
- [20] (contratto) Il numero di versione del codice diventa un intero (20); schema e calcolo restano a due numeri.
- [20] (contratto) Schema 4.1 (migrazione 0002, sola espansione): tabelle grafo_parametro, grafo_token, grafo_sessione, grafo_richiesta, grafo_mappa; SCHEMA_RICHIESTO passa a ~=4.1.
- [20] (contratto) Restrizioni dell'amministratore sulle versioni accettate (PARAMETRI, accettata(), restrizione_valida()): si aggiungono a ciò che il codice sa leggere, possono restringere e mai allargare; una restrizione scritta male viene ignorata.
- [20] (contratto) Sesto strumento mappa in NOMI_STRUMENTI; versioni del protocollo MCP parlate dal servizio HTTP (PROTOCOLLI_MCP).
- [21] (contratto) Schema 4.2 (migrazione 0003, sola espansione): su grafo_sessione le colonne accesso e client_oauth; nuovo parametro token_personali_ammessi; SCHEMA_RICHIESTO passa a ~=4.2.
- [21] (contratto) Nuove costanti ACCESSO_TOKEN, ACCESSO_OAUTH e AMBITO_OAUTH (l'ambito "grafo" richiesto dal servizio MCP).
- [22] (contratto) Settimo strumento calcola in NOMI_STRUMENTI; STRUMENTI_SENZA_ARCHIVIO elenca gli strumenti che non leggono punteggi e dati.
- [23] (contratto) Ottavo strumento scheda in NOMI_STRUMENTI e in STRUMENTI_SENZA_ARCHIVIO: legge l'archivio dei file caricati, non quello dell'analisi di rete.
- [25] (contratto) Nuova costante VERSIONE_CALCOLO_REGOLE (1.0+regole): stessa forma dei risultati della GNN, etichetta distinta; i lettori che accettano 1.0 la accettano.
- [26] (contratto) Nono strumento spazio in NOMI_STRUMENTI e in STRUMENTI_SENZA_ARCHIVIO: legge l'app indici, non l'archivio dell'analisi di rete.

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
- [18] (calcolo) Il dizionario delle descrizioni viene caricato nel database (salva_dizionario_indicatori) a ogni calcolo.
- [18] (calcolo) Ogni spiegazione conserva 10 indicatori invece di 3, per rendere utile la ricerca per indicatore.
- [18] (calcolo) Il messaggio per uno schema diverso dice di eliminare il file e rieseguire il calcolo.
- [19] (calcolo) scrittura.py usa i modelli Django: registra_dati_simulati(), registra_esecuzione(), salva_spiegazione(), richieste_pendenti(), esecuzione_piu_recente(), nodi_dei_soggetti().
- [19] (calcolo) Nulla viene più cancellato a ogni avvio: dati nuovi aggiungono una fotografia, dati identici riusano quella esistente (impronta), e solo il ricalcolo della stessa coppia calcolo/dati la sostituisce.
- [19] (calcolo) Le spiegazioni si salvano come documenti auto-descrittivi che nominano i soggetti con la chiave interna, non con l'indice del nodo (documento_spiegazione).
- [19] (calcolo) Un file di modello per ogni coppia calcolo/dati, nella cartella dati_grafo insieme ai file JSON in ingresso (calcolo_cartella.py).
- [19] (calcolo) Si avvia con python manage.py grafo_calcolo (--spiegazioni per la sola coda).
- [24] (calcolo) Nuovo modulo dati_reali.py e comando python manage.py grafo_dati_reali: fotografia dei dati presa dall'archivio dell'applicativo (un nodo per ogni soggetto dell'anagrafica mittente o destinatario di un documento confermato, un arco per documento), al posto dei dati simulati.
- [24] (calcolo) Anagrafica unica: il soggetto del grafo ricorda quello dell'anagrafica nel riferimento ANAG-<numero>; i documenti di caricamenti riservati a un'indagine non entrano nella fotografia; quelli senza data, importo o una delle due parti sono contati e riportati.
- [25] (calcolo) registra_esecuzione() accetta la versione del calcolo: l'indice a regole (app indici) si registra come esecuzione a sé, calcolo 1.0+regole, con le regole scattate come spiegazione.
- [25] (calcolo) La fotografia dei dati reali comprende anche le aziende che hanno dati per periodo (soggetti.DatiPerPeriodo), pur senza documenti.

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
- [18] (interrogazione) Le società si indicano anche per nome, anche parziale, numero di iscrizione o identificativo fiscale (risolvi_societa, elenco_societa): maiuscole, accenti e punteggiatura non contano.
- [18] (interrogazione) Un nome che corrisponde a più società non viene indovinato: lo strumento le elenca e chiede quale; per un nome sconosciuto propone i più simili.
- [18] (interrogazione) Tutti i testi riportano nome e numero di iscrizione accanto al numero della società (etichetta, nome_breve); verso_relazione() può nominare le società per nome.
- [18] (interrogazione) Nuovo strumento indicatore(termine, societa): cerca gli indicatori per parola della descrizione (cerca_indicatori) e dice per quali società pesano di più (contesto_indicatore), fra le spiegazioni già calcolate.
- [18] (interrogazione) consulta() riconosce nella domanda i nomi delle società e la ricerca di un indicatore; gli strumenti accettano per la società sia un numero sia un testo.
- [18] (interrogazione) Nei testi le features si chiamano indicatori; il contesto ne riporta i primi 5.
- [19] (interrogazione) Letture riscritte per PostgreSQL: passano tutte da _righe(), unico punto di contatto con il database, e usano la connessione di Django.
- [19] (interrogazione) Lettore tollerante: accetta gli schemi che soddisfano SCHEMA_RICHIESTO, nomina le colonne una per una, ignora tabelle, colonne e campi JSON sconosciuti (_normalizza_spiegazione).
- [19] (interrogazione) apri() sceglie la coppia calcolo/dati: la fotografia più recente fra i calcoli accettati, oppure una coppia precisa (parametri o variabili GRAFO_VERSIONE_CALCOLO e GRAFO_VERSIONE_DATI); ogni 60 secondi ricontrolla se ne esiste una più recente.
- [19] (interrogazione) Il numero di una società è la chiave interna del soggetto, stabile fra fotografie e calcoli (prima: l'indice del nodo).
- [19] (interrogazione) I testi dichiarano la coppia in uso ("calcolo 1.0 / dati 2"); nuove esecuzioni_disponibili() ed etichetta_esecuzione().
- [19] (interrogazione) La versione del progetto non produce più avvisi: è solo provenienza.
- [19] (interrogazione) Si prova senza chat con python manage.py grafo_consulta "domanda".
- [20] (interrogazione) apri() legge le restrizioni dell'amministratore (restrizioni_in_vigore) e le applica a schema, calcolo e documenti di spiegazione; i messaggi di errore dicono quando il rifiuto viene da una restrizione.
- [20] (interrogazione) in_esclusiva diventa un nome pubblico: lo usa lo strumento mappa.
- [28] (interrogazione) Con una fotografia dei dati senza indicatori (dati reali) contesto_indicatore() spiega che gli indicatori appartengono al calcolo della GNN e rimanda agli strumenti spazio e classifica, invece di chiedere di copiare un file.
- [29] (interrogazione) risolvi_societa() riconosce un codice comunque scritto: COE10000, COE 10000, C.O.E. SM 10000 e 10000 sono la stessa società; il codice viene cercato prima del numero interno della società, perché sui dati reali il numero che l'ispettore conosce è il COE.

## server

- [16] (server) Nuovo server MCP (server_mcp.py) che registra i quattro strumenti della libreria, per usare Unsloth Studio come chat.
- [16] (server) All'avvio apre l'archivio: se non combacia con il codice il server non parte.
- [17] (server) Compatibile con la libreria mcp 1.x (FastMCP) e 2.x (MCPServer): con la 2.x la versione 16 non partiva (ModuleNotFoundError).
- [17] (server) Strumenti registrati con add_tool() e trasporto stdio indicato in modo esplicito.
- [18] (server) Registra anche il quinto strumento, indicatore (nessuna modifica al codice: l'elenco viene da contratto.py).
- [19] (server) Si avvia con python manage.py grafo_server_mcp, che carica le impostazioni dell'applicativo.
- [20] (server) Nuovo servizio MCP su HTTP dentro l'applicativo (views.py, indirizzo /grafo/mcp/): la chat si collega dalla rete e si presenta con un token personale; senza token valido la risposta è 401.
- [20] (server) Il protocollo è scritto in protocollo_mcp.py (initialize, ping, tools/list, tools/call), senza la libreria mcp, che resta solo per il trasporto stdio.
- [20] (server) Ogni chiamata passa da servizio_mcp.esegui_strumento(): la richiesta viene registrata nella sessione prima dell'esecuzione e completata con esito, durata e coppia calcolo/dati.
- [20] (server) Ogni strumento ha in più il parametro facoltativo domanda, in cui il modello della chat ricopia la domanda dell'ispettore per il registro.
- [20] (server) Nuovo strumento mappa(societa): produce la mappa investigativa e restituisce il collegamento alla pagina /grafo/mappe/N/, visibile dopo l'accesso solo a chi l'ha chiesta.
- [20] (server) Nuove pagine: /grafo/collegamento/ (l'analista crea e revoca i propri token, ritrova le proprie mappe) e /grafo/cruscotto/ (l'amministratore vede le quattro versioni, i calcoli presenti, le sessioni, e modifica i parametri).
- [20] (server) Il server stdio (grafo_server_mcp) resta per le prove su un solo computer: non riconosce l'utente e non registra sessioni.
- [21] (server) Accesso OAuth 2.0 dal browser: l'applicativo è il server di autorizzazione (libreria django-oauth-toolkit 3.4, indirizzi sotto /o/); la chat si registra da sola, l'analista accede e autorizza, il token non si copia più a mano.
- [21] (server) Il rifiuto 401 indica alla chat il documento da cui partire (intestazione WWW-Authenticate con resource_metadata); i documenti di scoperta sono alla radice del sito (/.well-known/...).
- [21] (server) views.py riconosce chi chiama in un solo punto (_identita_della_richiesta): token OAuth verificato dalla libreria (scadenza, ambito, servizio a cui è destinato) oppure token personale.
- [21] (server) Utente riconosciuto ma senza il diritto usa_chat: risposta 403, distinta dal 401 che fa ripartire l'accesso.
- [21] (server) Nuova pagina di consenso in italiano (templates/oauth2_provider/authorize.html): mostra il programma che chiede l'accesso e l'indirizzo a cui si viene rimandati.
- [21] (server) La pagina "Collegamento alla chat" indica l'accesso OAuth come via normale e i token personali come ripiego; il cruscotto mostra per ogni sessione il tipo di accesso.
- [21] (server) La pagina di consenso si salta quando l'utente ha già autorizzato lo stesso programma e il suo token non è scaduto (REQUEST_APPROVAL_PROMPT auto; con CONTROLLI_OAUTH_CONSENSO=force torna a ogni accesso).
- [22] (server) Nuovo strumento calcola(espressione), nel modulo calcolatrice.py: aritmetica esatta per la chat, valutata come albero sintattico senza eseguire codice; limiti su lunghezza, esponente e dimensione del risultato.
- [22] (server) Le chiamate a calcola sono registrate nella sessione come le altre, senza coppia calcolo/dati; lo strumento funziona anche se l'archivio non è utilizzabile.
- [23] (server) Nuovo strumento scheda(azienda): dice ciò che l'archivio sa di un'azienda (voci note con il file di provenienza, voci non ancora arrivate, documenti confermati in cui compare con il ruolo e le altre parti); l'azienda si indica con COE, partita IVA o nome.
- [23] (server) scheda usa solo ciò che viene da file che l'utente della sessione può vedere (stessa regola delle pagine); senza sessione (trasporto stdio) non risponde.
- [26] (server) Nuovo strumento spazio(regola, azienda): racconta lo spazio degli indici (per quali aziende scatta una regola, quali si discostano dalle aziende simili, i rapporti di un'azienda dai documenti confermati) e dà il collegamento alla pagina in tre dimensioni, con regola e azienda già scelte.
- [26] (server) esegui_strumento() riceve l'indirizzo pubblico dell'applicativo, per i collegamenti alle pagine che non sono mappe.
- [27] (server) Lo strumento classifica risponde per criteri distinti: 1) regole di rischio che scattano (tutte quelle attive, o quella indicata nel nuovo parametro regola), 2) scostamento dalle aziende simili, 3) rapporti con aziende segnalate, 4) punteggio dell'analisi di rete; in testa le aziende segnalate da più criteri.
- [27] (server) Quando l'esecuzione in uso è l'indice a regole (dati reali), classifica non la presenta come un quarto criterio: dichiara che la GNN non è calcolata su quei dati. Senza sessione (stdio) classifica resta la sola analisi di rete.
- [28] (server) Lo strumento indicatore, se riceve come termine solo parole che indicano lo spazio degli indici (indici, spazio, regole), passa la domanda allo strumento spazio; le descrizioni dei due strumenti dicono esplicitamente quando usare l'uno e quando l'altro.
- [30] (server) La pagina di una mappa che non si può mostrare resta 404 ma spiega che cosa fare: con quale utente si è collegati e che la mappa si apre con l'utente che ha autorizzato la chat, oppure che il file non c'è più e va richiesta di nuovo; il motivo preciso va nel registro del server.
- [31] (server) Gli strumenti mappa e spazio dicono con quale utente va aperto il collegamento (quello che ha autorizzato la chat); la pagina di collegamento elenca le chat autorizzate con il proprio utente e permette di scollegarle.

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
- [18] (mappa) Il report mostra i primi 3 indicatori dei 10 ora conservati in ogni spiegazione.
- [19] (mappa) Il file della mappa porta nel nome soggetto e coppia calcolo/dati e viene scritto in dati_grafo: mappe diverse non si sovrascrivono.
- [19] (mappa) Si può scegliere il soggetto: python manage.py grafo_mappa --soggetto "nome o numero".
- [20] (mappa) Nuova produci(): restituisce percorso, nome del file e soggetto; chiesta dalla chat, la mappa porta nel nome anche il numero di sessione, così analisti diversi non si sovrascrivono.

## sessioni

- [20] (sessioni) Nuovo modulo sessioni.py: parametri dell'amministratore, token personali, sessioni, registro delle richieste e delle mappe.
- [20] (sessioni) Il numero di sessione è assegnato dal database quando la chat si collega; la sessione si chiude dopo i minuti di inattività scelti dall'amministratore (parametro minuti_inattivita_sessione, predefinito 30).
- [20] (sessioni) Conta come attività solo la chiamata a uno strumento; una richiesta che arriva a sessione scaduta ne apre una nuova sulla stessa connessione.
- [20] (sessioni) Del token si conserva solo l'impronta SHA-256: il testo in chiaro è mostrato una volta a chi lo crea; revocarlo chiude le sessioni aperte.
- [20] (sessioni) Un parametro viene controllato prima del salvataggio: una restrizione che escluderebbe lo schema attuale o tutti i calcoli presenti è rifiutata.
- [20] (sessioni) Nuovo diritto grafo.usa_chat (ruolo Analista); cruscotto e registro sono del ruolo Amministratore.
- [20] (sessioni) Nuovo comando python manage.py grafo_token UTENTE.
- [21] (sessioni) Le sessioni ricevono un'identità già verificata (Identita: utente, tipo di accesso, token o programma della chat) e non sanno più nulla di token: identita_da_token(), identita_oauth(), puo_usare_la_chat().
- [21] (sessioni) Ogni sessione registra come è stato fatto l'accesso (token oppure oauth) e, per OAuth, il nome con cui la chat si è registrata.
- [21] (sessioni) I token personali diventano un ripiego che l'amministratore può spegnere dal cruscotto (parametro token_personali_ammessi: si / no).
- [31] (sessioni) Nuove funzioni chat_autorizzate() e scollega_chat(): l'utente vede quali programmi di chat agiscono a suo nome con l'accesso OAuth e può revocarli; scollegare chiude le sessioni aperte, e la chat deve rifare l'accesso dal browser.
