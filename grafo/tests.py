"""
PROVA DI CABLAGGIO dell'app grafo: attraversa scrittura, database, libreria,
strumenti e report con un modello finto.

    python manage.py test grafo

Non richiede PyTorch, pyvis né la libreria mcp. Se un filo fra le parti si
stacca, o una regola di compatibilità viene violata, qui si vede.
"""
import ast
import pathlib
import random
import sys
from io import StringIO

from django.core.management import call_command
from django.test import SimpleTestCase, TestCase

from grafo import contratto, interrogazione, mappa, scrittura
from grafo.models import Esecuzione, InfoArchivio, Spiegazione, VersioneDati

CARTELLA_APP = pathlib.Path(__file__).resolve().parent
N_NODI = 300
T = contratto.NUM_TIPI
TIPI = contratto.TIPI_IRREGOLARITA
SOGLIE = [0.5, 0.6, 0.4, 0.7]
ELENCO_AZIENDE = {
    "7": {"nome_Azienda": "L'Oro <srl>", "nr_iscrizione_reg_società": "X1"},
    "3": {"nome_Azienda": "Rossi Costruzioni srl", "nr_iscrizione_reg_società": "R-0003"},
    "4": {"nome_Azienda": "Rossi Trasporti spa", "nr_iscrizione_reg_società": "R-0004"},
    "20": {"nome_Azienda": "Beta Legnami", "nr_iscrizione_reg_società": "B-0020"},
}
DIZIONARIO = {
    "5": "Variazioni repentine del CdA",
    "400": "Relazioni con paesi offshore",
    "401": "Fatturato dichiarato",
}


def dati_finti(seme=7):
    """Stessa forma dei dati prodotti da calcolo.py, ma generati senza modello."""
    g = random.Random(seme)
    archi = [[], []]
    while len(archi[0]) < 900:
        a, b = g.randrange(N_NODI), g.randrange(N_NODI)
        if a != b:
            archi[0].append(a)
            archi[1].append(b)
    ispezionati = g.sample(range(N_NODI), 90)
    ha_etichetta = [n in set(ispezionati) for n in range(N_NODI)]
    y = [[0] * T for _ in range(N_NODI)]
    for i, nodo in enumerate(ispezionati[:20]):
        y[nodo][i % T] = 1
    punteggi = [[g.random() for _ in range(T)] for _ in range(N_NODI)]
    return archi, ha_etichetta, y, punteggi


def carica(seme=7):
    """Parte 'calcolo' con modello finto: fotografia dei dati + esecuzione."""
    archi, ha_etichetta, y, punteggi = dati_finti(seme)
    versione_dati, soggetti = scrittura.registra_dati_simulati(
        archi, ha_etichetta, y, ELENCO_AZIENDE, DIZIONARIO
    )
    esecuzione = scrittura.registra_esecuzione(
        versione_dati, soggetti, punteggi, SOGLIE, {"esempio": {"pr_auc": float("nan")}}
    )
    return esecuzione, soggetti, archi, ha_etichetta, y, punteggi


def spiegazione_finta(soggetto, indice_tipo, features, relazioni=(), **altro):
    documento = {
        "schema": contratto.SCHEMA_SPIEGAZIONE,
        "soggetto": soggetto,
        "tipo_irregolarita": TIPI[indice_tipo],
        "features": features,
        "relazioni": [[[a, b], importanza] for a, b, importanza in relazioni],
        "impatto_testo": 0.1,
        "impatto_strutturati": 0.2,
    }
    documento.update(altro)
    return documento


