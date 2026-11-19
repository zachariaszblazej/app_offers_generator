"""Testy migratora SQLite -> SharePoint DEV (bez dostępu do sieci).

Uruchomienie: python -m unittest tests.sharepoint_migration_test -v
"""
import contextlib
import io
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import requests  # noqa: E402

from src.integrations.sharepoint import environment_manager, get_environment  # noqa: E402
from src.integrations.sharepoint.migration import datadir, mapping, runner, validate  # noqa: E402
from src.integrations.sharepoint.migration.guard import MigrationGuardError, assert_dev_only  # noqa: E402
from src.integrations.sharepoint.migration.idmap import IdMap  # noqa: E402
from src.integrations.sharepoint.migration.source import file_fingerprint, read_source_tables  # noqa: E402
from src.integrations.sharepoint.migration.writer import DevWriter, WriteError  # noqa: E402


def text_col(name, required=False, unique=False, max_len=255, multi=False):
    spec = {"allowMultipleLines": multi, "maxLength": 0 if multi else max_len}
    return {"name": name, "required": required, "enforceUniqueValues": unique,
            "readOnly": False, "hidden": False, "text": spec}


def num_col(name, required=True):
    return {"name": name, "required": required, "readOnly": False, "hidden": False,
            "number": {"decimalPlaces": "none", "minimum": -1e308, "maximum": 1e308}}


OFFER_COLUMNS = {c["name"]: c for c in (
    text_col("Title", True, True), num_col("OfferYearNumber"), num_col("OfferOrderNumber"),
    text_col("OfferFilePath", True, True), text_col("OfferContext", multi=True))}
CLIENT_COLUMNS = {c["name"]: c for c in (
    text_col("Title", True, True), text_col("CompanyName", True), text_col("AddressP1", True),
    text_col("AddressP2", True), text_col("Alias", True, True), text_col("Cena", multi=True),
    text_col("TerminRealizacji", multi=True), text_col("TerminPlatnosci", multi=True),
    text_col("WarunkiDostawy", multi=True), text_col("WaznoscOferty", multi=True),
    text_col("Gwarancja", multi=True))}
SUPPLIER_COLUMNS = {c["name"]: c for c in (
    text_col("Title", True, True), text_col("CompanyName", True), text_col("AddressP1", True),
    text_col("AddressP2", True), {"name": "IsDefault", "required": False, "readOnly": False,
                                  "hidden": False, "boolean": {}})}
WZ_COLUMNS = {c["name"]: c for c in (
    text_col("Title", True, True), num_col("WzYearNumber"), num_col("WzOrderNumber"),
    text_col("WzFilePath", True, True), text_col("WzContext", multi=True))}

# Wyłącznie dane syntetyczne (żadnych rzeczywistych nazw klientów ani NIP-ów).
ALIAS_MIXED, ALIAS_UPPER = "AlfaStal", "ALFASTAL"  # różnią się tylko wielkością liter
SYNTH_SUPPLIER_NIP = 1234563218  # 10 cyfr, poprawna suma kontrolna NIP (przykładowy numer)
SYNTH_CLIENT_NIP = 123456789
OFFER_PATH = f"2026/132_OF_2026_{ALIAS_UPPER}.docx"
WZ_PATH = "2026/WZ_39_2026_GAMMATECH.docx"


