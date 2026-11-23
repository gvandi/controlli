import io
import tempfile
import zipfile
from io import StringIO

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from archivio import caricamento, deposito, ingresso, models, servizi
from archivio.models import (
    Assegnazione, Evento, Faldone, Fascicolo, FileCaricato, SoggettoDichiarato, SoggettoInIndagine,
)
from decodifiche.models import TipoDocumento, TipoIdentificativo
from soggetti.models import Soggetto


def diritti(utente, *codici):
    """Assegna diritti scritti come 'app.codice'."""
    for codice in codici:
        app, nome = codice.split(".")
        utente.user_permissions.add(Permission.objects.get(content_type__app_label=app, codename=nome))


class ConUtenti(TestCase):
    """Utenti e attrezzi comuni alle prove dell'archivio."""

    @classmethod
    def setUpTestData(cls):
        call_command("carica_decodifiche", stdout=StringIO())
        cls.coe = TipoIdentificativo.objects.get(codice="COE")
        Utente = get_user_model()
        da_analista = (
            "archivio.view_fascicolo", "archivio.apre_indagini", "soggetti.add_soggetto", "archivio.add_filecaricato",
        )
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

    def apri_indagine(self, utente=None, titolo="Operazione Tramontana"):
        return servizi.apri_indagine(utente or self.anna, titolo)


class ArchivioTest(ConUtenti):
    """Parte 1: faldoni, fascicoli, indagini e visibilità."""

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


def un_file(nome, contenuto=b"contenuto"):
    return SimpleUploadedFile(nome, contenuto)


def uno_zip(voci, nome="carico.zip"):
    memoria = io.BytesIO()
    with zipfile.ZipFile(memoria, "w", zipfile.ZIP_DEFLATED) as archivio:
        for percorso, contenuto in voci:
            archivio.writestr(percorso, contenuto)
    return SimpleUploadedFile(nome, memoria.getvalue())