class ConArchivio(TestCase):
    """Base: un archivio con una fotografia dei dati e un'esecuzione finta."""

    @classmethod
    def setUpTestData(cls):
        cls.esecuzione, cls.soggetti, cls.archi, cls.ha_etichetta, cls.y, cls.punteggi = carica()
        # s[i] = chiave interna del soggetto che occupa il nodo i
        cls.vicini = {s: set() for s in cls.soggetti}
        for a, b in zip(*cls.archi):
            cls.vicini[cls.soggetti[a]].add(cls.soggetti[b])
            cls.vicini[cls.soggetti[b]].add(cls.soggetti[a])
        cls.nodo_di = {s: n for n, s in enumerate(cls.soggetti)}

    def setUp(self):
        # La libreria ricorda l'esecuzione in uso: ogni prova riparte da zero
        interrogazione.chiudi()
        self.addCleanup(interrogazione.chiudi)

    def s(self, nodo):
        return self.soggetti[nodo]


class LettureTest(ConArchivio):

    def test_vicini_diretti_e_a_due_passi(self):
        for soggetto in self.soggetti[::5]:
            self.assertEqual(interrogazione.vicini_diretti(soggetto), self.vicini[soggetto])
            attesi = set()
            for vicino in self.vicini[soggetto]:
                attesi |= self.vicini[vicino]
            attesi -= self.vicini[soggetto] | {soggetto}
            self.assertEqual(interrogazione.vicini_a_due_passi(soggetto), attesi)

    def test_classifica_coincide_con_il_calcolo_diretto(self):
        for tipo in (None, *TIPI):
            for popolazione in contratto.POPOLAZIONI:
                candidati = [
                    n for n in range(N_NODI)
                    if popolazione == "tutte" or self.ha_etichetta[n] == (popolazione == "ispezionate")
                ]
                if tipo is None:
                    valore = {n: max(self.punteggi[n]) for n in candidati}
                else:
                    valore = {n: self.punteggi[n][TIPI.index(tipo)] for n in candidati}
                attesi = [self.s(n) for n in sorted(candidati, key=lambda n: -valore[n])[:7]]
                classifica = interrogazione.classifica_rischio(n=7, tipo=tipo, popolazione=popolazione)
                self.assertEqual([v["nodo"] for v in classifica], attesi, (tipo, popolazione))
                for voce in classifica:
                    nodo = self.nodo_di[voce["nodo"]]
                    quota = 100 * sum(1 for n in candidati if valore[n] < valore[nodo]) / len(candidati)
                    self.assertAlmostEqual(voce["percentile"], quota, places=9)
                    indice = TIPI.index(voce["tipo"])
                    self.assertEqual(voce["sopra_soglia"], self.punteggi[nodo][indice] >= SOGLIE[indice])

    def test_stato_documenti_e_relazioni(self):
        accertato = next(n for n in range(N_NODI) if any(self.y[n]))
        non_ispezionato = next(n for n in range(N_NODI) if not self.ha_etichetta[n])
        self.assertTrue(interrogazione.stato_compliance(self.s(accertato)).startswith("IRREGOLARITÀ ACCERTATE"))
        self.assertTrue(interrogazione.stato_compliance(self.s(non_ispezionato)).startswith("Non ispezionato"))
        self.assertEqual(interrogazione.dati_azienda(self.s(7))["nome"], "L'Oro <srl>")

        a = next(s for s in self.soggetti if self.vicini[s])
        b = sorted(self.vicini[a])[0]
        documenti = interrogazione.documenti_relazione(a, b)
        attesi = sum(1 for x, y in zip(*self.archi) if {self.s(x), self.s(y)} == {a, b})
        self.assertEqual(documenti["numero"], attesi)
        self.assertGreater(documenti["totale"], 0)
        self.assertEqual(interrogazione.relazioni_fra([a, b]), {(min(a, b), max(a, b))})


