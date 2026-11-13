from datetime import date
from decimal import Decimal
from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from decodifiche import dati_iniziali as dati
from decodifiche import models

OGGI = date(2026, 11, 12)


def carica():
    call_command("carica_decodifiche", stdout=StringIO())


class CaricamentoTest(TestCase):
    def test_carica_tutte_le_tabelle(self):
        carica()
        self.assertEqual(models.ClasseDipendenti.objects.count(), len(dati.CLASSI_DIPENDENTI))
        self.assertEqual(models.ClasseFatturato.objects.count(), len(dati.CLASSI_FATTURATO))
        self.assertEqual(models.FormaGiuridica.objects.count(), len(dati.FORME_GIURIDICHE))
        self.assertEqual(models.PosizioneGruppo.objects.count(), len(dati.POSIZIONI_GRUPPO))
        self.assertEqual(models.AttivitaEconomica.objects.count(), len(dati.ATTIVITA_ESEMPIO))

    def test_ripetibile_e_non_sovrascrive(self):
        carica()
        models.FormaGiuridica.objects.filter(codice="SRL").update(descrizione="Modificata a mano")
        carica()
        self.assertEqual(models.FormaGiuridica.objects.count(), len(dati.FORME_GIURIDICHE))
        self.assertEqual(models.FormaGiuridica.objects.get(codice="SRL").descrizione, "Modificata a mano")


class ClassiTest(TestCase):
    def setUp(self):
        carica()

    def test_classi_dipendenti_agli_estremi(self):
        attesi = {0: "D0", 1: "D1", 2: "D1", 3: "D2", 9: "D3", 10: "D4", 49: "D5", 50: "D6", 249: "D6", 250: "D7", 10_000: "D7"}
        for valore, codice in attesi.items():
            with self.subTest(dipendenti=valore):
                self.assertEqual(models.ClasseDipendenti.per_valore(valore, OGGI).codice, codice)

    def test_classi_fatturato_agli_estremi(self):
        attesi = {
            "0": "F0",
            "99999.99": "F0",
            "100000": "F1",
            "1999999.99": "F4",
            "2000000": "F5",
            "50000000": "F7",
        }
        for valore, codice in attesi.items():
            with self.subTest(fatturato=valore):
                self.assertEqual(models.ClasseFatturato.per_valore(Decimal(valore), OGGI).codice, codice)

    def test_intervalli_contigui_senza_buchi(self):
        for modello in (models.ClasseDipendenti, models.ClasseFatturato):
            classi = list(modello.objects.order_by("minimo"))
            self.assertEqual(classi[0].minimo, 0)
            self.assertIsNone(classi[-1].massimo)
            for precedente, successiva in zip(classi, classi[1:]):
                self.assertEqual(precedente.massimo, successiva.minimo)

    def test_valore_negativo_senza_classe(self):
        self.assertIsNone(models.ClasseFatturato.per_valore(Decimal("-1"), OGGI))

    def test_classe_scaduta_non_viene_usata(self):
        models.ClasseDipendenti.objects.filter(codice="D0").update(valida_al=date(2025, 12, 31))
        self.assertIsNone(models.ClasseDipendenti.per_valore(0, OGGI))
        self.assertEqual(models.ClasseDipendenti.per_valore(0, date(2025, 6, 1)).codice, "D0")


class IdentificativiTest(TestCase):
    def setUp(self):
        carica()

    def test_coe_scritto_in_modi_diversi_e_lo_stesso_valore(self):
        coe = models.TipoIdentificativo.objects.get(codice="COE")
        for scritto in ("12345", "SM12345", "SM 12345", "COE 12345", "coe-12345", " sm.12345 "):
            with self.subTest(scritto=scritto):
                self.assertEqual(coe.normalizza(scritto), "12345")
                self.assertTrue(coe.accetta(scritto))

    def test_coe_non_valido(self):
        coe = models.TipoIdentificativo.objects.get(codice="COE")
        for scritto in ("", "1234", "123456", "12A45", "SM"):
            with self.subTest(scritto=scritto):
                self.assertFalse(coe.accetta(scritto))

    def test_partita_iva_italiana(self):
        piva = models.TipoIdentificativo.objects.get(codice="PIVA_IT")
        self.assertEqual(piva.normalizza("IT 01234567890"), "01234567890")
        self.assertTrue(piva.accetta("IT01234567890"))
        self.assertTrue(piva.accetta("01234567890"))
        self.assertFalse(piva.accetta("0123456789"))

    def test_tipo_senza_controllo_accetta_ogni_valore_non_vuoto(self):
        altro = models.TipoIdentificativo.objects.get(codice="ALTRO")
        self.assertTrue(altro.accetta("ABC-99/x"))
        self.assertFalse(altro.accetta("  "))

    def test_tipi_di_documento_e_ruoli_caricati(self):
        self.assertEqual(models.TipoDocumento.objects.count(), len(dati.TIPI_DOCUMENTO))
        self.assertEqual(models.RuoloNelDocumento.objects.count(), len(dati.RUOLI_NEL_DOCUMENTO))


class AttivitaTest(TestCase):
    def setUp(self):
        carica()

    def test_gerarchia(self):
        tabacchi = models.AttivitaEconomica.objects.get(codice="47.26")
        self.assertEqual([a.codice for a in tabacchi.antenati()], ["47.2", "47"])