class CaricamentoTest(ConUtenti):
    """Parte 2: fascicolo di caricamento, file, metadati, soggetti dichiarati, conferma."""

    def setUp(self):
        self._cartella = tempfile.TemporaryDirectory()
        self.addCleanup(self._cartella.cleanup)
        impostazioni = override_settings(ARCHIVIO_DEPOSITO=self._cartella.name)
        impostazioni.enable()
        self.addCleanup(impostazioni.disable)

    def nel_deposito(self):
        return [p for p in caricamento.cartella_deposito().rglob("*") if p.is_file()]

    def nuovo(self, utente=None, indagine=None, titolo="Verbale del 3 marzo"):
        return caricamento.nuovo(utente or self.anna, titolo, indagine)

    # ---- nascita e visibilità ------------------------------------------
    def test_un_caricamento_nasce_in_bozza_dal_faldone(self):
        risposta = self.pagina(self.anna, "faldone", models.CARICAMENTI, azione="nuovo_caricamento", titolo="Verbale")
        fascicolo = Fascicolo.objects.get()
        self.assertRedirects(risposta, reverse("archivio:fascicolo", args=[fascicolo.pk]))
        self.assertEqual((fascicolo.stato, fascicolo.faldone.codice), (models.BOZZA, models.CARICAMENTI))
        self.assertTrue(hasattr(fascicolo, "caricamento"))
        self.assertContains(self.pagina(self.anna, "fascicolo", fascicolo.pk), "Aggiungi file")
        # chi consulta soltanto vede il caricamento generale ma non gli strumenti per modificarlo
        scheda = self.pagina(self.lettore, "fascicolo", fascicolo.pk)
        self.assertNotContains(scheda, "Aggiungi file")
        self.pagina(self.lettore, "faldone", models.CARICAMENTI, azione="nuovo_caricamento", titolo="Non dovrei")
        self.assertEqual(Fascicolo.objects.count(), 1)

    def test_un_caricamento_riservato_lo_vede_solo_chi_e_nell_indagine(self):
        indagine = self.apri_indagine()
        self.pagina(
            self.anna, "faldone", models.CARICAMENTI,
            azione="nuovo_caricamento", titolo="Documenti riservati", indagine=indagine.pk,
        )
        fascicolo = Fascicolo.objects.get(faldone__codice=models.CARICAMENTI)
        self.assertEqual(fascicolo.riservato_a, indagine)
        caricamento.aggiungi_file(fascicolo, self.anna, [un_file("fattura.pdf")])
        riga = FileCaricato.objects.get()
        for altro in (self.bruno, self.lettore, self.capo):
            self.assertEqual(self.pagina(altro, "fascicolo", fascicolo.pk).status_code, 404, altro.username)
            self.assertEqual(self.pagina(altro, "file", riga.pk).status_code, 404, altro.username)
            self.assertEqual(self.pagina(altro, "scarica", riga.pk).status_code, 404, altro.username)
            self.assertNotContains(self.pagina(altro, "faldone", models.CARICAMENTI), "riservati")
        # non si riserva un caricamento a un'indagine altrui
        with self.assertRaises(caricamento.NonAmmesso):
            caricamento.nuovo(self.bruno, "Curiosità", indagine)
        # e chi vede ma non è nell'indagine non può nemmeno aggiungervi file
        with self.assertRaises(caricamento.NonAmmesso):
            caricamento.aggiungi_file(fascicolo, self.bruno, [un_file("x.pdf")])

    # ---- file -----------------------------------------------------------
    def test_sottocartelle_omonimi_e_doppioni(self):
        fascicolo = self.nuovo()
        self.client.force_login(self.anna)
        risposta = self.client.post(reverse("archivio:fascicolo", args=[fascicolo.pk]), {
            "azione": "carica",
            "cartella": [un_file("fattura.pdf", b"marzo"), un_file("fattura.pdf", b"aprile"), un_file("copia.pdf", b"marzo")],
            "percorso_cartella": ["carico/marzo/fattura.pdf", "carico/aprile/fattura.pdf", "carico/copia.pdf"],
        })
        self.assertEqual(risposta.status_code, 200)
        self.assertEqual(risposta.context["resoconto"]["aggiunti"], 3)
        percorsi = set(fascicolo.file.values_list("percorso_originale", flat=True))
        self.assertEqual(percorsi, {"carico/marzo/fattura.pdf", "carico/aprile/fattura.pdf", "carico/copia.pdf"})
        # stesso contenuto in due percorsi: due righe, una sola copia nel deposito, e viene segnalato
        self.assertEqual(len(self.nel_deposito()), 2)
        self.assertEqual(len(caricamento.doppioni(fascicolo)), 1)
        self.assertContains(risposta, "stesso contenuto di un altro file")

        # ricaricare lo stesso file allo stesso percorso non duplica; con contenuto diverso si tiene con un numero
        esito = caricamento.aggiungi_file(
            fascicolo, self.anna, [un_file("a", b"marzo"), un_file("b", b"corretta")],
            ["carico/marzo/fattura.pdf", "carico/marzo/fattura.pdf"],
        )
        self.assertEqual((esito["presenti"], esito["rinominati"], esito["aggiunti"]), (1, 1, 0))
        self.assertTrue(fascicolo.file.filter(percorso_originale="carico/marzo/fattura (2).pdf").exists())

        # l'originale si scarica identico, con il suo nome
        riga = fascicolo.file.get(percorso_originale="carico/aprile/fattura.pdf")
        scaricato = self.pagina(self.anna, "scarica", riga.pk)
        self.assertEqual(b"".join(scaricato.streaming_content), b"aprile")
        self.assertIn("fattura.pdf", scaricato["Content-Disposition"])

    def test_percorsi_pericolosi_e_file_troppo_grandi_sono_rifiutati(self):
        fascicolo = self.nuovo()
        with override_settings(ARCHIVIO_MASSIMO_BYTE_PER_FILE=10):
            esito = caricamento.aggiungi_file(
                fascicolo, self.anna,
                [un_file("a", b"ok"), un_file("b", b"x"), un_file("c", b"y" * 50), un_file("d.rar", b"z")],
                ["buono.txt", "../../etc/passwd", "grande.bin", "d.rar"],
            )
        self.assertEqual(esito["aggiunti"], 1)
        self.assertEqual(
            dict(esito["rifiutati"]),
            {
                "../../etc/passwd": "percorso non ammesso",
                "grande.bin": "supera la dimensione massima per file",
                "d.rar": "tipo di archivio non gestito: usare un file ZIP",
            },
        )
        self.assertEqual(len(self.nel_deposito()), 1)  # del file troppo grande non resta nulla

    def test_uno_zip_viene_aperto_con_i_suoi_limiti(self):
        fascicolo = self.nuovo()
        esito = caricamento.aggiungi_file(fascicolo, self.anna, [uno_zip([
            ("2025/marzo/fattura.pdf", b"uno"), ("2025/aprile/fattura.pdf", b"due"),
            ("../fuori.txt", b"x"), ("annidato.zip", b"x"),
        ])])
        self.assertEqual(esito["aggiunti"], 2)
        self.assertEqual({nome for nome, _ in esito["rifiutati"]}, {"../fuori.txt", "annidato.zip"})
        # lo ZIP non si conserva: restano solo i file che conteneva
        self.assertEqual(
            set(fascicolo.file.values_list("percorso_originale", flat=True)),
            {"2025/marzo/fattura.pdf", "2025/aprile/fattura.pdf"},
        )
        with override_settings(ARCHIVIO_ZIP_MASSIMO_FILE=1):
            troppi = caricamento.aggiungi_file(fascicolo, self.anna, [uno_zip([("a.txt", b"1"), ("b.txt", b"2")])])
        self.assertEqual(troppi["aggiunti"], 0)
        self.assertIn("il massimo è 1", troppi["rifiutati"][0][1])
        rotto = caricamento.aggiungi_file(fascicolo, self.anna, [un_file("finto.zip", b"non sono uno zip")])
        self.assertIn("non è un archivio ZIP", rotto["rifiutati"][0][1])
        self.assertEqual(fascicolo.file.count(), 2)

    # ---- metadati e soggetti -------------------------------------------
    def test_i_file_ereditano_i_metadati_finche_non_ne_hanno_di_propri(self):
        fascicolo = self.nuovo()
        caricamento.aggiungi_file(fascicolo, self.anna, [un_file("a.pdf", b"a"), un_file("b.pdf", b"b")])
        a, b = fascicolo.file.order_by("percorso_originale")
        fattura = TipoDocumento.objects.get(codice="FATTURA")
        self.pagina(
            self.anna, "fascicolo", fascicolo.pk, azione="metadati", provenienza="Sopralluogo del 3 marzo",
            natura="documenti", tipo_documento=fattura.pk, periodo_dal="2025-01-01", periodo_al="2025-03-31", note="n",
        )
        effettivi = caricamento.metadati_effettivi(a)
        self.assertEqual(effettivi["provenienza"], ("Sopralluogo del 3 marzo", True))
        self.assertEqual(effettivi["tipo_documento"], (fattura, True))
        # il file b ha un tipo proprio: quello cambia, il resto continua a ereditare
        ddt = TipoDocumento.objects.get(codice="DDT")
        self.pagina(self.anna, "file", b.pk, azione="metadati", tipo_documento=ddt.pk)
        b.refresh_from_db()
        effettivi = caricamento.metadati_effettivi(b)
        self.assertEqual(effettivi["tipo_documento"], (ddt, False))
        self.assertEqual(effettivi["provenienza"], ("Sopralluogo del 3 marzo", True))
        # correggere il caricamento arriva a chi eredita
        self.pagina(self.anna, "fascicolo", fascicolo.pk, azione="metadati", provenienza="Sopralluogo del 4 marzo")
        b = FileCaricato.objects.get(pk=b.pk)  # riletto: l'oggetto di prima ricorda i metadati vecchi
        self.assertEqual(caricamento.metadati_effettivi(b)["provenienza"][0], "Sopralluogo del 4 marzo")
        self.assertContains(self.pagina(self.anna, "file", b.pk), "proprio del file")
        # valori non ammessi
        errata = self.pagina(self.anna, "fascicolo", fascicolo.pk, azione="metadati", periodo_dal="2025-05-01", periodo_al="2025-01-01")
        self.assertContains(errata, "finisce prima di cominciare")
        with self.assertRaises(caricamento.NonAmmesso):
            caricamento.salva_metadati(fascicolo.caricamento, self.anna, {"natura": "inventata"}, TipoDocumento.objects.all())

    def test_i_campi_coe_principale_collegati_ed_ereditarieta(self):
        fascicolo = self.nuovo()
        caricamento.aggiungi_file(fascicolo, self.anna, [un_file("a.pdf", b"a"), un_file("b.pdf", b"b")])
        a, b = fascicolo.file.order_by("percorso_originale")
        for valore in ("SM 12345", "54321"):
            self.pagina(self.anna, "fascicolo", fascicolo.pk, azione="coe_aggiungi", tipo=self.coe.pk, valore=valore)
        principale, collegato = SoggettoDichiarato.objects.order_by("pk")
        self.assertEqual((principale.principale, principale.valore_normalizzato), (True, "12345"))
        self.assertFalse(collegato.principale)
        self.assertTrue(principale.soggetto.provvisorio)  # creato in anagrafica perché non c'era
        # un valore scritto male e un doppione non entrano
        self.assertContains(
            self.pagina(self.anna, "fascicolo", fascicolo.pk, azione="coe_aggiungi", tipo=self.coe.pk, valore="12"),
            "non è un valore valido",
        )
        self.pagina(self.anna, "fascicolo", fascicolo.pk, azione="coe_aggiungi", tipo=self.coe.pk, valore="COE 12345")
        self.assertEqual(SoggettoDichiarato.objects.count(), 2)
        # i file ereditano; un file con un soggetto proprio non eredita più
        self.assertEqual(caricamento.soggetti_effettivi(a), ([principale, collegato], True))
        self.pagina(self.anna, "file", b.pk, azione="coe_aggiungi", tipo=self.coe.pk, valore="77777")
        propri, ereditati = caricamento.soggetti_effettivi(b)
        self.assertEqual(([s.valore_normalizzato for s in propri], ereditati), (["77777"], False))
        # cambiare il principale; tolto il principale, lo diventa il primo rimasto
        self.pagina(self.anna, "fascicolo", fascicolo.pk, azione="coe_principale", riga=collegato.pk)
        self.assertEqual(caricamento.soggetti_effettivi(a)[0][0], collegato)
        self.pagina(self.anna, "fascicolo", fascicolo.pk, azione="coe_togli", riga=collegato.pk)
        principale.refresh_from_db()
        self.assertTrue(principale.principale)

    # ---- conferma, eliminazione, annullamento --------------------------
    def test_la_conferma_consegna_i_file_e_chiude_le_modifiche(self):
        fascicolo = self.nuovo()
        vuoto = self.pagina(self.anna, "fascicolo", fascicolo.pk, azione="conferma")
        self.assertContains(vuoto, "non contiene file")
        caricamento.aggiungi_file(fascicolo, self.anna, [un_file("a.pdf", b"a")])
        riga = FileCaricato.objects.get()
        self.assertEqual(riga.stato, models.FILE_BOZZA)
        self.pagina(self.anna, "fascicolo", fascicolo.pk, azione="conferma")
        fascicolo.refresh_from_db()
        riga.refresh_from_db()
        self.assertEqual((fascicolo.stato, riga.stato), (models.CONFERMATO, models.FILE_RICEVUTO))
        # nelle pagine si mostra a che punto sono i file, non "confermato"
        self.assertEqual(caricamento.avanzamento([fascicolo]), {fascicolo.pk: "1 in attesa di elaborazione"})
        self.assertContains(self.pagina(self.anna, "faldone", models.CARICAMENTI), "1 in attesa di elaborazione")
        FileCaricato.objects.filter(pk=riga.pk).update(stato=models.FILE_ELABORATO)
        self.assertEqual(caricamento.avanzamento([fascicolo]), {fascicolo.pk: "elaborato"})
        self.assertContains(self.pagina(self.anna, "fascicolo", fascicolo.pk), "<strong>elaborato</strong>")
        FileCaricato.objects.filter(pk=riga.pk).update(stato=models.FILE_RICEVUTO)
        # dopo la conferma: niente file nuovi, niente metadati, niente eliminazione
        for operazione in (
            lambda: caricamento.aggiungi_file(fascicolo, self.anna, [un_file("b.pdf")]),
            lambda: caricamento.salva_metadati(fascicolo.caricamento, self.anna, {}, TipoDocumento.objects.all()),
            lambda: caricamento.dichiara_soggetto(fascicolo, self.anna, self.coe, "12345"),
            lambda: caricamento.togli_file(riga, self.anna),
            lambda: caricamento.elimina_bozza(fascicolo, self.anna),
        ):
            with self.assertRaises(caricamento.NonAmmesso):
                operazione()
        self.assertNotContains(self.pagina(self.anna, "fascicolo", fascicolo.pk), "Aggiungi file")
        # si può solo annullare: i file restano, in stato annullato, e resta la traccia
        self.pagina(self.anna, "fascicolo", fascicolo.pk, azione="annulla")
        fascicolo.refresh_from_db()
        riga.refresh_from_db()
        self.assertEqual((fascicolo.stato, riga.stato), (models.ANNULLATO, models.FILE_ANNULLATO))
        self.assertEqual(len(self.nel_deposito()), 1)
        self.assertEqual(
            list(Evento.objects.filter(fascicolo=fascicolo).order_by("pk").values_list("azione", flat=True)),
            ["creato", "file aggiunti", "confermato", "annullato"],
        )

    def test_una_bozza_si_elimina_davvero_ma_non_i_contenuti_usati_altrove(self):
        primo, secondo = self.nuovo(titolo="Primo"), self.nuovo(titolo="Secondo")
        caricamento.aggiungi_file(primo, self.anna, [un_file("comune.pdf", b"comune"), un_file("solo.pdf", b"solo")])
        caricamento.aggiungi_file(secondo, self.anna, [un_file("altro/comune.pdf", b"comune")])
        self.assertEqual(len(self.nel_deposito()), 2)
        risposta = self.pagina(self.anna, "fascicolo", primo.pk, azione="elimina")
        self.assertRedirects(risposta, reverse("archivio:faldone", args=[models.CARICAMENTI]))
        self.assertFalse(Fascicolo.objects.filter(pk=primo.pk).exists())
        # il contenuto usato anche dal secondo caricamento resta; l'altro sparisce dal deposito
        self.assertEqual(len(self.nel_deposito()), 1)
        self.assertEqual(self.pagina(self.anna, "scarica", secondo.file.get().pk).status_code, 200)
        self.assertTrue(Evento.objects.filter(azione="bozza eliminata", fascicolo__isnull=True).exists())
        # togliere un singolo file dalla bozza
        riga = secondo.file.get()
        self.pagina(self.anna, "file", riga.pk, azione="togli_file")
        self.assertEqual((secondo.file.count(), len(self.nel_deposito())), (0, 0))


