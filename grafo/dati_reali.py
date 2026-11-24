# >>> NOVITA (generato da aggiorna_intestazioni.py da NOVITA.md: non modificare a mano)
#
#   dati_reali.py  -  app grafo, VERSIONE 33
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
DATI REALI: la fotografia dei dati in ingresso presa dall'archivio dell'applicativo,
al posto di quella simulata (DECISIONI.md, n. 85).

    archivio (file caricati)  -->  elaborazione (documenti confermati)  -->  QUI  -->  grafo_versione_dati
                                                                                       grafo_dati_soggetto
                                                                                       grafo_relazione

Che cosa entra nella fotografia:
  - un NODO per ogni soggetto dell'anagrafica che è mittente o destinatario di un
    documento confermato da una persona, oppure che ha dei dati per periodo
    (soggetti.DatiPerPeriodo: le aziende importate dall'anagrafica ufficiale); il soggetto del grafo ricorda quello
    dell'anagrafica nel campo riferimento ("ANAG-<numero>"): è l'anagrafica unica;
  - un ARCO per ogni documento confermato che ha mittente, destinatario, data e
    importo totale: mittente = venditore, destinatario = acquirente.

Che cosa NON entra:
  - i documenti che vengono da caricamenti riservati a un'indagine: il grafo lo
    consulta chiunque usi la chat, e non deve rivelare chi è sotto esame (n. 17-19, 63);
  - i documenti senza data o senza importo, o in cui manca una delle due parti:
    vengono contati e riportati, così si sa che cosa completare nella revisione;
  - il vettore: lo schema delle relazioni ha oggi solo venditore e acquirente.

La fotografia non contiene punteggi: quelli li produce un calcolo. Finché nessun
calcolo è stato eseguito su di lei, gli strumenti della chat continuano a usare
l'ultima esecuzione disponibile.

È l'unico modulo dell'app grafo che legge le altre app dell'applicativo.
"""
import collections

from django.db import transaction
from django.db.models import Max

from elaborazione import models as elaborazione
from elaborazione.models import Documento
from soggetti import servizi as anagrafica
from soggetti.models import DatiPerPeriodo
from soggetti.models import Soggetto as SoggettoAnagrafica

from . import scrittura
from .models import DatiSoggetto, Relazione, Soggetto, VersioneDati

PREFISSO = "ANAG-"

# Motivi per cui un documento confermato non diventa un arco
SENZA_MITTENTE, SENZA_DESTINATARIO, STESSO_SOGGETTO = "senza mittente", "senza destinatario", "mittente e destinatario coincidono"
SENZA_DATA, SENZA_IMPORTO = "senza data", "senza importo totale"


def riferimento(soggetto_anagrafica):
    """Come il soggetto del grafo ricorda quello dell'anagrafica."""
    return f"{PREFISSO}{soggetto_anagrafica.pk}"


def soggetto_dell_anagrafica(riferimento_del_grafo):
    """Il numero del soggetto dell'anagrafica a cui corrisponde un soggetto del grafo, o None (dati simulati)."""
    numero = riferimento_del_grafo[len(PREFISSO):] if riferimento_del_grafo.startswith(PREFISSO) else ""
    return int(numero) if numero.isdigit() else None


def come_arco(documento):
    """
    Un documento confermato visto come arco: (mittente, destinatario, None), oppure
    (None, None, motivo) se non può diventarlo. È il solo punto in cui lo si decide:
    lo usano la fotografia dei dati e la diagnosi.
    """
    per_ruolo = {}
    for parte in documento.parti.all():
        if not parte.ritirata and parte.soggetto_id:
            per_ruolo.setdefault(parte.ruolo, parte.soggetto)
    mittente, destinatario = per_ruolo.get(elaborazione.MITTENTE), per_ruolo.get(elaborazione.DESTINATARIO)
    if mittente is None:
        return None, None, SENZA_MITTENTE
    if destinatario is None:
        return None, None, SENZA_DESTINATARIO
    if mittente.pk == destinatario.pk:
        return None, None, STESSO_SOGGETTO
    if documento.data is None:
        return None, None, SENZA_DATA
    if documento.totale is None:
        return None, None, SENZA_IMPORTO
    return mittente, destinatario, None


def archi_dall_archivio():
    """
    I documenti confermati e non riservati che possono diventare archi.
    Restituisce (archi, esclusi): archi = [(mittente, destinatario, documento)] con i
    soggetti dell'anagrafica, esclusi = {motivo: quanti}.
    """
    documenti = (
        Documento.objects.utilizzabili()
        .filter(file__fascicolo__faldone__riservato=False, file__fascicolo__riservato_a__isnull=True)
        .prefetch_related("parti__soggetto").order_by("pk")
    )
    archi, esclusi = [], collections.Counter()
    for documento in documenti:
        mittente, destinatario, motivo = come_arco(documento)
        if motivo:
            esclusi[motivo] += 1
        else:
            archi.append((mittente, destinatario, documento))
    return archi, dict(esclusi)


def diagnosi(soggetto_anagrafica):
    """
    Perché un'azienda ha, o non ha, rapporti nell'analisi di rete: segue un documento
    lungo tutta la strada che deve fare per diventare una linea nella mappa.

        file caricato -> elaborato -> documento riconosciuto -> confermato da una persona
        -> mittente, destinatario, data e totale presenti -> non riservato a un'indagine
        -> entrato in una fotografia dei dati -> quella fotografia ha un calcolo -> è quella in uso

    Restituisce le righe di un resoconto, in parole. Non dice nulla dei file che chi
    esegue il comando non dovrebbe vedere oltre al fatto che esistono: è uno strumento
    per chi amministra il sistema, da terminale.
    """
    from archivio.models import CollegamentoFile

    from . import contratto, interrogazione

    righe = [f"Azienda: {anagrafica.etichetta(soggetto_anagrafica)} (soggetto n. {soggetto_anagrafica.pk} dell'anagrafica)"]

    # 1. I file che la riguardano e i documenti riconosciuti
    collegati = (
        CollegamentoFile.objects.filter(fascicolo__soggetto=soggetto_anagrafica)
        .select_related("file__fascicolo__faldone").order_by("file_id")
    )
    file_visti, pronti = {}, 0
    for collegamento in collegati:
        file_visti[collegamento.file_id] = collegamento.file
    righe.append(f"\n1. File che la riguardano: {len(file_visti)}")
    for file in file_visti.values():
        documenti = list(Documento.objects.filter(file=file).prefetch_related("parti__soggetto"))
        riservato = file.fascicolo.faldone.riservato or file.fascicolo.riservato_a_id is not None
        righe.append(f"   - file n. {file.pk} «{file.percorso_originale}»: stato «{file.stato}»"
                     + (f" ({file.ultimo_errore[:120]})" if file.ultimo_errore else ""))
        if not documenti:
            righe.append("       nessun documento riconosciuto: il file non è stato ancora elaborato dal modello, "
                         "oppure il modello non vi ha visto un documento commerciale")
        for documento in documenti:
            parti = "; ".join(
                f"{parte.ruolo or '(ruolo da assegnare)'}: {parte.denominazione or '-'}"
                + (" [senza soggetto]" if not parte.soggetto_id else "") + (" [tolta]" if parte.ritirata else "")
                for parte in documento.parti.all()
            )
            righe.append(f"       documento {documento.tipo or '?'} n. {documento.numero or '?'} del {documento.data or '?'}, "
                         f"totale {documento.totale if documento.totale is not None else '?'}; parti: {parti or 'nessuna'}")
            if documento.ritirato:
                esito = "NON entra: è stato scartato"
            elif not documento.confermato:
                esito = "NON entra: non è ancora confermato (aprire «Testo ed entità estratte» e chiudere la revisione)"
            elif riservato:
                esito = "NON entra: viene da un caricamento riservato a un'indagine"
            else:
                _, _, motivo = come_arco(documento)
                esito = f"NON entra: {motivo} (correggerlo nella revisione)" if motivo else "può entrare nel grafo"
                pronti += motivo is None
            righe.append(f"       -> {esito}")

    # 2. Le fotografie dei dati
    del_grafo = Soggetto.objects.filter(riferimento=riferimento(soggetto_anagrafica)).first()
    righe.append(f"\n2. Documenti pronti per il grafo: {pronti}")
    if del_grafo is None:
        righe.append("   L'azienda non è in nessuna fotografia dei dati: lanciare «Aggiorna il grafo e calcola gli indici» "
                     "(python manage.py calcola_indici).")
        return righe
    righe.append(f"   Nel grafo è la società n. {del_grafo.pk}.")
    fotografie = list(VersioneDati.objects.filter(
        pk__in=DatiSoggetto.objects.filter(soggetto=del_grafo).values("versione_dati")
    ).order_by("-numero"))
    conteggi = {}
    for fotografia in fotografie[:5]:
        conteggi[fotografia.numero] = (
            Relazione.objects.filter(versione_dati=fotografia, venditore=del_grafo).count()
            + Relazione.objects.filter(versione_dati=fotografia, acquirente=del_grafo).count()
        )
        righe.append(f"   - dati n. {fotografia.numero} ({fotografia.descrizione}): {conteggi[fotografia.numero]} rapporti dell'azienda")

    # 3. Che cosa stanno usando la chat e la mappa
    try:
        interrogazione.chiudi()
        interrogazione.apri()
        in_uso = interrogazione.leggi_esecuzione()
    except contratto.ArchivioIncompatibile as errore:
        righe.append(f"\n3. L'archivio dell'analisi di rete non è utilizzabile: {errore}")
        return righe
    numero = in_uso["numero_dati"]
    righe.append(f"\n3. In uso da chat e mappa: calcolo {in_uso['versione_calcolo']} / dati n. {numero}")
    piu_recente = fotografie[0].numero if fotografie else None
    if numero not in {f.numero for f in fotografie}:
        righe.append("   Questa fotografia NON contiene l'azienda: per questo la mappa non la mostra con i suoi rapporti. "
                     "Probabilmente è la fotografia dei dati simulati (calcolo della GNN).")
    else:
        righe.append(f"   In questa fotografia l'azienda ha {conteggi.get(numero, '?')} rapporti.")
    righe.append("\nChe cosa fare:")
    if pronti and (piu_recente is None or conteggi.get(piu_recente, 0) < pronti):
        righe.append("   - Ci sono documenti pronti che non sono ancora in una fotografia: lanciare «Aggiorna il grafo e calcola gli indici».")
    if piu_recente is not None and numero != piu_recente:
        righe.append(f"   - La fotografia più recente con l'azienda è la n. {piu_recente}, ma è in uso la n. {numero}: "
                     "manca un calcolo sulla più recente (lanciare «Aggiorna il grafo e calcola gli indici»), oppure una restrizione "
                     "del cruscotto sta scegliendo un altro calcolo.")
    if not pronti:
        righe.append("   - Nessun documento è pronto: guardare al punto 1 che cosa manca a ciascuno.")
    if pronti and piu_recente == numero and conteggi.get(numero, 0) >= pronti:
        righe.append("   - Nulla: i rapporti sono nella fotografia in uso. Richiedere la mappa.")
    return righe


def _identificativi(soggetto):
    """(numero di iscrizione, identificativo fiscale) da mostrare: il COE se c'è, e il primo identificativo."""
    righe = list(soggetto.identificativi.select_related("tipo").order_by("pk"))
    coe = next((riga.valore_normalizzato for riga in righe if riga.tipo.codice == "COE"), "")
    return coe, (str(righe[0]) if righe else "")


@transaction.atomic
def fotografa(descrizione="dati reali dall'archivio"):
    """
    Registra la fotografia dei dati reali e restituisce un resoconto:
        {"versione_dati", "nuova": bool, "soggetti": n, "relazioni": n, "esclusi": {motivo: quanti}}
    Se dall'ultima volta non è cambiato nulla NON crea una nuova fotografia (stessa
    impronta). Senza nessun soggetto non crea nulla: "versione_dati" è None.
    """
    archi, esclusi = archi_dall_archivio()
    resoconto = {"versione_dati": None, "nuova": False, "soggetti": 0, "relazioni": len(archi), "esclusi": esclusi}
    nodi = {s.pk: s for s in SoggettoAnagrafica.objects.filter(dati_per_periodo__isnull=False).distinct()}
    for mittente, destinatario, _ in archi:
        nodi[mittente.pk], nodi[destinatario.pk] = mittente, destinatario
    if not nodi:
        return resoconto
    resoconto["soggetti"] = len(nodi)
    schede = {
        numero: (soggetto.denominazione or anagrafica.etichetta(soggetto), *_identificativi(soggetto))
        for numero, soggetto in sorted(nodi.items())
    }
    righe = [
        (mittente.pk, destinatario.pk, f"{documento.tipo} {documento.numero}".strip(), documento.data, documento.totale)
        for mittente, destinatario, documento in archi
    ]
    # Anche i dati per periodo fanno parte dei dati in ingresso: se cambiano, la fotografia è un'altra
    per_periodo = list(
        DatiPerPeriodo.objects.filter(soggetto__in=list(nodi)).order_by("soggetto_id", "periodo")
        .values_list(
            "soggetto_id", "periodo", "codice_attivita", "dipendenti", "fatturato",
            "classe_dipendenti", "classe_fatturato",
        )
    )
    impronta = scrittura._impronta("dati reali", schede, righe, per_periodo)
    esistente = VersioneDati.objects.filter(impronta=impronta).first()
    if esistente is not None:
        resoconto["versione_dati"] = esistente
        return resoconto

    # I soggetti del grafo hanno una chiave stabile: si creano una volta sola
    riferimenti = {numero: riferimento(soggetto) for numero, soggetto in nodi.items()}
    gia_presenti = set(Soggetto.objects.filter(riferimento__in=riferimenti.values()).values_list("riferimento", flat=True))
    Soggetto.objects.bulk_create([Soggetto(riferimento=r) for r in riferimenti.values() if r not in gia_presenti])
    nel_grafo = dict(Soggetto.objects.filter(riferimento__in=riferimenti.values()).values_list("riferimento", "id"))
    chiave = {numero: nel_grafo[riferimenti[numero]] for numero in nodi}

    ultimo = VersioneDati.objects.aggregate(massimo=Max("numero"))["massimo"] or 0
    versione_dati = VersioneDati.objects.create(numero=ultimo + 1, impronta=impronta, descrizione=descrizione[:255])
    DatiSoggetto.objects.bulk_create([
        DatiSoggetto(
            versione_dati=versione_dati, soggetto_id=chiave[numero], nome=nome[:255],
            nr_iscrizione=iscrizione[:80], id_fiscale=fiscale[:80], ispezionata=False,
        )
        for numero, (nome, iscrizione, fiscale) in schede.items()
    ])
    Relazione.objects.bulk_create([
        Relazione(
            versione_dati=versione_dati, venditore_id=chiave[mittente], acquirente_id=chiave[destinatario],
            documento=(nome or "documento")[:80], data=data, importo=importo,
        )
        for mittente, destinatario, nome, data, importo in righe
    ])
    resoconto.update(versione_dati=versione_dati, nuova=True)
    return resoconto
