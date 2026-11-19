"""Test zgodności SharePointBackend (SharePoint DEV) z SQLite na danych z migracji - WYŁĄCZNIE ODCZYT.

Uruchomienie (wymaga logowania MSAL w przeglądarce):
    $env:HANTECH_LIVE_SP_TESTS = "1"
    python -m unittest tests.sharepoint_backend_live_test -v
Opcjonalnie: HANTECH_LIVE_MISSING_WZ_PATH = względna ścieżka WZ, której pliku brakuje na dysku (rekord ma być zmigrowany).

Zasady bezpieczeństwa:
* wyłącznie środowisko DEV i wyłącznie żądania GET do Microsoft Graph (każde inne żądanie poza logowaniem MSAL
  jest blokowane i kończy test błędem),
* punktem odniesienia jest kopia bazy z migracji (weryfikowana hashem), otwierana z tymczasowego katalogu,
* prawdziwa baza użytkownika jest tylko haszowana (bez otwierania), nic nie jest do niej zapisywane,
* raport szczegółowy trafia poza repozytorium (katalog danych migracji).
"""
import glob
import hashlib
import json
import os
import shutil
import sys
import tempfile
import time
import unittest
from collections import Counter
from unittest import mock
from urllib.parse import urlparse

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import requests  # noqa: E402

from src.data.backends import BackendContext, SharePointBackend, SqliteBackend  # noqa: E402
from src.integrations.sharepoint import get_environment  # noqa: E402
from src.integrations.sharepoint.migration import datadir, mapping  # noqa: E402
from src.integrations.sharepoint.migration.idmap import IdMap  # noqa: E402
from src.integrations.sharepoint.migration.source import file_fingerprint, read_source_tables  # noqa: E402
from src.integrations.sharepoint.reader import RetryingGraphClient  # noqa: E402
from src.integrations.sharepoint.session import SharePointSession  # noqa: E402

LIVE = os.environ.get("HANTECH_LIVE_SP_TESTS") == "1"
EXPECTED_COUNTS = {"Suppliers": 1, "Clients": 39, "Offers": 417, "Wuzetkas": 227}
MIGRATION_DB_SHA256 = "089cd491f0c26136d2fd4be297279c79d7a8675ed5c805f3811a75dc86f5ace7"
REAL_DB_PATH = os.environ.get("HANTECH_LIVE_REAL_DB", "")
MISSING_WZ_PATH = os.environ.get("HANTECH_LIVE_MISSING_WZ_PATH", "")
LOGIN_HOSTS = ("login.microsoftonline.com", "login.windows.net")
GRAPH_HOST = "graph.microsoft.com"
MIGRATED_FIELDS = {
    "Suppliers": ("Title", "CompanyName", "AddressP1", "AddressP2", "IsDefault"),
    "Clients": ("Title", "CompanyName", "AddressP1", "AddressP2", "Alias", "TerminRealizacji", "TerminPlatnosci",
                "WarunkiDostawy", "WaznoscOferty", "Gwarancja", "Cena"),
    "Offers": ("Title", "OfferYearNumber", "OfferOrderNumber", "OfferFilePath", "OfferContext"),
    "Wuzetkas": ("Title", "WzYearNumber", "WzOrderNumber", "WzFilePath", "WzContext"),
}


def sha256_of(path):
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def same_value(expected, actual):
    """Porównanie pola: SharePoint pomija null i "" oraz zwraca liczby jako float."""
    if expected is None or expected == "":
        return actual is None or actual == ""
    if isinstance(expected, bool) or isinstance(actual, bool):
        return expected is actual or (isinstance(expected, bool) and isinstance(actual, bool) and expected == actual)
    if isinstance(expected, (int, float)) and isinstance(actual, (int, float)):
        return float(expected) == float(actual)
    return expected == actual


def find_migration_backup():
    pattern = os.path.join(datadir.migration_dir(), "backup", f"*_{MIGRATION_DB_SHA256[:8]}.db")
    for path in sorted(glob.glob(pattern)):
        if sha256_of(path) == MIGRATION_DB_SHA256:
            return path
    return None


