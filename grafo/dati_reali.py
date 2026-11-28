# >>> NOVITA (generato da aggiorna_intestazioni.py da NOVITA.md: non modificare a mano)
#
#   dati_reali.py  -  app grafo, VERSIONE 39
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
#   [35] I testi della diagnosi e dei comandi dicono «società» al posto di azienda e soggetto.
#   [37] La fotografia dei dati reali accetta i criteri di ammissione
#        (elaborazione/ammissione.py): con quelli larghi entrano anche i documenti non
#        confermati, con i ruoli proposti dal modello, segnati come non verificati; la
#        descrizione della fotografia ricorda i criteri, il resoconto conta i rapporti non
#        verificati, la diagnosi dice «può entrare, come NON VERIFICATO».
#   [38] Nuova funzione stato_dei_dati() in dati_reali.py: dice se la fotografia in uso (la più
#        recente con un calcolo) è quella che l'archivio darebbe ora, confrontando l'impronta
#        dei dati, per ogni combinazione dei criteri sui documenti; le pagine la usano per
#        l'avviso «dati non aggiornati». fotografa() e stato_dei_dati() leggono l'archivio con
#        la stessa funzione _ingresso().
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

from elaborazione import ammissione
from elaborazione import models as elaborazione
from elaborazione.models import Documento
from soggetti import servizi as anagrafica
from soggetti.models import DatiPerPeriodo
from soggetti.models import Soggetto as SoggettoAnagrafica

from . import contratto, scrittura
from .models import DatiSoggetto, Relazione, Soggetto, VersioneDati

PREFISSO = "ANAG-"

# Motivi per cui un documento confermato non diventa un arco
SENZA_MITTENTE, SENZA_DESTINATARIO, STESSO_SOGGETTO = "senza mittente", "senza destinatario", "mittente e destinatario coincidono"
SENZA_DATA, SENZA_IMPORTO = "senza data", "senza importo totale"
# Come un rapporto ricorda di venire da un documento che nessuno ha ancora confermato: sta in
# coda al nome del documento, così lo mostrano senza modifiche chat, mappa e ogni altro lettore.
NON_VERIFICATO = contratto.SEGNO_NON_VERIFICATO


def nome_del_documento(documento):
    """Il nome con cui un documento entra nella fotografia: "fattura 12", con il segno se non è confermato."""
    nome = f"{documento.tipo} {documento.numero}".strip() or "documento"
    return nome[:80] if documento.confermato else nome[:80 - len(NON_VERIFICATO)] + NON_VERIFICATO


def riferimento(soggetto_anagrafica):
    """Come il soggetto del grafo ricorda quello dell'anagrafica."""
    return f"{PREFISSO}{soggetto_anagrafica.pk}"


def soggetto_dell_anagrafica(riferimento_del_grafo):
    """Il numero del soggetto dell'anagrafica a cui corrisponde un soggetto del grafo, o None (dati simulati)."""
    numero = riferimento_del_grafo[len(PREFISSO):] if riferimento_del_grafo.startswith(PREFISSO) else ""
    return int(numero) if numero.isdigit() else None