class IngressoTest(SimpleTestCase):
    """Controlli su ciò che arriva da fuori, senza database."""

    def test_i_percorsi_vengono_resi_innocui_o_rifiutati(self):
        self.assertEqual(ingresso.pulisci_percorso("2025\\marzo\\fattura.pdf"), "2025/marzo/fattura.pdf")
        self.assertEqual(ingresso.pulisci_percorso("/assoluto//./x.pdf"), "assoluto/x.pdf")
        for cattivo in ("../x", "a/../../x", "", "/", "C:/x", "a\x00b", "x" * 600):
            self.assertIsNone(ingresso.pulisci_percorso(cattivo), cattivo)

    def test_il_deposito_salva_una_volta_sola_e_non_lascia_residui(self):
        with tempfile.TemporaryDirectory() as cartella:
            prima, _ = deposito.salva(cartella, [b"ciao ", b"mondo"])
            seconda, dimensione = deposito.salva(cartella, [b"ciao mondo"])
            self.assertEqual((prima, dimensione), (seconda, 10))
            self.assertEqual(deposito.percorso(cartella, prima).read_bytes(), b"ciao mondo")
            with self.assertRaises(deposito.TroppoGrande):
                deposito.salva(cartella, [b"x" * 10, b"y" * 10], limite=15)
            import pathlib

            self.assertEqual(len([p for p in pathlib.Path(cartella).rglob("*") if p.is_file()]), 1)


class MigrazioniTest(TestCase):
    def test_la_migrazione_scritta_a_mano_coincide_con_i_modelli(self):
        try:
            call_command("makemigrations", "archivio", check=True, dry_run=True, stdout=StringIO())
        except SystemExit:
            self.fail("models.py e migrations/ non coincidono: eseguire 'python manage.py makemigrations archivio'.")
