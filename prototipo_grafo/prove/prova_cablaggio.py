"""
PROVA DI CABLAGGIO: attraversa tutte le parti del progetto con un modello finto.

    python -m unittest prove.prova_cablaggio -v        (dalla cartella del progetto)

Non richiede PyTorch, pyvis né la libreria mcp. Sostituisce la garanzia che
prima dava il file unico: se un filo fra le parti si stacca, qui si vede.

  scrittura (modello finto) -> database -> interrogazione -> strumenti / report
"""

import ast
import os
import pathlib
import random
import sys
import tempfile
import unittest

RADICE = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RADICE))

import aggiorna_intestazioni  # noqa: E402
from controlli_grafo import contratto, interrogazione, mappa, scrittura  # noqa: E402

PACCHETTO = RADICE / "controlli_grafo"
N_NODI = 300
T = contratto.NUM_TIPI


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
    soglie = [0.5, 0.6, 0.4, 0.7]
    return archi, ha_etichetta, y, punteggi, soglie


class ProvaCablaggio(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.cartella = tempfile.TemporaryDirectory()
        cls.percorso = os.path.join(cls.cartella.name, "prova.sqlite")
        cls.archi, cls.ha_etichetta, cls.y, cls.punteggi, cls.soglie = dati_finti()

        # --- parte "calcolo", con modello finto ---
        conn = scrittura.apri_in_scrittura(cls.percorso)
        scrittura.salva_dati_simulati(
            conn, cls.archi, cls.ha_etichetta, cls.y,
            {"7": {"nome_Azienda": "L'Oro <srl>", "nr_iscrizione_reg_società": "X1"}},
        )
        scrittura.salva_esecuzione(conn, "prova-1", cls.punteggi, cls.soglie, {"esempio": {"pr_auc": 0.3}})
        conn.close()

        # --- parte "interrogazione" ---
        interrogazione.apri(cls.percorso)

        # calcolo diretto, per confronto
        cls.vicini = {n: set() for n in range(N_NODI)}
        for a, b in zip(*cls.archi):
            cls.vicini[a].add(b)
            cls.vicini[b].add(a)

    @classmethod
    def tearDownClass(cls):
        interrogazione.chiudi()
        cls.cartella.cleanup()

    # ------------------------------------------------------------ letture
    def test_vicini_diretti_coincidono_con_il_calcolo_diretto(self):
        for nodo in range(0, N_NODI, 5):
            self.assertEqual(interrogazione.vicini_diretti(nodo), self.vicini[nodo])

    def test_vicini_a_due_passi_coincidono_con_il_calcolo_diretto(self):
        for nodo in range(0, N_NODI, 5):
            attesi = set().union(*(self.vicini[v] for v in self.vicini[nodo])) if self.vicini[nodo] else set()
            attesi -= self.vicini[nodo] | {nodo}
            self.assertEqual(interrogazione.vicini_a_due_passi(nodo), attesi)

    def test_classifica_coincide_con_il_calcolo_diretto(self):
        for tipo in (None, *contratto.TIPI_IRREGOLARITA):
            for popolazione in contratto.POPOLAZIONI:
                candidati = [
                    n for n in range(N_NODI)
                    if popolazione == "tutte" or self.ha_etichetta[n] == (popolazione == "ispezionate")
                ]
                if tipo is None:
                    valore = {n: max(self.punteggi[n]) for n in candidati}
                else:
                    valore = {n: self.punteggi[n][contratto.TIPI_IRREGOLARITA.index(tipo)] for n in candidati}
                attesi = sorted(candidati, key=lambda n: -valore[n])[:7]
                classifica = interrogazione.classifica_rischio(n=7, tipo=tipo, popolazione=popolazione)
                self.assertEqual([v["nodo"] for v in classifica], attesi, (tipo, popolazione))
                for voce in classifica:
                    quota = 100 * sum(1 for n in candidati if valore[n] < valore[voce["nodo"]]) / len(candidati)
                    self.assertAlmostEqual(voce["percentile"], quota, places=9)
                    indice = contratto.TIPI_IRREGOLARITA.index(voce["tipo"])
                    self.assertEqual(voce["sopra_soglia"], self.punteggi[voce["nodo"]][indice] >= self.soglie[indice])

    def test_stato_e_dati_azienda(self):
        accertato = next(n for n in range(N_NODI) if any(self.y[n]))
        non_ispezionato = next(n for n in range(N_NODI) if not self.ha_etichetta[n])
        self.assertTrue(interrogazione.stato_compliance(accertato).startswith("IRREGOLARITÀ ACCERTATE"))
        self.assertTrue(interrogazione.stato_compliance(non_ispezionato).startswith("Non ispezionato"))
        self.assertEqual(interrogazione.dati_azienda(7)["nome"], "L'Oro <srl>")

    # ------------------------------------------------------------ strumenti
    def test_gli_strumenti_sono_quelli_del_contratto(self):
        self.assertEqual(tuple(interrogazione.STRUMENTI), contratto.NOMI_STRUMENTI)
        for nome, funzione in interrogazione.STRUMENTI.items():
            self.assertEqual(funzione.__name__, nome)  # il server registra il nome della funzione
            self.assertTrue(funzione.__doc__)  # la descrizione è ciò che legge la chat

    def test_gli_strumenti_rispondono(self):
        nodo = next(n for n in range(N_NODI) if self.vicini[n])
        altro = sorted(self.vicini[nodo])[0]
        self.assertIn("1. Società", interrogazione.classifica(3))
        self.assertIn("Connessione diretta fra A e B: SI", interrogazione.relazione(nodo, altro))
        self.assertIn("Controparti dirette", interrogazione.vicinato(nodo))
        self.assertIn("Punteggi calcolati il", interrogazione.spiegazione(nodo))

    def test_parametri_non_ammessi_producono_un_messaggio(self):
        self.assertIn("non riconosciuto", interrogazione.classifica(3, tipo="inventato"))
        self.assertIn("non riconosciuta", interrogazione.classifica(3, popolazione="altre"))
        self.assertIn("fra 1 e", interrogazione.classifica(0))
        self.assertIn("non è presente", interrogazione.vicinato(999999))
        self.assertIn("due società diverse", interrogazione.relazione(1, 1))

    def test_consulta_a_parole_chiave(self):
        nodo = next(n for n in range(N_NODI) if self.vicini[n])
        self.assertIn("CLASSIFICA", interrogazione.consulta("Quali sono le 3 aziende più rischiose?"))
        self.assertIn("RELAZIONI COMMERCIALI", interrogazione.consulta(f"Con chi commercia la società {nodo}?"))
        self.assertIn("SPIEGAZIONE", interrogazione.consulta(f"Perché la società {nodo} è a rischio?"))
        self.assertEqual(interrogazione.consulta("Che tempo fa?"), interrogazione.MESSAGGIO_NON_SUPPORTATA)

    # ------------------------------------------------------------ coda delle spiegazioni
    def test_spiegazione_mancante_va_in_coda_e_poi_viene_letta(self):
        nodo, indice_tipo = 11, 2
        testo = interrogazione.spiegazione(nodo, contratto.TIPI_IRREGOLARITA[indice_tipo])
        self.assertIn("NON ancora calcolata", testo)

        conn = scrittura.apri_in_scrittura(self.percorso)
        self.assertIn((nodo, indice_tipo), scrittura.richieste_pendenti(conn, "prova-1"))
        # il processo di calcolo (qui finto) elabora la richiesta
        vicino = sorted(self.vicini[nodo])[0] if self.vicini[nodo] else nodo
        scrittura.salva_spiegazione(conn, "prova-1", {
            "nodo": nodo, "indice_tipo": indice_tipo,
            "tipo_irregolarita": contratto.TIPI_IRREGOLARITA[indice_tipo],
            "features": [{"indice": 5, "tipo": "Testuale (NLP)", "descrizione": "prova", "peso": 0.9}],
            "relazioni": [[[min(nodo, vicino), max(nodo, vicino)], 0.8]],
            "impatto_testo": 0.1, "impatto_strutturati": 0.2,
        })
        self.assertNotIn((nodo, indice_tipo), scrittura.richieste_pendenti(conn, "prova-1"))
        conn.close()

        testo = interrogazione.spiegazione(nodo, contratto.TIPI_IRREGOLARITA[indice_tipo])
        self.assertIn("Feature #5", testo)
        self.assertNotIn("NON ancora calcolata", testo)

    # ------------------------------------------------------------ report
    def test_il_report_si_compone_dal_solo_database(self):
        report, bolla = mappa.costruisci_report()
        self.assertIsNotNone(bolla)
        self.assertIn("FASE ISPETTIVA", report)
        self.assertEqual(set(bolla["vicini_1"]), self.vicini[bolla["target"]])
        self.assertIn("L&#x27;Oro &lt;srl&gt;", mappa.genera_nodi_interattivi_html([7]))

    # ------------------------------------------------------------ compatibilità
    def _copia_archivio(self, modifica):
        import shutil
        copia = os.path.join(self.cartella.name, "copia.sqlite")
        shutil.copy(self.percorso, copia)
        conn = contratto.connetti(copia)
        with conn:
            conn.execute(modifica)
        conn.close()
        return copia

    def test_schema_diverso_viene_rifiutato(self):
        copia = self._copia_archivio("UPDATE info_archivio SET valore = '999' WHERE chiave = 'versione_schema'")
        try:
            with self.assertRaises(contratto.ArchivioIncompatibile):
                interrogazione.apri(copia)
            with self.assertRaises(contratto.ArchivioIncompatibile):
                scrittura.apri_in_scrittura(copia)
        finally:
            interrogazione.apri(self.percorso)

    def test_tassonomia_diversa_viene_rifiutata(self):
        copia = self._copia_archivio("UPDATE esecuzione_modello SET tassonomia_json = '[\"altro\"]'")
        try:
            with self.assertRaises(contratto.ArchivioIncompatibile):
                interrogazione.apri(copia)
        finally:
            interrogazione.apri(self.percorso)

    def test_archivio_senza_esecuzioni_viene_rifiutato(self):
        vuoto = os.path.join(self.cartella.name, "vuoto.sqlite")
        scrittura.apri_in_scrittura(vuoto).close()
        try:
            with self.assertRaises(contratto.ArchivioIncompatibile):
                interrogazione.apri(vuoto)
        finally:
            interrogazione.apri(self.percorso)

    # ------------------------------------------------------------ dipendenze fra le parti
    def _importazioni(self, nome_file):
        """Moduli importati da un file: (interni al pacchetto, esterni)."""
        albero = ast.parse((PACCHETTO / nome_file).read_text(encoding="utf-8"))
        interni, esterni = set(), set()
        for nodo in ast.walk(albero):
            if isinstance(nodo, ast.ImportFrom) and nodo.level > 0:
                interni |= {nodo.module} if nodo.module else {a.name for a in nodo.names}
            elif isinstance(nodo, ast.ImportFrom):
                esterni.add(nodo.module.split(".")[0])
            elif isinstance(nodo, ast.Import):
                esterni |= {a.name.split(".")[0] for a in nodo.names}
        return interni, esterni

    def test_le_dipendenze_vanno_in_una_sola_direzione(self):
        ammesse = {
            "contratto.py": set(),
            "scrittura.py": {"contratto"},
            "calcolo.py": {"contratto", "scrittura"},
            "interrogazione.py": {"contratto"},
            "server_mcp.py": {"contratto", "interrogazione"},
            "mappa.py": {"contratto", "interrogazione"},
        }
        for nome_file, permesse in ammesse.items():
            interni, _ = self._importazioni(nome_file)
            self.assertLessEqual(interni, permesse, f"{nome_file} importa {interni - permesse}")

    def test_solo_il_calcolo_usa_pytorch(self):
        for nome_file in ("contratto.py", "scrittura.py", "interrogazione.py", "server_mcp.py", "mappa.py"):
            _, esterni = self._importazioni(nome_file)
            self.assertFalse(esterni & {"torch", "torch_geometric"}, nome_file)
        self.assertNotIn("torch", sys.modules)  # questa prova ha importato la libreria senza PyTorch

    # ------------------------------------------------------------ registro e intestazioni
    def test_registro_e_intestazioni_sono_allineati(self):
        versione, _ = aggiorna_intestazioni.leggi_registro()
        self.assertEqual(versione, contratto.VERSIONE_CODICE)
        self.assertEqual(aggiorna_intestazioni.esegui(solo_verifica=True), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