def come_arco(documento):
    """
    Un documento visto come arco (confermato o no: per uno non confermato valgono i ruoli proposti): (mittente, destinatario, None), oppure
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


def archi_dall_archivio(criteri=None):
    """
    I documenti ammessi dai criteri (elaborazione/ammissione.py; None = quelli predefiniti) e non
    riservati che possono diventare archi. Con i criteri severi sono i soli documenti confermati.
    Restituisce (archi, esclusi): archi = [(mittente, destinatario, documento)] con i
    soggetti dell'anagrafica, esclusi = {motivo: quanti}. documento.confermato dice se è verificato.
    """
    documenti = (
        ammissione.documenti(criteri)
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

    from . import interrogazione

    righe = [f"Società: {anagrafica.etichetta(soggetto_anagrafica)} (società n. {soggetto_anagrafica.pk} dell'anagrafica)"]

    # 1. I file che la riguardano e i documenti riconosciuti
    collegati = (
        CollegamentoFile.objects.filter(fascicolo__soggetto=soggetto_anagrafica)
        .select_related("file__fascicolo__faldone").order_by("file_id")
    )
    file_visti, pronti = {}, 0
    ammessi = set(ammissione.documenti().values_list("pk", flat=True))   # con i criteri predefiniti
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
                + (" [senza società]" if not parte.soggetto_id else "") + (" [tolta]" if parte.ritirata else "")
                for parte in documento.parti.all()
            )
            righe.append(f"       documento {documento.tipo or '?'} n. {documento.numero or '?'} del {documento.data or '?'}, "
                         f"totale {documento.totale if documento.totale is not None else '?'}; parti: {parti or 'nessuna'}")
            if documento.ritirato:
                esito = "NON entra: è stato scartato"
            elif documento.pk not in ammessi:
                esito = ("NON entra: non è confermato, e i criteri in vigore non ammettono i documenti non confermati "
                         "(o le letture incomplete): confermarlo, oppure cambiare i criteri al lancio del calcolo")
            elif riservato:
                esito = "NON entra: viene da un caricamento riservato a un'indagine"
            else:
                _, _, motivo = come_arco(documento)
                esito = f"NON entra: {motivo} (correggerlo nella revisione)" if motivo else (
                    "può entrare nel grafo" if documento.confermato else "può entrare nel grafo, come NON VERIFICATO")
                pronti += motivo is None
            righe.append(f"       -> {esito}")

    # 2. Le fotografie dei dati
    del_grafo = Soggetto.objects.filter(riferimento=riferimento(soggetto_anagrafica)).first()
    righe.append(f"\n2. Documenti pronti per il grafo: {pronti}")
    if del_grafo is None:
        righe.append("   La società non è in nessuna fotografia dei dati: lanciare «Aggiorna il grafo e calcola gli indici» "
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
        righe.append(f"   - dati n. {fotografia.numero} ({fotografia.descrizione}): {conteggi[fotografia.numero]} rapporti della società")

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
        righe.append("   Questa fotografia NON contiene la società: per questo la mappa non la mostra con i suoi rapporti. "
                     "Probabilmente è la fotografia dei dati simulati (calcolo della GNN).")
    else:
        righe.append(f"   In questa fotografia la società ha {conteggi.get(numero, '?')} rapporti.")
    righe.append("\nChe cosa fare:")
    if pronti and (piu_recente is None or conteggi.get(piu_recente, 0) < pronti):
        righe.append("   - Ci sono documenti pronti che non sono ancora in una fotografia: lanciare «Aggiorna il grafo e calcola gli indici».")
    if piu_recente is not None and numero != piu_recente:
        righe.append(f"   - La fotografia più recente con la società è la n. {piu_recente}, ma è in uso la n. {numero}: "
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


def _ingresso(criteri):
    """
    Ciò che l'archivio darebbe ORA a una fotografia, senza scrivere nulla:
        {"archi", "esclusi", "nodi": {numero: soggetto}, "schede", "righe", "impronta"}
    Lo usano fotografa(), che lo registra, e stato_dei_dati(), che lo confronta con ciò che è in uso.
    Senza nessuna società "impronta" è None.
    """
    archi, esclusi = archi_dall_archivio(criteri)
    nodi = {s.pk: s for s in SoggettoAnagrafica.objects.filter(dati_per_periodo__isnull=False).distinct()}
    for mittente, destinatario, _ in archi:
        nodi[mittente.pk], nodi[destinatario.pk] = mittente, destinatario
    ingresso = {"archi": archi, "esclusi": esclusi, "nodi": nodi, "schede": {}, "righe": [], "impronta": None}
    if not nodi:
        return ingresso
    ingresso["schede"] = {
        numero: (soggetto.denominazione or anagrafica.etichetta(soggetto), *_identificativi(soggetto))
        for numero, soggetto in sorted(nodi.items())
    }
    ingresso["righe"] = [
        (mittente.pk, destinatario.pk, nome_del_documento(documento), documento.data, documento.totale)
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
    ingresso["impronta"] = scrittura._impronta("dati reali", ingresso["schede"], ingresso["righe"], per_periodo)
    return ingresso


def stato_dei_dati():
    """
    I dati che chat, mappa e classifica stanno usando sono quelli che l'archivio darebbe ora?
        {"aggiornati": bool, "vuoto": bool, "mai_calcolati": bool, "numero_in_uso": n o None,
         "societa_ora", "societa_in_uso", "rapporti_ora", "rapporti_in_uso"}
    "In uso" è la fotografia più recente su cui esiste un calcolo. Il confronto è esatto (stessa
    impronta dei dati), e vale per qualunque combinazione dei criteri sui documenti: se
    l'amministratore ha calcolato con criteri diversi da quelli predefiniti, i dati sono aggiornati
    lo stesso. Non scrive nulla. "vuoto": l'archivio non ha ancora dati reali da calcolare.
    """
    from .models import Esecuzione

    predefiniti = ammissione.predefiniti()
    ora = _ingresso(predefiniti)
    stato = {
        "aggiornati": True, "vuoto": not ora["nodi"], "mai_calcolati": False, "numero_in_uso": None,
        "societa_ora": len(ora["nodi"]), "rapporti_ora": len(ora["archi"]), "societa_in_uso": 0, "rapporti_in_uso": 0,
    }
    if stato["vuoto"]:
        return stato
    in_uso = (
        VersioneDati.objects.filter(pk__in=Esecuzione.objects.values("versione_dati")).order_by("-numero").first()
    )
    if in_uso is None or not in_uso.descrizione.startswith("dati reali"):
        stato.update(aggiornati=False, mai_calcolati=True)
        return stato
    stato.update(
        numero_in_uso=in_uso.numero,
        societa_in_uso=DatiSoggetto.objects.filter(versione_dati=in_uso).count(),
        rapporti_in_uso=Relazione.objects.filter(versione_dati=in_uso).count(),
    )
    if ora["impronta"] == in_uso.impronta:
        return stato
    # criteri diversi da quelli predefiniti, scelti al lancio del calcolo
    altri = (
        ammissione.SOLO_VERIFICATI,
        predefiniti._replace(documenti_non_confermati=True, letture_incomplete=False),
        predefiniti._replace(documenti_non_confermati=True, letture_incomplete=True),
    )
    stato["aggiornati"] = any(
        criteri != predefiniti and _ingresso(criteri)["impronta"] == in_uso.impronta for criteri in altri
    )
    return stato


def stato_per_le_pagine():
    """
    stato_dei_dati() per le pagine: None se non si riesce a calcolarlo. Un avviso che non si
    può calcolare non deve impedire di aprire una pagina; l'errore va nel registro.
    """
    import logging

    try:
        return stato_dei_dati()
    except Exception:
        logging.getLogger(__name__).exception("Stato dei dati non calcolabile")
        return None


@transaction.atomic
def fotografa(descrizione="dati reali dall'archivio", criteri=None):
    """
    Registra la fotografia dei dati reali e restituisce un resoconto:
        {"versione_dati", "nuova": bool, "soggetti": n, "relazioni": n, "non_verificate": n,
         "criteri": Criteri, "esclusi": {motivo: quanti}}
    criteri dice che cosa è ammesso oltre ai documenti confermati (None = quelli predefiniti):
    la scelta è scritta nella descrizione della fotografia, e ogni rapporto non verificato lo dice nel nome.
    Se dall'ultima volta non è cambiato nulla NON crea una nuova fotografia (stessa
    impronta). Senza nessun soggetto non crea nulla: "versione_dati" è None.
    """
    criteri = criteri or ammissione.predefiniti()
    ingresso = _ingresso(criteri)
    archi, nodi, schede, righe, impronta = (ingresso[k] for k in ("archi", "nodi", "schede", "righe", "impronta"))
    resoconto = {
        "versione_dati": None, "nuova": False, "soggetti": len(nodi), "relazioni": len(archi), "esclusi": ingresso["esclusi"],
        "non_verificate": sum(1 for _, _, documento in archi if not documento.confermato), "criteri": criteri,
    }
    descrizione = f"{descrizione}; {ammissione.descrivi(criteri, solo_documenti=True)}"
    if not nodi:
        return resoconto
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
