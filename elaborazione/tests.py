import datetime
import decimal
import json
import tempfile
import types
from io import StringIO

from django.core.management import call_command
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from archivio import cancellazione, caricamento
from archivio import models as archivio
from archivio.models import CollegamentoFile, Evento, Fascicolo, FileCaricato
from archivio.tests import ConUtenti, diritti, un_file
from elaborazione import coda, lettura_modello, models, regole, riconoscimento
from elaborazione.models import Documento, Elaborazione, EntitaEstratta, ParteDelDocumento, TestoPagina, VoceCatalogo
from soggetti import servizi as anagrafica
from soggetti.models import IdentificativoSoggetto, Soggetto

VERBALE = """VERBALE DI SOPRALLUOGO n. 12 del 3 marzo 2025
Presso la sede della Alfa S.r.l., C.O.E. SM 12345, P.IVA IT 01234567890,
è stato accertato un importo non dichiarato di € 12.500,00.
Contatti: amministrazione@alfa.example. Controparte: COE 54321."""

NON_PERTINENTE = """Verbale della riunione condominiale del 3 marzo 2025.
Spese per la manutenzione dell'ascensore: € 1.200,00. Scrivere a condominio@palazzo.example."""


def risposta_del_modello(testo, fine="stop"):
    """Una risposta nella forma della libreria openai."""
    messaggio = types.SimpleNamespace(content=testo)
    return types.SimpleNamespace(choices=[types.SimpleNamespace(message=messaggio, finish_reason=fine)])


def entita_json(*entita):
    campi = ("etichetta", "valore", "citazione", "evento", "periodo")
    return risposta_del_modello(json.dumps({"entita": [dict(zip(campi, e)) for e in entita]}))


DDT = """DOCUMENTO DI TRASPORTO n. 45/2026 del 12/11/2026
Mittente: Alfa S.r.l., C.O.E. SM 10000
Destinatario: Notizie & Media Italia S.r.l., P.IVA IT 01234567890
Vettore: Trasporti Beta S.r.l., COE 54321
Totale: € 1.234,56"""

DDT_DAL_MODELLO = {
    "tipo": "ddt", "numero": "45/2026", "data": "12/11/2026", "totale": "€ 1.234,56",
    "parti": [
        # il modello scambia mittente e destinatario: è l'errore che la revisione deve poter correggere
        {"ruolo": "destinatario", "denominazione": "Alfa S.r.l.", "identificativo": "C.O.E. SM 10000"},
        {"ruolo": "mittente", "denominazione": "Notizie & Media Italia S.r.l.", "identificativo": "IT 01234567890"},
        {"ruolo": "corriere", "denominazione": "Trasporti Beta S.r.l.", "identificativo": "54321"},
        {"ruolo": "banca d'appoggio", "denominazione": "Banca Gamma", "identificativo": "COE 77777"},
    ],
}


class ModelloFinto:
    """Al posto del server del modello: restituisce le risposte preparate, nell'ordine, e ricorda le richieste."""

    def __init__(self, risposte, documento=None):
        self.risposte, self.richieste = list(risposte), []
        # Le richieste del documento commerciale si tengono a parte e hanno una risposta
        # fissa (nessun documento, se non ne è stato preparato uno): così le prove sulle
        # entità non devono contarle.
        self.documento, self.richieste_documento = documento, []
        self.chat = types.SimpleNamespace(completions=self)

    def create(self, **richiesta):
        contenuto = richiesta["messages"][0]["content"]
        if isinstance(contenuto, str) and "documento commerciale" in contenuto:
            self.richieste_documento.append(richiesta)
            if isinstance(self.documento, Exception):
                raise self.documento
            if hasattr(self.documento, "choices"):
                return self.documento
            return risposta_del_modello(json.dumps({"documento": self.documento}))
        self.richieste.append(richiesta)
        risposta = self.risposte.pop(0)
        if isinstance(risposta, Exception):
            raise risposta
        return risposta


class LettoreFinto:
    """Un lettore che restituisce ciò che gli si dice: per provare la coda senza modello."""

    nome = "finto"
    nature = (riconoscimento.TESTO,)

    def __init__(self, entita=None, errore=None):
        self.entita, self.errore = entita, errore

    def disponibile(self):
        return True, ""

    def leggi(self, percorso, natura, voci):
        if self.errore:
            raise self.errore
        with open(percorso, "rb") as contenuto:
            testo = contenuto.read().decode()
        proposte = self.entita(testo) if callable(self.entita) else (self.entita or [])
        campi = ("etichetta", "valore", "evento", "periodo")
        entita = [dict(zip(campi, e + ("",) * (4 - len(e))), pagina=1, fonte=models.DA_MODELLO) for e in proposte]
        entita += [dict(e, pagina=1, fonte=models.DA_REGOLA) for e in regole.estrai(testo)]
        return coda.Lettura([(1, testo, models.TESTO_DIRETTO)], entita, "modello-finto", "0")


