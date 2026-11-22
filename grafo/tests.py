"""
PROVA DI CABLAGGIO dell'app grafo: attraversa scrittura, database, libreria,
strumenti e report con un modello finto.

    python manage.py test grafo

Non richiede PyTorch, pyvis né la libreria mcp. Se un filo fra le parti si
stacca, o una regola di compatibilità viene violata, qui si vede.
"""
import ast
import base64
import datetime
import hashlib
import json
import pathlib
import random
import sys
import tempfile
from io import StringIO
from unittest import mock
from urllib.parse import parse_qs, urlsplit

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.management import call_command
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from grafo import contratto, interrogazione, mappa, protocollo_mcp, scrittura, servizio_mcp, sessioni
from grafo.models import (
    Esecuzione, InfoArchivio, MappaProdotta, Parametro, Richiesta, Sessione, Spiegazione, VersioneDati,
)

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
        self.assertEqual(tuple(servizio_mcp.STRUMENTI), contratto.NOMI_STRUMENTI)
        for nome, funzione in servizio_mcp.STRUMENTI.items():
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


def _mappa_finta(report_html, bolla, nome_file):
    """Al posto di mappa.scrivi_mappa: scrive il file senza networkx e pyvis."""
    pathlib.Path(nome_file).write_text(f"<html>mappa di {bolla['target']}</html>", encoding="utf-8")
    return nome_file