class NomiEStrumentiTest(ConArchivio):

    def test_le_societa_si_riconoscono_da_nome_numero_e_codici(self):
        attesi = {
            "Beta Legnami": 20, "beta legnami": 20, "legnami": 20, "rossi costruzioni": 3,
            "l'oro": 7, "X1": 7, "b-0020": 20, "SIM-00020": 20,
        }
        for riferimento, nodo in attesi.items():
            self.assertEqual(interrogazione.risolvi_societa(riferimento), (self.s(nodo), None), riferimento)
        numero = self.s(12)
        for riferimento in (numero, str(numero), f"società {numero}"):
            self.assertEqual(interrogazione.risolvi_societa(riferimento), (numero, None))

    def test_un_nome_ambiguo_o_sconosciuto_non_viene_indovinato(self):
        nodo, messaggio = interrogazione.risolvi_societa("Rossi")
        self.assertIsNone(nodo)
        self.assertIn("corrisponde a 2 società", messaggio)
        self.assertIn("Beta Legnami", interrogazione.risolvi_societa("Bata Legnami")[1])
        self.assertIn("non è presente", interrogazione.vicinato(999999999))
        self.assertIn("corrisponde a 2 società", interrogazione.relazione("Rossi", self.s(5)))

    def test_gli_strumenti_sono_quelli_del_contratto_e_rispondono(self):
        self.assertEqual(tuple(interrogazione.STRUMENTI), contratto.NOMI_STRUMENTI)
        for nome, funzione in interrogazione.STRUMENTI.items():
            self.assertEqual(funzione.__name__, nome)  # il server registra il nome della funzione
            self.assertTrue(funzione.__doc__)  # la descrizione è ciò che legge la chat

        etichetta = f"Società {self.s(20)} «Beta Legnami» (iscrizione B-0020)"
        self.assertIn(etichetta, interrogazione.vicinato("Beta Legnami"))
        self.assertIn(etichetta, interrogazione.relazione("Beta Legnami", "Rossi Costruzioni srl"))
        testo = interrogazione.classifica(3)
        self.assertIn("1. Società", testo)
        self.assertIn(f"calcolo {contratto.VERSIONE_CALCOLO} / dati 1", testo)

        self.assertIn("non riconosciuto", interrogazione.classifica(3, tipo="inventato"))
        self.assertIn("fra 1 e", interrogazione.classifica(0))
        self.assertIn("due società diverse", interrogazione.relazione(self.s(1), self.s(1)))

    def test_consulta_a_parole_chiave(self):
        self.assertIn("CLASSIFICA", interrogazione.consulta("Quali sono le 3 aziende più rischiose?"))
        self.assertIn("«Beta Legnami»", interrogazione.consulta("Con chi commercia la Beta Legnami?"))
        self.assertEqual(interrogazione.consulta("Che tempo fa?"), interrogazione.MESSAGGIO_NON_SUPPORTATA)
        uscita = StringIO()
        call_command("grafo_consulta", "Quali", "sono", "le", "3", "aziende", "più", "rischiose?", stdout=uscita)
        self.assertIn("CLASSIFICA", uscita.getvalue())

    def test_spiegazione_mancante_va_in_coda_e_poi_viene_letta(self):
        soggetto, indice_tipo = self.s(11), 2
        self.assertIn("NON ancora calcolata", interrogazione.spiegazione(soggetto, TIPI[indice_tipo]))
        interrogazione.spiegazione(soggetto, TIPI[indice_tipo])  # richiesta ripetuta: nessun doppione
        self.assertEqual(scrittura.richieste_pendenti(self.esecuzione), [(soggetto, indice_tipo)])

        # il processo di calcolo (qui finto) elabora la richiesta
        vicino = sorted(self.vicini[soggetto])[0]
        scrittura.salva_spiegazione(self.esecuzione, spiegazione_finta(
            soggetto, indice_tipo,
            [{"indice": 5, "tipo": "Testuale (NLP)", "descrizione": "prova", "peso": 0.9}],
            [(soggetto, vicino, 0.8)],
        ))
        self.assertEqual(scrittura.richieste_pendenti(self.esecuzione), [])
        testo = interrogazione.spiegazione(soggetto, TIPI[indice_tipo])
        self.assertIn("Indicatore #5", testo)
        self.assertIn("impatto 80.00%", testo)
        self.assertNotIn("NON ancora calcolata", testo)

    def test_gli_indicatori_si_cercano_per_parola(self):
        scrittura.salva_spiegazione(self.esecuzione, spiegazione_finta(self.s(20), 0, [
            {"indice": 400, "tipo": "Strutturata", "descrizione": "Relazioni con paesi offshore", "peso": 0.7},
            {"indice": 5, "tipo": "Testuale (NLP)", "descrizione": "Variazioni repentine del CdA", "peso": 0.2},
        ]))
        testo = interrogazione.indicatore("offshore")
        self.assertIn("Indicatore #400: Relazioni con paesi offshore", testo)
        self.assertIn("«Beta Legnami»", testo)
        self.assertIn("posizione 1", testo)
        self.assertIn("Indicatore #400", interrogazione.indicatore("Paesi OFFSHORE", "Beta Legnami"))
        self.assertIn("Nessun indicatore", interrogazione.indicatore("zzz"))
        self.assertIn("- nessuna", interrogazione.indicatore("fatturato"))
        self.assertIn("Indicatore #400", interrogazione.consulta("Quali aziende hanno l'indicatore sui paesi offshore?"))

    def test_il_report_si_compone_dal_solo_database(self):
        report, bolla = mappa.costruisci_report()
        self.assertIsNotNone(bolla)
        self.assertIn("FASE ISPETTIVA", report)
        self.assertEqual(set(bolla["vicini_1"]), self.vicini[bolla["target"]])
        self.assertIn("L&#x27;Oro &lt;srl&gt;", mappa.genera_nodi_interattivi_html([self.s(7)]))
        _, bolla = mappa.costruisci_report(self.s(20))
        self.assertEqual(bolla["target"], self.s(20))