def make_db(path):
    c = sqlite3.connect(path)
    c.executescript("""
    CREATE TABLE Clients (Nip INTEGER PRIMARY KEY, CompanyName TEXT NOT NULL, AddressP1 TEXT NOT NULL,
        AddressP2 TEXT NOT NULL, Alias TEXT NOT NULL UNIQUE, TerminRealizacji TEXT, TerminPlatnosci TEXT,
        WarunkiDostawy TEXT, WaznoscOferty TEXT, Gwarancja TEXT, Cena TEXT);
    CREATE TABLE Suppliers (Nip INTEGER PRIMARY KEY, CompanyName TEXT NOT NULL, AddressP1 TEXT NOT NULL,
        AddressP2 TEXT NOT NULL, IsDefault INTEGER DEFAULT 0);
    CREATE TABLE Offers (OfferYearNumber INTEGER NOT NULL, OfferOrderNumber INTEGER NOT NULL,
        OfferFilePath TEXT NOT NULL UNIQUE, OfferContext TEXT);
    CREATE TABLE Wuzetkas (WzYearNumber INTEGER NOT NULL, WzOrderNumber INTEGER NOT NULL,
        WzFilePath TEXT NOT NULL UNIQUE, WzContext TEXT);
    """)
    # Dane wyłącznie syntetyczne. NIP klienta ma 9 cyfr celowo: testuje dopełnianie zerami do 10 znaków.
    c.execute("INSERT INTO Clients VALUES (?, 'Firma A', 'ul. A 1', '00-001' || char(10) || 'Miasto', "
              "?, NULL, NULL, 'DAP', NULL, NULL, NULL)", (SYNTH_CLIENT_NIP, ALIAS_MIXED))
    c.execute("INSERT INTO Suppliers VALUES (?, 'Dostawca', 'ul. B 2', '58-300', 1)", (SYNTH_SUPPLIER_NIP,))
    ctx = json.dumps({"offer_number": f"132/OF/2026_{ALIAS_UPPER}", "client_name": "<w:r>x</w:r>"}, ensure_ascii=False)
    c.execute("INSERT INTO Offers VALUES (2026, 132, ?, ?)", (OFFER_PATH, ctx))
    c.execute("INSERT INTO Wuzetkas VALUES (2026, 39, ?, ?)", (WZ_PATH, json.dumps({"wz_number": "WZ_39_2026_GAMMATECH"})))
    c.commit()
    c.close()


class MappingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = os.path.join(self.tmp.name, "t.db")
        make_db(self.db)
        self.tables = read_source_tables(self.db)

    def tearDown(self):
        self.tmp.cleanup()

    def test_titles_and_unchanged_business_fields(self):
        m = mapping.map_all(self.tables)
        offer, wz = m["Offers"][0], m["Wuzetkas"][0]
        self.assertEqual(offer.fields["Title"], "132/OF/2026")
        self.assertEqual(offer.fields["OfferFilePath"], OFFER_PATH)
        self.assertEqual(offer.fields["OfferContext"], self.tables["Offers"][0]["OfferContext"])
        self.assertEqual(wz.fields["Title"], "WZ_39_2026")
        self.assertEqual(wz.fields["WzFilePath"], WZ_PATH)
        self.assertEqual(wz.fields["WzContext"], self.tables["Wuzetkas"][0]["WzContext"])

    def test_nip_zero_padding_and_address_newline(self):
        m = mapping.map_all(self.tables)
        self.assertEqual(m["Clients"][0].fields["Title"], "0123456789")
        self.assertEqual(m["Suppliers"][0].fields["Title"], "1234563218")
        self.assertEqual(m["Clients"][0].fields["AddressP2"], "00-001, Miasto")
        self.assertEqual(m["Clients"][0].fields["Alias"], ALIAS_MIXED)
        self.assertNotIn("Cena", m["Clients"][0].fields)  # NULL = pominięte
        self.assertIs(m["Suppliers"][0].fields["IsDefault"], True)

    def test_case_differing_aliases_are_preserved_and_only_reported(self):
        # alias klienta ("AlfaStal") i alias w nazwie pliku oferty ("ALFASTAL") różnią się tylko wielkością liter
        m = mapping.map_all(self.tables)
        self.assertEqual(m["Clients"][0].fields["Alias"], ALIAS_MIXED)
        self.assertEqual(m["Offers"][0].fields["OfferFilePath"], OFFER_PATH)
        self.assertIn(ALIAS_UPPER, m["Offers"][0].fields["OfferFilePath"])
        self.assertNotEqual(ALIAS_MIXED, ALIAS_UPPER)
        self.assertTrue(any("wielkość liter" in i for i in m["Offers"][0].infos))
        self.assertFalse(m["Offers"][0].errors)

    def test_aliases_differing_only_by_case_collide_in_unique_column(self):
        # SharePoint nie rozróżnia wielkości liter w kolumnie unikalnej - kolizja ma być wykryta przed zapisem
        rows = [{"_rowid_": i, "Nip": nip, "CompanyName": "F", "AddressP1": "a", "AddressP2": "b", "Alias": alias}
                for i, (nip, alias) in enumerate([(111111111, ALIAS_MIXED), (222222222, ALIAS_UPPER)], 1)]
        plan = validate.plan_list(mapping.map_clients(rows), CLIENT_COLUMNS, [])
        self.assertEqual([e.action for e in plan], [validate.CREATE, validate.ERROR])
        self.assertTrue(any("Alias" in e and "duplikat" in e for e in plan[1].record.errors))
        # wartości w obu rekordach pozostają oryginalne (bez normalizacji wielkości liter)
        self.assertEqual([e.record.fields["Alias"] for e in plan], [ALIAS_MIXED, ALIAS_UPPER])

    def test_xml_leftovers_are_kept_and_only_reported(self):
        offer = mapping.map_all(self.tables)["Offers"][0]
        self.assertIn("<w:r>", offer.fields["OfferContext"])
        self.assertTrue(any("XML" in i for i in offer.infos))
        self.assertFalse(offer.errors)

    def test_bad_nip_is_record_error(self):
        recs = mapping.map_suppliers([{"_rowid_": 1, "Nip": "12A"}])
        self.assertTrue(recs[0].errors)