class ConFile(ConUtenti):
    """Deposito temporaneo, catalogo caricato e un attrezzo per portare un file fino alla coda."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        call_command("carica_catalogo", stdout=StringIO())
        for utente in (cls.anna, cls.bruno, cls.lettore):
            diritti(utente, "elaborazione.view_entitaestratta")
        diritti(cls.anna, "elaborazione.change_entitaestratta")
        diritti(cls.carla, "elaborazione.change_vocecatalogo")

    def setUp(self):
        cartella = tempfile.TemporaryDirectory()
        self.addCleanup(cartella.cleanup)
        impostazioni = override_settings(ARCHIVIO_DEPOSITO=cartella.name)
        impostazioni.enable()
        self.addCleanup(impostazioni.disable)

    def carica(self, contenuto, nome="verbale.txt", coe=None, indagine=None, conferma=True, titolo="Caricamento"):
        """Un caricamento con un file, eventualmente con un COE dichiarato, già confermato."""
        fascicolo = caricamento.nuovo(self.anna, titolo, indagine)
        dati = contenuto if isinstance(contenuto, bytes) else contenuto.encode()
        caricamento.aggiungi_file(fascicolo, self.anna, [un_file(nome, dati)])
        if coe:
            caricamento.dichiara_soggetto(fascicolo, self.anna, self.coe, coe)
        if conferma:
            caricamento.conferma(fascicolo, self.anna)
        return FileCaricato.objects.get(fascicolo=fascicolo)

    def stato(self, file):
        return FileCaricato.objects.get(pk=file.pk).stato

    def entita(self, file, etichetta):
        return EntitaEstratta.objects.get(file=file, etichetta=etichetta)


class CodaTest(ConFile):
    """La coda, i file di testo e le regole: tutto ciò che non ha bisogno del modello."""

    def test_un_verbale_di_testo_diventa_testo_entita_e_collegamenti(self):
        file = self.carica(VERBALE, coe="12345")
        resoconto = coda.esegui(lettori=[coda.LettoreTesto()])
        self.assertEqual((resoconto[coda.ELABORATO], resoconto["in attesa"]), (1, 0))
        self.assertEqual(self.stato(file), archivio.FILE_ELABORATO)

        elaborazione = Elaborazione.objects.get()
        self.assertEqual((elaborazione.esito, elaborazione.natura, elaborazione.motore, elaborazione.pagine),
                         (models.ESITO_OK, riconoscimento.TESTO, "testo-2", 1))
        self.assertEqual(TestoPagina.objects.get().testo, VERBALE)

        # ogni entità porta il file, la pagina e la citazione da cui viene
        tutte = EntitaEstratta.objects.filter(file=file)
        self.assertTrue(all(e.pagina == 1 and e.citazione and e.verificata for e in tutte))
        # significative: gli identificativi, che il catalogo conosce
        principale = anagrafica.trova(self.coe, "12345")
        significative = {(e.voce.codice, e.valore_normalizzato): e for e in tutte if e.significativa}
        self.assertEqual(set(significative), {("COE", "12345"), ("COE", "54321"), ("PARTITA_IVA", "01234567890")})
        self.assertEqual(significative["COE", "12345"].soggetto, principale)
        self.assertEqual(significative["COE", "54321"].soggetto, anagrafica.trova(self.coe, "54321"))
        # fuori catalogo: raccolte lo stesso, distinte dal fatto di non avere una voce
        fuori = {e.etichetta for e in tutte if not e.significativa}
        self.assertEqual(fuori, {regole.DATA, regole.IMPORTO, regole.EMAIL})
        self.assertEqual(set(EntitaEstratta.objects.fuori_catalogo().values_list("etichetta", flat=True)), fuori)
        self.assertEqual(self.entita(file, regole.IMPORTO).soggetto, principale)
        self.assertEqual(EntitaEstratta.objects.utilizzabili().count(), 3)

        # il file resta nel suo caricamento ed è collegato alle aziende che riguarda
        collegati = dict(CollegamentoFile.objects.values_list("fascicolo__soggetto", "origine"))
        self.assertEqual(collegati[principale.pk], "dichiarato")
        self.assertEqual(collegati[anagrafica.trova(self.coe, "54321").pk], "estratto")
        self.assertEqual(len(collegati), 3)
        self.assertEqual(FileCaricato.objects.get().fascicolo.faldone.codice, archivio.CARICAMENTI)

    def test_un_file_non_pertinente_si_carica_ma_non_produce_dati_utilizzabili(self):
        file = self.carica(NON_PERTINENTE)
        coda.esegui(lettori=[coda.LettoreTesto()])
        self.assertEqual(self.stato(file), archivio.FILE_ELABORATO)
        raccolte = EntitaEstratta.objects.filter(file=file)
        self.assertEqual({e.etichetta for e in raccolte}, {regole.DATA, regole.IMPORTO, regole.EMAIL})
        self.assertTrue(all(e.soggetto is None and not e.significativa for e in raccolte))
        # nulla che possa entrare nel calcolo, nessuna azienda creata, nessun collegamento
        self.assertEqual(EntitaEstratta.objects.utilizzabili().count(), 0)
        self.assertFalse(Fascicolo.objects.filter(faldone__codice=archivio.AZIENDE).exists())
        self.assertFalse(CollegamentoFile.objects.exists())

    def test_la_coda_segue_priorita_e_limite_e_lascia_il_resto_in_attesa(self):
        primo = self.carica("primo", titolo="A")
        secondo = self.carica("secondo", titolo="B")
        urgente = self.carica("urgente", titolo="C")
        FileCaricato.objects.filter(pk=urgente.pk).update(priorita=5)
        bozza = self.carica("bozza", conferma=False, titolo="D")
        annullato = self.carica("annullato", titolo="E")
        caricamento.annulla(annullato.fascicolo, self.anna)

        resoconto = coda.esegui(massimo=1, lettori=[coda.LettoreTesto()])
        self.assertEqual((resoconto[coda.ELABORATO], resoconto["in attesa"]), (1, 2))
        self.assertEqual(self.stato(urgente), archivio.FILE_ELABORATO)
        resoconto = coda.esegui(massimo=1, lettori=[coda.LettoreTesto()])
        self.assertEqual(self.stato(primo), archivio.FILE_ELABORATO)  # il più vecchio dei rimasti
        self.assertEqual(self.stato(secondo), archivio.FILE_RICEVUTO)
        coda.esegui(lettori=[coda.LettoreTesto()])
        self.assertEqual(self.stato(secondo), archivio.FILE_ELABORATO)
        # bozze e caricamenti annullati non si toccano; un file elaborato non si riprende
        self.assertEqual((self.stato(bozza), self.stato(annullato)), (archivio.FILE_BOZZA, archivio.FILE_ANNULLATO))
        self.assertEqual(Elaborazione.objects.count(), 3)
        self.assertEqual(coda.esegui(lettori=[coda.LettoreTesto()])[coda.ELABORATO], 0)
        self.assertEqual(Elaborazione.objects.count(), 3)

    def test_gli_errori_si_ritentano_fino_al_massimo(self):
        file = self.carica("testo")
        rotto = [LettoreFinto(errore=lettura_modello.LetturaFallita("Risposta tagliata"))]
        for tentativo in (1, 2, 3):
            self.assertEqual(coda.esegui(lettori=rotto)[coda.ERRORE], 1)
            riga = FileCaricato.objects.get(pk=file.pk)
            self.assertEqual((riga.stato, riga.tentativi, riga.ultimo_errore), (archivio.FILE_ERRORE, tentativo, "Risposta tagliata"))
        self.assertEqual(coda.esegui(lettori=rotto)[coda.ERRORE], 0)  # esauriti: non si riprende più
        self.assertEqual(Elaborazione.objects.filter(esito=models.ESITO_ERRORE).count(), 3)
        self.assertEqual(EntitaEstratta.objects.count(), 0)
        # un errore imprevisto del lettore non ferma la coda
        altro = self.carica("altro", titolo="Secondo")
        self.assertEqual(coda.esegui(lettori=[LettoreFinto(errore=RuntimeError("guasto"))])[coda.ERRORE], 1)
        self.assertIn("guasto", FileCaricato.objects.get(pk=altro.pk).ultimo_errore)

    def test_un_tipo_non_gestito_e_un_lettore_non_disponibile(self):
        binario = self.carica(bytes(range(256)) * 4, nome="dati.bin", titolo="Binario")
        scansione = self.carica(b"%PDF-1.4 scansione finta", nome="scansione.pdf", titolo="Scansione")
        testo = self.carica("solo testo", titolo="Testo")
        with override_settings(ELABORAZIONE_MODELLO_URL=""):
            resoconto = coda.esegui(lettori=[coda.LettoreTesto(), coda.LettoreModello()])
        # il binario è un errore definitivo; la scansione aspetta il modello; il testo (sole regole) va avanti
        riga = FileCaricato.objects.get(pk=binario.pk)
        self.assertEqual((riga.stato, riga.tentativi), (archivio.FILE_ERRORE, coda.massimo_tentativi()))
        self.assertIn("non gestito", riga.ultimo_errore)
        self.assertEqual(self.stato(scansione), archivio.FILE_RICEVUTO)
        self.assertEqual(self.stato(testo), archivio.FILE_ELABORATO)
        self.assertEqual((resoconto[coda.SALTATO], resoconto["in attesa"]), (1, 1))
        self.assertIn("non configurato", next(iter(resoconto["motivi"])))
        self.assertFalse(Elaborazione.objects.filter(file=scansione).exists())

    def test_un_file_saltato_non_consuma_il_massimo(self):
        scansione = self.carica(b"%PDF-1.4 scansione finta", nome="scansione.pdf", titolo="Scansione")
        testo = self.carica("solo testo", titolo="Testo")
        with override_settings(ELABORAZIONE_MODELLO_URL=""):
            resoconto = coda.esegui(massimo=1, lettori=[coda.LettoreTesto(), coda.LettoreModello()])
        # la scansione, più vecchia, viene saltata; il posto resta per il file di testo
        self.assertEqual((resoconto[coda.SALTATO], resoconto[coda.ELABORATO]), (1, 1))
        self.assertEqual((self.stato(scansione), self.stato(testo)), (archivio.FILE_RICEVUTO, archivio.FILE_ELABORATO))

    @override_settings(ELABORAZIONE_MODELLO_NOME="modello-di-prova")
    def test_un_file_di_testo_passa_anche_dal_modello(self):
        testo = "Verbale di sopralluogo presso la Alfa S.r.l., COE 12345.\nAmministratore: Mario Rossi."
        modello = ModelloFinto([entita_json(
            ("AMMINISTRATORE", "Mario Rossi", "Amministratore: Mario Rossi.", "sopralluogo", ""),
            ("COE", "99999", "", "", ""),  # gli identificativi li leggono le regole, non il modello
        )])
        file = self.carica(testo)
        resoconto = coda.esegui(lettori=[coda.LettoreTesto(coda.LettoreModello(cliente=modello))])
        self.assertEqual(resoconto[coda.ELABORATO], 1)
        self.assertEqual(self.stato(file), archivio.FILE_ELABORATO)
        elaborazione = Elaborazione.objects.get()
        self.assertEqual(
            (elaborazione.motore, elaborazione.modello, elaborazione.versione_prompt, elaborazione.esito),
            ("testo-2", "modello-di-prova", lettura_modello.VERSIONE_PROMPT, models.ESITO_OK),
        )
        # al modello arriva il testo del file, senza passare da immagini
        self.assertEqual(len(modello.richieste), 1)
        self.assertIn(f"<documento>\n{testo}\n</documento>", modello.richieste[0]["messages"][0]["content"])
        amministratore = self.entita(file, "AMMINISTRATORE")
        self.assertEqual(
            (amministratore.fonte, amministratore.verificata, amministratore.evento, amministratore.soggetto),
            (models.DA_MODELLO, True, "sopralluogo", anagrafica.trova(self.coe, "12345")),
        )
        self.assertEqual(self.entita(file, regole.COE).fonte, models.DA_REGOLA)
        self.assertFalse(EntitaEstratta.objects.filter(valore="99999").exists())
        # il testo non viene da una scansione: nessuna revisione obbligata
        self.assertFalse(EntitaEstratta.objects.filter(da_rivedere=True).exists())

    @override_settings(ELABORAZIONE_MODELLO_NOME="modello-di-prova")
    def test_senza_modello_si_applicano_le_regole_e_il_file_resta_da_elaborare(self):
        file = self.carica(VERBALE + "\nAmministratore: Mario Rossi.", coe="12345")
        with override_settings(ELABORAZIONE_MODELLO_URL=""):
            resoconto = coda.esegui(lettori=coda.lettori_predefiniti())
            # le regole hanno lavorato, ma il file non è dichiarato elaborato
            self.assertEqual((resoconto[coda.PARZIALE], resoconto[coda.ELABORATO], resoconto["in attesa"]), (1, 0, 1))
            self.assertEqual(self.stato(file), archivio.FILE_RICEVUTO)
            self.assertEqual(Elaborazione.objects.get().esito, models.ESITO_PARZIALE)
            dalle_regole = EntitaEstratta.objects.filter(file=file).count()
            self.assertEqual(dalle_regole, 6)
            self.assertTrue(CollegamentoFile.objects.filter(file=file).exists())
            # finché il modello manca non si rifà lo stesso lavoro ogni notte
            resoconto = coda.esegui(lettori=coda.lettori_predefiniti())
            self.assertEqual((resoconto[coda.SALTATO], resoconto[coda.PARZIALE]), (1, 0))
            self.assertIn("in attesa del modello", next(iter(resoconto["motivi"])))
            self.assertEqual((Elaborazione.objects.count(), EntitaEstratta.objects.count()), (1, dalle_regole))

        # il modello torna: il file viene completato, senza ripetere ciò che le regole avevano già raccolto
        modello = ModelloFinto([entita_json(("AMMINISTRATORE", "Mario Rossi", "Amministratore: Mario Rossi.", "sopralluogo", ""))])
        resoconto = coda.esegui(lettori=[coda.LettoreTesto(coda.LettoreModello(cliente=modello))])
        self.assertEqual(resoconto[coda.ELABORATO], 1)
        self.assertEqual(self.stato(file), archivio.FILE_ELABORATO)
        self.assertEqual(EntitaEstratta.objects.filter(file=file).count(), dalle_regole + 1)
        self.assertEqual(self.entita(file, "AMMINISTRATORE").fonte, models.DA_MODELLO)
        self.assertEqual(
            list(Elaborazione.objects.order_by("pk").values_list("esito", flat=True)),
            [models.ESITO_PARZIALE, models.ESITO_OK],
        )
        # ora è definitivo: non si riprende più
        self.assertEqual(coda.esegui(lettori=[coda.LettoreTesto(coda.LettoreModello(cliente=ModelloFinto([])))])[coda.ELABORATO], 0)

    def test_un_file_interrotto_a_meta_viene_ripreso(self):
        file = self.carica("testo")
        FileCaricato.objects.filter(pk=file.pk).update(stato=archivio.FILE_IN_ELABORAZIONE)
        resoconto = coda.esegui(lettori=[coda.LettoreTesto()])
        self.assertEqual((resoconto["sbloccati"], resoconto[coda.ELABORATO]), (1, 1))

    def test_soggetto_dichiarato_ma_il_file_ne_nomina_un_altro(self):
        file = self.carica("Fattura alla Beta S.p.A., COE 54321, del 10/01/2025.", coe="12345")
        coda.esegui(lettori=[coda.LettoreTesto()])
        self.assertEqual(self.stato(file), archivio.FILE_DA_RIVEDERE)
        data = self.entita(file, regole.DATA)
        self.assertTrue(data.da_rivedere)
        self.assertIn("società dichiarate", data.motivo_revisione)
        # l'identificativo trovato è un fatto: resta attribuito al suo soggetto, senza revisione
        self.assertFalse(self.entita(file, regole.COE).da_rivedere)

    def test_due_fonti_con_valori_diversi_vanno_riviste_salvo_le_voci_che_cambiano(self):
        primo = self.carica("Ricavi 2024: 100.000. Amministratore Mario Rossi.", coe="12345", titolo="Primo")
        coda.esegui(lettori=[LettoreFinto([("RICAVI", "100.000", "bilancio", "2024"), ("AMMINISTRATORE", "Mario Rossi")])])
        self.assertEqual(self.stato(primo), archivio.FILE_ELABORATO)
        self.assertEqual(EntitaEstratta.objects.utilizzabili().count(), 2)

        secondo = self.carica("Ricavi 2024: 250.000. Ricavi 2023: 90.000. Amministratore Anna Bianchi.", coe="12345", titolo="Secondo")
        coda.esegui(lettori=[LettoreFinto([
            ("RICAVI", "250.000", "bilancio", "2024"), ("RICAVI", "90.000", "bilancio", "2023"),
            ("AMMINISTRATORE", "Anna Bianchi"),
        ])])
        # stesso soggetto, stessa voce, stesso anno, valori diversi: entrambi da rivedere, anche il file già elaborato
        ricavi_2024 = EntitaEstratta.objects.filter(voce__codice="RICAVI", periodo="2024")
        self.assertEqual([e.da_rivedere for e in ricavi_2024], [True, True])
        self.assertEqual((self.stato(primo), self.stato(secondo)), (archivio.FILE_DA_RIVEDERE, archivio.FILE_DA_RIVEDERE))
        # un altro anno non è un conflitto; l'amministratore cambia nel tempo: nessun conflitto, il più recente per primo
        self.assertFalse(EntitaEstratta.objects.get(voce__codice="RICAVI", periodo="2023").da_rivedere)
        soggetto = anagrafica.trova(self.coe, "12345")
        scheda = {riga["voce"].codice: riga for riga in coda.scheda_del_soggetto(soggetto, self.anna)}
        self.assertEqual([e.valore for e in scheda["AMMINISTRATORE"]["valori"]], ["Anna Bianchi", "Mario Rossi"])
        self.assertEqual([e.periodo for e in scheda["RICAVI"]["valori"]], ["2023"])  # il 2024 aspetta la revisione
        self.assertTrue(scheda["UTILE"]["mancante"])  # non ancora arrivato: mancante, non zero

        # il revisore scarta il valore sbagliato e conferma l'altro: i file tornano elaborati
        sbagliato = ricavi_2024.get(file=primo)
        self.pagina(self.anna, "file", primo.pk, azione="scarta", entita=sbagliato.pk)
        self.pagina(self.anna, "file", secondo.pk, azione="conferma_tutte")
        self.assertEqual((self.stato(primo), self.stato(secondo)), (archivio.FILE_ELABORATO, archivio.FILE_ELABORATO))
        scheda = {riga["voce"].codice: riga for riga in coda.scheda_del_soggetto(soggetto, self.anna)}
        self.assertEqual({e.valore for e in scheda["RICAVI"]["valori"]}, {"250.000", "90.000"})

    def pagina(self, chi, nome, /, *argomenti, **dati):
        """Come l'attrezzo dell'archivio, ma per le pagine dell'elaborazione."""
        self.client.force_login(chi)
        indirizzo = reverse(f"elaborazione:{nome}", args=argomenti)
        return self.client.post(indirizzo, dati) if dati else self.client.get(indirizzo)

    def test_un_valore_che_non_compare_nel_testo_non_e_utilizzabile(self):
        file = self.carica("Amministratore Mario Rossi.", coe="12345")
        coda.esegui(lettori=[LettoreFinto([("AMMINISTRATORE", "Mario Rossi"), ("SOCIO", "Luigi Verdi")])])
        self.assertTrue(self.entita(file, "AMMINISTRATORE").verificata)
        inventato = self.entita(file, "SOCIO")
        self.assertFalse(inventato.verificata)
        self.assertEqual([e.etichetta for e in EntitaEstratta.objects.utilizzabili()], ["AMMINISTRATORE"])
        self.assertContains(self.pagina(self.anna, "file", file.pk), "non trovata nel testo")

    def test_annullare_il_caricamento_ritira_le_entita(self):
        file = self.carica(VERBALE, coe="12345")
        coda.esegui(lettori=[coda.LettoreTesto()])
        self.assertTrue(EntitaEstratta.objects.utilizzabili().exists())
        caricamento.annulla(file.fascicolo, self.anna)
        self.assertFalse(EntitaEstratta.objects.utilizzabili().exists())
        self.assertFalse(EntitaEstratta.objects.filter(ritirata=False).exists())
        self.assertFalse(CollegamentoFile.objects.exists())
        self.assertGreater(EntitaEstratta.objects.count(), 0)  # restano, come traccia

    def test_un_etichetta_fuori_catalogo_si_promuove_senza_rileggere_il_file(self):
        file = self.carica("Capitale sociale 26.000 euro.", coe="12345")
        coda.esegui(lettori=[LettoreFinto([("capitale sociale", "26.000")])])
        raccolta = self.entita(file, "capitale sociale")
        self.assertFalse(raccolta.significativa)
        self.assertEqual(EntitaEstratta.objects.utilizzabili().filter(file=file, fonte=models.DA_MODELLO).count(), 0)

        voce = VoceCatalogo.objects.create(codice="CAPITALE", descrizione="Capitale sociale versato", tipo_valore="importo")
        self.assertContains(self.pagina(self.carla, "fuori_catalogo"), "capitale sociale")
        self.assertEqual(self.pagina(self.anna, "fuori_catalogo").status_code, 403)  # solo chi gestisce il catalogo
        self.pagina(self.carla, "fuori_catalogo", etichetta="Capitale  Sociale", voce=voce.pk)
        raccolta.refresh_from_db()
        self.assertEqual(raccolta.voce, voce)
        self.assertEqual(Elaborazione.objects.count(), 1)  # nessuna rilettura
        self.assertIn("Capitale Sociale", VoceCatalogo.objects.get(pk=voce.pk).sinonimi)
        # d'ora in poi il modello che usa quell'etichetta viene riconosciuto subito
        altro = self.carica("Capitale sociale 50.000 euro.", coe="54321", titolo="Altro")
        coda.esegui(lettori=[LettoreFinto([("capitale sociale", "50.000")])])
        self.assertEqual(self.entita(altro, "capitale sociale").voce, voce)

    def test_testo_ed_entita_seguono_la_visibilita_del_file(self):
        indagine = self.apri_indagine()
        riservato = self.carica("Amministratore Mario Rossi. COE 12345.", indagine=indagine, titolo="Riservato")
        generale = self.carica("Socio Luigi Verdi. COE 12345.", titolo="Generale")
        coda.esegui(lettori=[LettoreFinto(
            lambda testo: [("AMMINISTRATORE", "Mario Rossi")] if "Mario" in testo else [("SOCIO", "Luigi Verdi")]
        )])
        soggetto = anagrafica.trova(self.coe, "12345")
        azienda = Fascicolo.objects.get(faldone__codice=archivio.AZIENDE, soggetto=soggetto)

        def voci_note(utente):
            return {r["voce"].codice for r in coda.scheda_del_soggetto(soggetto, utente) if not r["mancante"]}

        # Anna è nell'indagine e vede tutto; Bruno vede solo ciò che viene dal caricamento generale
        self.assertEqual(voci_note(self.anna), {"COE", "AMMINISTRATORE", "SOCIO"})
        self.assertEqual(voci_note(self.bruno), {"COE", "SOCIO"})
        self.assertEqual(self.pagina(self.bruno, "file", riservato.pk).status_code, 404)
        self.assertEqual(self.pagina(self.bruno, "file", generale.pk).status_code, 200)
        scheda = self.pagina(self.bruno, "soggetto", azienda.pk)
        self.assertContains(scheda, "Luigi Verdi")
        self.assertNotContains(scheda, "Mario Rossi")
        # anche l'elenco dei file nel fascicolo dell'azienda rispetta la visibilità
        self.client.force_login(self.bruno)
        fascicolo = self.client.get(reverse("archivio:fascicolo", args=[azienda.pk]))
        self.assertEqual([c.file for c in fascicolo.context["file_collegati"]], [generale])
        self.client.force_login(self.anna)
        fascicolo = self.client.get(reverse("archivio:fascicolo", args=[azienda.pk]))
        self.assertEqual({c.file for c in fascicolo.context["file_collegati"]}, {generale, riservato})
        # un documento di un caricamento riservato non entra nella fotografia dei dati del grafo
        from grafo import dati_reali
        for file, numero in ((riservato, "1"), (generale, "2")):
            documento = Documento.objects.create(
                elaborazione=file.elaborazioni.first(), file=file, tipo="FATTURA", numero=numero,
                data=datetime.date(2026, 1, 10), totale=decimal.Decimal("100"), confermato=True,
            )
            for ruolo, coe in ((models.MITTENTE, "12345"), (models.DESTINATARIO, "54321")):
                altro, _ = anagrafica.trova_o_crea(self.coe, coe)
                ParteDelDocumento.objects.create(documento=documento, ruolo=ruolo, soggetto=altro)
        archi, esclusi = dati_reali.archi_dall_archivio()
        self.assertEqual(([d.numero for _, _, d in archi], esclusi), (["2"], {}))
        # e così ciò che la chat può raccontare dell'azienda
        self.assertIn("Mario Rossi", coda.descrivi_azienda("12345", self.anna))
        self.assertNotIn("Mario Rossi", coda.descrivi_azienda("12345", self.bruno))
        self.assertIn("Luigi Verdi", coda.descrivi_azienda("12345", self.bruno))
        # chi non può rivedere non modifica nulla
        entita = self.entita(generale, "SOCIO")
        self.pagina(self.bruno, "file", generale.pk, azione="conserva")
        self.assertFalse(EntitaEstratta.objects.get(pk=entita.pk).ritirata)