class VersioniTest(ConArchivio):
    """Regole di COMPATIBILITA.md: versioni che coesistono e lettore tollerante."""

    def test_lo_schema_scritto_dalle_migrazioni_e_quello_dichiarato_dal_codice(self):
        nel_database = InfoArchivio.objects.get(chiave="versione_schema").valore
        self.assertEqual(nel_database, contratto.VERSIONE_SCHEMA)
        self.assertTrue(contratto.compatibile(nel_database, contratto.SCHEMA_RICHIESTO))

    def test_il_lettore_accetta_le_espansioni_e_rifiuta_il_resto(self):
        primo, secondo = contratto.VERSIONE_SCHEMA.split(".")[:2]
        accettati = [f"{primo}.{int(secondo) + 1}", f"{primo}.{int(secondo) + 7}"]
        rifiutati = [f"{int(primo) - 1}.0", f"{int(primo) + 1}.0", "non-una-versione"]
        for valore in accettati:
            InfoArchivio.objects.filter(chiave="versione_schema").update(valore=valore)
            interrogazione.chiudi()
            self.assertTrue(interrogazione.apri(), valore)
        for valore in rifiutati:
            InfoArchivio.objects.filter(chiave="versione_schema").update(valore=valore)
            interrogazione.chiudi()
            with self.assertRaises(contratto.ArchivioIncompatibile, msg=valore):
                interrogazione.apri()

    def test_gli_stessi_dati_non_creano_una_nuova_fotografia(self):
        archi, ha_etichetta, y, _ = dati_finti()
        versione_dati, soggetti = scrittura.registra_dati_simulati(archi, ha_etichetta, y, ELENCO_AZIENDE, DIZIONARIO)
        self.assertEqual(versione_dati.numero, 1)
        self.assertEqual(soggetti, self.soggetti)
        self.assertEqual(VersioneDati.objects.count(), 1)

    def test_dati_nuovi_si_aggiungono_e_i_vecchi_restano_interrogabili(self):
        prima = interrogazione.classifica_rischio(3, popolazione="tutte")
        _, soggetti, _, _, _, punteggi = carica(seme=8)
        self.assertEqual(soggetti, self.soggetti)  # le chiavi dei soggetti non cambiano
        self.assertEqual(VersioneDati.objects.count(), 2)
        self.assertEqual(Esecuzione.objects.count(), 2)

        interrogazione.chiudi()
        self.assertEqual(interrogazione.apri(), f"calcolo {contratto.VERSIONE_CALCOLO} / dati 2")
        migliore = max(range(N_NODI), key=lambda n: max(punteggi[n]))
        self.assertEqual(interrogazione.classifica_rischio(1, popolazione="tutte")[0]["nodo"], self.s(migliore))

        self.assertEqual(interrogazione.apri(numero_dati=1), f"calcolo {contratto.VERSIONE_CALCOLO} / dati 1")
        self.assertEqual(interrogazione.classifica_rischio(3, popolazione="tutte"), prima)

    def test_ripetere_il_calcolo_sulla_stessa_coppia_la_sostituisce(self):
        scrittura.salva_spiegazione(self.esecuzione, spiegazione_finta(self.s(20), 0, [{"indice": 5, "peso": 1.0}]))
        archi, ha_etichetta, y, punteggi = dati_finti()
        versione_dati, soggetti = scrittura.registra_dati_simulati(archi, ha_etichetta, y, ELENCO_AZIENDE, DIZIONARIO)
        scrittura.registra_esecuzione(versione_dati, soggetti, punteggi, SOGLIE, {})
        self.assertEqual(Esecuzione.objects.count(), 1)
        self.assertEqual(Spiegazione.objects.count(), 0)  # le spiegazioni del calcolo sostituito non valgono più

    def test_un_calcolo_non_compatibile_viene_ignorato_ma_si_puo_scegliere(self):
        altra = VersioneDati.objects.create(numero=9, impronta="altra")
        Esecuzione.objects.create(
            versione_calcolo="99.0", versione_dati=altra, versione_codice="x",
            tassonomia=list(TIPI), soglie={}, metriche={},
        )
        self.assertEqual(interrogazione.apri(), f"calcolo {contratto.VERSIONE_CALCOLO} / dati 1")
        self.assertEqual(interrogazione.apri(versione_calcolo="99.0"), "calcolo 99.0 / dati 9")

    def test_i_documenti_json_si_leggono_in_modo_tollerante(self):
        primo, secondo = contratto.SCHEMA_SPIEGAZIONE.split("/")[1].split(".")
        # versione successiva compatibile, con campi che questo codice non conosce: si legge
        scrittura.salva_spiegazione(self.esecuzione, spiegazione_finta(
            self.s(30), 0, [{"indice": 5, "peso": 0.9, "campo_futuro": 1}],
            schema=f"spiegazione/{primo}.{int(secondo) + 1}", campo_aggiunto=[1, 2],
        ))
        self.assertIn("Indicatore #5", interrogazione.spiegazione(self.s(30), TIPI[0]))
        # campi facoltativi mancanti: valori predefiniti, nessun errore
        scrittura.salva_spiegazione(self.esecuzione, {
            "schema": contratto.SCHEMA_SPIEGAZIONE, "soggetto": self.s(31),
            "tipo_irregolarita": TIPI[0], "features": [{"indice": 5}],
        })
        self.assertIn("Indicatore #5", interrogazione.spiegazione(self.s(31), TIPI[0]))
        # versione che TOGLIE qualcosa: non si legge, vale come mancante
        Spiegazione.objects.create(
            esecuzione=self.esecuzione, soggetto_id=self.s(32), tipo=TIPI[0],
            dati=spiegazione_finta(self.s(32), 0, [{"indice": 5}], schema=f"spiegazione/{int(primo) + 1}.0"),
        )
        self.assertIn("NON ancora calcolata", interrogazione.spiegazione(self.s(32), TIPI[0]))
        # chi scrive non può salvare un documento che non si dichiara
        with self.assertRaises(ValueError):
            scrittura.salva_spiegazione(self.esecuzione, {"soggetto": self.s(33), "tipo_irregolarita": TIPI[0]})

    def test_archivio_senza_esecuzioni_viene_rifiutato(self):
        Esecuzione.objects.all().delete()
        with self.assertRaises(contratto.ArchivioIncompatibile):
            interrogazione.apri()