class SessioniTest(ConArchivio):
    """Versioni 20 e 21: servizio MCP su HTTP, accesso (OAuth e token), sessioni, registro, mappa, cruscotto."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        Utente = get_user_model()
        diritto = lambda codice: Permission.objects.get(content_type__app_label="grafo", codename=codice)
        cls.analista = Utente.objects.create_user("analista", password="x")
        cls.analista.user_permissions.add(diritto("usa_chat"))
        cls.collega = Utente.objects.create_user("collega", password="x")
        cls.collega.user_permissions.add(diritto("usa_chat"))
        cls.amministratore = Utente.objects.create_user("amministratore", password="x")
        cls.amministratore.user_permissions.add(diritto("change_parametro"), diritto("view_mappaprodotta"))
        cls.senza_diritti = Utente.objects.create_user("ospite", password="x")
        cls.riga_token, cls.token = sessioni.crea_token(cls.analista, "prova")

    # ---- attrezzi -------------------------------------------------------
    def invia(self, messaggio, token=None, connessione=None):
        intestazioni = {"HTTP_AUTHORIZATION": f"Bearer {token or self.token}"}
        if connessione:
            intestazioni["HTTP_MCP_SESSION_ID"] = connessione
        return self.client.post(
            reverse("grafo:mcp"), data=json.dumps(messaggio), content_type="application/json", **intestazioni
        )

    def collega_chat(self, token=None):
        """Come fa la chat all'avvio: initialize, poi l'avviso initialized."""
        risposta = self.invia(
            {"jsonrpc": "2.0", "id": 1, "method": "initialize",
             "params": {"protocolVersion": contratto.PROTOCOLLI_MCP[1], "clientInfo": {"name": "prova", "version": "1"}}},
            token,
        )
        self.assertEqual(risposta.status_code, 200)
        connessione = risposta["Mcp-Session-Id"]
        avviso = self.invia({"jsonrpc": "2.0", "method": "notifications/initialized"}, token, connessione)
        self.assertEqual(avviso.status_code, 202)
        return connessione, risposta.json()["result"]

    def chiama(self, connessione, strumento, token=None, **argomenti):
        risposta = self.invia(
            {"jsonrpc": "2.0", "id": 9, "method": "tools/call", "params": {"name": strumento, "arguments": argomenti}},
            token, connessione,
        )
        self.assertEqual(risposta.status_code, 200)
        return risposta.json()["result"]

    # ---- accesso --------------------------------------------------------
    def test_senza_token_valido_il_servizio_risponde_401(self):
        messaggio = {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}
        senza = self.client.post(reverse("grafo:mcp"), data=json.dumps(messaggio), content_type="application/json")
        self.assertEqual(senza.status_code, 401)
        self.assertIn("Bearer", senza["WWW-Authenticate"])
        self.assertEqual(self.invia(messaggio, "ctrl_inventato").status_code, 401)
        _, senza_diritto = sessioni.crea_token(self.senza_diritti)
        self.assertEqual(self.invia(messaggio, senza_diritto).status_code, 401)
        self.assertEqual(self.client.get(reverse("grafo:mcp")).status_code, 405)
        self.assertEqual(Sessione.objects.count(), 0)

    def test_del_token_si_conserva_solo_l_impronta_e_la_revoca_chiude_le_sessioni(self):
        self.assertNotIn(self.token, json.dumps(list(self.riga_token.__dict__.values()), default=str))
        connessione, _ = self.collega_chat()
        sessioni.revoca_token(self.riga_token)
        self.assertEqual(self.invia({"jsonrpc": "2.0", "id": 1, "method": "ping"}, connessione=connessione).status_code, 401)
        self.assertEqual(Sessione.objects.get().motivo_chiusura, sessioni.CHIUSA_PER_REVOCA)

    # ---- accesso OAuth (versione 21) -----------------------------------
    SERVIZIO = "http://testserver/grafo/mcp"

    def accesso_oauth(self, utente, risorsa=SERVIZIO):
        """
        Tutto il percorso che fa la chat: si registra come client, l'utente accede e
        autorizza nel browser, la chat scambia il codice con il token (con PKCE).
        Restituisce il token di accesso.
        """
        ritorno = "http://127.0.0.1:8765/callback"
        registrazione = self.client.post(
            reverse("oauth2_provider:dcr-register"),
            data=json.dumps({
                "client_name": "Studio di prova", "redirect_uris": [ritorno],
                "grant_types": ["authorization_code", "refresh_token"], "response_types": ["code"],
                "token_endpoint_auth_method": "none",
            }),
            content_type="application/json",
        )
        self.assertEqual(registrazione.status_code, 201, registrazione.content)
        client_id = registrazione.json()["client_id"]

        segreto = "v" * 64  # PKCE: la chat tiene il segreto e ne manda solo l'impronta
        sfida = base64.urlsafe_b64encode(hashlib.sha256(segreto.encode()).digest()).rstrip(b"=").decode()
        richiesta = {
            "response_type": "code", "client_id": client_id, "redirect_uri": ritorno,
            "scope": contratto.AMBITO_OAUTH, "state": "stato-di-prova",
            "code_challenge": sfida, "code_challenge_method": "S256", "resource": risorsa,
        }
        autorizzazione = reverse("oauth2_provider:authorize")
        self.client.logout()
        self.assertEqual(self.client.get(autorizzazione, richiesta).status_code, 302)  # prima si accede
        self.client.force_login(utente)
        consenso = self.client.get(autorizzazione, richiesta)
        self.assertContains(consenso, "Studio di prova")
        self.assertContains(consenso, ritorno)
        approvata = self.client.post(autorizzazione, {**richiesta, "allow": "Authorize"})
        self.assertEqual(approvata.status_code, 302, approvata.content)
        destinazione = urlsplit(approvata["Location"])
        self.assertTrue(approvata["Location"].startswith(ritorno))
        esito = parse_qs(destinazione.query)
        self.assertEqual(esito["state"], ["stato-di-prova"])
        self.client.logout()

        scambio = self.client.post(reverse("oauth2_provider:token"), {
            "grant_type": "authorization_code", "code": esito["code"][0], "redirect_uri": ritorno,
            "client_id": client_id, "code_verifier": segreto, "resource": risorsa,
        })
        self.assertEqual(scambio.status_code, 200, scambio.content)
        return scambio.json()["access_token"]

    def test_la_chat_scopre_da_sola_dove_chiedere_l_accesso(self):
        messaggio = {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}
        rifiuto = self.client.post(reverse("grafo:mcp"), data=json.dumps(messaggio), content_type="application/json")
        self.assertEqual(rifiuto.status_code, 401)
        documento = "http://testserver/.well-known/oauth-protected-resource/grafo/mcp"
        self.assertIn(f'resource_metadata="{documento}"', rifiuto["WWW-Authenticate"])

        risorsa = self.client.get(urlsplit(documento).path).json()
        self.assertEqual(risorsa["resource"], self.SERVIZIO)
        self.assertEqual(risorsa["authorization_servers"], ["http://testserver/o"])
        self.assertIn(contratto.AMBITO_OAUTH, risorsa["scopes_supported"])

        for indirizzo in ("/.well-known/oauth-authorization-server/o", "/o/.well-known/oauth-authorization-server"):
            server = self.client.get(indirizzo).json()
            self.assertEqual(server["issuer"], "http://testserver/o", indirizzo)
            self.assertEqual(server["authorization_endpoint"], "http://testserver/o/authorize/")
            self.assertEqual(server["token_endpoint"], "http://testserver/o/token/")
            self.assertEqual(server["registration_endpoint"], "http://testserver/o/register/")
            self.assertIn("S256", server["code_challenge_methods_supported"])
            self.assertEqual(server["grant_types_supported"], ["authorization_code", "refresh_token"])
        # le pagine della libreria per creare applicazioni a mano non sono esposte
        self.client.force_login(self.analista)
        self.assertEqual(self.client.get("/o/applications/").status_code, 404)

    def test_con_l_accesso_oauth_la_sessione_nasce_a_nome_dell_utente(self):
        accesso = self.accesso_oauth(self.analista)
        connessione, _ = self.collega_chat(accesso)
        sessione = Sessione.objects.get()
        self.assertEqual((sessione.utente, sessione.accesso, sessione.token), (self.analista, contratto.ACCESSO_OAUTH, None))
        self.assertEqual(sessione.client_oauth, "Studio di prova")
        self.assertIn("1. Società", self.chiama(connessione, "classifica", accesso)["content"][0]["text"])
        self.assertEqual(Richiesta.objects.get().sessione, sessione)

        # il token di un altro utente non può usare questa connessione
        altro = self.accesso_oauth(self.collega)
        self.assertEqual(self.invia({"jsonrpc": "2.0", "id": 2, "method": "ping"}, altro, connessione).status_code, 404)

        # token scaduto: 401, e la chat sa di dover rifare l'accesso
        from oauth2_provider.models import AccessToken
        AccessToken.objects.all().update(expires=sessione.iniziata_il - datetime.timedelta(days=1))
        scaduto = self.invia({"jsonrpc": "2.0", "id": 3, "method": "ping"}, accesso, connessione)
        self.assertEqual(scaduto.status_code, 401)
        self.assertIn("resource_metadata=", scaduto["WWW-Authenticate"])

    def test_l_accesso_oauth_non_basta_senza_il_diritto_e_vale_solo_per_questo_servizio(self):
        # utente riconosciuto ma senza il diritto usa_chat: 403, rifare l'accesso non serve
        senza_diritto = self.accesso_oauth(self.senza_diritti)
        ping = {"jsonrpc": "2.0", "id": 1, "method": "ping"}
        rifiuto = self.invia(ping, senza_diritto)
        self.assertEqual(rifiuto.status_code, 403)
        self.assertNotIn("WWW-Authenticate", rifiuto)
        # token rilasciato per un altro servizio: qui non vale
        per_altro = self.accesso_oauth(self.analista, risorsa="http://testserver/altro-servizio")
        self.assertEqual(self.invia(ping, per_altro).status_code, 401)
        self.assertEqual(self.invia(ping, "token-inventato").status_code, 401)
        self.assertEqual(Sessione.objects.count(), 0)

    def test_l_amministratore_puo_spegnere_i_token_personali(self):
        ping = {"jsonrpc": "2.0", "id": 1, "method": "ping"}
        self.assertEqual(self.invia(ping).status_code, 200)
        self.assertTrue(sessioni.errore_parametro(contratto.PARAMETRO_TOKEN_PERSONALI, "forse"))
        self.assertIsNone(sessioni.errore_parametro(contratto.PARAMETRO_TOKEN_PERSONALI, "no"))
        sessioni.salva_parametro(contratto.PARAMETRO_TOKEN_PERSONALI, "no")
        self.assertEqual(self.invia(ping).status_code, 401)
        # l'accesso OAuth continua a funzionare
        self.assertEqual(self.invia(ping, self.accesso_oauth(self.analista)).status_code, 200)

    # ---- sessioni e registro -------------------------------------------
    def test_la_sessione_nasce_alla_connessione_e_registra_le_richieste(self):
        connessione, presentazione = self.collega_chat()
        self.assertEqual(presentazione["protocolVersion"], contratto.PROTOCOLLI_MCP[1])
        self.assertEqual(presentazione["serverInfo"]["version"], contratto.VERSIONE_CODICE)
        sessione = Sessione.objects.get()
        self.assertEqual((sessione.utente, sessione.id_connessione, sessione.chiusa_il), (self.analista, connessione, None))
        self.assertEqual(sessione.client, "prova 1")
        self.assertEqual((sessione.accesso, sessione.token), (contratto.ACCESSO_TOKEN, self.riga_token))

        elenco = self.invia({"jsonrpc": "2.0", "id": 2, "method": "tools/list"}, connessione=connessione).json()
        self.assertEqual(tuple(s["name"] for s in elenco["result"]["tools"]), contratto.NOMI_STRUMENTI)
        self.assertEqual(Richiesta.objects.count(), 0)  # elencare gli strumenti non è una richiesta

        risultato = self.chiama(connessione, "classifica", n=3, domanda="quali sono le 3 peggiori?")
        self.assertFalse(risultato["isError"])
        self.assertIn("1. Società", risultato["content"][0]["text"])
        richiesta = Richiesta.objects.get()
        self.assertEqual((richiesta.sessione, richiesta.strumento, richiesta.parametri), (sessione, "classifica", {"n": 3}))
        self.assertEqual((richiesta.domanda, richiesta.esito), ("quali sono le 3 peggiori?", "ok"))
        self.assertEqual((richiesta.versione_calcolo, richiesta.numero_dati), (contratto.VERSIONE_CALCOLO, 1))

        # un parametro non ammesso è un testo per la chat, e resta nel registro
        self.assertIn("non riconosciuto", self.chiama(connessione, "classifica", tipo="boh")["content"][0]["text"])
        self.assertTrue(self.chiama(connessione, "relazione", societa_a=1)["isError"])  # manca societa_b
        self.assertEqual(Richiesta.objects.count(), 2)

    def test_la_sessione_si_chiude_per_inattivita_secondo_il_parametro(self):
        connessione, _ = self.collega_chat()
        prima = Sessione.objects.get()
        fermo_da = lambda minuti: Sessione.objects.filter(pk=prima.pk).update(
            ultima_attivita=prima.ultima_attivita - datetime.timedelta(minutes=minuti)
        )
        fermo_da(contratto.MINUTI_INATTIVITA_PREDEFINITI + 5)
        # i messaggi di servizio non contano come attività e non riaprono nulla
        self.invia({"jsonrpc": "2.0", "id": 2, "method": "ping"}, connessione=connessione)
        self.assertEqual(Sessione.objects.count(), 1)
        # la richiesta dell'ispettore trova la sessione scaduta: chiusa, e ne nasce un'altra
        self.assertFalse(self.chiama(connessione, "classifica")["isError"])
        prima.refresh_from_db()
        self.assertEqual(prima.motivo_chiusura, sessioni.CHIUSA_PER_INATTIVITA)
        nuova = Sessione.objects.exclude(pk=prima.pk).get()
        self.assertGreater(nuova.pk, prima.pk)
        self.assertEqual(Richiesta.objects.get().sessione, nuova)

        # l'amministratore allunga il tempo: la stessa pausa non chiude più
        sessioni.salva_parametro(contratto.PARAMETRO_INATTIVITA, "120", self.amministratore)
        Sessione.objects.filter(pk=nuova.pk).update(
            ultima_attivita=nuova.ultima_attivita - datetime.timedelta(minutes=60)
        )
        self.chiama(connessione, "classifica")
        self.assertEqual(Sessione.objects.count(), 2)
        self.assertEqual(sessioni.chiudi_scadute(), 0)

    def test_la_chat_puo_chiudere_la_sessione_e_non_usa_quelle_degli_altri(self):
        connessione, _ = self.collega_chat()
        _, token_collega = sessioni.crea_token(self.collega)
        ping = {"jsonrpc": "2.0", "id": 2, "method": "ping"}
        self.assertEqual(self.invia(ping, token_collega, connessione).status_code, 404)
        chiusura = self.client.delete(
            reverse("grafo:mcp"), HTTP_AUTHORIZATION=f"Bearer {self.token}", HTTP_MCP_SESSION_ID=connessione
        )
        self.assertEqual(chiusura.status_code, 204)
        self.assertEqual(Sessione.objects.get().motivo_chiusura, sessioni.CHIUSA_DAL_CLIENT)
        self.assertEqual(self.invia(ping, connessione=connessione).status_code, 404)

    # ---- mappa ----------------------------------------------------------
    def test_la_mappa_restituisce_un_collegamento_riservato_a_chi_l_ha_chiesta(self):
        connessione, _ = self.collega_chat()
        with tempfile.TemporaryDirectory() as cartella, override_settings(GRAFO_CARTELLA=cartella), \
                mock.patch.object(mappa, "scrivi_mappa", _mappa_finta):
            testo = self.chiama(connessione, "mappa", societa="Beta Legnami")["content"][0]["text"]
            riga = MappaProdotta.objects.get()
            sessione = Sessione.objects.get()
            self.assertEqual((riga.sessione, riga.soggetto_id), (sessione, self.s(20)))
            self.assertIn(f"sessione-{sessione.pk}_soggetto-{self.s(20)}_", riga.nome_file)
            self.assertEqual(riga.richiesta, Richiesta.objects.get())
            indirizzo = reverse("grafo:mappa", args=[riga.pk])
            self.assertIn("http://testserver" + indirizzo, testo)
            self.assertIn(f"Sessione n. {sessione.pk}", testo)
            self.assertIn("Beta Legnami", testo)

            self.assertEqual(self.client.get(indirizzo).status_code, 302)  # senza accesso: alla pagina di accesso
            for utente, atteso in ((self.analista, 200), (self.collega, 404), (self.amministratore, 200)):
                self.client.force_login(utente)
                self.assertEqual(self.client.get(indirizzo).status_code, atteso, utente.username)
            self.client.force_login(self.analista)
            self.assertIn(f"mappa di {self.s(20)}", self.client.get(indirizzo).content.decode())
            # rifare la stessa mappa nella stessa sessione non crea una seconda riga
            self.chiama(connessione, "mappa", societa="Beta Legnami")
            self.assertEqual(MappaProdotta.objects.count(), 1)
            # un nome ambiguo non viene indovinato nemmeno qui
            self.assertIn("corrisponde a 2 società", self.chiama(connessione, "mappa", societa="Rossi")["content"][0]["text"])

    # ---- parametri e cruscotto -----------------------------------------
    def test_le_restrizioni_dell_amministratore_restringono_e_non_allargano(self):
        altra = VersioneDati.objects.create(numero=9, impronta="altra")
        nuovo_calcolo = contratto.VERSIONE_CALCOLO.split(".")[0] + ".9"
        Esecuzione.objects.create(
            versione_calcolo=nuovo_calcolo, versione_dati=altra, versione_codice="x",
            tassonomia=list(TIPI), soglie={}, metriche={},
        )
        self.assertEqual(interrogazione.apri(), f"calcolo {nuovo_calcolo} / dati 9")
        sessioni.salva_parametro(contratto.PARAMETRO_CALCOLO, f"=={contratto.VERSIONE_CALCOLO}")
        self.assertEqual(interrogazione.apri(), f"calcolo {contratto.VERSIONE_CALCOLO} / dati 1")
        # una restrizione scritta male non spegne il servizio; una che esclude tutto sì, e lo dice
        sessioni.salva_parametro(contratto.PARAMETRO_CALCOLO, "non un intervallo")
        self.assertEqual(interrogazione.apri(), f"calcolo {nuovo_calcolo} / dati 9")
        sessioni.salva_parametro(contratto.PARAMETRO_SCHEMA, "==99.0")
        with self.assertRaisesRegex(contratto.ArchivioIncompatibile, "restrizione dell'amministratore"):
            interrogazione.apri()
        # non può allargare: ciò che il codice non sa leggere resta rifiutato
        sessioni.salva_parametro(contratto.PARAMETRO_SCHEMA, ">=1.0")
        InfoArchivio.objects.filter(chiave="versione_schema").update(valore="99.0")
        with self.assertRaises(contratto.ArchivioIncompatibile):
            interrogazione.apri()

    def test_i_parametri_si_controllano_prima_di_salvarli(self):
        controlla = lambda nome, valore: sessioni.errore_parametro(
            nome, valore, contratto.VERSIONE_SCHEMA, [contratto.VERSIONE_CALCOLO]
        )
        for nome, valore in (
            (contratto.PARAMETRO_INATTIVITA, "0"), (contratto.PARAMETRO_INATTIVITA, "dieci"),
            (contratto.PARAMETRO_INATTIVITA, "5000"), (contratto.PARAMETRO_CALCOLO, "uno"),
            (contratto.PARAMETRO_CALCOLO, "==99.0"), (contratto.PARAMETRO_SCHEMA, "==99.0"), ("inventato", "1"),
        ):
            self.assertTrue(controlla(nome, valore), (nome, valore))
        for nome, valore in (
            (contratto.PARAMETRO_INATTIVITA, "45"), (contratto.PARAMETRO_CALCOLO, ""),
            (contratto.PARAMETRO_CALCOLO, f"=={contratto.VERSIONE_CALCOLO}"),
            (contratto.PARAMETRO_SCHEMA, f">={contratto.VERSIONE_SCHEMA}"), (contratto.PARAMETRO_SPIEGAZIONE, "~=1.0"),
        ):
            self.assertIsNone(controlla(nome, valore), (nome, valore))
        # la migrazione ha creato tutti i parametri del contratto con i valori predefiniti
        self.assertEqual(set(Parametro.objects.values_list("nome", flat=True)), set(contratto.PARAMETRI))
        self.assertEqual(sessioni.minuti_di_inattivita(), contratto.MINUTI_INATTIVITA_PREDEFINITI)

    def test_il_cruscotto_mostra_le_versioni_e_salva_solo_valori_validi(self):
        indirizzo = reverse("grafo:cruscotto")
        self.client.force_login(self.analista)
        self.assertEqual(self.client.get(indirizzo).status_code, 403)
        self.client.force_login(self.amministratore)
        pagina = self.client.get(indirizzo)
        self.assertEqual(pagina.status_code, 200)
        self.assertEqual(pagina.context["versione_codice"], contratto.VERSIONE_CODICE)
        self.assertEqual(pagina.context["schema_database"], contratto.VERSIONE_SCHEMA)
        self.assertEqual(pagina.context["in_uso"], f"calcolo {contratto.VERSIONE_CALCOLO} / dati 1")
        self.assertContains(pagina, contratto.SCHEMA_RICHIESTO)

        valori = {nome: predefinito for nome, (predefinito, _) in contratto.PARAMETRI.items()}
        rifiutata = self.client.post(indirizzo, {**valori, contratto.PARAMETRO_CALCOLO: "==99.0"})
        self.assertFalse(rifiutata.context["salvato"])
        self.assertContains(rifiutata, "escluderebbe")
        self.assertEqual(sessioni.leggi_parametri()[contratto.PARAMETRO_CALCOLO], "")

        accettata = self.client.post(indirizzo, {
            **valori, contratto.PARAMETRO_INATTIVITA: "45",
            contratto.PARAMETRO_CALCOLO: f"=={contratto.VERSIONE_CALCOLO}",
        })
        self.assertTrue(accettata.context["salvato"])
        self.assertEqual(sessioni.minuti_di_inattivita(), 45)
        self.assertEqual(Parametro.objects.get(nome=contratto.PARAMETRO_INATTIVITA).modificato_da, self.amministratore)

    def test_l_analista_crea_e_revoca_i_propri_token_dalla_pagina(self):
        indirizzo = reverse("grafo:collegamento")
        self.client.force_login(self.senza_diritti)
        self.assertEqual(self.client.get(indirizzo).status_code, 403)
        self.client.force_login(self.collega)
        pagina = self.client.post(indirizzo, {"azione": "crea", "etichetta": "portatile"})
        nuovo = pagina.context["token_appena_creato"]
        self.assertTrue(nuovo.startswith(sessioni.PREFISSO_TOKEN))
        self.assertContains(pagina, reverse("grafo:mcp"))
        self.assertEqual(sessioni.token_valido(nuovo).utente, self.collega)
        # non si revoca il token di un altro
        self.client.post(indirizzo, {"azione": "revoca", "token": self.riga_token.pk})
        self.assertIsNotNone(sessioni.token_valido(self.token))
        self.client.post(indirizzo, {"azione": "revoca", "token": sessioni.token_valido(nuovo).pk})
        self.assertIsNone(sessioni.token_valido(nuovo))


class ProtocolloTest(SimpleTestCase):
    """Il protocollo MCP, senza database: descrizione degli strumenti e messaggi."""

    def test_ogni_strumento_si_descrive_con_i_suoi_parametri(self):
        descrizioni = {d["name"]: d for d in map(protocollo_mcp.descrivi_strumento, servizio_mcp.STRUMENTI.values())}
        self.assertEqual(tuple(descrizioni), contratto.NOMI_STRUMENTI)
        for descrizione in descrizioni.values():
            self.assertTrue(descrizione["description"])
            self.assertIn(protocollo_mcp.PARAMETRO_DOMANDA, descrizione["inputSchema"]["properties"])
        self.assertEqual(descrizioni["relazione"]["inputSchema"]["required"], ["societa_a", "societa_b"])
        self.assertEqual(descrizioni["classifica"]["inputSchema"]["properties"]["n"], {"type": "integer", "default": 3})
        self.assertNotIn("required", descrizioni["mappa"]["inputSchema"])

    def test_messaggi_sconosciuti_o_malformati_non_fanno_cadere_il_servizio(self):
        rispondi = lambda messaggio: protocollo_mcp.rispondi(messaggio, {}, lambda *a: ("", False))
        self.assertIsNone(rispondi({"jsonrpc": "2.0", "method": "notifications/cancelled"}))
        self.assertEqual(rispondi({"jsonrpc": "2.0", "id": 1, "method": "resources/list"})["error"]["code"], -32601)
        self.assertEqual(rispondi({"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "x"}})["error"]["code"], -32602)
        self.assertEqual(rispondi(["non", "un", "messaggio"])["error"]["code"], -32600)
        futura = rispondi({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2099-01-01"}})
        self.assertEqual(futura["result"]["protocolVersion"], contratto.PROTOCOLLI_MCP[0])


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
            "mappa.py": {"contratto", "interrogazione"},
            "sessioni.py": {"contratto", "models"},
            "protocollo_mcp.py": {"contratto"},
            "servizio_mcp.py": {"contratto", "interrogazione", "mappa", "sessioni", "calcolo_cartella"},
            "server_mcp.py": {"contratto", "interrogazione", "servizio_mcp"},
            "views.py": {
                "contratto", "interrogazione", "protocollo_mcp", "servizio_mcp", "sessioni",
                "calcolo_cartella", "models",
            },
        }
        for nome_file, permesse in ammesse.items():
            interni, _ = self._importazioni(nome_file)
            self.assertLessEqual(interni, permesse, f"{nome_file} importa {interni - permesse}")

    def test_solo_il_calcolo_usa_pytorch_e_il_contratto_non_usa_django(self):
        for nome_file in (
            "contratto.py", "models.py", "scrittura.py", "interrogazione.py", "server_mcp.py", "mappa.py",
            "sessioni.py", "protocollo_mcp.py", "servizio_mcp.py", "views.py",
        ):
            _, esterni = self._importazioni(nome_file)
            self.assertFalse(esterni & {"torch", "torch_geometric"}, nome_file)
        self.assertNotIn("django", self._importazioni("contratto.py")[1])
        # il protocollo si prova da solo: niente Django; solo il server stdio usa la libreria mcp
        self.assertNotIn("django", self._importazioni("protocollo_mcp.py")[1])
        for nome_file in ("protocollo_mcp.py", "servizio_mcp.py", "views.py", "sessioni.py"):
            self.assertNotIn("mcp", self._importazioni(nome_file)[1], nome_file)
        # la libreria OAuth si usa in un solo punto: dove si verifica il token (views.py)
        for nome_file in ("sessioni.py", "servizio_mcp.py", "protocollo_mcp.py", "interrogazione.py", "models.py"):
            self.assertNotIn("oauth2_provider", self._importazioni(nome_file)[1], nome_file)
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