class CancellazioneTest(ConFile):
    """Cancellazione definitiva di un file e di ciò che ne deriva, con diritto apposito."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        from django.contrib.auth import get_user_model

        cls.dora = get_user_model().objects.create_user("dora", password="x")
        diritti(cls.dora, "archivio.view_fascicolo", "archivio.cancella_definitivamente", "elaborazione.view_entitaestratta")

    def pagina(self, chi, /, numero, **dati):
        self.client.force_login(chi)
        indirizzo = reverse("archivio:cancella_file", args=[numero])
        return self.client.post(indirizzo, dati) if dati else self.client.get(indirizzo)

    def nel_deposito(self):
        return [p for p in caricamento.cartella_deposito().rglob("*") if p.is_file()]

    def due_file(self):
        """Il primo nomina due aziende; la 12345 compare anche nel secondo, la 54321 solo nel primo."""
        primo = self.carica("Fattura della Alfa, COE 12345, alla Beta, COE 54321, del 10/01/2025.", titolo="Primo")
        secondo = self.carica("Sollecito alla Alfa, COE 12345, del 20/02/2025.", titolo="Secondo")
        coda.esegui(lettori=[coda.LettoreTesto()])
        return primo, secondo

    def test_la_cancellazione_toglie_il_file_i_suoi_dati_e_i_soggetti_rimasti_soli(self):
        primo, secondo = self.due_file()
        solo_del_primo = anagrafica.trova(self.coe, "54321")
        comune = anagrafica.trova(self.coe, "12345")
        prima = (EntitaEstratta.objects.count(), Soggetto.objects.count(), Fascicolo.objects.count())

        # l'anteprima dice esattamente che cosa sparirà, e non cancella nulla
        anteprima = dict(cancellazione.anteprima(primo, anche_soggetti=True)["righe"])
        self.assertEqual(anteprima["file"], 1)
        self.assertEqual(anteprima["elaborazioni"], 1)
        self.assertEqual(anteprima["pagine di testo"], 1)
        self.assertEqual(anteprima["entità estratte"], 3)  # due COE e una data
        self.assertEqual(anteprima["collegamenti ai fascicoli delle società"], 2)
        self.assertEqual(anteprima["società che esistevano solo per questo file"], 1)
        self.assertEqual(anteprima["fascicoli di società rimasti vuoti"], 1)
        self.assertEqual((EntitaEstratta.objects.count(), Soggetto.objects.count(), Fascicolo.objects.count()), prima)
        self.assertEqual(len(self.nel_deposito()), 2)
        pagina = self.pagina(self.dora, primo.pk)
        self.assertContains(pagina, "entità estratte")
        self.assertEqual(FileCaricato.objects.count(), 2)

        # senza motivo non si cancella
        senza_motivo = self.pagina(self.dora, primo.pk, azione="cancella", anche_soggetti="si", motivazione="boh")
        self.assertContains(senza_motivo, "Scrivere il motivo")
        self.assertEqual(FileCaricato.objects.count(), 2)

        fatto = self.pagina(
            self.dora, primo.pk, azione="cancella", anche_soggetti="si",
            motivazione="File caricato per errore: appartiene a un'altra pratica.",
        )
        self.assertContains(fatto, "sono stati cancellati")
        # il file e tutto ciò che ne derivava non ci sono più
        self.assertFalse(FileCaricato.objects.filter(pk=primo.pk).exists())
        self.assertFalse(Elaborazione.objects.filter(file_id=primo.pk).exists())
        self.assertFalse(EntitaEstratta.objects.filter(file_id=primo.pk).exists())
        self.assertFalse(CollegamentoFile.objects.filter(file_id=primo.pk).exists())
        self.assertEqual(TestoPagina.objects.count(), 1)
        self.assertEqual(len(self.nel_deposito()), 1)
        # la Beta esisteva solo per quel file: sparisce con il suo fascicolo e il suo identificativo
        self.assertFalse(Soggetto.objects.filter(pk=solo_del_primo.pk).exists())
        self.assertFalse(Fascicolo.objects.filter(soggetto_id=solo_del_primo.pk).exists())
        self.assertFalse(IdentificativoSoggetto.objects.filter(valore_normalizzato="54321").exists())
        # la Alfa è nominata anche dal secondo file: resta, con il suo fascicolo e i dati dell'altro file
        self.assertTrue(Soggetto.objects.filter(pk=comune.pk).exists())
        self.assertEqual(self.stato(secondo), archivio.FILE_ELABORATO)
        self.assertEqual(EntitaEstratta.objects.filter(file=secondo).count(), 2)
        self.assertEqual(CollegamentoFile.objects.filter(file=secondo).count(), 1)

        # resta la traccia: chi, il motivo, numero e impronta; non il nome del file
        traccia = Evento.objects.get(azione="file cancellato")
        self.assertEqual((traccia.utente, traccia.fascicolo_id), (self.dora, primo.fascicolo_id))
        self.assertIn("altra pratica", traccia.dettaglio)
        self.assertIn(primo.impronta[:16], traccia.dettaglio)
        self.assertNotIn(primo.percorso_originale, traccia.dettaglio)
        self.assertIn("3 entità estratte", Evento.objects.get(azione="dati cancellati").dettaglio)

    def test_serve_il_diritto_apposito_e_poter_vedere_il_file(self):
        primo, _ = self.due_file()
        # l'analista carica, rivede e annulla, ma non cancella definitivamente
        self.assertEqual(self.pagina(self.anna, primo.pk).status_code, 403)
        self.assertEqual(self.pagina(self.capo, primo.pk).status_code, 200)  # il superutente ha ogni diritto...
        with self.assertRaises(cancellazione.NonAmmessa):
            cancellazione.cancella(primo, self.anna, "Motivo scritto per esteso.")
        self.client.force_login(self.anna)
        self.assertNotContains(self.client.get(reverse("archivio:file", args=[primo.pk])), "Cancella definitivamente")
        self.client.force_login(self.dora)
        self.assertContains(self.client.get(reverse("archivio:file", args=[primo.pk])), "Cancella definitivamente")

        # ...ma nemmeno chi può cancellare vede i file di un'indagine a cui non è assegnato
        riservato = self.carica("Documento riservato, COE 77777.", indagine=self.apri_indagine(), titolo="Riservato")
        for utente in (self.dora, self.capo):
            self.assertEqual(self.pagina(utente, riservato.pk).status_code, 404, utente.username)
            with self.assertRaises(cancellazione.NonAmmessa):
                cancellazione.cancella(riservato, utente, "Motivo scritto per esteso.")
        self.assertTrue(FileCaricato.objects.filter(pk=riservato.pk).exists())
        # un file in lavorazione non si cancella
        FileCaricato.objects.filter(pk=primo.pk).update(stato=archivio.FILE_IN_ELABORAZIONE)
        with self.assertRaises(cancellazione.NonAmmessa):
            cancellazione.cancella(FileCaricato.objects.get(pk=primo.pk), self.dora, "Motivo scritto per esteso.")

    def test_soggetti_e_contenuti_ancora_usati_restano(self):
        testo = "Fattura della Alfa, COE 12345, alla Beta, COE 54321."
        primo = self.carica(testo, titolo="Primo")
        copia = self.carica(testo, nome="copia.txt", titolo="Copia")  # stesso contenuto in un altro caricamento
        coda.esegui(lettori=[coda.LettoreTesto()])
        self.assertEqual(len(self.nel_deposito()), 1)
        self.assertTrue(cancellazione.anteprima(primo)["contenuto_condiviso"])

        # senza la spunta i soggetti restano comunque
        cancellazione.cancella(primo, self.dora, "Doppione del file già presente.", anche_soggetti=False)
        self.assertEqual(Soggetto.objects.count(), 2)
        # il contenuto è ancora usato dalla copia: resta nel deposito e si scarica
        self.assertEqual(len(self.nel_deposito()), 1)
        self.client.force_login(self.anna)
        self.assertEqual(self.client.get(reverse("archivio:scarica", args=[copia.pk])).status_code, 200)
        # un soggetto dichiarato sul caricamento, o citato in un'indagine, non si tocca nemmeno con la spunta
        indagine = self.apri_indagine()
        from archivio import servizi as servizi_archivio

        servizi_archivio.aggiungi_soggetto(indagine, self.coe, "54321", self.anna)
        caricamento_copia = Fascicolo.objects.get(pk=copia.fascicolo_id)
        cancellazione.cancella(FileCaricato.objects.get(pk=copia.pk), self.dora, "Rimozione completa del doppione.", anche_soggetti=True)
        self.assertTrue(Soggetto.objects.filter(pk=anagrafica.trova(self.coe, "54321").pk).exists())  # è in un'indagine
        self.assertIsNone(anagrafica.trova(self.coe, "12345"))  # nessuno lo citava più
        self.assertEqual(len(self.nel_deposito()), 0)
        self.assertTrue(Fascicolo.objects.filter(pk=caricamento_copia.pk).exists())  # il caricamento resta, vuoto


@override_settings(ELABORAZIONE_MODELLO_NOME="modello-di-prova")
class DocumentoTest(ConFile):
    """Il documento commerciale e le sue parti: ciò che lega fra loro i soggetti di un file."""

    def elabora_il_ddt(self):
        file = self.carica(DDT, nome="ddt.txt")
        modello = ModelloFinto([entita_json()], documento=DDT_DAL_MODELLO)
        coda.esegui(lettori=[coda.LettoreTesto(coda.LettoreModello(cliente=modello))])
        return file

    def parte(self, nome):
        return ParteDelDocumento.objects.get(denominazione__startswith=nome)

    @override_settings(ELABORAZIONE_MODELLO_NOME="modello-di-prova")
    def test_un_ddt_diventa_un_documento_con_le_parti_e_i_ruoli_li_conferma_una_persona(self):
        file = self.elabora_il_ddt()
        documento = Documento.objects.get(file=file)
        self.assertEqual(
            (documento.tipo, documento.numero, documento.data, documento.totale, documento.pagina),
            ("DDT", "45/2026", datetime.date(2026, 11, 12), decimal.Decimal("1234.56"), 1),
        )
        mittente, vettore = anagrafica.trova(self.coe, "10000"), anagrafica.trova(self.coe, "54321")
        self.assertEqual((self.parte("Alfa").soggetto, self.parte("Trasporti").soggetto), (mittente, vettore))
        destinatario = self.parte("Notizie").soggetto
        self.assertNotIn(destinatario, (None, mittente, vettore))
        self.assertEqual(self.parte("Trasporti").ruolo, models.VETTORE)  # "corriere" è un altro nome del vettore
        # un ruolo non previsto resta da assegnare; un identificativo che le regole non hanno letto non crea soggetti
        banca = self.parte("Banca")
        self.assertEqual((banca.ruolo, banca.ruolo_proposto, banca.soggetto), ("", "banca d'appoggio", None))
        # finché nessuno conferma i ruoli il documento non è utilizzabile e il file va rivisto
        self.assertEqual(self.stato(file), archivio.FILE_DA_RIVEDERE)
        self.assertFalse(Documento.objects.utilizzabili().exists())

        # il revisore corregge lo scambio fra mittente e destinatario, toglie la banca e chiude
        self.client.force_login(self.anna)
        indirizzo = reverse("elaborazione:file", args=[file.pk])
        pagina = self.client.get(indirizzo)
        self.assertContains(pagina, "Documento e parti")
        modulo = {
            "azione": "conserva", "entita": list(EntitaEstratta.objects.filter(file=file).values_list("pk", flat=True)),
            "documento_valido": "si", "documento_tipo": "ddt", "documento_numero": "45/2026",
            "documento_data": "2026-11-12", "documento_totale": "1.234,56",
        }
        scelte = {"Alfa": (models.MITTENTE, mittente), "Notizie": (models.DESTINATARIO, destinatario),
                  "Trasporti": (models.VETTORE, vettore), "Banca": ("", None)}
        for nome, (ruolo, soggetto) in scelte.items():
            parte = self.parte(nome)
            modulo[f"ruolo_{parte.pk}"], modulo[f"soggetto_{parte.pk}"] = ruolo, soggetto.pk if soggetto else ""
        # una data illeggibile non salva nulla
        self.client.post(indirizzo, dict(modulo, documento_data="ieri"))
        self.assertFalse(Documento.objects.get().confermato)
        risposta = self.client.post(indirizzo, modulo, follow=True)
        self.assertContains(risposta, "Documento e ruoli confermati")
        self.assertEqual(self.stato(file), archivio.FILE_ELABORATO)
        ruoli = {
            parte.ruolo: parte.soggetto
            for parte in Documento.objects.utilizzabili().get().parti.filter(ritirata=False)
        }
        self.assertEqual(ruoli, {models.MITTENTE: mittente, models.DESTINATARIO: destinatario, models.VETTORE: vettore})
        self.assertTrue(self.parte("Banca").ritirata)

        # il nome confermato diventa la denominazione del soggetto, nella scheda e in anagrafica
        nomi = {e.soggetto: (e.valore, e.fonte) for e in EntitaEstratta.objects.utilizzabili().filter(etichetta="DENOMINAZIONE")}
        self.assertEqual(nomi[mittente], ("Alfa S.r.l.", models.DA_DOCUMENTO))
        self.assertEqual(len(nomi), 3)
        mittente.refresh_from_db()
        self.assertEqual(mittente.denominazione, "Alfa S.r.l.")
        # e la scheda dell'azienda elenca il documento, con il ruolo e le altre parti
        (riga,) = coda.documenti_del_soggetto(mittente, self.anna)
        self.assertEqual((riga["ruolo"], {p.ruolo for p in riga["altre"]}), (models.MITTENTE, {models.DESTINATARIO, models.VETTORE}))
        azienda = Fascicolo.objects.get(faldone__codice=archivio.AZIENDE, soggetto=mittente)
        self.assertIn("Alfa S.r.l.", azienda.titolo)
        scheda = self.client.get(reverse("elaborazione:soggetto", args=[azienda.pk]))
        self.assertContains(scheda, "Trasporti Beta S.r.l.")
        self.assertEqual(coda.documenti_del_soggetto(mittente, self.bruno)[0]["ruolo"], models.MITTENTE)
        # la chat riceve le stesse cose in parole, cercando per identificativo o per nome
        racconto = coda.descrivi_azienda("COE 10000", self.anna)
        for atteso in ("Alfa S.r.l.", "Denominazione", "DDT n. 45/2026 del 2026-11-12", "totale 1234.56",
                       "ruolo della società: mittente", "vettore: Trasporti Beta S.r.l.", "non ancora arrivate"):
            self.assertIn(atteso, racconto)
        self.assertEqual(coda.descrivi_azienda("alfa", self.anna), racconto)
        self.assertIn("Nessuna società nota", coda.descrivi_azienda("99999", self.anna))
        self.assertIn("Più società", coda.descrivi_azienda("s.r.l.", self.anna))
        # lo strumento della chat risponde solo a chi ha una sessione, con la sua visibilità
        from grafo import servizio_mcp
        self.assertIn("solo da una sessione", servizio_mcp.scheda("10000"))
        servizio_mcp._chiamata.sessione = types.SimpleNamespace(utente=self.anna)
        self.addCleanup(setattr, servizio_mcp._chiamata, "sessione", None)
        self.assertEqual(servizio_mcp.scheda(10000), racconto)
        self.assertIn("non ha il diritto", coda.descrivi_azienda("10000", self.carla))
        # la fotografia dei dati reali per l'analisi di rete: due nodi e un arco, agganciati all'anagrafica
        from grafo import dati_reali
        from grafo import models as grafo
        resoconto = dati_reali.fotografa()
        self.assertEqual((resoconto["nuova"], resoconto["soggetti"], resoconto["relazioni"]), (True, 2, 1))
        arco = grafo.Relazione.objects.get(versione_dati=resoconto["versione_dati"])
        self.assertEqual(
            (arco.venditore.riferimento, arco.acquirente.riferimento, arco.documento, arco.data, arco.importo),
            (f"ANAG-{mittente.pk}", f"ANAG-{destinatario.pk}", "DDT 45/2026", datetime.date(2026, 11, 12), decimal.Decimal("1234.56")),
        )
        self.assertEqual(dati_reali.soggetto_dell_anagrafica(arco.venditore.riferimento), mittente.pk)
        nodo = grafo.DatiSoggetto.objects.get(versione_dati=resoconto["versione_dati"], soggetto=arco.venditore)
        self.assertEqual(nodo.nome, "Alfa S.r.l.")
        self.assertIn("10000", nodo.nr_iscrizione)
        # la diagnosi segue il documento fino al grafo e dice a che punto è
        diagnosi = "\n".join(dati_reali.diagnosi(mittente))
        for atteso in ("File che la riguardano: 1", "documento DDT n. 45/2026 del 2026-11-12, totale 1234.56",
                       "-> può entrare nel grafo", "Documenti pronti per il grafo: 1", "1 rapporti della società",
                       "non è utilizzabile"):   # nessun calcolo ancora: chat e mappa non hanno nulla da usare
            self.assertIn(atteso, diagnosi)
        Documento.objects.filter(file=file).update(confermato=False)
        self.assertIn("NON entra: non è ancora confermato", "\n".join(dati_reali.diagnosi(mittente)))
        Documento.objects.filter(file=file).update(confermato=True, totale=None)
        self.assertIn("NON entra: senza importo totale", "\n".join(dati_reali.diagnosi(mittente)))
        Documento.objects.filter(file=file).update(totale=decimal.Decimal("1234.56"))
        # senza novità non nasce una seconda fotografia
        self.assertFalse(dati_reali.fotografa()["nuova"])
        self.assertEqual(grafo.VersioneDati.objects.count(), 1)
        # il rapporto compare anche nello spazio degli indici, e la chat lo può chiedere
        from django.contrib.auth import get_user_model

        from indici import importazione, spazio
        from indici.models import RegolaDiRischio
        RegolaDiRischio.objects.create(
            codice="SENZA_DIPENDENTI", descrizione="Commercio senza dipendenti", tipo="falsa_fatturazione",
            peso="0.60", prefissi_attivita="47", classi_dipendenti="D0",
        )
        importazione.importa(
            "coe;piva;periodo;ateco;dipendenti;fatturato\n10000;;2025;47.26;D0;F3\n;01234567890;2025;63.91;D2;F2\n"
        )
        elenco, _ = spazio.rapporti()
        self.assertEqual(elenco, [{"da": mittente.pk, "a": destinatario.pk, "quanti": 1, "importo": 1234.56}])
        dati = spazio.costruisci(RegolaDiRischio.objects.get())
        self.assertEqual((len(dati["punti"]), dati["rapporti"], dati["fuori"]), (2, elenco, {}))
        diritti(self.anna, "indici.view_regoladirischio")
        anna = get_user_model().objects.get(pk=self.anna.pk)  # riletta: i diritti di un utente già usato restano in memoria
        testo, parametri = spazio.racconta(anna, "senza dipendenti", "COE 10000")
        self.assertEqual(parametri, {"regola": "SENZA_DIPENDENTI", "azienda": mittente.pk})
        for atteso in ("La regola SCATTA", "vende a Notizie & Media Italia S.r.l. (nessuna segnalazione): 1 documenti, importo totale 1234.56"):
            self.assertIn(atteso, testo)
        self.assertIn("compra da Alfa S.r.l. (la regola scatta)", spazio.racconta(anna, "", "01234567890")[0])
        generale, parametri = spazio.racconta(anna)
        self.assertIn("La regola scatta per 1", generale)
        self.assertEqual(parametri, {"regola": "SENZA_DIPENDENTI"})
        self.assertIn("Nessuna regola corrisponde", spazio.racconta(anna, "inesistente")[0])
        self.assertIn("non ha il diritto", spazio.racconta(self.bruno)[0])
        # nella classifica per criteri, chi ha rapporti con un'azienda segnalata compare nel terzo criterio
        from indici import classifica
        (collegata,) = classifica.criteri()["rapporti"]
        self.assertEqual((collegata[0], collegata[1][0][:3], collegata[2]), (destinatario.pk, (mittente.pk, ["regole"], 1), 1234.56))
        self.assertIn("- Notizie & Media Italia S.r.l.", classifica.racconta(anna).split("CRITERIO 3")[1])
        # lo strumento della chat aggiunge il collegamento alla pagina, con regola e azienda già scelte
        servizio_mcp._chiamata.sessione = types.SimpleNamespace(utente=anna)
        servizio_mcp._chiamata.indirizzo_pubblico = "https://controlli.example"
        self.addCleanup(setattr, servizio_mcp._chiamata, "indirizzo_pubblico", "")
        risposta = servizio_mcp.spazio("SENZA_DIPENDENTI", 10000)
        self.assertIn(f"https://controlli.example/indici/spazio/?regola=SENZA_DIPENDENTI&azienda={mittente.pk}", risposta)
        pagina = self.client.get(reverse("indici:spazio"), {"regola": "SENZA_DIPENDENTI", "azienda": mittente.pk})
        self.assertEqual(pagina.context["dati"]["apri"], mittente.pk)
        servizio_mcp._chiamata.sessione = None
        self.assertIn("solo da una sessione", servizio_mcp.spazio())
        servizio_mcp._chiamata.sessione = types.SimpleNamespace(utente=anna)
        # rivedere di nuovo non raddoppia le denominazioni
        self.client.post(indirizzo, dict(modulo, entita=list(EntitaEstratta.objects.filter(file=file).values_list("pk", flat=True))))
        self.assertEqual(EntitaEstratta.objects.filter(etichetta="DENOMINAZIONE").count(), 3)

    @override_settings(ELABORAZIONE_MODELLO_NOME="modello-di-prova")
    def test_documento_e_citazione_non_allungano_la_risposta_sulle_entita(self):
        file = self.carica(DDT + "\nAmministratore: Mario Rossi.", nome="ddt.txt")
        modello = ModelloFinto([entita_json(("AMMINISTRATORE", "Mario Rossi"))], documento=DDT_DAL_MODELLO)
        coda.esegui(lettori=[coda.LettoreTesto(coda.LettoreModello(cliente=modello))])
        # due richieste distinte, e in quella delle entità non si chiedono né documento né citazione
        self.assertEqual((len(modello.richieste), len(modello.richieste_documento)), (1, 1))
        richiesta = modello.richieste[0]["messages"][0]["content"]
        self.assertNotIn('"citazione"', richiesta)
        self.assertNotIn('"parti"', richiesta)
        # la citazione la ricava il programma dal testo
        self.assertIn("Amministratore: Mario Rossi.", self.entita(file, "AMMINISTRATORE").citazione)
        self.assertTrue(Documento.objects.filter(file=file).exists())

    @override_settings(ELABORAZIONE_MODELLO_NOME="modello-di-prova")
    def test_un_documento_si_puo_scartare_e_sparisce_con_il_file(self):
        file = self.elabora_il_ddt()
        coda.chiudi_revisione(file, [], {"valido": False})
        self.assertEqual(self.stato(file), archivio.FILE_ELABORATO)
        self.assertFalse(Documento.objects.utilizzabili().exists())
        diritti(self.anna, "archivio.cancella_definitivamente")
        riepilogo = dict(cancellazione.anteprima(FileCaricato.objects.get(pk=file.pk), True)["righe"])
        self.assertEqual(riepilogo["documenti riconosciuti"], 1)
        cancellazione.cancella(FileCaricato.objects.get(pk=file.pk), self.anna, "Documento caricato per errore", True)
        self.assertEqual((Documento.objects.count(), ParteDelDocumento.objects.count()), (0, 0))
        self.assertFalse(Soggetto.objects.exists())

    def test_importi_e_documenti_proposti_dal_modello(self):
        self.assertEqual(coda.importo_da_testo("€ 1.234,56"), decimal.Decimal("1234.56"))
        self.assertEqual(coda.importo_da_testo("1234.5"), decimal.Decimal("1234.50"))
        self.assertIsNone(coda.importo_da_testo("da definire"))
        # un documento su due pagine: la seconda completa la prima senza ripetere le parti
        prima = lettura_modello.documento_dalla_risposta({"documento": dict(DDT_DAL_MODELLO, totale="")})
        seconda = lettura_modello.documento_dalla_risposta({"documento": DDT_DAL_MODELLO})
        unito = coda.unisci_documento(coda.unisci_documento(None, prima, 1), seconda, 2)
        self.assertEqual((unito["totale"], unito["pagina"], len(unito["parti"])), ("€ 1.234,56", 1, 4))
        # senza numero e senza parti non è un documento
        self.assertIsNone(lettura_modello.documento_dalla_risposta({"documento": {"tipo": "ALTRO"}}))
        self.assertIsNone(lettura_modello.documento_dalla_risposta({"documento": None}))


class ScansioneTest(ConFile):
    """Il percorso delle scansioni: immagini, trascrizione, regole, entità del modello. Con un modello finto."""

    PAGINA_1 = "Assemblea dei soci della Alfa S.r.l., C.O.E. SM 12345, tenuta in Serravalle.\nAmministratore: Mario Rossi."
    PAGINA_2 = "Bilancio 2024\nRicavi delle vendite: € 150.000,00"

    def lettore_di_scansioni(self, modello):
        return coda.LettoreModello(cliente=modello, pagine_del_pdf=lambda percorso, punti: [b"pagina-1", b"pagina-2"])

    def test_una_scansione_di_due_pagine(self):
        modello = ModelloFinto([
            risposta_del_modello("<think>guardo l'immagine</think>" + self.PAGINA_1),
            entita_json(
                ("AMMINISTRATORE", "Mario Rossi", "Amministratore: Mario Rossi.", "assemblea dei soci", ""),
                ("SOCIO", "Luigi Verdi", "", "assemblea dei soci", ""),       # non è nel testo: inventato
                ("luogo", "Serravalle", "tenuta in Serravalle", "", ""),       # fuori catalogo
                ("COE", "99999", "", "", ""),                                  # gli identificativi li leggono le regole
            ),
            risposta_del_modello(self.PAGINA_2),
            entita_json(("RICAVI", "150.000,00", "Ricavi delle vendite: € 150.000,00", "", "2024")),
        ])
        file = self.carica(b"%PDF-1.4 scansione finta", nome="assemblea.pdf")
        resoconto = coda.esegui(lettori=[self.lettore_di_scansioni(modello)])
        self.assertEqual(resoconto[coda.DA_RIVEDERE], 1)

        elaborazione = Elaborazione.objects.get()
        self.assertEqual(
            (elaborazione.natura, elaborazione.motore, elaborazione.modello, elaborazione.versione_prompt, elaborazione.pagine),
            (riconoscimento.PDF, "modello-visivo-1", "modello-di-prova", lettura_modello.VERSIONE_PROMPT, 2),
        )
        testi = list(TestoPagina.objects.order_by("pagina").values_list("testo", "origine"))
        self.assertEqual(testi, [(self.PAGINA_1, models.TESTO_OCR), (self.PAGINA_2, models.TESTO_OCR)])
        # quattro richieste: trascrizione ed entità per ciascuna pagina; l'evento passa alla pagina dopo
        self.assertEqual(len(modello.richieste), 4)
        self.assertIn("Evento della pagina precedente: assemblea dei soci", modello.richieste[3]["messages"][0]["content"])
        self.assertIn("- RICAVI:", modello.richieste[1]["messages"][0]["content"])

        soggetto = anagrafica.trova(self.coe, "12345")  # nessuno dichiarato, uno solo nominato: è lui
        amministratore = self.entita(file, "AMMINISTRATORE")
        self.assertEqual(
            (amministratore.voce.codice, amministratore.verificata, amministratore.soggetto, amministratore.evento,
             amministratore.pagina, amministratore.fonte, amministratore.da_rivedere),
            ("AMMINISTRATORE", True, soggetto, "assemblea dei soci", 1, models.DA_MODELLO, False),
        )
        self.assertFalse(self.entita(file, "SOCIO").verificata)
        self.assertFalse(self.entita(file, "luogo").significativa)
        self.assertFalse(EntitaEstratta.objects.filter(valore="99999").exists())
        ricavi = self.entita(file, "RICAVI")
        self.assertEqual((ricavi.periodo, ricavi.evento, ricavi.pagina), ("2024", "assemblea dei soci", 2))
        # identificativi e importi letti da una scansione aspettano una persona
        self.assertTrue(ricavi.da_rivedere and self.entita(file, regole.COE).da_rivedere)
        self.assertEqual(self.stato(file), archivio.FILE_DA_RIVEDERE)
        self.assertEqual([e.etichetta for e in EntitaEstratta.objects.utilizzabili()], ["AMMINISTRATORE"])

        coda.conferma(FileCaricato.objects.get(pk=file.pk))
        self.assertEqual(self.stato(file), archivio.FILE_ELABORATO)
        note = {r["voce"].codice for r in coda.scheda_del_soggetto(soggetto, self.anna) if not r["mancante"]}
        self.assertEqual(note, {"COE", "AMMINISTRATORE", "RICAVI"})

    def test_il_revisore_sceglie_che_cosa_conservare_e_torna_al_file(self):
        modello = ModelloFinto([
            risposta_del_modello(self.PAGINA_1),
            entita_json(
                ("AMMINISTRATORE", "Mario Rossi", "", "", ""), ("luogo", "Serravalle", "", "", ""),
                ("SOCIO", "Luigi Verdi", "", "", ""),  # non è nel testo
            ),
            risposta_del_modello(self.PAGINA_2),
            entita_json(("RICAVI", "150.000,00", "", "", "2024")),
        ])
        file = self.carica(b"%PDF-1.4 scansione finta", nome="assemblea.pdf")
        coda.esegui(lettori=[self.lettore_di_scansioni(modello)])
        self.assertEqual(self.stato(file), archivio.FILE_DA_RIVEDERE)
        luogo = self.entita(file, "luogo")
        tenute = list(EntitaEstratta.objects.filter(file=file).exclude(pk=luogo.pk).values_list("pk", flat=True))

        self.client.force_login(self.anna)
        indirizzo = reverse("elaborazione:file", args=[file.pk])
        risposta = self.client.post(indirizzo, {"azione": "conserva", "entita": tenute}, follow=True)
        # si torna alla pagina del file in archivio, che dice che cosa è successo
        self.assertRedirects(risposta, reverse("archivio:file", args=[file.pk]))
        self.assertContains(risposta, "Revisione chiusa")
        self.assertEqual(self.stato(file), archivio.FILE_ELABORATO)
        self.assertTrue(EntitaEstratta.objects.get(pk=luogo.pk).ritirata)
        self.assertFalse(EntitaEstratta.objects.filter(file=file, da_rivedere=True).exists())
        self.assertIn("RICAVI", [e.etichetta for e in EntitaEstratta.objects.utilizzabili()])
        # la conferma di una persona prevale sul controllo contro il testo
        socio = self.entita(file, "SOCIO")
        self.assertEqual((socio.verificata, socio.confermata), (False, True))
        self.assertIn("SOCIO", [e.etichetta for e in EntitaEstratta.objects.utilizzabili()])

        # un'entità scartata per errore si ripristina: torna in attesa, e il file con lei
        self.client.post(indirizzo, {"ripristina": luogo.pk})
        luogo.refresh_from_db()
        self.assertEqual((luogo.ritirata, luogo.da_rivedere, luogo.confermata), (False, True, False))
        self.assertEqual(self.stato(file), archivio.FILE_DA_RIVEDERE)

    def test_una_risposta_tagliata_e_un_errore_da_ritentare_non_un_risultato(self):
        modello = ModelloFinto([risposta_del_modello(self.PAGINA_1), risposta_del_modello('{"entita": [', fine="length")])
        file = self.carica(b"%PDF-1.4 scansione finta", nome="assemblea.pdf")
        self.assertEqual(coda.esegui(lettori=[self.lettore_di_scansioni(modello)])[coda.ERRORE], 1)
        riga = FileCaricato.objects.get(pk=file.pk)
        self.assertEqual((riga.stato, riga.tentativi), (archivio.FILE_ERRORE, 1))
        # il messaggio dice in quale pagina e in quale passaggio
        self.assertTrue(riga.ultimo_errore.startswith("Pagina 1, entità: Risposta tagliata"), riga.ultimo_errore)
        # di una lettura fallita non resta nulla a metà
        self.assertEqual((TestoPagina.objects.count(), EntitaEstratta.objects.count()), (0, 0))

    @override_settings(ELABORAZIONE_RIVEDI_LE_SCANSIONI=False)
    def test_una_risposta_tagliata_a_meta_elenco_non_butta_via_cio_che_e_arrivato(self):
        # il modello non si ferma: ripete le stesse entità finché raggiunge il limite, e l'ultima resta a metà
        ripetute = '{"etichetta": "AMMINISTRATORE", "valore": "Mario Rossi", "evento": "assemblea", "periodo": ""}, ' * 8
        tagliata = '{"entita": [{"etichetta": "luogo", "valore": "Serravalle", "evento": "", "periodo": ""}, ' + ripetute + '{"etichetta": "SOC'
        modello = ModelloFinto([risposta_del_modello(self.PAGINA_1), risposta_del_modello(tagliata, fine="length")])
        file = self.carica(b"\xff\xd8\xff\xe0 immagine finta", nome="pagina.jpg", coe="12345")
        lettore = coda.LettoreModello(cliente=modello, immagine_come_jpeg=lambda percorso: b"jpeg")
        resoconto = coda.esegui(lettori=[lettore])
        self.assertEqual((resoconto[coda.ERRORE], resoconto[coda.DA_RIVEDERE]), (0, 1))
        # le entità arrivate intere ci sono, una volta sola
        del_modello = EntitaEstratta.objects.filter(file=file, fonte=models.DA_MODELLO)
        self.assertEqual(sorted(del_modello.values_list("etichetta", flat=True)), ["AMMINISTRATORE", "luogo"])
        # il file va rivisto, e il revisore legge perché
        riga = FileCaricato.objects.get(pk=file.pk)
        self.assertEqual(riga.stato, archivio.FILE_DA_RIVEDERE)
        for atteso in ("Pagina 1: la risposta del modello sulle entità è stata tagliata", "tenute le 2 arrivate intere", "ha ripetuto 7 volte"):
            self.assertIn(atteso, riga.ultimo_errore)
        self.assertEqual(Elaborazione.objects.get(file=file).errore, riga.ultimo_errore)
        # ... in parole sue: il testo tecnico resta nel database e lo vede, ripiegato, solo chi amministra
        self.client.force_login(self.anna)
        for nome in ("archivio:file", "elaborazione:file"):
            pagina = self.client.get(reverse(nome, args=[file.pk]))
            self.assertContains(pagina, "La lettura di questo file è incompleta")
            self.assertContains(pagina, "Pagina 1: la lettura delle entità è incompleta: qualcuna può mancare.")
            self.assertContains(pagina, "Confronta l&#x27;elenco delle entità con il documento originale")
            self.assertNotContains(pagina, "limite di lunghezza")
            self.assertNotContains(pagina, "Dettaglio tecnico")
        from django.contrib.auth import get_user_model

        self.client.force_login(get_user_model().objects.create_superuser("radice", password="x"))
        pagina = self.client.get(reverse("archivio:file", args=[file.pk]))
        self.assertContains(pagina, "Dettaglio tecnico")
        self.assertContains(pagina, "tagliata dal limite di lunghezza")
        # chiusa la revisione il file è elaborato e l'avviso non serve più
        coda.chiudi_revisione(file, list(EntitaEstratta.objects.filter(file=file).values_list("pk", flat=True)))
        riga.refresh_from_db()
        self.assertEqual((riga.stato, riga.ultimo_errore), (archivio.FILE_ELABORATO, ""))
        # al modello si dice di non elencare le righe di merce
        self.assertIn("NON elencare le righe", modello.richieste[1]["messages"][0]["content"])
        self.assertEqual(lettura_modello.oggetti_interi('{"entita": [{"a": 1}, {"a": 2}, {"a":'), [{"a": 1}, {"a": 2}])
        self.assertEqual(lettura_modello.oggetti_interi("nessun elenco"), [])

    @override_settings(ELABORAZIONE_RIVEDI_LE_SCANSIONI=False)
    def test_la_revisione_delle_scansioni_si_puo_spegnere(self):
        modello = ModelloFinto([risposta_del_modello(self.PAGINA_2), entita_json()])
        file = self.carica(b"\xff\xd8\xff\xe0 immagine finta", nome="pagina.jpg", coe="12345")
        lettore = coda.LettoreModello(cliente=modello, immagine_come_jpeg=lambda percorso: b"jpeg")
        coda.esegui(lettori=[lettore])
        self.assertEqual(self.stato(file), archivio.FILE_ELABORATO)
        self.assertEqual(Elaborazione.objects.get().natura, riconoscimento.IMMAGINE)


class OriginaleTest(ConFile):
    """Il documento originale accanto alle entità, e le pagine con l'azione accanto all'elenco."""

    def test_pdf_e_immagini_si_mostrano_nella_pagina_gli_altri_file_no(self):
        pdf = self.carica(b"%PDF-1.4 scansione finta", nome="fattura.pdf", titolo="Uno")
        png = self.carica(b"\x89PNG\r\n\x1a\n immagine finta", nome="pagina.png", titolo="Due")
        # il tipo si decide dai primi byte, non dal nome: una pagina HTML chiamata .pdf non si mostra
        finto = self.carica(b"<html><script>alert(1)</script></html>", nome="finto.pdf", titolo="Tre")
        testo = self.carica("solo testo", nome="verbale.txt", titolo="Quattro")
        self.assertEqual(
            [caricamento.tipo_in_pagina(f) for f in (pdf, png, finto, testo)], ["application/pdf", "image/png", None, None]
        )
        self.client.force_login(self.anna)
        risposta = self.client.get(reverse("archivio:anteprima", args=[pdf.pk]))
        self.assertEqual((risposta.status_code, risposta["Content-Type"]), (200, "application/pdf"))
        self.assertTrue(risposta["Content-Disposition"].startswith("inline"))
        self.assertEqual((risposta["X-Frame-Options"], risposta["X-Content-Type-Options"]), ("SAMEORIGIN", "nosniff"))
        self.assertEqual(b"".join(risposta.streaming_content), b"%PDF-1.4 scansione finta")
        for altro in (finto, testo):
            self.assertEqual(self.client.get(reverse("archivio:anteprima", args=[altro.pk])).status_code, 404)

        # nella revisione: la cornice per il PDF, l'immagine per il PNG, il solo collegamento per il resto
        pagina = self.client.get(reverse("elaborazione:file", args=[pdf.pk]))
        self.assertContains(pagina, f'<iframe id="cornice-originale" src="{reverse("archivio:anteprima", args=[pdf.pk])}"')
        self.assertContains(self.client.get(reverse("elaborazione:file", args=[png.pk])), 'alt="Immagine del documento originale"')
        pagina = self.client.get(reverse("elaborazione:file", args=[testo.pk]))
        self.assertNotContains(pagina, "cornice-originale")
        self.assertContains(pagina, "non si può mostrare accanto alle entità")

    def test_l_originale_segue_la_visibilita_del_file(self):
        from archivio import servizi

        indagine = servizi.apri_indagine(self.anna, "Riservata")
        riservato = self.carica(b"%PDF-1.4 riservato", nome="riservato.pdf", indagine=indagine)
        self.client.force_login(self.bruno)   # non assegnato all'indagine
        self.assertEqual(self.client.get(reverse("archivio:anteprima", args=[riservato.pk])).status_code, 404)
        self.client.logout()
        self.assertEqual(self.client.get(reverse("archivio:anteprima", args=[riservato.pk])).status_code, 302)

    def test_nel_faldone_l_azione_sta_accanto_all_elenco(self):
        for numero in range(3):
            self.carica("testo", titolo=f"Lotto {numero}")
        self.client.force_login(self.anna)
        pagina = self.client.get(reverse("archivio:faldone", args=["CARICAMENTI"]))
        self.assertContains(pagina, 'class="affiancati con-azione"')
        self.assertContains(pagina, "3 in tutto.")
        testo = pagina.content.decode()
        self.assertLess(testo.index('role="search"'), testo.index("Nuovo caricamento"))
        cercata = self.client.get(reverse("archivio:faldone", args=["CARICAMENTI"]), {"q": "Lotto 1"})
        self.assertContains(cercata, "1 trovati per «Lotto 1».")
        self.assertContains(cercata, "Mostra tutti")


class MessaggiTest(SimpleTestCase):
    """Gli errori di lettura in parole dell'utente (elaborazione/messaggi.py)."""

    def test_un_errore_dice_che_cosa_e_successo_e_se_il_programma_riprovera(self):
        from elaborazione import messaggi

        tecnico = "Pagina 2, trascrizione: Risposta tagliata: il modello ha raggiunto il limite di lunghezza."
        primo = messaggi.in_chiaro(tecnico, archivio.FILE_ERRORE, 1, 3)
        self.assertEqual(primo["titolo"], "La lettura di questo file non è riuscita.")
        self.assertEqual(primo["righe"], ["Pagina 2: il testo è troppo lungo per essere trascritto in una volta sola."])
        self.assertIn("Non devi fare nulla", primo["fare"])
        self.assertIn("tentativo 1 di 3", primo["fare"])
        self.assertEqual(primo["tecnico"], tecnico)
        # finiti i tentativi il programma non riprova: serve una persona
        ultimo = messaggi.in_chiaro(tecnico, archivio.FILE_ERRORE, 3, 3)
        self.assertIn("non riproverà da solo", ultimo["fare"])
        self.assertIn("amministratore", ultimo["fare"])
        # ciò che il programma non riconosce non mostra mai il testo tecnico al posto della spiegazione
        ignoto = messaggi.in_chiaro("Errore imprevisto: KeyError 'x'", archivio.FILE_ERRORE, 1, 3)
        self.assertEqual(ignoto["righe"], ["Si è verificato un errore che il programma non sa descrivere."])
        self.assertIn("amministratore", ignoto["fare"])
        for riga in primo["righe"] + ultimo["righe"] + ignoto["righe"]:
            for parola in ("modello ha raggiunto", "token", "JSON", "KeyError"):
                self.assertNotIn(parola, riga)

    def test_gli_avvisi_si_raccolgono_per_pagina_e_dicono_che_cosa_fare(self):
        from elaborazione import messaggi

        tagliata = "la risposta del modello sulle entità è stata tagliata dal limite di lunghezza: tenute le 4 arrivate intere, qualcuna può mancare."
        tecnico = f"Pagina 1: {tagliata} Pagina 1: il modello ha ripetuto 9 volte entità già elencate. Pagina 3: {tagliata}"
        avviso = messaggi.in_chiaro(tecnico, archivio.FILE_DA_RIVEDERE)
        self.assertIn("incompleta", avviso["titolo"])
        self.assertEqual(avviso["righe"], [
            "Pagine 1 e 3: la lettura delle entità è incompleta: qualcuna può mancare.",
            "Pagina 1: alcune entità comparivano più volte e sono state contate una volta sola.",
        ])
        self.assertEqual(avviso["fare"], messaggi.CONFRONTA)
        # altri casi noti, e nessun messaggio quando non c'è nulla da dire
        self.assertIn("(binario) non può essere letto", messaggi.in_chiaro("Tipo di file non gestito (binario).", "errore", 3, 3)["righe"][0])
        self.assertIn("non ha risposto", messaggi.in_chiaro("Pagina 1, entità: Il server del modello non ha risposto: timeout", "errore", 1, 3)["righe"][0])
        self.assertIsNone(messaggi.in_chiaro("", archivio.FILE_ELABORATO))
        self.assertEqual((messaggi.ERRORE, messaggi.DA_RIVEDERE), (archivio.FILE_ERRORE, archivio.FILE_DA_RIVEDERE))