class ValidationTests(unittest.TestCase):
    def offer(self, **over):
        row = {"_rowid_": 1, "OfferYearNumber": 2026, "OfferOrderNumber": 1,
               "OfferFilePath": "2026/1_OF_2026_X.docx", "OfferContext": "{}"}
        row.update(over)
        return mapping.map_offers([row])[0]

    def test_valid_record_creates(self):
        plan = validate.plan_list([self.offer()], OFFER_COLUMNS, [])
        self.assertEqual(plan[0].action, validate.CREATE)

    def test_length_required_and_newline(self):
        rec = self.offer(OfferFilePath="x" * 300)
        validate.validate_record(rec, OFFER_COLUMNS)
        self.assertTrue(any("limit 255" in e for e in rec.errors))
        rec2 = self.offer(OfferFilePath="a\nb")
        validate.validate_record(rec2, OFFER_COLUMNS)
        self.assertTrue(any("nowa linia" in e for e in rec2.errors))
        c = mapping.map_clients([{"_rowid_": 1, "Nip": 1, "CompanyName": "A", "AddressP1": "",
                                  "AddressP2": "x", "Alias": "A"}])[0]
        validate.validate_record(c, CLIENT_COLUMNS)
        self.assertTrue(any("AddressP1" in e and "wymagan" in e for e in c.errors))

    def test_duplicates_in_source(self):
        a = self.offer()
        b = self.offer(OfferOrderNumber=2)  # ta sama ścieżka pliku
        plan = validate.plan_list([a, b], OFFER_COLUMNS, [])
        self.assertEqual([e.action for e in plan], [validate.CREATE, validate.ERROR])

    def test_resume_identical_and_conflict(self):
        rec = self.offer()
        existing = [{"id": "7", "fields": dict(rec.fields, OfferYearNumber=2026.0)}]
        plan = validate.plan_list([rec], OFFER_COLUMNS, existing)
        self.assertEqual((plan[0].action, plan[0].existing_id), (validate.EXISTS, "7"))
        rec2 = self.offer()
        existing2 = [{"id": "8", "fields": dict(rec2.fields, OfferFilePath="inna")}]
        plan2 = validate.plan_list([rec2], OFFER_COLUMNS, existing2)
        self.assertEqual(plan2[0].action, validate.ERROR)

    def test_unique_collision_with_other_existing_item(self):
        rec = self.offer()
        existing = [{"id": "9", "fields": {"Title": "999/OF/2026", "OfferFilePath": rec.fields["OfferFilePath"]}}]
        plan = validate.plan_list([rec], OFFER_COLUMNS, existing)
        self.assertEqual(plan[0].action, validate.ERROR)


class GuardTests(unittest.TestCase):
    def tearDown(self):
        environment_manager.reset()

    def test_dev_passes(self):
        self.assertEqual(assert_dev_only().name, "DEV")

    def test_prod_active_is_refused(self):
        environment_manager.set_active("PROD")
        with self.assertRaises(MigrationGuardError):
            assert_dev_only()
        with self.assertRaises(MigrationGuardError):
            assert_dev_only(get_environment("PROD"))

    def test_wrong_site_id_is_refused(self):
        dev = get_environment("DEV")
        bad = type(dev)(dev.name, dev.site_url, get_environment("PROD").site_id, dev.lists)
        with self.assertRaises(MigrationGuardError):
            assert_dev_only(bad)

    def test_dry_run_and_execute_refuse_in_prod(self):
        environment_manager.set_active("PROD")
        with self.assertRaises(MigrationGuardError):
            runner.run_dry_run(db_path="x.db", token_provider=lambda: "t", log=lambda *_: None)
        with self.assertRaises(MigrationGuardError):
            runner.run_execute(runner.CONFIRM_PHRASE, lists="Clients", db_path="x.db", token_provider=lambda: "t")


