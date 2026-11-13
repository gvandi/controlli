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