class RegoleTest(SimpleTestCase):
    """Riconoscimento, regole e risposta del modello: senza database."""

    def test_un_testo_lungo_si_divide_senza_perdere_nulla(self):
        testo = "riga di testo numero uno\n" * 400
        pezzi = coda._pezzi(testo, 1000)
        self.assertEqual("".join(pezzi), testo)
        self.assertTrue(all(len(pezzo) <= 1000 for pezzo in pezzi) and len(pezzi) > 5)
        self.assertEqual(coda._pezzi("breve"), ["breve"])

    def test_la_natura_si_legge_dai_primi_byte(self):
        casi = {
            b"%PDF-1.7\n": riconoscimento.PDF, b"\xff\xd8\xff\xe0JFIF": riconoscimento.IMMAGINE,
            b"\x89PNG\r\n\x1a\n": riconoscimento.IMMAGINE, b'<?xml version="1.0"?><a/>': riconoscimento.XML,
            "Verbale n. 3 è qui".encode(): riconoscimento.TESTO, bytes(range(256)): riconoscimento.ALTRO,
            b"": riconoscimento.ALTRO,
        }
        for inizio, attesa in casi.items():
            self.assertEqual(riconoscimento.natura(inizio), attesa, inizio[:12])

    def test_le_regole_leggono_identificativi_date_e_importi(self):
        testo = VERBALE + "\nRif. interno 54399, in data 03/03/2025 e 2025-02-28; saldo 1.250,50 euro. Data impossibile 45/13/2025."
        trovate = {}
        for entita in regole.estrai(testo):
            trovate.setdefault(entita["etichetta"], []).append(entita["normalizzato"])
        self.assertEqual(trovate[regole.COE], ["12345", "54321"])  # cinque cifre senza sigla non sono un COE
        self.assertEqual(trovate[regole.PARTITA_IVA], ["01234567890"])
        self.assertEqual(trovate[regole.DATA], ["2025-03-03", "2025-02-28"])  # la stessa data scritta in due modi conta una volta
        self.assertEqual(trovate[regole.IMPORTO], ["12500.00", "1250.50"])
        self.assertEqual(trovate[regole.EMAIL], ["amministrazione@alfa.example"])

    def test_un_valore_vale_solo_se_compare_nel_testo(self):
        self.assertTrue(regole.compare_nel_testo("ALFA SRL", VERBALE))
        self.assertTrue(regole.compare_nel_testo("12500,00", VERBALE))
        self.assertFalse(regole.compare_nel_testo("Beta S.p.A.", VERBALE))
        self.assertFalse(regole.compare_nel_testo("", VERBALE))

    def test_dalla_risposta_del_modello_si_prende_solo_json_valido(self):
        buona = risposta_del_modello('Ecco:\n```json\n{"entita": [{"etichetta": "SOCIO", "valore": "Luigi Verdi"}, {"etichetta": ""}]}\n```')
        entita, evento = lettura_modello.estrai_entita(ModelloFinto([buona]), "m", "testo", [], "prima")
        self.assertEqual([(e["etichetta"], e["evento"]) for e in entita], [("SOCIO", "prima")])
        self.assertEqual(evento, "prima")
        self.assertEqual(lettura_modello.estrai_entita(ModelloFinto([]), "m", "  ", [], "prima"), ([], "prima"))
        for cattiva in (
            risposta_del_modello("{", fine="length"), risposta_del_modello(""), risposta_del_modello("nessun json"),
            risposta_del_modello("{rotto}"), risposta_del_modello('{"altro": 1}'), RuntimeError("server spento"),
        ):
            with self.assertRaises(lettura_modello.LetturaFallita):
                lettura_modello.estrai_entita(ModelloFinto([cattiva]), "m", "testo", [])


class MigrazioniTest(TestCase):
    def test_la_migrazione_scritta_a_mano_coincide_con_i_modelli(self):
        try:
            call_command("makemigrations", "elaborazione", check=True, dry_run=True, stdout=StringIO())
        except SystemExit:
            self.fail("models.py e migrations/ non coincidono: eseguire 'python manage.py makemigrations elaborazione'.")
