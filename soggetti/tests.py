from io import StringIO

from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.test import TestCase

from decodifiche.models import TipoIdentificativo
from soggetti import servizi
from soggetti.models import IdentificativoSoggetto, Soggetto


class AnagraficaTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("carica_decodifiche", stdout=StringIO())
        cls.coe = TipoIdentificativo.objects.get(codice="COE")
        cls.piva = TipoIdentificativo.objects.get(codice="PIVA_IT")

    def test_scritture_diverse_dello_stesso_identificativo_sono_lo_stesso_soggetto(self):
        primo, creato = servizi.trova_o_crea(self.coe, "SM 12345", "Alfa S.r.l.")
        self.assertTrue(creato)
        self.assertTrue(primo.provvisorio)
        for scritto in ("12345", "COE 12345", "coe-12345"):
            secondo, creato = servizi.trova_o_crea(self.coe, scritto)
            self.assertEqual((secondo, creato), (primo, False), scritto)
        self.assertEqual(Soggetto.objects.count(), 1)
        riga = IdentificativoSoggetto.objects.get()
        self.assertEqual((riga.valore_originale, riga.valore_normalizzato), ("SM 12345", "12345"))
        self.assertEqual(servizi.etichetta(primo), "Alfa S.r.l. (COE 12345)")

    def test_lo_stesso_numero_con_tipi_diversi_sono_soggetti_diversi(self):
        sammarinese, _ = servizi.trova_o_crea(self.coe, "12345")
        italiano, _ = servizi.trova_o_crea(self.piva, "IT 01234567890")
        self.assertNotEqual(sammarinese, italiano)
        self.assertIsNone(servizi.trova(self.piva, "12345678901"))
        self.assertEqual(servizi.trova(self.piva, "01234567890"), italiano)

    def test_un_valore_fuori_formato_viene_rifiutato(self):
        for scritto in ("123", "1234567", "abcde", ""):
            with self.assertRaises(servizi.IdentificativoNonValido, msg=scritto):
                servizi.trova_o_crea(self.coe, scritto)
        self.assertEqual(Soggetto.objects.count(), 0)

    def test_la_denominazione_arrivata_dopo_completa_il_soggetto_senza_sovrascrivere(self):
        soggetto, _ = servizi.trova_o_crea(self.coe, "12345")
        self.assertEqual(servizi.etichetta(soggetto), "Senza denominazione (COE 12345)")
        servizi.trova_o_crea(self.coe, "12345", "Alfa S.r.l.")
        servizi.trova_o_crea(self.coe, "12345", "Un altro nome")
        soggetto.refresh_from_db()
        self.assertEqual(soggetto.denominazione, "Alfa S.r.l.")

    def test_il_database_impedisce_due_soggetti_con_lo_stesso_identificativo(self):
        soggetto, _ = servizi.trova_o_crea(self.coe, "12345")
        altro = Soggetto.objects.create()
        with self.assertRaises(IntegrityError), transaction.atomic():
            IdentificativoSoggetto.objects.create(
                soggetto=altro, tipo=self.coe, valore_originale="12345", valore_normalizzato="12345"
            )


class NomiInItalianoTest(TestCase):
    def test_ogni_modello_dell_applicativo_dichiara_singolare_e_plurale(self):
        """Senza un nome dichiarato Django aggiunge una "s": "Faldones", "Soggettos"."""
        from django.apps import apps

        nostre = {"archivio", "decodifiche", "elaborazione", "grafo", "indici", "lavori", "soggetti", "utenti"}
        mancanti = []
        for modello in apps.get_models():
            if modello._meta.app_label not in nostre or modello._meta.auto_created:
                continue
            opzioni = modello._meta.original_attrs
            if "verbose_name" not in opzioni or "verbose_name_plural" not in opzioni:
                mancanti.append(modello._meta.label)
        self.assertEqual(mancanti, [], "Aggiungere verbose_name e verbose_name_plural in class Meta.")


class MigrazioniTest(TestCase):
    def test_la_migrazione_scritta_a_mano_coincide_con_i_modelli(self):
        try:
            call_command("makemigrations", "soggetti", check=True, dry_run=True, stdout=StringIO())
        except SystemExit:
            self.fail("models.py e migrations/ non coincidono: eseguire 'python manage.py makemigrations soggetti'.")