@unittest.skipUnless(LIVE, "Test na żywo - ustaw HANTECH_LIVE_SP_TESTS=1 (tylko odczyt, SharePoint DEV).")
class LiveCompatibilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.env = get_environment("DEV")
        assert cls.env.name == "DEV" and not cls.env.is_prod
        cls.report = {"started": time.strftime("%Y-%m-%d %H:%M:%S"), "environment": "DEV"}
        cls.http_log = []
        cls._install_http_guard()

        backup = find_migration_backup()
        if backup is None:
            raise unittest.SkipTest("Nie znaleziono kopii bazy z migracji o oczekiwanym hashu.")
        cls.tmp = tempfile.TemporaryDirectory()
        cls.db_copy = os.path.join(cls.tmp.name, "migration_copy.db")
        shutil.copyfile(backup, cls.db_copy)
        cls.backup_hash = sha256_of(backup)
        cls.copy_hash_before = sha256_of(cls.db_copy)
        cls.real_before = file_fingerprint(REAL_DB_PATH) if REAL_DB_PATH else None

        cls.tables = read_source_tables(cls.db_copy)
        cls.expected = mapping.map_all(cls.tables)

        cls.session = SharePointSession()
        cls.session.sign_in(interactive_log=print)
        cls.client = RetryingGraphClient(cls.env, cls.session.get_token())

        cls.popups, cls.logs = [], []
        cls.context = BackendContext(
            offers_folder=lambda: os.path.join(cls.tmp.name, "offers"),
            wz_folder=lambda: os.path.join(cls.tmp.name, "wz"),
            popups_enabled=lambda: False,
            show_error=lambda title, message: cls.popups.append((title, message)),
            log=lambda *a, **k: cls.logs.append(a))
        cls.sp = SharePointBackend(cls.context, cls.session, cls.env)
        cls.sq = SqliteBackend(lambda: cls.db_copy, cls.context)
        cls.actual_items = cls._fetch_all_items()
        cls.record_rows = []

    @classmethod
    def tearDownClass(cls):
        cls._uninstall_http_guard()
        try:
            cls.report["finished"] = time.strftime("%Y-%m-%d %H:%M:%S")
            cls.report["http_requests"] = dict(Counter(f"{m} {h}" for m, h, _ in cls.http_log))
            cls.report["records"] = cls.record_rows
            out_dir = datadir.assert_outside_repo(datadir.migration_dir())
            os.makedirs(out_dir, exist_ok=True)
            path = os.path.join(out_dir, f"backend_compat_{time.strftime('%Y%m%d%H%M%S')}.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump(cls.report, f, ensure_ascii=False, indent=1)
            print(f"\nRaport szczegółowy (poza repozytorium): {path}")
        finally:
            cls.tmp.cleanup()

    # ------------------------------------------------------------------
    # strażnik HTTP: poza logowaniem MSAL dozwolone wyłącznie GET do Graph
    # ------------------------------------------------------------------
    @classmethod
    def _install_http_guard(cls):
        original = requests.Session.request

        def guarded(session, method, url, *args, **kwargs):
            host = urlparse(url).netloc.lower()
            cls.http_log.append((method.upper(), host, urlparse(url).path))
            if host in LOGIN_HOSTS:
                return original(session, method, url, *args, **kwargs)
            if method.upper() != "GET" or host != GRAPH_HOST:
                raise AssertionError(f"ZABLOKOWANE żądanie {method.upper()} {host} - test jest wyłącznie do odczytu z Graph.")
            return original(session, method, url, *args, **kwargs)

        cls._guard_patch = mock.patch.object(requests.Session, "request", guarded)
        cls._guard_patch.start()

    @classmethod
    def _uninstall_http_guard(cls):
        cls._guard_patch.stop()

    # ------------------------------------------------------------------
    @classmethod
    def _fetch_all_items(cls):
        items = {}
        for list_name, fields in MIGRATED_FIELDS.items():
            path = f"/sites/{cls.env.site_id}/lists/{cls.env.lists[list_name]}/items"
            params = {"$select": "id", "$expand": f"fields($select={','.join(fields)})", "$top": "999"}
            items[list_name] = cls.client.get_all(path, params)
        return items

    def test_00_environment_is_dev_and_guard_is_active(self):
        self.assertEqual(self.env.name, "DEV")
        self.assertFalse(self.env.is_prod)
        self.assertEqual(self.backup_hash, MIGRATION_DB_SHA256)
        self.assertEqual(self.copy_hash_before, MIGRATION_DB_SHA256)

    def test_01_counts_match_migration(self):
        counts = {name: len(items) for name, items in self.actual_items.items()}
        self.report["counts"] = counts
        self.assertEqual(counts, EXPECTED_COUNTS)
        self.assertEqual(sum(counts.values()), 684)
        self.assertEqual({k: len(v) for k, v in self.expected.items()}, EXPECTED_COUNTS)

    def test_02_every_record_matches_source_in_all_migrated_fields(self):
        mismatches = []
        for list_name, records in self.expected.items():
            by_title = {}
            for raw in self.actual_items[list_name]:
                title = (raw.get("fields") or {}).get("Title")
                self.assertNotIn(title, by_title, f"duplikat Title w {list_name}: {title}")
                by_title[title] = raw
            self.assertEqual(set(by_title), {r.title for r in records}, f"zbiór Title w {list_name}")
            for rec in records:
                raw = by_title[rec.title]
                actual = raw.get("fields") or {}
                bad = [k for k, v in rec.fields.items() if not same_value(v, actual.get(k))]
                extra = [k for k in actual if k not in rec.fields and actual[k] not in (None, "") and not k.startswith("@")]
                row = {"list": list_name, "key": rec.key, "title": rec.title, "item_id": str(raw["id"]),
                       "fields_ok": not bad and not extra}
                self.record_rows.append(row)
                if bad or extra:
                    mismatches.append((list_name, rec.title, bad, extra))
        self.report["field_mismatches"] = len(mismatches)
        self.assertEqual(mismatches, [])

    def test_03_id_map_matches_actual_items(self):
        id_map_path = os.path.join(datadir.migration_dir(), "id_map_DEV.json")
        id_map = IdMap.load(id_map_path, "DEV", self.env.site_id)
        self.assertEqual({k: id_map.count(k) for k in EXPECTED_COUNTS}, EXPECTED_COUNTS)
        problems = []
        for list_name, records in self.expected.items():
            actual_by_id = {str(r["id"]): (r.get("fields") or {}).get("Title") for r in self.actual_items[list_name]}
            mapped_ids = []
            for rec in records:
                entry = id_map.get(list_name, rec.key)
                if entry is None:
                    problems.append((list_name, rec.key, "brak wpisu w mapie"))
                    continue
                mapped_ids.append(entry["item_id"])
                if actual_by_id.get(entry["item_id"]) != rec.title or entry["title"] != rec.title:
                    problems.append((list_name, rec.key, "ID/Title niezgodne z elementem"))
            if len(set(mapped_ids)) != len(mapped_ids):
                problems.append((list_name, "*", "duplikaty ID w mapie"))
            if set(mapped_ids) != set(actual_by_id):
                problems.append((list_name, "*", "ID w mapie != ID elementów listy"))
        self.report["id_map_problems"] = len(problems)
        self.assertEqual(problems, [])

    def test_04_pagination_has_no_skipped_or_duplicated_records(self):
        results = {}
        for list_name in ("Clients", "Offers", "Wuzetkas", "Suppliers"):
            fields = ("Title",)
            per_page = {}
            for size in (7, 25, 999):
                backend = SharePointBackend(self.context, self.session, self.env, page_size=size)
                before = backend.page_requests
                items = backend._items(list_name, fields)
                ids = [i.id for i in items]
                self.assertEqual(len(ids), len(set(ids)), f"duplikaty przy page_size={size}")
                per_page[size] = {"ids": ids, "pages": backend.page_requests - before}
            self.assertEqual(per_page[7]["ids"], per_page[999]["ids"])
            self.assertEqual(per_page[25]["ids"], per_page[999]["ids"])
            self.assertEqual(len(per_page[999]["ids"]), EXPECTED_COUNTS[list_name])
            expected_pages = -(-EXPECTED_COUNTS[list_name] // 25)
            self.assertEqual(per_page[25]["pages"], expected_pages)
            results[list_name] = {str(s): v["pages"] for s, v in per_page.items()}
        self.report["pagination_pages"] = results

    def test_05_clients_and_suppliers_parity(self):
        def with_comma(row):  # zatwierdzona transformacja migracji
            return row[:3] + (mapping.newline_to_comma(row[3]),) + row[4:]

        for extended in (False, True):
            expected = [with_comma(r) for r in self.sq.get_clients(extended)]
            self.assertEqual(self.sp.get_clients(extended), expected)
        for row in self.sq.get_clients(True):
            nip = row[0]
            self.assertEqual(self.sp.get_client_by_nip(nip), with_comma(self.sq.get_client_by_nip(nip)))
            self.assertEqual(self.sp.get_client_by_nip(str(nip).zfill(10)), with_comma(self.sq.get_client_by_nip(nip)))
            self.assertEqual(self.sp.validate_nip(str(nip).zfill(10)), self.sq.validate_nip(str(nip).zfill(10)))
        for nip in ("9999999999", "123", "abcdefghij"):
            self.assertEqual(self.sp.validate_nip(nip), self.sq.validate_nip(nip))
            self.assertEqual(self.sp.get_client_by_nip(nip), self.sq.get_client_by_nip(nip))
        for alias in ("X", "", "   "):
            self.assertEqual(self.sp.validate_alias(alias), self.sq.validate_alias(alias))

        self.assertEqual(self.sp.get_suppliers(), self.sq.get_suppliers())
        self.assertEqual(self.sp.get_default_supplier(), self.sq.get_default_supplier())
        for row in self.sq.get_suppliers():
            nip = row[0]
            self.assertEqual(self.sp.get_supplier_by_nip(nip), self.sq.get_supplier_by_nip(nip))
            self.assertEqual(self.sp.validate_supplier_nip(str(nip).zfill(10)), self.sq.validate_supplier_nip(str(nip).zfill(10)))
        self.assertEqual(self.sp.validate_supplier_nip("9999999999"), self.sq.validate_supplier_nip("9999999999"))

    def test_06_tuple_shapes_and_types(self):
        for extended, length in ((False, 5), (True, 11)):
            rows = self.sp.get_clients(extended)
            sqlite_rows = {r[0]: r for r in self.sq.get_clients(extended)}
            self.assertEqual(len(rows), EXPECTED_COUNTS["Clients"])
            for row in rows:
                self.assertIsInstance(row, tuple)
                self.assertEqual(len(row), length)
                self.assertEqual([type(v) for v in row], [type(v) for v in sqlite_rows[row[0]]])
        suppliers = self.sp.get_suppliers()
        self.assertEqual(len(suppliers), 1)
        self.assertEqual([type(v) for v in suppliers[0]], [type(v) for v in self.sq.get_suppliers()[0]])
        for row in self.sp.get_all_wz():
            self.assertEqual(len(row), 6)
            self.assertIs(type(row[0]), int)
            self.assertTrue(all(isinstance(v, str) for v in row[1:]))
        for path in self.sp.get_all_offer_file_paths() + self.sp.get_all_wz_file_paths():
            self.assertIs(type(path), str)

    def test_07_offers_parity_and_contexts_on_demand(self):
        paths = self.sp.get_all_offer_file_paths()
        self.assertEqual(paths, self.sq.get_all_offer_file_paths())
        self.assertEqual(len(paths), EXPECTED_COUNTS["Offers"])
        mismatches = []
        for rec in self.expected["Offers"]:
            path = rec.fields["OfferFilePath"]
            if self.sp.get_offer_context(path) != self.sq.get_offer_context(path):
                mismatches.append(("context", rec.title))
            if self.sp.find_offer_by_filename(os.path.basename(path)) != self.sq.find_offer_by_filename(os.path.basename(path)):
                mismatches.append(("find", rec.title))
        self.report["offers_parity_mismatches"] = len(mismatches)
        self.assertEqual(mismatches, [])
        self.assertIsNone(self.sp.get_offer_context("2099/999_OF_2099_BRAK.docx"))
        self.assertIsNone(self.sp.find_offer_by_filename("nie_istnieje_zzz.docx"))

    def test_08_wz_parity_contexts_and_missing_file_record(self):
        self.assertEqual(self.sp.get_all_wz_file_paths(), self.sq.get_all_wz_file_paths())
        self.assertEqual(self.sp.get_all_wz(), self.sq.get_all_wz())
        self.assertEqual(len(self.sp.get_all_wz()), EXPECTED_COUNTS["Wuzetkas"])
        mismatches = []
        for rec in self.expected["Wuzetkas"]:
            path = rec.fields["WzFilePath"]
            if self.sp.get_wz_context(path) != self.sq.get_wz_context(path):
                mismatches.append(rec.title)
        self.report["wz_parity_mismatches"] = len(mismatches)
        self.assertEqual(mismatches, [])
        if MISSING_WZ_PATH:
            self.assertIn(MISSING_WZ_PATH, self.sp.get_all_wz_file_paths())
            self.assertIsNotNone(self.sp.get_wz_context(MISSING_WZ_PATH))
            self.assertEqual(self.sp.get_wz_context(MISSING_WZ_PATH), self.sq.get_wz_context(MISSING_WZ_PATH))
            self.report["missing_file_record_migrated"] = True

    def test_09_zz_no_writes_and_sources_unchanged(self):
        non_get = [(m, h) for m, h, _ in self.http_log if m != "GET" and h not in LOGIN_HOSTS]
        self.assertEqual(non_get, [])
        graph = [(m, p) for m, h, p in self.http_log if h == GRAPH_HOST]
        self.assertTrue(graph)
        self.assertTrue(all(m == "GET" for m, _ in graph))
        site_prefix = f"/v1.0/sites/{self.env.site_id}".lower()
        self.assertTrue(all(p.lower().startswith(site_prefix) for _, p in graph))
        self.assertNotIn(get_environment("PROD").site_id.lower(), " ".join(p.lower() for _, p in graph))
        self.assertEqual(sha256_of(self.db_copy), self.copy_hash_before)
        self.assertEqual(sha256_of(self.db_copy), MIGRATION_DB_SHA256)
        if self.real_before is not None:
            self.assertTrue(file_fingerprint(REAL_DB_PATH).same_as(self.real_before))
        self.report["graph_get_requests"] = len(graph)
        self.report["non_get_graph_requests"] = 0
        self.report["real_db_hash"] = self.real_before.sha256 if self.real_before else None
        self.report["real_db_equals_migration_copy"] = (
            self.real_before.sha256 == MIGRATION_DB_SHA256 if self.real_before else None)


if __name__ == "__main__":
    unittest.main()
