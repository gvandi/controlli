"""Prove dell'anagrafica per periodo, delle regole e dell'indice che ne risulta."""
import decimal
from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from archivio import models as archivio
from archivio.models import Fascicolo
from decodifiche.models import TipoIdentificativo
from grafo import contratto
from grafo import models as grafo
from indici import calcolo, importazione
from indici.models import RegolaDiRischio
from soggetti import servizi as anagrafica
from soggetti.models import DatiPerPeriodo

CSV = """coe;piva;periodo;denominazione;ateco;dipendenti;fatturato
10000;;2025;Alfa S.r.l.;47.26;0;350.000,00
54321;;2025;Trasporti Beta S.r.l.;49.41;12;1.250.000,00
20000;;2025;Gamma Commerciale S.r.l.;46.19;0;90.000,00
30000;;2025;Delta S.r.l.;47.11;;
;;2025;Senza identificativo;47;0;1
40000;;25;Periodo sbagliato;47;0;1
1;;2025;COE sbagliato;47;0;1
50000;;2025;Fatturato sbagliato;47;0;molto
"""


class IndiciTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("carica_decodifiche", stdout=StringIO())
        call_command("carica_regole", stdout=StringIO())
        cls.coe = TipoIdentificativo.objects.get(codice="COE")

    def dato(self, coe, periodo="2025"):
        return DatiPerPeriodo.objects.get(soggetto=anagrafica.trova(self.coe, coe), periodo=periodo)

    def test_l_anagrafica_si_importa_per_periodo(self):
        resoconto = importazione.importa(CSV, "prova")
        self.assertEqual((resoconto["create"], resoconto["aggiornate"]), (4, 0))
        self.assertEqual([numero for numero, _ in resoconto["rifiutate"]], [6, 7, 8, 9])
        alfa = self.dato("10000")
        self.assertEqual(
            (alfa.codice_attivita, alfa.dipendenti, alfa.fatturato, alfa.fonte),
            ("47.26", 0, decimal.Decimal("350000.00"), "prova"),
        )
        # un dato che la fonte non dà resta mancante, non zero
        delta = self.dato("30000")
        self.assertEqual((delta.dipendenti, delta.fatturato), (None, None))
        # l'azienda importata è in anagrafica, non più provvisoria, e ha il suo fascicolo
        self.assertEqual((alfa.soggetto.denominazione, alfa.soggetto.provvisorio), ("Alfa S.r.l.", False))
        self.assertTrue(Fascicolo.objects.filter(faldone__codice=archivio.AZIENDE, soggetto=alfa.soggetto).exists())

        # stesso COE e stesso periodo: aggiorna; periodo nuovo (anche anno e mese): aggiunge
        altro = "coe,periodo,dipendenti,fatturato\n10000,2025,2,400000.00\n10000,2026,3,\n10000,2026-03,4,\n"
        resoconto = importazione.importa(altro)
        self.assertEqual((resoconto["create"], resoconto["aggiornate"], resoconto["rifiutate"]), (2, 1, []))
        self.assertEqual(self.dato("10000").dipendenti, 2)
        self.assertEqual(DatiPerPeriodo.objects.filter(soggetto=alfa.soggetto).count(), 3)
        with self.assertRaises(importazione.RigaNonValida):
            importazione.importa("nome;valore\nx;1\n")

    def test_la_fonte_puo_dare_la_classe_al_posto_del_valore(self):
        testo = (
            "coe;periodo;ateco;dipendenti;fatturato\n"
            "10000;2025;47.26;D0;F2\n"      # classi: la regola scatta come con i valori
            "20000;2025;46.19;d0;f0\n"      # minuscole accettate; fatturato sotto 100.000
            "30000;2025;47.11;0;F3\n"       # un valore e una classe insieme
            "40000;2025;47.11;D99;F1\n"     # classe che non esiste
            "50000;2025;47.11;D0;tanto\n"
        )
        resoconto = importazione.importa(testo)
        self.assertEqual((resoconto["create"], [n for n, _ in resoconto["rifiutate"]]), (3, [5, 6]))
        alfa = self.dato("10000")
        self.assertEqual(
            (alfa.dipendenti, alfa.classe_dipendenti, alfa.fatturato, alfa.classe_fatturato), (None, "D0", None, "F2")
        )
        regola = RegolaDiRischio.objects.get(codice="COMMERCIO_SENZA_DIPENDENTI")
        attese = {"10000": True, "20000": False, "30000": True}
        for coe, attesa in attese.items():
            self.assertEqual(calcolo.scatta(regola, calcolo.descrivi(self.dato(coe))), attesa, coe)
        self.assertEqual(calcolo.descrivi(self.dato("20000"))["classe_fatturato"], "F0")
        # reimportare con il valore al posto della classe toglie la classe
        importazione.importa("coe;periodo;dipendenti\n10000;2025;3\n")
        alfa.refresh_from_db()
        self.assertEqual((alfa.dipendenti, alfa.classe_dipendenti), (3, ""))

    def test_una_regola_scatta_solo_se_valgono_tutte_le_sue_condizioni(self):
        importazione.importa(CSV)
        regola = RegolaDiRischio.objects.get(codice="COMMERCIO_SENZA_DIPENDENTI")
        attese = {"10000": True, "54321": False, "20000": False, "30000": False}  # 20000: fatturato sotto 100.000
        for coe, attesa in attese.items():
            self.assertEqual(calcolo.scatta(regola, calcolo.descrivi(self.dato(coe))), attesa, coe)
        self.assertEqual(
            calcolo.descrivi(self.dato("10000")),
            {"periodo": "2025", "attivita": "47.26", "classe_dipendenti": "D0", "classe_fatturato": "F2"},
        )
        # una regola senza condizioni non scatta mai; due regole dello stesso tipo si combinano senza superare 1
        vuota = RegolaDiRischio(codice="VUOTA", descrizione="", tipo="triangolazione", peso="0.90")
        self.assertFalse(calcolo.scatta(vuota, calcolo.descrivi(self.dato("10000"))))
        seconda = RegolaDiRischio(codice="B", descrizione="", tipo=regola.tipo, peso="0.50")
        indice = contratto.TIPI_IRREGOLARITA.index(regola.tipo)
        self.assertEqual(calcolo.punteggi([regola])[indice], 0.6)
        self.assertEqual(calcolo.punteggi([regola, seconda])[indice], 0.8)

    def test_l_indice_e_un_esecuzione_a_se_dell_analisi_di_rete(self):
        self.assertIsNone(calcolo.esegui()["esecuzione"])  # nessun dato reale
        importazione.importa(CSV)
        resoconto = calcolo.esegui()
        self.assertEqual(
            (resoconto["aziende"], resoconto["segnalate"], resoconto["senza_dati"], resoconto["regole"]), (4, 1, 0, 1)
        )
        esecuzione = resoconto["esecuzione"]
        self.assertEqual(esecuzione.versione_calcolo, "1.0+regole")
        # i lettori che accettano il calcolo 1.0 lo accettano; con ===1.0 l'amministratore lo esclude
        self.assertTrue(contratto.accettata(esecuzione.versione_calcolo, contratto.CALCOLO_ACCETTATO, ""))
        self.assertFalse(contratto.accettata(esecuzione.versione_calcolo, contratto.CALCOLO_ACCETTATO, "===1.0"))

        alfa = grafo.Soggetto.objects.get(riferimento=f"ANAG-{anagrafica.trova(self.coe, '10000').pk}")
        punteggio = grafo.PunteggioRischio.objects.get(esecuzione=esecuzione, soggetto=alfa, tipo="falsa_fatturazione")
        self.assertEqual((punteggio.punteggio, punteggio.sopra_soglia), (0.6, True))
        self.assertFalse(
            grafo.PunteggioRischio.objects.filter(esecuzione=esecuzione, sopra_soglia=True).exclude(soggetto=alfa).exists()
        )
        # la spiegazione è la regola scattata
        spiegazione = grafo.Spiegazione.objects.get(esecuzione=esecuzione, soggetto=alfa)
        self.assertIn("COMMERCIO_SENZA_DIPENDENTI", spiegazione.dati["features"][0]["descrizione"])
        self.assertEqual(grafo.Spiegazione.objects.filter(esecuzione=esecuzione).count(), 1)

        # rieseguire senza novità sostituisce la stessa esecuzione; con dati nuovi nasce una nuova fotografia
        self.assertEqual(calcolo.esegui()["versione_dati"], resoconto["versione_dati"])
        self.assertEqual(grafo.Esecuzione.objects.count(), 1)
        importazione.importa("coe;periodo;fatturato\n20000;2025;120.000,00\n")  # ora anche la 20000 supera i 100.000
        self.assertNotEqual(calcolo.esegui()["versione_dati"], resoconto["versione_dati"])
        self.assertEqual(grafo.Esecuzione.objects.count(), 2)
        self.assertEqual(grafo.PunteggioRischio.objects.filter(sopra_soglia=True).count(), 1 + 2)


class MigrazioniTest(TestCase):
    def test_la_migrazione_scritta_a_mano_coincide_con_i_modelli(self):
        try:
            call_command("makemigrations", "indici", check=True, dry_run=True, stdout=StringIO())
        except SystemExit:
            self.fail("models.py e migrations/ non coincidono: eseguire 'python manage.py makemigrations indici'.")
