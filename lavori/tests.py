"""Prove dei lavori lanciati dall'interfaccia."""
from io import StringIO
from unittest import mock

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from lavori import servizi
from lavori.models import FALLITO, FINITO, IN_CORSO, RICHIESTO, Esecutore, Lavoro
from soggetti.models import DatiPerPeriodo

CSV = "coe;periodo;denominazione;ateco;dipendenti;fatturato\n10000;2025;Alfa S.r.l.;47.26;D0;F3\n20000;2025;Beta S.r.l.;62.01;D2;F2\n1;2025;Sbagliata;47;D0;F1\n"


def con_diritti(nome, *codici):
    utente = get_user_model().objects.create_user(nome, password="x")
    for codice in codici:
        utente.user_permissions.add(Permission.objects.get(content_type__app_label="lavori", codename=codice))
    return utente


class LavoriTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("carica_decodifiche", stdout=StringIO())
        call_command("carica_regole", stdout=StringIO())
        cls.ada = con_diritti("ada", "lancia_lavori", "view_lavoro")   # amministratore
        cls.bruno = con_diritti("bruno")

    def test_un_lavoro_si_chiede_una_volta_e_lo_esegue_il_processo(self):
        lavoro, nuovo = servizi.richiedi("calcola_indici", self.ada)
        self.assertEqual((nuovo, lavoro.stato), (True, RICHIESTO))
        # un secondo clic non ne avvia un altro, né mentre aspetta né mentre è in corso
        self.assertEqual(servizi.richiedi("calcola_indici", self.ada), (lavoro, False))
        preso = servizi.prendi()
        self.assertEqual((preso, preso.stato), (lavoro, IN_CORSO))
        self.assertEqual(servizi.richiedi("calcola_indici", self.ada), (lavoro, False))
        self.assertIsNone(servizi.prendi())
        servizi.esegui(preso)
        lavoro.refresh_from_db()
        self.assertEqual(lavoro.stato, FINITO)
        self.assertIn("Nessun dato reale", lavoro.esito)
        self.assertIsNotNone(lavoro.durata)
        # finito quello, se ne può chiedere un altro
        self.assertTrue(servizi.richiedi("calcola_indici", self.ada)[1])
        with self.assertRaises(ValueError):
            servizi.richiedi("inventato", self.ada)

    def test_un_errore_diventa_un_lavoro_fallito_e_non_ferma_gli_altri(self):
        servizi.richiedi("allinea_denominazioni", self.ada)
        servizi.richiedi("dati_reali", self.ada)

        def guasto(lavoro):
            raise RuntimeError("guasto di prova")

        def senza_libreria(lavoro):
            raise ModuleNotFoundError("No module named 'torch'", name="torch")

        finti = dict(
            servizi.TIPI, allinea_denominazioni=servizi.TIPI["allinea_denominazioni"]._replace(funzione=guasto),
            calcola_gnn=servizi.TIPI["calcola_gnn"]._replace(funzione=senza_libreria),
        )
        with mock.patch.object(servizi, "TIPI", finti), self.assertLogs("lavori.servizi", level="ERROR"):
            servizi.richiedi("calcola_gnn", self.ada)
            call_command("esegui_lavori", una_volta=True, stdout=StringIO())
        stati = {lavoro.tipo: (lavoro.stato, lavoro.esito) for lavoro in Lavoro.objects.all()}
        self.assertEqual(stati["allinea_denominazioni"][0], FALLITO)
        self.assertTrue(stati["allinea_denominazioni"][1].startswith("Il lavoro non è riuscito"))
        self.assertTrue(stati["allinea_denominazioni"][1].endswith("Dettaglio tecnico: RuntimeError: guasto di prova"))
        self.assertEqual(stati["dati_reali"][0], FINITO)
        self.assertEqual(stati["calcola_gnn"][0], FALLITO)
        self.assertIn("manca la libreria 'torch'", stati["calcola_gnn"][1])
        # il processo ha detto di essere vivo, e all'avvio chiude i lavori interrotti da uno spegnimento
        self.assertEqual(Esecutore.objects.count(), 1)
        self.assertEqual(servizi.tipi_serviti(), set(servizi.TIPI))
        Lavoro.objects.create(tipo="elabora_file", stato=IN_CORSO)
        call_command("esegui_lavori", una_volta=True, tipi="elabora_file", stdout=StringIO())
        self.assertIn("Interrotto", Lavoro.objects.get(tipo="elabora_file").esito)

    def test_un_processo_esegue_solo_i_tipi_che_gli_sono_stati_dati(self):
        servizi.richiedi("calcola_indici", self.ada)
        servizi.richiedi("dati_reali", self.ada)
        call_command("esegui_lavori", una_volta=True, tipi="dati_reali", stdout=StringIO())
        self.assertEqual(
            {lavoro.tipo: lavoro.stato for lavoro in Lavoro.objects.all()}, {"calcola_indici": RICHIESTO, "dati_reali": FINITO}
        )
        self.assertEqual(servizi.tipi_serviti(), {"dati_reali"})

    def test_dall_interfaccia_si_importa_il_csv_e_si_calcolano_gli_indici(self):
        self.client.force_login(self.bruno)
        self.assertEqual(self.client.post(reverse("lavori:richiedi"), {"tipo": "calcola_indici"}).status_code, 403)
        self.assertEqual(self.client.get(reverse("lavori:elenco")).status_code, 403)

        self.client.force_login(self.ada)
        file = SimpleUploadedFile("anagrafica.csv", CSV.encode("utf-8"), content_type="text/csv")
        risposta = self.client.post(
            reverse("lavori:richiedi"), {"tipo": "importa_anagrafica", "file": file, "fonte": "prova", "ritorno": "/"}
        )
        self.assertRedirects(risposta, "/", fetch_redirect_response=False)
        self.client.post(reverse("lavori:richiedi"), {"tipo": "calcola_indici"})
        self.client.post(reverse("lavori:richiedi"), {"tipo": "calcola_indici"})   # doppio clic
        self.assertEqual(Lavoro.objects.count(), 2)
        call_command("esegui_lavori", una_volta=True, stdout=StringIO())

        importazione, indici = Lavoro.objects.get(tipo="importa_anagrafica"), Lavoro.objects.get(tipo="calcola_indici")
        self.assertEqual((importazione.stato, importazione.ingresso, importazione.nome_ingresso), (FINITO, "", "anagrafica.csv"))
        self.assertIn("Righe nuove: 2; aggiornate: 0; rifiutate: 1.", importazione.esito)
        self.assertEqual(DatiPerPeriodo.objects.filter(fonte="prova").count(), 2)
        self.assertEqual(indici.stato, FINITO)
        self.assertIn("2 società, 1 sopra soglia", indici.esito)

        # le pagine mostrano l'esito: l'elenco e la pagina iniziale, con la stessa sequenza
        elenco = self.client.get(reverse("lavori:elenco"))
        self.assertContains(elenco, "Righe nuove: 2")
        self.assertContains(elenco, "Calcola la GNN (dati simulati)")
        inizio = self.client.get(reverse("home")).content.decode()
        # nell'ordine in cui vanno fatti, con i passi che fa una persona
        attesi = ["Caricare i file", "Elabora i file in attesa", "Rivedere e confermare i documenti",
                  "Importa l&#x27;anagrafica da CSV", "Aggiorna il grafo e calcola gli indici",
                  "Calcola la GNN (dati simulati)", "Riallinea le denominazioni"]
        posizioni = [inizio.index(f">{testo}<") for testo in attesi]
        self.assertEqual(posizioni, sorted(posizioni))
        self.assertEqual(inizio.count('name="tipo"'), len(servizi.TIPI))   # ogni pulsante una volta sola
        # richieste non valide: tipo sconosciuto, file mancante, file non di testo
        for dati in ({"tipo": "inventato"}, {"tipo": "importa_anagrafica"},
                     {"tipo": "importa_anagrafica", "file": SimpleUploadedFile("x.csv", b"\xff\xfe\x00")},
                     {"tipo": "elabora_file", "massimo": "tanti"}):
            self.client.post(reverse("lavori:richiedi"), dati)
        self.assertEqual(Lavoro.objects.count(), 2)

    def test_chi_non_puo_lanciare_non_vede_i_pulsanti(self):
        self.client.force_login(self.bruno)
        self.assertNotContains(self.client.get(reverse("home")), "calcola gli indici")

    def test_la_sequenza_contiene_ogni_lavoro_una_volta_e_numera_solo_i_dati_reali(self):
        gruppi = servizi.per_le_pagine()
        self.assertEqual([gruppo["codice"] for gruppo in gruppi], [servizi.REALI, servizi.SIMULATA, servizi.SERVIZIO])
        tipi = [voce["tipo"] for gruppo in gruppi for voce in gruppo["voci"] if voce["tipo"]]
        self.assertEqual(sorted(tipi), sorted(servizi.TIPI))
        self.assertEqual({servizi.TIPI[tipo].gruppo for tipo in tipi if tipo in ("calcola_gnn", "spiegazioni")}, {servizi.SIMULATA})
        for gruppo in gruppi:
            for voce in gruppo["voci"]:
                if voce["tipo"]:
                    self.assertEqual(servizi.TIPI[voce["tipo"]].gruppo, gruppo["codice"])
        self.assertEqual([voce["passo"] for voce in gruppi[0]["voci"]], [1, 2, 3, 4, 5])
        self.assertEqual([voce["tipo"] for voce in gruppi[0]["voci"]], [None, "elabora_file", None, "importa_anagrafica", "calcola_indici"])
        self.assertTrue(all(voce["passo"] is None for gruppo in gruppi[1:] for voce in gruppo["voci"]))

    def test_l_amministratore_sceglie_che_cosa_ammettere_oltre_ai_documenti_confermati(self):
        self.client.force_login(self.ada)
        pagina = self.client.get(reverse("home"))
        self.assertContains(pagina, 'name="ammette_documenti_non_confermati"', count=2)   # indici e fotografia
        self.assertNotContains(pagina, 'name="ammette_entita_fuori_catalogo"')            # non cambia il grafo
        # una casella non spuntata vale "no"; le letture incomplete non hanno senso senza i non confermati
        self.client.post(reverse("lavori:richiedi"), {"tipo": "calcola_indici", "criteri_mostrati": "1", "ammette_letture_incomplete": "si"})
        ammette = Lavoro.objects.get(tipo="calcola_indici").parametri["ammette"]
        self.assertEqual((ammette["documenti_non_confermati"], ammette["letture_incomplete"]), (False, False))
        self.client.post(reverse("lavori:richiedi"), {
            "tipo": "dati_reali", "criteri_mostrati": "1", "ammette_documenti_non_confermati": "si", "ammette_letture_incomplete": "si",
        })
        ammette = Lavoro.objects.get(tipo="dati_reali").parametri["ammette"]
        self.assertEqual((ammette["documenti_non_confermati"], ammette["letture_incomplete"]), (True, True))
        # i due lavori si eseguono con i criteri scelti (qui non ci sono dati: lo dicono)
        call_command("esegui_lavori", una_volta=True, stdout=StringIO())
        self.assertEqual(set(Lavoro.objects.values_list("stato", flat=True)), {FINITO})

    def test_la_fotografia_da_sola_avverte_che_non_e_in_uso(self):
        from indici import importazione

        importazione.importa(CSV, "prova")
        servizi.richiedi("dati_reali", self.ada)
        lavoro = servizi.esegui(servizi.prendi())
        self.assertEqual(lavoro.stato, FINITO)
        self.assertIn("Chat e mappa non la usano ancora", lavoro.esito)


class MigrazioniTest(TestCase):
    def test_la_migrazione_scritta_a_mano_coincide_con_i_modelli(self):
        try:
            call_command("makemigrations", "lavori", check=True, dry_run=True, stdout=StringIO())
        except SystemExit:
            self.fail("models.py e migrations/ non coincidono: eseguire 'python manage.py makemigrations lavori'.")
