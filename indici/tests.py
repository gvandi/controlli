"""Prove dell'anagrafica per periodo, delle regole e dell'indice che ne risulta."""
import decimal
from io import StringIO

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from archivio import models as archivio
from archivio.models import Fascicolo
from decodifiche.models import TipoIdentificativo
from grafo import contratto
from grafo import models as grafo
from indici import calcolo, importazione, spazio
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


class SpazioTest(TestCase):
    """Le aziende come punti in tre dimensioni: indice a regole e scostamento dalle aziende simili."""

    @classmethod
    def setUpTestData(cls):
        call_command("carica_decodifiche", stdout=StringIO())
        call_command("carica_regole", stdout=StringIO())
        righe = ["coe;periodo;denominazione;ateco;dipendenti;fatturato"]
        righe += [f"{10001 + i};2025;Negozio {i};47.11;D1;F1" for i in range(9)]   # nove negozi uguali
        righe += [
            "10000;2025;Alfa S.r.l.;47.26;D0;F6",      # senza dipendenti e fatturato altissimo
            "20000;2025;Software S.r.l.;62.01;D2;F2",  # sola nella sua attività
            "30000;2025;Incompleta S.r.l.;47.11;D1;",  # manca il fatturato: non si può collocare
        ]
        importazione.importa("\n".join(righe))

    def test_lo_z_score_robusto_non_si_fa_spostare_dai_valori_estremi(self):
        z = spazio.z_robusti([1, 2, 3, 4, 5, 6, 7, 100])
        self.assertAlmostEqual(z[3], -0.169, places=3)   # mediana 4,5 e MAD 2
        self.assertGreater(z[-1], 30)
        # se più di metà dei valori coincide la MAD è zero: si usa lo scarto assoluto medio
        self.assertAlmostEqual(spazio.z_robusti([1, 1, 1, 1, 4])[-1], 3.99, places=2)
        self.assertEqual(spazio.z_robusti([2, 2, 2]), [0.0, 0.0, 0.0])
        self.assertEqual(spazio.z_robusti([5]), [0.0])

    def test_ogni_azienda_ha_tre_coordinate_una_regola_e_uno_scostamento(self):
        regola = RegolaDiRischio.objects.get(codice="COMMERCIO_SENZA_DIPENDENTI")
        dati = spazio.costruisci(regola)
        self.assertEqual((len(dati["punti"]), dati["esclusi"]), (11, 1))
        self.assertEqual([a["codice"] for a in dati["assi"]["attivita"]], ["47", "62"])
        self.assertEqual((dati["rapporti"], dati["fuori"]), ([], {}))  # nessun documento confermato
        per_nome = {p["nome"]: p for p in dati["punti"]}
        alfa, negozio, software = per_nome["Alfa S.r.l."], per_nome["Negozio 0"], per_nome["Software S.r.l."]
        # coordinate: posizione della classe sui due assi ordinati, e divisione dell'attività
        self.assertEqual((alfa["d"], alfa["f"], alfa["a"]), (0, 6, 0))
        self.assertEqual((software["d"], software["f"], software["a"]), (2, 2, 1))
        # per Alfa la regola scatta E Alfa si discosta dalle altre aziende della sua attività
        self.assertEqual((alfa["scatta"], alfa["altre"], alfa["gruppo"]), (True, [], "attività 47"))
        self.assertGreater(alfa["z"], spazio.SOGLIA_Z)
        self.assertEqual((negozio["scatta"], negozio["z"]), (False, 0.0))
        # un'attività con poche aziende si confronta con tutte
        self.assertEqual(software["gruppo"], spazio.TUTTE)
        # ciò che la regola richiede su ogni asse, per evidenziarlo: D0, da F1 in su, la divisione 47
        self.assertEqual(dati["regola"]["dentro"], {"dipendenti": [0], "fatturato": [1, 2, 3, 4, 5, 6, 7], "attivita": [0]})

        # un'altra regola: cambia per chi scatta, non lo scostamento; la prima compare fra le "altre"
        piccoli = RegolaDiRischio.objects.create(
            codice="NEGOZI_PICCOLI", descrizione="Dettaglio con 1-2 dipendenti", tipo="fuori_oggetto_licenza",
            peso="0.30", prefissi_attivita="47.1", classi_dipendenti="D1", attiva=False,
        )
        altro = spazio.costruisci(piccoli)
        self.assertEqual(sum(p["scatta"] for p in altro["punti"]), 9)
        per_nome = {p["nome"]: p for p in altro["punti"]}
        self.assertEqual((per_nome["Alfa S.r.l."]["scatta"], per_nome["Alfa S.r.l."]["altre"]), (False, ["COMMERCIO_SENZA_DIPENDENTI"]))
        self.assertEqual([p["z"] for p in altro["punti"]], [p["z"] for p in dati["punti"]])
        # senza regole restano i soli scostamenti
        nessuna = spazio.costruisci(None)
        self.assertIsNone(nessuna["regola"])
        self.assertFalse(any(p["scatta"] for p in nessuna["punti"]))

    def test_la_pagina_e_per_chi_puo_consultare_gli_indici(self):
        Utente = get_user_model()
        anna, bruno = Utente.objects.create_user("anna", password="x"), Utente.objects.create_user("bruno", password="x")
        anna.user_permissions.add(Permission.objects.get(content_type__app_label="indici", codename="view_regoladirischio"))
        self.client.force_login(bruno)
        self.assertEqual(self.client.get(reverse("indici:spazio")).status_code, 403)
        self.client.force_login(anna)
        RegolaDiRischio.objects.create(codice="ALTRA", descrizione="Altra regola", tipo="triangolazione", peso="0.10", classi_dipendenti="D7")
        # senza scelta, o con un codice che non esiste, vale la prima regola attiva
        for richiesta in ({}, {"regola": "inventata"}):
            self.assertEqual(self.client.get(reverse("indici:spazio"), richiesta).context["regola"].codice, "ALTRA")
        pagina = self.client.get(reverse("indici:spazio"), {"regola": "COMMERCIO_SENZA_DIPENDENTI"})
        self.assertEqual(pagina.context["regola"].codice, "COMMERCIO_SENZA_DIPENDENTI")
        self.assertContains(pagina, "Alfa S.r.l.")
        self.assertContains(pagina, 'value="2.5"')
        # senza il diritto di aprire le schede non ci sono collegamenti alle aziende
        self.assertTrue(all(p["scheda"] == "" for p in pagina.context["dati"]["punti"]))


class MigrazioniTest(TestCase):
    def test_la_migrazione_scritta_a_mano_coincide_con_i_modelli(self):
        try:
            call_command("makemigrations", "indici", check=True, dry_run=True, stdout=StringIO())
        except SystemExit:
            self.fail("models.py e migrations/ non coincidono: eseguire 'python manage.py makemigrations indici'.")
