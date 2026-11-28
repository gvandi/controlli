from io import StringIO

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from utenti import ruoli


def crea_ruoli():
    call_command("crea_ruoli", stdout=StringIO())


class RuoliTest(TestCase):
    def setUp(self):
        crea_ruoli()

    def test_crea_tutti_i_ruoli(self):
        nomi = set(Group.objects.values_list("name", flat=True))
        self.assertEqual(nomi, set(ruoli.DIRITTI))

    def test_configuratore_modifica_le_decodifiche_e_lettore_no(self):
        Utente = get_user_model()
        configuratore = Utente.objects.create_user("conf", password="x")
        configuratore.groups.add(Group.objects.get(name=ruoli.CONFIGURATORE))
        lettore = Utente.objects.create_user("lett", password="x")
        lettore.groups.add(Group.objects.get(name=ruoli.LETTORE))

        self.assertTrue(configuratore.has_perm("decodifiche.change_formagiuridica"))
        self.assertTrue(lettore.has_perm("decodifiche.view_formagiuridica"))
        self.assertFalse(lettore.has_perm("decodifiche.change_formagiuridica"))

    def test_comando_ripetibile(self):
        crea_ruoli()
        self.assertEqual(Group.objects.count(), len(ruoli.DIRITTI))


class AccessoTest(TestCase):
    def test_home_richiede_accesso(self):
        risposta = self.client.get(reverse("home"))
        self.assertRedirects(risposta, f"{reverse('login')}?next=/")

    def test_traduzione_automatica_del_browser_disattivata(self):
        risposta = self.client.get(reverse("login"))
        self.assertContains(risposta, 'translate="no"')
        self.assertContains(risposta, '<meta name="google" content="notranslate">')

    def test_home_dopo_accesso(self):
        get_user_model().objects.create_user("mario", password="una-password-lunga")
        self.client.login(username="mario", password="una-password-lunga")
        risposta = self.client.get(reverse("home"))
        self.assertEqual(risposta.status_code, 200)
        # la pagina è a schede; chi non ha diritti vede le tre di tutti, senza quelle di chi amministra
        self.assertContains(risposta, 'role="tablist"')
        for scheda in ("da-fare", "caricamento", "societa"):
            self.assertContains(risposta, f'id="scheda-{scheda}"')
        for scheda in ("aggiornamento", "configurazione"):
            self.assertNotContains(risposta, f'id="scheda-{scheda}"')
        self.assertContains(risposta, 'data-iniziale="da-fare"')
        # una ricerca senza i diritti per le schede non rivela nulla
        risposta = self.client.get(reverse("home"), {"societa": "10000"})
        self.assertNotContains(risposta, "Ciò che se ne sa")


class MappaDallaPaginaTest(TestCase):
    """Il pulsante "Mostra la mappa di rete" della scheda "Società e analisi"."""

    def test_chi_non_puo_non_passa_e_una_societa_fuori_dal_grafo_viene_spiegata(self):
        from django.contrib.auth.models import Permission

        Utente = get_user_model()
        senza = Utente.objects.create_user("senza", password="x")
        self.client.force_login(senza)
        self.assertEqual(self.client.post(reverse("grafo:nuova_mappa"), {"soggetto": "1"}).status_code, 403)
        self.assertEqual(self.client.get(reverse("grafo:nuova_mappa")).status_code, 403)

        analista = Utente.objects.create_user("analista_di_prova", password="x")
        analista.user_permissions.add(Permission.objects.get(content_type__app_label="grafo", codename="usa_chat"))
        self.client.force_login(analista)
        self.assertEqual(self.client.get(reverse("grafo:nuova_mappa")).status_code, 405)   # solo con il pulsante
        # una società che non è nei dati dell'analisi: si torna alla scheda, con la spiegazione
        risposta = self.client.post(reverse("grafo:nuova_mappa"), {"soggetto": "999999", "cercata": "10276"}, follow=True)
        self.assertEqual(risposta.redirect_chain[0][0], reverse("home") + "?societa=10276#societa")
        self.assertContains(risposta, "non è ancora nei dati dell&#x27;analisi di rete")
        self.assertContains(risposta, 'role="alert"')