class MigrazioniTest(TestCase):

    def test_le_migrazioni_coincidono_con_i_modelli(self):
        """Se fallisce: models.py è cambiato senza una migrazione (e senza aggiornare lo schema)."""
        try:
            call_command("makemigrations", "grafo", check=True, dry_run=True, stdout=StringIO())
        except SystemExit:
            self.fail(
                "models.py e migrazioni non coincidono: eseguire 'python manage.py makemigrations grafo' "
                "e seguire la lista di controllo di grafo/COMPATIBILITA.md."
            )


class StrutturaTest(SimpleTestCase):
    """Regole che non riguardano i dati: dipendenze fra le parti, registro delle novità."""

    def _importazioni(self, nome_file):
        """Moduli importati da un file: (interni all'app, esterni)."""
        albero = ast.parse((CARTELLA_APP / nome_file).read_text(encoding="utf-8"))
        interni, esterni = set(), set()
        for nodo in ast.walk(albero):
            if isinstance(nodo, ast.ImportFrom) and nodo.level > 0:
                interni |= {nodo.module.split(".")[0]} if nodo.module else {a.name for a in nodo.names}
            elif isinstance(nodo, ast.ImportFrom):
                esterni.add(nodo.module.split(".")[0])
            elif isinstance(nodo, ast.Import):
                esterni |= {a.name.split(".")[0] for a in nodo.names}
        return interni, esterni

    def test_le_dipendenze_vanno_in_una_sola_direzione(self):
        ammesse = {
            "contratto.py": set(),
            "models.py": set(),
            "calcolo_cartella.py": set(),
            "scrittura.py": {"contratto", "models"},
            "calcolo.py": {"contratto", "scrittura", "calcolo_cartella"},
            "interrogazione.py": {"contratto"},
            "server_mcp.py": {"contratto", "interrogazione"},
            "mappa.py": {"contratto", "interrogazione"},
        }
        for nome_file, permesse in ammesse.items():
            interni, _ = self._importazioni(nome_file)
            self.assertLessEqual(interni, permesse, f"{nome_file} importa {interni - permesse}")

    def test_solo_il_calcolo_usa_pytorch_e_il_contratto_non_usa_django(self):
        for nome_file in ("contratto.py", "models.py", "scrittura.py", "interrogazione.py", "server_mcp.py", "mappa.py"):
            _, esterni = self._importazioni(nome_file)
            self.assertFalse(esterni & {"torch", "torch_geometric"}, nome_file)
        self.assertNotIn("django", self._importazioni("contratto.py")[1])
        self.assertNotIn("torch", sys.modules)  # queste prove hanno caricato l'app senza PyTorch

    def test_registro_e_intestazioni_sono_allineati(self):
        sys.path.insert(0, str(CARTELLA_APP))
        try:
            import aggiorna_intestazioni
        finally:
            sys.path.remove(str(CARTELLA_APP))
        versione, _ = aggiorna_intestazioni.leggi_registro()
        self.assertEqual(versione, contratto.VERSIONE_CODICE)
        self.assertEqual(aggiorna_intestazioni.esegui(solo_verifica=True), [])

    def test_le_versioni_dichiarate_sono_coerenti(self):
        self.assertTrue(contratto.compatibile(contratto.VERSIONE_SCHEMA, contratto.SCHEMA_RICHIESTO))
        self.assertTrue(contratto.compatibile(contratto.VERSIONE_CALCOLO, contratto.CALCOLO_ACCETTATO))
        self.assertTrue(contratto.documento_leggibile(
            {"schema": contratto.SCHEMA_SPIEGAZIONE}, "spiegazione", contratto.SPIEGAZIONE_ACCETTATA
        ))
        # la versione scritta dall'ultima migrazione deve essere quella dichiarata dal codice
        ultima = sorted((CARTELLA_APP / "migrations").glob("0*.py"))[-1].read_text(encoding="utf-8")
        self.assertIn(f'VERSIONE_SCHEMA = "{contratto.VERSIONE_SCHEMA}"', ultima)