class SourceTests(unittest.TestCase):
    def test_read_only_and_hash_unchanged(self):
        with tempfile.TemporaryDirectory() as d:
            db = os.path.join(d, "t.db")
            make_db(db)
            before = file_fingerprint(db)
            read_source_tables(db)
            self.assertTrue(before.same_as(file_fingerprint(db)))
            self.assertEqual(sorted(os.listdir(d)), ["t.db"])

    def test_missing_file_is_not_created(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(Exception):
                read_source_tables(os.path.join(d, "nie_ma.db"))
            self.assertEqual(os.listdir(d), [])


class FakeResp:
    def __init__(self, status, body=None, headers=None):
        self.status_code, self._body, self.headers, self.text = status, body or {}, headers or {}, ""

    def json(self):
        return self._body


class WriterTests(unittest.TestCase):
    def tearDown(self):
        environment_manager.reset()

    def writer(self, responses, reader=None):
        posts, sleeps = [], []
        it = iter(responses)

        def post(url, json=None, headers=None, timeout=None):
            posts.append((url, json))
            r = next(it)
            if isinstance(r, Exception):
                raise r
            return r

        w = DevWriter(get_environment("DEV"), lambda: "tok", reader or mock.Mock(), sleep=sleeps.append, http_post=post)
        return w, posts, sleeps

    def test_url_is_dev_list_and_retry_after_is_honoured(self):
        w, posts, sleeps = self.writer([FakeResp(429, headers={"Retry-After": "7"}), FakeResp(201, {"id": "5"})])
        self.assertEqual(w.create_item("Offers", {"Title": "1/OF/2026"}), "5")
        self.assertEqual(sleeps, [7.0])
        dev = get_environment("DEV")
        self.assertEqual(posts[0][0].split("/lists/")[1], f"{dev.lists['Offers']}/items")
        self.assertIn(dev.site_id, posts[0][0])

    def test_backoff_without_retry_after_and_503(self):
        w, _, sleeps = self.writer([FakeResp(503), FakeResp(503), FakeResp(201, {"id": "1"})])
        w.create_item("Clients", {"Title": "x"})
        self.assertEqual(sleeps, [1, 2])

    def test_client_error_raises_without_retry(self):
        w, posts, sleeps = self.writer([FakeResp(400, {"error": {"message": "zła wartość"}})])
        with self.assertRaises(WriteError):
            w.create_item("Clients", {"Title": "x"})
        self.assertEqual((len(posts), sleeps), (1, []))

    def test_ambiguous_timeout_checks_existing_before_retry(self):
        reader = mock.Mock()
        reader.get.return_value = {"value": [{"id": "42"}]}
        w, posts, _ = self.writer([requests.Timeout("t")], reader=reader)
        self.assertEqual(w.create_item("Offers", {"Title": "1/OF/2026"}), "42")
        self.assertEqual(len(posts), 1)  # brak drugiego POST - nie ma duplikatu

    def test_writer_refuses_prod(self):
        environment_manager.set_active("PROD")
        with self.assertRaises(MigrationGuardError):
            DevWriter(get_environment("PROD"), lambda: "t", mock.Mock())


class DryRunTests(unittest.TestCase):
    def tearDown(self):
        environment_manager.reset()

    def test_dry_run_makes_no_writes_and_keeps_source(self):
        with tempfile.TemporaryDirectory() as d:
            db = os.path.join(d, "t.db")
            make_db(db)
            before = file_fingerprint(db)
            dev = get_environment("DEV")
            remote = runner.Remote()
            remote.site = {"id": dev.site_id, "displayName": "DEV", "webUrl": dev.site_url}
            remote.lists_info = {n: "ok" for n in runner.LIST_ORDER}
            remote.columns = {"Offers": OFFER_COLUMNS, "Clients": CLIENT_COLUMNS,
                              "Suppliers": SUPPLIER_COLUMNS, "Wuzetkas": WZ_COLUMNS}
            remote.items = {n: [] for n in runner.LIST_ORDER}
            with mock.patch.object(runner, "fetch_remote", return_value=remote), \
                    mock.patch.object(runner, "_document_roots", return_value={"Offers": "", "Wuzetkas": ""}), \
                    mock.patch.object(requests, "post", side_effect=AssertionError("zapis w dry-run!")), \
                    mock.patch.object(requests, "patch", side_effect=AssertionError("zapis w dry-run!")), \
                    mock.patch.object(requests, "delete", side_effect=AssertionError("zapis w dry-run!")):
                rep = runner.run_dry_run(db_path=db, report_dir=d, token_provider=lambda: "tok", log=lambda *_: None)
            self.assertEqual(rep["tryb"], "dry-run")
            self.assertEqual(rep["zapisy_wykonane"], 0)
            self.assertEqual(rep["http"].get("POST", 0), 0)
            self.assertTrue(rep["zrodlo"]["niezmienione"])
            self.assertTrue(before.same_as(file_fingerprint(db)))
            self.assertEqual({n: s["do_utworzenia"] for n, s in rep["listy"].items()},
                             {"Suppliers": 1, "Clients": 1, "Offers": 1, "Wuzetkas": 1})
            self.assertFalse(os.path.exists(rep["mapa_id"]["sciezka"]))

    def test_execute_requires_confirmation_and_dry_run(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(runner.MigrationRefused):
                runner.run_execute("", lists="Clients", db_path="x", report_dir=d)
            db = os.path.join(d, "t.db")
            make_db(db)
            with self.assertRaises(runner.MigrationRefused):
                runner.run_execute(runner.CONFIRM_PHRASE, lists="Clients", db_path=db, report_dir=d)
            with self.assertRaises(runner.MigrationRefused):  # brak jawnego wyboru list
                runner.run_execute(runner.CONFIRM_PHRASE, lists="", db_path=db, report_dir=d)
            with self.assertRaises(runner.MigrationRefused):  # nieznana lista
                runner.run_execute(runner.CONFIRM_PHRASE, lists="Foo", db_path=db, report_dir=d)


class StagedExecuteTests(unittest.TestCase):
    """Etapowa migracja na atrapie SharePoint: wybór list, idempotencja, weryfikacja."""

    def tearDown(self):
        environment_manager.reset()

    def make_env(self, d):
        dev = get_environment("DEV")
        store = {n: {} for n in runner.LIST_ORDER}
        counter = {"n": 0, "posts": 0}

        def post(url, json=None, headers=None, timeout=None):
            list_id = url.split("/lists/")[1].split("/")[0]
            name = next(n for n, v in dev.lists.items() if v == list_id)
            counter["n"] += 1
            counter["posts"] += 1
            item_id = str(counter["n"])
            store[name][item_id] = {"id": item_id, "fields": dict(json["fields"], id=item_id)}
            return FakeResp(201, {"id": item_id})

        def fetch(reader, env):
            remote = runner.Remote()
            remote.site = {"id": dev.site_id, "displayName": "DEV", "webUrl": dev.site_url}
            remote.lists_info = {n: "ok" for n in runner.LIST_ORDER}
            remote.columns = {"Offers": OFFER_COLUMNS, "Clients": CLIENT_COLUMNS,
                              "Suppliers": SUPPLIER_COLUMNS, "Wuzetkas": WZ_COLUMNS}
            remote.items = {n: list(store[n].values()) for n in runner.LIST_ORDER}
            return remote

        patches = [
            mock.patch.object(runner, "fetch_remote", side_effect=fetch),
            mock.patch.object(runner, "_document_roots", return_value={"Offers": "", "Wuzetkas": ""}),
            mock.patch.object(runner, "DevWriter", side_effect=lambda env, tp, reader, sleep=None: DevWriter(
                env, tp, reader, sleep=lambda s: None, http_post=post)),
        ]
        return store, counter, patches

    def test_stages_are_isolated_idempotent_and_verified(self):
        with tempfile.TemporaryDirectory() as d:
            db = os.path.join(d, "t.db")
            make_db(db)
            store, counter, patches = self.make_env(d)
            for p in patches:
                p.start()
            self.addCleanup(lambda: [p.stop() for p in patches])
            common = dict(db_path=db, report_dir=d, token_provider=lambda: "tok", log=lambda *_: None)
            runner.save_report(runner.run_dry_run(**common), d, "dryrun")

            # Etap 1 - tylko Suppliers i Clients
            rep = runner.run_execute(runner.CONFIRM_PHRASE, lists="Clients,Suppliers", **common)
            self.assertTrue(rep["wykonanie"]["ok"], rep["wykonanie"]["weryfikacja"])
            self.assertEqual(list(rep["listy"]), ["Suppliers", "Clients"])
            self.assertEqual({n: len(v) for n, v in store.items()},
                             {"Suppliers": 1, "Clients": 1, "Offers": 0, "Wuzetkas": 0})
            self.assertEqual(rep["wykonanie"]["utworzono"], 2)
            with open(os.path.join(d, "id_map_DEV.json"), encoding="utf-8") as f:
                idmap = json.load(f)
            self.assertEqual(sorted(idmap["lists"]), ["Clients", "Suppliers"])

            # Wznowienie tego samego etapu: bez duplikatów i bez nowych POST
            posts = counter["posts"]
            rep2 = runner.run_execute(runner.CONFIRM_PHRASE, lists="Suppliers,Clients", **common)
            self.assertEqual((counter["posts"], rep2["wykonanie"]["utworzono"], rep2["wykonanie"]["pominieto"]),
                             (posts, 0, 2))

            # Konflikt: element o tym samym Title, ale z innymi danymi, nie jest nadpisywany
            item = next(iter(store["Clients"].values()))
            item["fields"]["CompanyName"] = "ZMIENIONE RĘCZNIE"
            with self.assertRaises(runner.MigrationRefused):
                runner.run_execute(runner.CONFIRM_PHRASE, lists="Clients", **common)
            self.assertEqual(item["fields"]["CompanyName"], "ZMIENIONE RĘCZNIE")
            item["fields"]["CompanyName"] = "Firma A"

            # Etap 2 - Offers
            rep3 = runner.run_execute(runner.CONFIRM_PHRASE, lists="Offers", **common)
            self.assertTrue(rep3["wykonanie"]["ok"])
            self.assertEqual({n: len(v) for n, v in store.items()},
                             {"Suppliers": 1, "Clients": 1, "Offers": 1, "Wuzetkas": 0})
            self.assertEqual(next(iter(store["Offers"].values()))["fields"]["Title"], "132/OF/2026")

    def test_hash_change_blocks_execute(self):
        with tempfile.TemporaryDirectory() as d:
            db = os.path.join(d, "t.db")
            make_db(db)
            store, counter, patches = self.make_env(d)
            for p in patches:
                p.start()
            self.addCleanup(lambda: [p.stop() for p in patches])
            common = dict(db_path=db, report_dir=d, token_provider=lambda: "tok", log=lambda *_: None)
            runner.save_report(runner.run_dry_run(**common), d, "dryrun")
            c = sqlite3.connect(db)
            c.execute("INSERT INTO Offers VALUES (2026, 133, '2026/133_OF_2026_X.docx', '{}')")
            c.commit()
            c.close()
            with self.assertRaises(runner.MigrationRefused):
                runner.run_execute(runner.CONFIRM_PHRASE, lists="Offers", **common)
            self.assertEqual(counter["posts"], 0)


class FakeSP:
    """Pamięciowa atrapa listy Clients: POST/DELETE (writer) oraz GET (reader)."""

    def __init__(self, preset=None, corrupt_field=None):
        self.items = dict(preset or {})
        self.next_id = 1
        self.posts = self.deletes = 0
        self.corrupt_field = corrupt_field

    def post(self, url, json=None, headers=None, timeout=None):
        self.posts += 1
        item_id = str(self.next_id)
        self.next_id += 1
        fields = dict(json["fields"], id=item_id)
        if self.corrupt_field:
            fields[self.corrupt_field] = "ZMIENIONE"
        self.items[item_id] = {"id": item_id, "fields": fields}
        return FakeResp(201, {"id": item_id, "fields": fields})

    def delete(self, url, headers=None, timeout=None):
        self.deletes += 1
        item_id = url.rsplit("/", 1)[1]
        return FakeResp(204) if self.items.pop(item_id, None) else FakeResp(404)

    def get(self, path, params=None):
        if "/items/" in path:
            item = self.items.get(path.rsplit("/", 1)[1])
            if item is None:
                from src.integrations.sharepoint.graph_client import GraphError
                raise GraphError("HTTP 404", status=404)
            return item
        return {"value": list(self.items.values())}

    def get_all(self, path, params=None):
        return list(self.items.values())


class SyntheticTests(unittest.TestCase):
    def tearDown(self):
        environment_manager.reset()

    def setup(self, sp):
        from src.integrations.sharepoint.migration import synthetic_test as st
        env = get_environment("DEV")
        reader = mock.Mock()
        reader.get.side_effect, reader.get_all.side_effect = sp.get, sp.get_all
        writer = DevWriter(env, lambda: "tok", reader, sleep=lambda s: None,
                           http_post=sp.post, http_delete=sp.delete)
        return st, env, reader, writer

    def test_full_scenario_creates_reads_deletes_and_verifies(self):
        sp = FakeSP()
        st, env, reader, writer = self.setup(sp)
        rep = st.execute_synthetic(env, reader, writer, CLIENT_COLUMNS, [], "T1", log=lambda *_: None)
        self.assertEqual(rep["wynik"], "UDANY")
        self.assertEqual((sp.posts, sp.deletes, len(sp.items)), (1, 1, 0))
        self.assertTrue(rep["odczyt_zwrotny"]["zgodne"])
        self.assertEqual(rep["weryfikacja_koncowa"]["clients_elementow"], 0)
        self.assertFalse(rep["weryfikacja_koncowa"]["element_istnieje"])
        self.assertTrue(rep["item_id"] and rep["payload"]["Title"].startswith("ZZTEST-"))

    def test_nonempty_list_aborts_before_any_write(self):
        sp = FakeSP()
        st, env, reader, writer = self.setup(sp)
        rep = st.execute_synthetic(env, reader, writer, CLIENT_COLUMNS, [{"id": "1"}], "T2", log=lambda *_: None)
        self.assertEqual(rep["wynik"], "NIEUDANY")
        self.assertEqual((sp.posts, sp.deletes), (0, 0))

    def test_readback_mismatch_fails_but_test_item_is_cleaned_up(self):
        sp = FakeSP(corrupt_field="CompanyName")
        st, env, reader, writer = self.setup(sp)
        rep = st.execute_synthetic(env, reader, writer, CLIENT_COLUMNS, [], "T3", log=lambda *_: None)
        self.assertEqual(rep["wynik"], "NIEUDANY")
        self.assertEqual(rep["odczyt_zwrotny"]["roznice"], ["CompanyName"])
        self.assertEqual((sp.posts, sp.deletes, len(sp.items)), (1, 1, 0))

    def test_delete_is_restricted(self):
        sp = FakeSP()
        sp.items["5"] = {"id": "5", "fields": {"Title": "PRAWDZIWY KLIENT"}}
        sp.items["6"] = {"id": "6", "fields": {"Title": "ZZTEST-abc"}}
        st, env, reader, writer = self.setup(sp)
        with self.assertRaises(WriteError):
            writer.delete_synthetic_item("Offers", "6", "ZZTEST-abc")      # inna lista
        with self.assertRaises(WriteError):
            writer.delete_synthetic_item("Clients", "5", "PRAWDZIWY KLIENT")  # brak prefiksu
        with self.assertRaises(WriteError):
            writer.delete_synthetic_item("Clients", "6 or 1=1", "ZZTEST-abc")  # nienumeryczne ID
        with self.assertRaises(WriteError):
            writer.delete_synthetic_item("Clients", "5", "ZZTEST-abc")      # Title nie zgadza się z elementem
        self.assertEqual((sp.deletes, len(sp.items)), (0, 2))
        self.assertTrue(writer.delete_synthetic_item("Clients", "6", "ZZTEST-abc"))
        self.assertEqual((sp.deletes, sorted(sp.items)), (1, ["5"]))

    def test_run_requires_confirmation_and_dev(self):
        from src.integrations.sharepoint.migration import synthetic_test as st
        with self.assertRaises(ValueError):
            st.run_synthetic_test("")
        environment_manager.set_active("PROD")
        with self.assertRaises(MigrationGuardError):
            st.run_synthetic_test(st.CONFIRM_SYNTHETIC, token_provider=lambda: "t")


class DataDirTests(unittest.TestCase):
    """Raporty, mapa ID i inne dane migracji nie mogą trafić do repozytorium."""

    def setUp(self):
        self.root = datadir.project_root()
        self.inside = os.path.join(self.root, "zz_migration_data_test")
        self.addCleanup(lambda: self.assertFalse(os.path.exists(self.inside), "w repozytorium powstał katalog danych"))

    def test_project_root_is_the_repository(self):
        self.assertTrue(os.path.isfile(os.path.join(self.root, "main.py")))
        self.assertTrue(os.path.isdir(os.path.join(self.root, "src")))

    def test_rejects_repo_root_and_subdirectories(self):
        for path in (self.root, os.path.join(self.root, "reports"), self.inside,
                     os.path.join(self.root, "src", "integrations", "x", "y")):
            with self.subTest(path=path), self.assertRaises(datadir.DataDirError):
                datadir.assert_outside_repo(path)

    def test_rejects_parent_traversal_and_relative_paths(self):
        traversal = os.path.join(self.root, "docs", "..", "src", "..", "leak")
        with self.assertRaises(datadir.DataDirError):
            datadir.assert_outside_repo(traversal)
        # wyjście do katalogu nadrzędnego i powrót do repozytorium
        back = os.path.join(self.root, "..", os.path.basename(self.root), "leak")
        with self.assertRaises(datadir.DataDirError):
            datadir.assert_outside_repo(back)
        old = os.getcwd()
        os.chdir(self.root)
        try:
            for rel in (".", "reports", os.path.join("docs", "..", "leak"),
                        os.path.join("..", os.path.basename(self.root), "leak")):
                with self.subTest(relative=rel), self.assertRaises(datadir.DataDirError):
                    datadir.assert_outside_repo(rel)
        finally:
            os.chdir(old)

    @unittest.skipUnless(os.name == "nt", "wielkość liter ścieżek ma znaczenie tylko na Windows")
    def test_rejects_different_letter_case_on_windows(self):
        with self.assertRaises(datadir.DataDirError):
            datadir.assert_outside_repo(os.path.join(self.root.swapcase(), "Leak"))

    def test_rule_is_scoped_to_the_project_repository_only(self):
        # inne repozytorium git (np. założone w katalogu domowym) nie blokuje katalogu poza projektem
        with tempfile.TemporaryDirectory() as d:
            os.mkdir(os.path.join(d, ".git"))
            target = os.path.join(d, "reports", "migration")
            self.assertEqual(os.path.normcase(datadir.assert_outside_repo(target)),
                             os.path.normcase(os.path.realpath(target)))

    def test_rejects_link_pointing_into_repository(self):
        with tempfile.TemporaryDirectory() as d:
            link = os.path.join(d, "link")
            target = os.path.join(self.root, "docs")
            if os.name == "nt":
                made = subprocess.run(["cmd", "/c", "mklink", "/J", link, target], capture_output=True).returncode == 0
            else:
                try:
                    os.symlink(target, link)
                    made = True
                except OSError:
                    made = False
            if not made:
                self.skipTest("nie można utworzyć dowiązania/junctiony")
            try:
                with self.assertRaises(datadir.DataDirError):
                    datadir.assert_outside_repo(os.path.join(link, "leak"))
            finally:
                os.rmdir(link) if os.name == "nt" else os.unlink(link)

    def test_outside_directories_and_default_location_are_allowed(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(os.path.normcase(datadir.resolve_data_dir(os.path.join(d, "r"))),
                             os.path.normcase(os.path.realpath(os.path.join(d, "r"))))
        default = datadir.resolve_data_dir(None)
        self.assertTrue(default.lower().endswith(os.path.join("hantechdokumenty", "migration")))
        self.assertFalse(datadir._is_within(datadir._canonical(default), datadir._canonical(self.root)))

    def test_every_write_entry_point_refuses_before_any_io_or_network(self):
        def boom():
            raise AssertionError("pobrano token mimo odmowy")

        with self.assertRaises(datadir.DataDirError):
            runner.run_dry_run(db_path="x.db", report_dir=self.inside, token_provider=boom, log=lambda *_: None)
        with self.assertRaises(datadir.DataDirError):
            runner.run_execute(runner.CONFIRM_PHRASE, lists="Clients", db_path="x.db", report_dir=self.inside,
                               token_provider=boom)
        from src.integrations.sharepoint.migration import synthetic_test as st
        with self.assertRaises(datadir.DataDirError):
            st.run_synthetic_test(st.CONFIRM_SYNTHETIC, token_provider=boom, report_dir=self.inside)
        with self.assertRaises(datadir.DataDirError):
            runner.save_report({"tryb": "x"}, self.inside, "x")
        with self.assertRaises(datadir.DataDirError):
            IdMap(os.path.join(self.inside, "id_map_DEV.json"), "DEV", "site").save()

    def test_cli_refuses_report_dir_in_repository(self):
        from src.integrations.sharepoint.migration.__main__ import main
        for argv in (["--report-dir", self.inside],
                     ["--report-dir", os.path.join(self.root, "docs", "..", "zz_migration_data_test")],
                     ["--execute", "--lists", "Offers", "--confirm", "MIGRATE-DEV", "--report-dir", self.inside],
                     ["--synthetic-test", "--confirm", "SYNTHETIC-TEST-DEV", "--report-dir", self.inside]):
            out = io.StringIO()
            with self.subTest(argv=argv), contextlib.redirect_stdout(out):
                self.assertEqual(main(argv), 4)
            self.assertIn("ODMOWA", out.getvalue())


if __name__ == "__main__":
    unittest.main()
