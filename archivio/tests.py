from io import StringIO

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from archivio import models, servizi
from archivio.models import Assegnazione, Faldone, Fascicolo, SoggettoInIndagine
from decodifiche.models import TipoIdentificativo
from soggetti.models import Soggetto


def diritti(utente, *codici):
    """Assegna diritti scritti come 'app.codice'."""
    for codice in codici:
        app, nome = codice.split(".")
        utente.user_permissions.add(Permission.objects.get(content_type__app_label=app, codename=nome))


class ArchivioTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("carica_decodifiche", stdout=StringIO())
        cls.coe = TipoIdentificativo.objects.get(codice="COE")
        Utente = get_user_model()
        da_analista = ("archivio.view_fascicolo", "archivio.apre_indagini", "soggetti.add_soggetto")
        cls.anna = Utente.objects.create_user("anna", password="x")
        cls.bruno = Utente.objects.create_user("bruno", password="x")
        cls.carla = Utente.objects.create_user("carla", password="x")
        for analista in (cls.anna, cls.bruno, cls.carla):
            diritti(analista, *da_analista)
        cls.lettore = Utente.objects.create_user("lettore", password="x")
        diritti(cls.lettore, "archivio.view_fascicolo")
        cls.esterno = Utente.objects.create_user("esterno", password="x")
        cls.capo = Utente.objects.create_superuser("capo", password="x")

    # ---- attrezzi -------------------------------------------------------
    def pagina(self, chi, nome, /, *argomenti, **dati):
        """Apre la pagina come l'utente 'chi'; con dei dati li invia come modulo.
        I primi due parametri sono solo posizionali: i moduli hanno campi che si
        chiamano 'utente' e 'nome' e non devono scontrarsi con loro."""
        self.client.force_login(chi)
        indirizzo = reverse(f"archivio:{nome}", args=argomenti)
        return self.client.post(indirizzo, dati) if dati else self.client.get(indirizzo)

    def numero_visibile(self, utente, codice):
        return dict((f.codice, n) for f, n in servizi.conteggi_per_faldone(utente))[codice]

    # ---- struttura ------------------------------------------------------
    def test_la_migrazione_crea_i_tre_faldoni(self):
        faldoni = {f.codice: f for f in Faldone.objects.all()}
        self.assertEqual(set(faldoni), {models.CARICAMENTI, models.AZIENDE, models.INDAGINI})
        self.assertTrue(faldoni[models.INDAGINI].riservato)
        self.assertFalse(faldoni[models.AZIENDE].riservato)
        self.assertTrue(faldoni[models.AZIENDE].creato_dal_sistema)

    def test_senza_diritto_l_archivio_non_si_apre(self):
        self.assertEqual(self.pagina(self.esterno, "faldoni").status_code, 403)
        self.assertEqual(self.pagina(self.esterno, "faldone", models.AZIENDE).status_code, 403)
        self.client.logout()
        self.assertEqual(self.client.get(reverse("archivio:faldoni")).status_code, 302)

    # ---- aziende --------------------------------------------------------
    def test_un_azienda_ha_un_solo_fascicolo_comunque_sia_scritto_il_coe(self):
        risposta = self.pagina(
            self.anna, "faldone", models.AZIENDE,
            azione="aggiungi_azienda", tipo=self.coe.pk, valore="SM 12345", denominazione="Alfa S.r.l.",
        )
        fascicolo = Fascicolo.objects.get()
        self.assertRedirects(risposta, reverse("archivio:fascicolo", args=[fascicolo.pk]))
        self.assertEqual(fascicolo.titolo, "Alfa S.r.l. (COE 12345)")
        self.assertEqual(fascicolo.faldone.codice, models.AZIENDE)
        self.pagina(self.bruno, "faldone", models.AZIENDE, azione="aggiungi_azienda", tipo=self.coe.pk, valore="12345")
        self.assertEqual((Fascicolo.objects.count(), Soggetto.objects.count()), (1, 1))
        # le aziende le vede chiunque possa consultare l'archivio, e si cercano per identificativo
        self.assertContains(self.pagina(self.lettore, "fascicolo", fascicolo.pk), "12345")
        self.client.force_login(self.lettore)
        elenco = reverse("archivio:faldone", args=[models.AZIENDE])
        self.assertContains(self.client.get(elenco, {"q": "1234"}), "Alfa S.r.l.")
        self.assertNotContains(self.client.get(elenco, {"q": "99999"}), "Alfa S.r.l.")

    def test_un_coe_scritto_male_e_chi_non_ha_diritto_non_creano_nulla(self):
        sbagliato = self.pagina(
            self.anna, "faldone", models.AZIENDE, azione="aggiungi_azienda", tipo=self.coe.pk, valore="12"
        )
        self.assertContains(sbagliato, "non è un valore valido")
        self.pagina(self.lettore, "faldone", models.AZIENDE, azione="aggiungi_azienda", tipo=self.coe.pk, valore="12345")
        self.assertEqual((Fascicolo.objects.count(), Soggetto.objects.count()), (0, 0))

    # ---- indagini e visibilità -----------------------------------------
    def apri_indagine(self, utente=None, titolo="Operazione Tramontana"):
        return servizi.apri_indagine(utente or self.anna, titolo)

    def test_un_indagine_la_vede_solo_chi_vi_e_assegnato(self):
        risposta = self.pagina(
            self.anna, "faldone", models.INDAGINI, azione="apri_indagine", titolo="Operazione Tramontana"
        )
        indagine = Fascicolo.objects.get()
        self.assertRedirects(risposta, reverse("archivio:fascicolo", args=[indagine.pk]))
        self.assertEqual(Assegnazione.objects.get().utente, self.anna)

        self.assertContains(self.pagina(self.anna, "fascicolo", indagine.pk), "Operazione Tramontana")
        self.assertEqual(self.numero_visibile(self.anna, models.INDAGINI), 1)
        # per tutti gli altri l'indagine non esiste: né pagina, né elenco, né conteggio.
        # Vale anche per il superutente.
        for altro in (self.bruno, self.lettore, self.capo):
            self.assertEqual(self.pagina(altro, "fascicolo", indagine.pk).status_code, 404, altro.username)
            self.assertNotContains(self.pagina(altro, "faldone", models.INDAGINI), "Tramontana")
            self.assertEqual(self.numero_visibile(altro, models.INDAGINI), 0, altro.username)
            self.assertFalse(Fascicolo.objects.visibili_a(altro).exists())

    def test_le_persone_le_decide_chi_ha_aperto_l_indagine(self):
        indagine = self.apri_indagine()
        self.pagina(self.anna, "fascicolo", indagine.pk, azione="assegna", utente=self.bruno.pk)
        self.assertEqual(self.pagina(self.bruno, "fascicolo", indagine.pk).status_code, 200)
        # Bruno è assegnato ma non ha aperto l'indagine: non può aggiungere né togliere persone
        negata = self.pagina(self.bruno, "fascicolo", indagine.pk, azione="assegna", utente=self.carla.pk)
        self.assertContains(negata, "chi ha aperto")
        self.assertEqual(self.pagina(self.carla, "fascicolo", indagine.pk).status_code, 404)
        # chi ha aperto non può essere tolto; Bruno sì, e da quel momento non vede più nulla
        with self.assertRaises(servizi.OperazioneNonAmmessa):
            servizi.revoca(indagine, self.anna, self.anna)
        self.pagina(self.anna, "fascicolo", indagine.pk, azione="revoca", utente=self.bruno.pk)
        self.assertEqual(self.pagina(self.bruno, "fascicolo", indagine.pk).status_code, 404)

    def test_aprire_un_indagine_richiede_il_diritto(self):
        self.pagina(self.lettore, "faldone", models.INDAGINI, azione="apri_indagine", titolo="Non dovrei")
        self.assertEqual(Fascicolo.objects.count(), 0)
        with self.assertRaises(servizi.OperazioneNonAmmessa):
            servizi.apri_indagine(self.lettore, "Non dovrei")
        with self.assertRaises(servizi.OperazioneNonAmmessa):
            servizi.apri_indagine(self.anna, "   ")

    def test_dall_azienda_non_si_risale_all_indagine(self):
        azienda = servizi.acquisisci_azienda(self.coe, "12345", "Alfa S.r.l.")
        indagine = self.apri_indagine()
        self.pagina(
            self.anna, "fascicolo", indagine.pk,
            azione="aggiungi_soggetto", tipo=self.coe.pk, valore="COE 12345", nota="segnalazione",
        )
        collegamento = SoggettoInIndagine.objects.get()
        self.assertEqual((collegamento.fascicolo, collegamento.soggetto), (indagine, azienda.soggetto))
        self.assertContains(self.pagina(self.anna, "fascicolo", indagine.pk), "Alfa S.r.l.")
        # il fascicolo dell'azienda non dice nulla dell'indagine, nemmeno a chi vi è assegnato
        for utente in (self.anna, self.bruno, self.lettore):
            scheda = self.pagina(utente, "fascicolo", azienda.pk)
            self.assertEqual(scheda.status_code, 200)
            self.assertNotContains(scheda, "Tramontana")
        # e dal modello Soggetto non esiste un percorso verso le indagini
        self.assertFalse(any("indagine" in campo.name for campo in Soggetto._meta.get_fields()))
        # un soggetto nuovo indicato nell'indagine nasce provvisorio, senza fascicolo in Aziende
        self.pagina(self.anna, "fascicolo", indagine.pk, azione="aggiungi_soggetto", tipo=self.coe.pk, valore="54321")
        self.assertEqual(SoggettoInIndagine.objects.count(), 2)
        self.assertEqual(self.numero_visibile(self.lettore, models.AZIENDE), 1)
        # chi non è assegnato non può toccare i soggetti dell'indagine
        with self.assertRaises(servizi.OperazioneNonAmmessa):
            servizi.aggiungi_soggetto(indagine, self.coe, "11111", self.bruno)
        self.pagina(self.anna, "fascicolo", indagine.pk, azione="togli_soggetto", riga=collegamento.pk)
        self.assertEqual(SoggettoInIndagine.objects.count(), 1)

    def test_un_fascicolo_legato_a_un_indagine_ne_eredita_la_riservatezza(self):
        """Prepara la parte 2: un caricamento riservato a un'indagine."""
        indagine = self.apri_indagine()
        caricamenti = Faldone.objects.get(codice=models.CARICAMENTI)
        generale = Fascicolo.objects.create(faldone=caricamenti, titolo="Caricamento generale")
        riservato = Fascicolo.objects.create(faldone=caricamenti, titolo="Caricamento riservato", riservato_a=indagine)
        self.assertEqual(set(Fascicolo.objects.visibili_a(self.anna)), {indagine, generale, riservato})
        self.assertEqual(set(Fascicolo.objects.visibili_a(self.bruno)), {generale})
        self.assertEqual(self.numero_visibile(self.bruno, models.CARICAMENTI), 1)
        self.assertEqual(self.pagina(self.bruno, "fascicolo", riservato.pk).status_code, 404)
        servizi.assegna(indagine, self.bruno, self.anna)
        self.assertEqual(set(Fascicolo.objects.visibili_a(self.bruno)), {indagine, generale, riservato})

    def test_i_fascicoli_non_sono_nell_amministrazione(self):
        from django.contrib import admin

        registrati = {modello.__name__ for modello in admin.site._registry}
        self.assertIn("Faldone", registrati)
        self.assertFalse({"Fascicolo", "Assegnazione", "SoggettoInIndagine"} & registrati)


class MigrazioniTest(TestCase):
    def test_la_migrazione_scritta_a_mano_coincide_con_i_modelli(self):
        try:
            call_command("makemigrations", "archivio", check=True, dry_run=True, stdout=StringIO())
        except SystemExit:
            self.fail("models.py e migrations/ non coincidono: eseguire 'python manage.py makemigrations archivio'.")
