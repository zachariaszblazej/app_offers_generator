"""Testy integracyjne dostawców (etap 4B-4) na SharePoint DEV - WYŁĄCZNIE syntetyczne rekordy `ZZTEST-`.

Uruchomienie (wymaga logowania MSAL w przeglądarce):
    $env:HANTECH_LIVE_SP_SUPPLIER_TESTS = "1"
    python -m unittest tests.sharepoint_supplier_live_test -v

Bezwzględna ochrona prawdziwego dostawcy (ID 1, IsDefault=True):
* strażnik HTTP `SupplierWriteGuard` blokuje żądanie PRZED wysłaniem: ID 1 nigdy nie może być celem PATCH ani DELETE,
  a PATCH/DELETE dopuszcza wyłącznie dla ID z rejestru rekordów utworzonych przez bieżący przebieg (rejestr jest tworzony od nowa),
* algorytm `set_default_supplier` czyta całą listę, więc testy zapisu używają `ScopedSupplierBackend` - podklasy testowej,
  której widok listy Suppliers jest ograniczony do rejestru bieżącego przebiegu (prawdziwy ID 1 jest dla algorytmu niewidoczny).
  Kod produkcyjny pozostaje bez zmian; ochrona ID 1 jest sprawdzana offline (zawsze uruchamiane klasy poniżej).
* przed testami: stan ID 1 (ETag, wersja, IsDefault, hash pól), liczność list, brak pozostałości `ZZTEST-`;
  po testach: sprzątanie po dokładnych ID (z ponowną weryfikacją ID, Title i ETagu) i porównanie wszystkiego z wartościami sprzed.
Szczegółowy raport (bez tokenów) trafia poza repozytorium.
"""
import json
import os
import re
import sys
import time
import unittest
from collections import Counter
from unittest import mock
from urllib.parse import urlparse

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import requests  # noqa: E402

import tests.sharepoint_backend_test as spt  # noqa: E402  (moduł - bez duplikowania testów)
import tests.sharepoint_client_write_live_test as lw  # noqa: E402  (pomocnicze: sha256_json, hosty)
from src.data.backends import BackendContext, SharePointBackend  # noqa: E402
from src.data.errors import ConflictMessage  # noqa: E402
from src.integrations.sharepoint import environment_manager, get_environment  # noqa: E402
from src.integrations.sharepoint.environment import get_active_environment  # noqa: E402
from src.integrations.sharepoint.graph_client import GraphError  # noqa: E402
from src.integrations.sharepoint.migration import datadir  # noqa: E402
from src.integrations.sharepoint.reader import RetryingGraphClient  # noqa: E402
from src.integrations.sharepoint.session import SharePointSession  # noqa: E402
from src.integrations.sharepoint.writer import GraphWriter  # noqa: E402

LIVE = os.environ.get("HANTECH_LIVE_SP_SUPPLIER_TESTS") == "1"
PREFIX = "ZZTEST-"
REAL_ID = "1"
SYNTHETIC_TITLE = re.compile(r"^999\d{7}$")
CONCRETE_ETAG = re.compile(r'^"[0-9a-fA-F-]{36},\d+"$')
POST_FIELDS = {"Title", "CompanyName", "AddressP1", "AddressP2", "IsDefault"}
PATCH_FIELDS = {"CompanyName", "AddressP1", "AddressP2", "IsDefault"}
ADD_OK = (True, "Dostawca został pomyślnie dodany do bazy")
UPDATE_OK = (True, "Dane dostawcy zostały zaktualizowane")
DELETE_OK = (True, "Dostawca został usunięty z bazy")
NOT_FOUND = (False, "Dostawca nie został znaleziony")
NIP_TAKEN = (False, "Dostawca z tym NIP już istnieje w bazie")
DEFAULT_REFUSED = (False, "Nie można usunąć domyślnego dostawcy. Najpierw ustaw innego dostawcę jako domyślny.")
SET_OK = (True, "Dostawca został ustawiony jako domyślny")


# ---------------------------------------------------------------------------
# strażnik zapisów HTTP (czysta logika; blokuje przed wysłaniem)
# ---------------------------------------------------------------------------
def concrete_etag(value):
    return isinstance(value, str) and bool(CONCRETE_ETAG.match(value))


class SupplierWriteGuard:
    def __init__(self, env, prod, registry):
        self.env, self.registry = env, registry
        self.site = f"/v1.0/sites/{env.site_id}".lower()
        self.items = f"{self.site}/lists/{env.lists['Suppliers']}/items".lower()
        self.prod_markers = {prod.site_id.lower(), *(v.lower() for v in prod.lists.values())}

    def check(self, method, url, body=None, headers=None):
        """Zwraca None albo zgłasza AssertionError z powodem blokady (żądanie nie zostaje wysłane)."""
        parsed = urlparse(url)
        host, path = parsed.netloc.lower(), parsed.path.lower()
        headers = headers or {}
        if host in lw.LOGIN_HOSTS:
            return
        if host != lw.GRAPH_HOST:
            raise AssertionError(f"ZABLOKOWANE: host {host}")
        active = get_active_environment()
        if active.name != "DEV" or self.env.name != "DEV" or self.env.is_prod:
            raise AssertionError(f"ZABLOKOWANE: środowisko nie jest DEV (aktywne: {active.name})")
        if any(marker in path for marker in self.prod_markers):
            raise AssertionError("ZABLOKOWANE: identyfikator PROD")
        if not path.startswith(self.site):
            raise AssertionError(f"ZABLOKOWANE: ścieżka spoza witryny DEV: {path[:60]}")
        method = method.upper()
        if method == "GET":
            return
        if method not in ("POST", "PATCH", "DELETE"):
            raise AssertionError(f"ZABLOKOWANE: metoda {method}")
        if not path.startswith(self.items):
            raise AssertionError(f"ZABLOKOWANE: zapis poza listą Suppliers: {method} {path[-48:]}")
        rest = path[len(self.items):]
        if method == "POST":
            fields = (body or {}).get("fields") if isinstance(body, dict) else None
            if rest or not isinstance(fields, dict):
                raise AssertionError("ZABLOKOWANE: nieprawidłowy POST")
            if not SYNTHETIC_TITLE.match(str(fields.get("Title", ""))):
                raise AssertionError("ZABLOKOWANE: POST bez syntetycznego Title")
            if not str(fields.get("CompanyName", "")).startswith(PREFIX):
                raise AssertionError("ZABLOKOWANE: POST bez prefiksu ZZTEST- w CompanyName")
            if set(fields) - POST_FIELDS or fields.get("IsDefault", False) is not False:
                raise AssertionError("ZABLOKOWANE: POST z nieznanym polem lub IsDefault różnym od false")
            return
        m = re.fullmatch(r"/(\d+)(/fields)?", rest)
        if not m:
            raise AssertionError(f"ZABLOKOWANE: {method} {rest[:40]}")
        item_id = m.group(1)
        if item_id == REAL_ID:
            raise AssertionError("ZABLOKOWANE: ID 1 (prawdziwy dostawca) jest nietykalny")
        if item_id not in self.registry:
            raise AssertionError(f"ZABLOKOWANE: {method} elementu spoza rejestru bieżącego przebiegu: {item_id}")
        if not concrete_etag(headers.get("If-Match")):
            raise AssertionError(f"ZABLOKOWANE: {method} bez konkretnego If-Match (brak, pusty lub *)")
        if method == "PATCH":
            if not m.group(2) or not isinstance(body, dict) or not body or set(body) - PATCH_FIELDS:
                raise AssertionError("ZABLOKOWANE: PATCH z niedozwolonymi polami lub poza /fields")
            if "IsDefault" in body and not isinstance(body["IsDefault"], bool):
                raise AssertionError("ZABLOKOWANE: IsDefault musi być true albo false")
            return
        if m.group(2):
            raise AssertionError("ZABLOKOWANE: DELETE /fields")


class ScopedSupplierBackend(SharePointBackend):
    """TYLKO DO TESTÓW: widok listy Suppliers ograniczony do rejestru bieżącego przebiegu.

    Algorytmy backendu czytają całą listę; tu prawdziwy dostawca (ID 1) nie jest im w ogóle widoczny, więc nie może zostać
    odznaczony, usunięty ani zaktualizowany. Produkcyjny SharePointBackend nie jest modyfikowany."""

    def __init__(self, *args, registry, **kwargs):
        super().__init__(*args, **kwargs)
        self._registry = registry

    def _items(self, list_name, fields, odata_filter=None):
        items = super()._items(list_name, fields, odata_filter)
        if list_name == "Suppliers":
            items = [i for i in items if str(i.id) in self._registry and str(i.id) != REAL_ID]
        return items


# ---------------------------------------------------------------------------
# testy offline (zawsze uruchamiane): strażnik i ochrona ID 1
# ---------------------------------------------------------------------------
class SupplierWriteGuardLogicTests(unittest.TestCase):
    def setUp(self):
        self.env, self.prod = get_environment("DEV"), get_environment("PROD")
        self.registry = {"41", "42"}
        self.guard = SupplierWriteGuard(self.env, self.prod, self.registry)
        self.base = f"https://graph.microsoft.com/v1.0/sites/{self.env.site_id}/lists/{self.env.lists['Suppliers']}/items"
        self.etag = '"00000000-0000-0000-0000-000000000041,3"'
        self.post = {"fields": {"Title": "9990000011", "CompanyName": "ZZTEST-A", "AddressP1": "a", "AddressP2": "b", "IsDefault": False}}

    def blocked(self, method, url, body=None, headers=None):
        with self.assertRaises(AssertionError):
            self.guard.check(method, url, body, headers)

    def test_allows_only_the_synthetic_records_of_the_current_run(self):
        self.guard.check("POST", self.base, self.post)
        self.guard.check("POST", self.base, {"fields": {"Title": "9990000011", "CompanyName": "ZZTEST-A"}})
        self.guard.check("PATCH", f"{self.base}/41/fields", {"IsDefault": True}, {"If-Match": self.etag})
        self.guard.check("PATCH", f"{self.base}/42/fields", {"CompanyName": "x", "AddressP1": None}, {"If-Match": self.etag})
        self.guard.check("DELETE", f"{self.base}/41", None, {"If-Match": self.etag})
        self.guard.check("GET", f"{self.base}/1")  # odczyt prawdziwego dostawcy jest dozwolony (tylko GET)
        self.guard.check("POST", "https://login.microsoftonline.com/x/oauth2/v2.0/token")

    def test_the_real_supplier_id_1_can_never_be_patched_or_deleted_even_if_registered(self):
        for registry in (set(), {"1"}, {"1", "41"}):
            guard = SupplierWriteGuard(self.env, self.prod, registry)
            for method, suffix, body in (("PATCH", "/fields", {"IsDefault": False}), ("PATCH", "/fields", {"CompanyName": "x"}),
                                         ("DELETE", "", None)):
                with self.assertRaises(AssertionError):
                    guard.check(method, f"{self.base}/1{suffix}", body, {"If-Match": self.etag})

    def test_ids_outside_the_registry_are_blocked(self):
        for item_id in ("2", "40", "43", "99999999", "0"):
            self.blocked("PATCH", f"{self.base}/{item_id}/fields", {"IsDefault": False}, {"If-Match": self.etag})
            self.blocked("DELETE", f"{self.base}/{item_id}", None, {"If-Match": self.etag})

    def test_a_fresh_registry_does_not_remember_earlier_runs(self):
        other = SupplierWriteGuard(self.env, self.prod, set())
        with self.assertRaises(AssertionError):
            other.check("DELETE", f"{self.base}/41", None, {"If-Match": self.etag})

    def test_post_requires_a_synthetic_title_prefix_and_safe_fields(self):
        ok = self.post["fields"]
        for override in ({"Title": "1234563218"}, {"Title": "99900001"}, {"Title": "ZZTEST-1"}, {"CompanyName": "Prawdziwa Firma"},
                         {"CompanyName": "zztest-a"}, {"IsDefault": True}, {"IsDefault": None}, {"Alias": "ZZTEST-A"}):
            self.blocked("POST", self.base, {"fields": {**ok, **override}})
        self.blocked("POST", self.base, {})
        self.blocked("POST", self.base, None)
        self.blocked("POST", f"{self.base}/41", self.post)

    def test_patch_allows_only_the_permitted_fields(self):
        for body in ({"Title": "9990000012"}, {"Alias": "x"}, {"IsDefault": None}, {"IsDefault": "true"}, {"IsDefault": 1},
                     {"CompanyName": "x", "Title": "y"}, {}, None, ["IsDefault"]):
            self.blocked("PATCH", f"{self.base}/41/fields", body, {"If-Match": self.etag})
        self.blocked("PATCH", f"{self.base}/41", {"IsDefault": True}, {"If-Match": self.etag})  # nie /fields

    def test_a_concrete_if_match_is_required_for_patch_and_delete(self):
        for headers in (None, {}, {"If-Match": ""}, {"If-Match": "   "}, {"If-Match": "*"}, {"If-Match": " * "},
                        {"If-Match": "bez-cudzyslowow,1"}, {"If-Match": '"x,1"'}, {"If-Match": self.etag + "\r\nX: 1"}):
            self.blocked("PATCH", f"{self.base}/41/fields", {"IsDefault": True}, headers)
            self.blocked("DELETE", f"{self.base}/41", None, headers)

    def test_other_lists_prod_other_sites_hosts_and_methods_are_blocked(self):
        for name in ("Clients", "Offers", "Wuzetkas"):
            other = f"https://graph.microsoft.com/v1.0/sites/{self.env.site_id}/lists/{self.env.lists[name]}/items"
            self.blocked("POST", other, self.post)
            self.blocked("PATCH", f"{other}/41/fields", {"IsDefault": True}, {"If-Match": self.etag})
            self.blocked("DELETE", f"{other}/41", None, {"If-Match": self.etag})
        prod_url = f"https://graph.microsoft.com/v1.0/sites/{self.prod.site_id}/lists/{self.prod.lists['Suppliers']}/items"
        for method in ("GET", "POST", "PATCH", "DELETE"):
            self.blocked(method, prod_url, self.post, {"If-Match": self.etag})
        self.blocked("GET", "https://graph.microsoft.com/v1.0/me/drive")
        self.blocked("GET", "https://example.com/x")
        self.blocked("PUT", f"{self.base}/41", self.post, {"If-Match": self.etag})
        self.blocked("POST", f"https://graph.microsoft.com/v1.0/sites/{self.env.site_id}/lists", self.post)

    def test_nothing_is_allowed_when_the_application_is_not_in_dev(self):
        environment_manager.set_active("PROD")
        self.addCleanup(environment_manager.reset)
        self.blocked("GET", f"{self.base}/1")
        self.blocked("POST", self.base, self.post)
        self.blocked("PATCH", f"{self.base}/41/fields", {"IsDefault": True}, {"If-Match": self.etag})
        self.blocked("DELETE", f"{self.base}/41", None, {"If-Match": self.etag})

    def test_a_guard_built_for_a_non_dev_environment_blocks_everything(self):
        guard = SupplierWriteGuard(self.prod, self.prod, {"41"})
        with self.assertRaises(AssertionError):
            guard.check("GET", f"https://graph.microsoft.com/v1.0/sites/{self.prod.site_id}/lists")
        with self.assertRaises(AssertionError):
            guard.check("DELETE", f"{self.base}/41", None, {"If-Match": self.etag})


class ScopedViewProtectionTests(unittest.TestCase):
    """Dowód offline, że algorytmy nie mogą dotknąć prawdziwego dostawcy ID 1 w widoku ograniczonym do rejestru."""

    SYNTHETIC = ("9990000101", "9990000102", "9990000103")
    REAL_NIP = "1234567890"

    def setUp(self):
        data = spt.build_graph_data(spt.TABLES)
        real = {"id": 1, "fields": {"Title": self.REAL_NIP, "CompanyName": "Prawdziwa Firma", "AddressP1": "ul. R",
                                    "AddressP2": "00-000", "IsDefault": True}}
        synthetic = [{"id": 2 + i, "fields": {"Title": nip, "CompanyName": f"{PREFIX}{i}", "AddressP1": "a", "AddressP2": "b",
                                              "IsDefault": False}} for i, nip in enumerate(self.SYNTHETIC)]
        data["Suppliers"] = [real] + synthetic
        self.graph = spt.FakeGraph(data)
        self.session = spt.FakeSession()
        self.registry = {"2", "3", "4"}
        context = BackendContext(offers_folder=lambda: "", wz_folder=lambda: "", popups_enabled=lambda: False,
                                 show_error=lambda t, m: None, log=lambda *a, **k: None)
        factory = lambda: GraphWriter(spt.DEV_ENV, "TOKEN", http=self.graph.http, sleep=lambda s: None)  # noqa: E731
        kwargs = dict(client_factory=lambda: self.graph, writer_factory=factory)
        self.scoped = ScopedSupplierBackend(context, self.session, spt.DEV_ENV, registry=self.registry, **kwargs)
        self.plain = SharePointBackend(context, self.session, spt.DEV_ENV, **kwargs)
        self.real_item = self.graph.data["Suppliers"][0]
        self.real_before = (self.graph._etag(self.real_item), dict(self.real_item["fields"]), self.real_item.get("version", 1))

    def real_untouched(self):
        return (self.graph._etag(self.real_item), dict(self.real_item["fields"]), self.real_item.get("version", 1)) == self.real_before

    def written_ids(self):
        return [w["path"].rsplit("/", 2)[-2] if w["path"].endswith("/fields") else w["path"].rsplit("/", 1)[-1]
                for w in self.graph.writes if w["method"] in ("PATCH", "DELETE")]

    def test_control_without_scoping_the_algorithm_WOULD_clear_the_real_supplier_and_the_guard_blocks_that_request(self):
        # dowód konieczności izolacji: zwykły backend odznaczyłby ID 1 jako „poprzedniego domyślnego”
        self.assertEqual(self.plain.set_default_supplier(self.SYNTHETIC[0]), SET_OK)
        self.assertIn("1", self.written_ids())
        self.assertFalse(self.real_untouched())
        # strażnik HTTP zablokowałby dokładnie to żądanie (ID 1), a żądanie dla syntetycznego rekordu przepuścił
        guard = SupplierWriteGuard(spt.DEV_ENV, get_environment("PROD"), set(self.registry))
        base = f"https://graph.microsoft.com/v1.0/sites/{spt.DEV_ENV.site_id}/lists/{spt.DEV_ENV.lists['Suppliers']}/items"
        outcomes = []
        for write in self.graph.writes:
            try:
                guard.check(write["method"], base + write["path"].split("/items")[-1], write["json"], {"If-Match": write["if_match"]})
                outcomes.append((write["path"].rsplit("/", 2)[-2], "przepuszczone"))
            except AssertionError:
                outcomes.append((write["path"].rsplit("/", 2)[-2], "zablokowane"))
        self.assertEqual(outcomes, [("2", "przepuszczone"), ("1", "zablokowane")])

    def test_scoped_set_default_never_reads_writes_or_clears_the_real_supplier(self):
        a, b, c = self.SYNTHETIC
        self.assertEqual(self.scoped.set_default_supplier(a), SET_OK)  # brak syntetycznego domyślnego
        self.assertEqual(self.scoped.set_default_supplier(b), SET_OK)  # przełączenie A -> B
        self.graph.data["Suppliers"][3]["fields"]["IsDefault"] = True
        self.graph.data["Suppliers"][2]["fields"]["IsDefault"] = True  # dwóch syntetycznych domyślnych (B i C)
        self.assertEqual(self.scoped.set_default_supplier(b), SET_OK)  # naprawa
        self.graph.writes.clear()
        self.assertEqual(self.scoped.set_default_supplier(b), SET_OK)  # idempotencja
        self.assertEqual(self.graph.writes, [])
        self.assertEqual(self.scoped.set_default_supplier("9990000199"), NOT_FOUND)
        self.assertEqual(self.graph.writes, [])
        self.assertNotIn("1", self.written_ids())
        self.assertTrue(self.real_untouched())
        self.assertFalse(any(r[1].endswith("/items/1") for r in self.graph.requests))  # nawet odczyt po ID
        synthetic_defaults = [i["fields"]["Title"] for i in self.graph.data["Suppliers"][1:] if i["fields"]["IsDefault"]]
        self.assertEqual(synthetic_defaults, [b])

    def test_the_real_supplier_is_invisible_and_immutable_for_every_scoped_operation(self):
        self.assertNotIn(int(self.REAL_NIP), [r[0] for r in self.scoped.get_suppliers()])
        self.assertIsNone(self.scoped.get_default_supplier())
        self.assertIsNone(self.scoped.get_supplier_by_nip(self.REAL_NIP))
        self.assertEqual(self.scoped.update_supplier(self.REAL_NIP, "x", "y", "z"), NOT_FOUND)
        self.assertEqual(self.scoped.delete_supplier(self.REAL_NIP), NOT_FOUND)
        self.assertEqual(self.scoped.set_default_supplier(self.REAL_NIP), NOT_FOUND)
        self.assertEqual(self.graph.writes, [])
        self.assertTrue(self.real_untouched())

    def test_the_unscoped_backend_still_sees_the_real_supplier_for_read_only_checks(self):
        self.assertEqual(self.plain.get_default_supplier()[0], int(self.REAL_NIP))
        self.assertEqual(self.graph.writes, [])

    def test_every_write_of_the_scoped_lifecycle_passes_the_guard(self):
        guard = SupplierWriteGuard(spt.DEV_ENV, get_environment("PROD"), self.registry)
        base = f"https://graph.microsoft.com/v1.0/sites/{spt.DEV_ENV.site_id}/lists/{spt.DEV_ENV.lists['Suppliers']}/items"
        a, b, _ = self.SYNTHETIC
        self.scoped.set_default_supplier(a)
        self.scoped.set_default_supplier(b)
        self.scoped.update_supplier(b, f"{PREFIX}zmiana", "ul. Z", "11-111")
        self.assertEqual(self.scoped.delete_supplier(a), DELETE_OK)
        self.assertTrue(self.graph.writes)
        for write in self.graph.writes:
            guard.check(write["method"], base + write["path"].split("/items")[-1], write["json"], {"If-Match": write["if_match"]})
        self.assertTrue(self.real_untouched())


# ---------------------------------------------------------------------------
# testy na żywo (DEV)
# ---------------------------------------------------------------------------
@unittest.skipUnless(LIVE, "Test na żywo - ustaw HANTECH_LIVE_SP_SUPPLIER_TESTS=1 (SharePoint DEV, rekordy ZZTEST-).")
class LiveSupplierTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.env, cls.prod = get_environment("DEV"), get_environment("PROD")
        assert cls.env.name == "DEV" and not cls.env.is_prod
        cls.registry, cls.labels, cls.http_log, cls.blocked, cls.current = set(), {}, [], [], "setup"
        cls.guard = SupplierWriteGuard(cls.env, cls.prod, cls.registry)
        cls.report = {"started": time.strftime("%Y-%m-%d %H:%M:%S"), "environment": "DEV", "tests": {}}
        cls.run_tag, cls.run_num, cls.seq = time.strftime("%H%M%S"), int(time.time()) % 10000, 0
        cls.cleaned = False
        cls._install_http_guard()
        cls.addClassCleanup(cls._uninstall_http_guard)

        cls.session = SharePointSession()
        if not cls.session.resume():
            cls.session.sign_in(interactive_log=print)
        token = cls.session.get_token()
        cls.reader = RetryingGraphClient(cls.env, token)
        cls.raw_writer = GraphWriter(cls.env, token)
        cls.popups, cls.logs = [], []
        context = BackendContext(offers_folder=lambda: "", wz_folder=lambda: "", popups_enabled=lambda: False,
                                 show_error=lambda title, message: cls.popups.append((title, message)),
                                 log=lambda *a, **k: cls.logs.append(a))
        cls.scoped = ScopedSupplierBackend(context, cls.session, cls.env, registry=cls.registry)
        cls.plain = SharePointBackend(context, cls.session, cls.env)  # tylko odczyty
        cls.list_path = f"/sites/{cls.env.site_id}/lists/{cls.env.lists['Suppliers']}"
        cls.base = f"{cls.list_path}/items"

        cls.before = cls.snapshot()
        problems = cls.preflight_problems(cls.before)
        if problems:  # nie usuwamy niczego automatycznie - zatrzymanie i zgłoszenie
            raise RuntimeError("PREFLIGHT NIE PRZESZEDŁ (żadnych zapisów nie wykonano): " + "; ".join(problems))
        cls.report["real_supplier_before"] = cls.before["real"]
        cls.report["suppliers_count_before"] = cls.before["count"]

    @classmethod
    def tearDownClass(cls):
        try:
            if not cls.cleaned:
                cls.cleanup()
        finally:
            cls.report["finished"] = time.strftime("%Y-%m-%d %H:%M:%S")
            writes = [e for e in cls.http_log if e["method"] != "GET"]
            cls.report["writes"] = dict(Counter(e["method"] for e in writes if e.get("status", 0) and e["status"] < 400))
            cls.report["write_attempts_by_status"] = dict(Counter(f"{e['method']} {e['status']}" for e in writes))
            cls.report["blocked_attempts"] = cls.blocked
            cls.report["http_log"] = cls.http_log
            out_dir = datadir.assert_outside_repo(datadir.migration_dir())
            os.makedirs(out_dir, exist_ok=True)
            path = os.path.join(out_dir, f"supplier_live_4b4_{time.strftime('%Y%m%d%H%M%S')}.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump(cls.report, f, ensure_ascii=False, indent=1)
            print(f"\nRaport szczegółowy (poza repozytorium): {path}")

    def setUp(self):
        type(self).current = self._testMethodName

    # --- strażnik HTTP, dziennik żądań (bez tokenów) ---
    @classmethod
    def _install_http_guard(cls):
        original = requests.Session.request

        def guarded(session, method, url, *args, **kwargs):
            method = method.upper()
            body, headers = kwargs.get("json"), kwargs.get("headers") or {}
            try:
                cls.guard.check(method, url, body, headers)  # AssertionError => żądanie NIE zostaje wysłane
            except AssertionError as e:
                cls.blocked.append({"test": cls.current, "method": method, "path": urlparse(url).path[-60:], "powód": str(e)})
                raise
            if urlparse(url).netloc.lower() in lw.LOGIN_HOSTS:
                return original(session, method, url, *args, **kwargs)
            path = urlparse(url).path
            entry = {"test": cls.current, "method": method,
                     "path": re.sub(r"^/v1\.0/sites/[^/]+/lists/[0-9a-f-]+", "…/Suppliers", path)}
            if method != "GET":
                entry["if_match"] = headers.get("If-Match")
                entry["body"] = body
            response = original(session, method, url, *args, **kwargs)
            entry["status"] = response.status_code
            if method != "GET":
                entry["etag"] = response.headers.get("ETag")
            if response.status_code >= 400:
                try:
                    error = response.json().get("error", {})
                    entry["code"], entry["message"] = error.get("code"), error.get("message")
                except ValueError:
                    pass
            if method == "POST" and response.status_code == 201:
                new_id = str(response.json()["id"])
                cls.registry.add(new_id)
                entry["created_id"] = new_id
            cls.http_log.append(entry)
            return response

        cls._guard_patch = mock.patch.object(requests.Session, "request", guarded)
        cls._guard_patch.start()

    @classmethod
    def _uninstall_http_guard(cls):
        cls._guard_patch.stop()

    # --- stan i pomocnicze ---
    @classmethod
    def snapshot(cls):
        items = cls.reader.get_all(f"{cls.base}", {"$expand": "fields", "$top": "999"})
        real = next((i for i in items if str(i["id"]) == REAL_ID), None)
        data = {"count": len(items), "ids": sorted(str(i["id"]) for i in items),
                "zz": [str(i["id"]) for i in items if cls._looks_synthetic(i.get("fields") or {})]}
        data["real"] = None if real is None else {
            "etag": real.get("@odata.etag"), "version": real["fields"].get("_UIVersionString"),
            "IsDefault": real["fields"].get("IsDefault"), "fields_hash": lw.sha256_json(real["fields"])}
        data["others"], data["schema"] = {}, {}
        for name in ("Clients", "Offers", "Wuzetkas"):
            path = f"/sites/{cls.env.site_id}/lists/{cls.env.lists[name]}"
            rows = cls.reader.get_all(f"{path}/items", {"$select": "id", "$top": "999"})
            data["others"][name] = {"count": len(rows), "hash": lw.sha256_json(sorted((str(r["id"]), r.get("@odata.etag")) for r in rows))}
        for name in ("Suppliers", "Clients", "Offers", "Wuzetkas"):
            path = f"/sites/{cls.env.site_id}/lists/{cls.env.lists[name]}"
            cols = cls.reader.get_all(f"{path}/columns", {"$top": "200"})
            data["schema"][name] = lw.sha256_json(sorted(cols, key=lambda c: c.get("name", "")))
        return data

    @staticmethod
    def _looks_synthetic(fields):
        return str(fields.get("CompanyName", "")).startswith(PREFIX) or bool(SYNTHETIC_TITLE.match(str(fields.get("Title", ""))))

    @classmethod
    def preflight_problems(cls, state):
        problems = []
        if state["real"] is None:
            problems.append("brak dostawcy ID 1")
        elif state["real"]["IsDefault"] is not True:
            problems.append("dostawca ID 1 nie jest domyślny (oczekiwano True)")
        if state["count"] != 1:
            problems.append(f"lista Suppliers ma {state['count']} rekordów (oczekiwano 1)")
        if state["zz"]:
            problems.append(f"pozostałości syntetyczne z poprzednich przebiegów (ID {state['zz']}) - nie usuwam ich automatycznie")
        return problems

    def next_nip(self):
        type(self).seq += 1
        return f"999{self.run_num:04d}{self.seq:03d}"

    def create_supplier(self, label, **override):
        """Dodaje dostawcę przez ScopedSupplierBackend (prawdziwy POST); zwraca dane z ID elementu."""
        nip = override.pop("nip", None) or self.next_nip()
        data = {"nip": nip, "name": f"{PREFIX}4B4-{self.run_tag}-{label}", "address1": "ul. Testowa 1", "address2": "00-000 Testowo"}
        data.update(override)
        self.assertEqual(self.scoped.add_supplier(data["nip"], data["name"], data["address1"], data["address2"]), ADD_OK)
        item = self.item_by_title(nip)
        self.assertIsNotNone(item)
        self.assertIn(str(item["id"]), self.registry)
        data["id"] = str(item["id"])
        type(self).labels[data["id"]] = label
        return data

    def item_by_title(self, title):
        found = self.reader.get(self.base, {"$filter": f"fields/Title eq '{title}'", "$expand": "fields", "$top": "5"})["value"]
        return found[0] if found else None

    def item_by_id(self, item_id):
        return self.reader.get(f"{self.base}/{item_id}", {"$expand": "fields"})

    def mark(self):
        return len(self.http_log)

    def writes_since(self, mark):
        return [e for e in self.http_log[mark:] if e["method"] != "GET"]

    def gets_after_last_write(self, mark):
        entries = self.http_log[mark:]
        last = max((i for i, e in enumerate(entries) if e["method"] != "GET"), default=-1)
        return any(e["method"] == "GET" for e in entries[last + 1:])

    def synthetic_defaults(self):
        items = self.reader.get_all(self.base, {"$expand": "fields", "$top": "999"})
        return sorted(str(i["id"]) for i in items if str(i["id"]) in self.registry and i["fields"].get("IsDefault") is True)

    def raw_set_default_flag(self, supplier, value):
        """Przygotowanie stanu testowego: flaga syntetycznego rekordu przez GraphWriter (strażnik dopuszcza tylko rejestr)."""
        etag = self.item_by_id(supplier["id"])["@odata.etag"]
        self.raw_writer.update_item_fields("Suppliers", supplier["id"], {"IsDefault": value}, etag)

    def clear_synthetic_defaults(self):
        """Przywraca czysty punkt wyjścia: zeruje IsDefault wyłącznie na rekordach z rejestru (ID 1 nigdy nie jest widoczne)."""
        items = self.reader.get_all(self.base, {"$expand": "fields", "$top": "999"})
        for item in items:
            item_id = str(item["id"])
            if item_id in self.registry and item["fields"].get("IsDefault") is True:
                self.raw_writer.update_item_fields("Suppliers", item_id, {"IsDefault": False}, item["@odata.etag"])
        self.assertEqual(self.synthetic_defaults(), [])

    def assert_real_supplier_untouched(self):
        now = self.snapshot_real()
        self.assertEqual(now, type(self).before["real"], "prawdziwy dostawca ID 1 został zmieniony!")

    @classmethod
    def snapshot_real(cls):
        real = cls.item_by_id_cls(REAL_ID)
        return {"etag": real.get("@odata.etag"), "version": real["fields"].get("_UIVersionString"),
                "IsDefault": real["fields"].get("IsDefault"), "fields_hash": lw.sha256_json(real["fields"])}

    @classmethod
    def item_by_id_cls(cls, item_id):
        return cls.reader.get(f"{cls.base}/{item_id}", {"$expand": "fields"})

    def record(self, **facts):
        self.report["tests"].setdefault(self._testMethodName, {}).update(facts)

    @classmethod
    def cleanup(cls):
        """Usuwa WYŁĄCZNIE rekordy z rejestru bieżącego przebiegu; przed każdym DELETE ponownie sprawdza ID, Title i ETag."""
        cls.current = "cleanup"
        results = {}
        for item_id in sorted(cls.registry, key=int):
            try:
                got = cls.item_by_id_cls(item_id)
            except GraphError as e:
                results[item_id] = "już nie istnieje" if e.status == 404 else f"BŁĄD odczytu HTTP {e.status}"
                continue
            fields, etag = got.get("fields") or {}, got.get("@odata.etag")
            if item_id == REAL_ID or not (str(fields.get("CompanyName", "")).startswith(PREFIX)
                                          and SYNTHETIC_TITLE.match(str(fields.get("Title", "")))):
                results[item_id] = "POMINIĘTO (to nie jest rekord testowy)"
                continue
            try:
                GraphWriter(cls.env, cls.session.get_token()).delete_item("Suppliers", item_id, etag)
                results[item_id] = "usunięty"
            except GraphError as e:
                results[item_id] = f"BŁĄD usuwania: HTTP {e.status}"
        cls.report["cleanup"] = results
        cls.cleaned = True
        return results

    # =======================================================================
    # testy
    # =======================================================================
    def test_00_preflight_state_is_clean_and_the_real_supplier_is_recorded(self):
        before = type(self).before
        self.assertEqual(self.preflight_problems(before), [])
        self.assertEqual(before["count"], 1)
        self.assertEqual(before["real"]["IsDefault"], True)
        self.assertRegex(before["real"]["etag"], r'^"[0-9a-f-]{36},\d+"$')
        self.assertEqual(self.registry, set())  # rejestr bieżącego przebiegu jest pusty
        self.record(real_supplier_before=before["real"], suppliers_before=before["count"],
                    other_lists_before={k: v["count"] for k, v in before["others"].items()})

    # ----- add / update / delete -----
    def test_01_add_supplier_reads_back_all_fields_with_is_default_false_and_refuses_a_duplicate(self):
        mark = self.mark()
        s = self.create_supplier("add")
        stored = self.item_by_id(s["id"])["fields"]
        self.assertEqual({k: stored.get(k) for k in ("Title", "CompanyName", "AddressP1", "AddressP2", "IsDefault")},
                         {"Title": s["nip"], "CompanyName": s["name"], "AddressP1": s["address1"], "AddressP2": s["address2"],
                          "IsDefault": False})
        self.assertIs(stored["IsDefault"], False)
        self.assertEqual(self.scoped.get_supplier_by_nip(s["nip"]), (int(s["nip"]), s["name"], s["address1"], s["address2"], 0))
        posts = [e for e in self.writes_since(mark) if e["method"] == "POST"]
        self.assertEqual([(e["status"], e["body"]["fields"]["IsDefault"]) for e in posts], [(201, False)])
        mark = self.mark()
        self.assertEqual(self.scoped.add_supplier(s["nip"], f"{PREFIX}DUPLIKAT", "x", "y"), NIP_TAKEN)
        self.assertEqual(self.writes_since(mark), [])  # drugiego POST nie było
        self.assertEqual(self.item_by_id(s["id"])["fields"]["CompanyName"], s["name"])  # istniejący nietknięty
        self.record(post_status=201, duplicate="odmowa bez POST")

    def test_02_update_supplier_changes_the_three_fields_and_never_touches_is_default(self):
        s = self.create_supplier("upd")
        before = self.item_by_id(s["id"])
        mark = self.mark()
        self.assertEqual(self.scoped.update_supplier(s["nip"], s["name"] + "-NOWA", "ul. Nowa 2", "11-111 Nowo"), UPDATE_OK)
        after = self.item_by_id(s["id"])["fields"]
        self.assertEqual((after["CompanyName"], after["AddressP1"], after["AddressP2"], after["Title"]),
                         (s["name"] + "-NOWA", "ul. Nowa 2", "11-111 Nowo", s["nip"]))
        self.assertIs(after["IsDefault"], False)
        patches = [e for e in self.writes_since(mark) if e["method"] == "PATCH"]
        self.assertEqual(len(patches), 1)
        self.assertEqual(set(patches[0]["body"]), {"CompanyName", "AddressP1", "AddressP2"})  # nigdy IsDefault ani Title
        self.assertEqual((patches[0]["status"], patches[0]["if_match"]), (200, before["@odata.etag"]))
        self.record(patch_status=200, if_match=before["@odata.etag"], etag_after=patches[0]["etag"])

    def test_03_update_conflict_412_when_another_user_changed_the_supplier(self):
        s = self.create_supplier("412")
        self.scoped.get_supplier_by_nip(s["nip"])  # ETag zapamiętany przy odczycie
        seen = self.item_by_id(s["id"])["@odata.etag"]
        self.raw_writer.update_item_fields("Suppliers", s["id"], {"AddressP1": "zmiana innego użytkownika"}, seen)
        mark = self.mark()
        result = self.scoped.update_supplier(s["nip"], s["name"] + "-MOJA", "moja zmiana", s["address2"])
        self.assertFalse(result[0])
        self.assertIsInstance(result[1], ConflictMessage)
        patches = [e for e in self.writes_since(mark) if e["method"] == "PATCH"]
        self.assertEqual([(e["status"], e["code"], e["if_match"]) for e in patches], [(412, "resourceModified", seen)])  # bez retry
        after = self.item_by_id(s["id"])["fields"]
        self.assertEqual((after["AddressP1"], after["CompanyName"]), ("zmiana innego użytkownika", s["name"]))
        self.assertEqual(self.scoped.update_supplier(s["nip"], s["name"] + "-MOJA", "moja zmiana", s["address2"]), UPDATE_OK)
        self.record(conflict_status=412, conflict_code="resourceModified")

    def test_04_delete_refuses_a_default_supplier_without_any_delete_request(self):
        s = self.create_supplier("defdel")
        self.raw_set_default_flag(s, True)  # syntetyczny domyślny przygotowany poza testowanym algorytmem
        self.assertEqual(self.item_by_id(s["id"])["fields"]["IsDefault"], True)
        mark = self.mark()
        self.assertEqual(self.scoped.delete_supplier(s["nip"]), DEFAULT_REFUSED)
        self.assertEqual(self.writes_since(mark), [])  # żadnego DELETE
        self.assertIsNotNone(self.item_by_title(s["nip"]))
        self.raw_set_default_flag(s, False)  # powrót do czystego stanu przed kolejnymi testami
        self.record(delete_default="odmowa bez DELETE")

    def test_05_delete_removes_a_non_default_supplier_with_a_concrete_if_match(self):
        s = self.create_supplier("del")
        etag = self.item_by_id(s["id"])["@odata.etag"]
        mark = self.mark()
        self.assertEqual(self.scoped.delete_supplier(s["nip"]), DELETE_OK)
        deletes = [e for e in self.writes_since(mark) if e["method"] == "DELETE"]
        self.assertEqual([(e["status"], e["path"].rsplit("/", 1)[-1], e["if_match"]) for e in deletes], [(204, s["id"], etag)])
        with self.assertRaises(GraphError) as gone:
            self.item_by_id(s["id"])
        self.assertEqual(gone.exception.status, 404)
        self.assertEqual(self.scoped.delete_supplier(s["nip"]), NOT_FOUND)
        again = self.create_supplier("reuse", nip=s["nip"])  # NIP można ponownie wykorzystać po usunięciu
        self.assertNotEqual(again["id"], s["id"])
        self.record(delete_status=204, deleted_id=s["id"], if_match=etag, reused_nip_new_id=again["id"])

    # ----- set_default_supplier (wyłącznie na rekordach syntetycznych) -----
    def test_06_set_default_when_no_synthetic_supplier_was_default(self):
        a = self.create_supplier("A1")
        self.assertEqual(self.synthetic_defaults(), [])
        etag = self.item_by_id(a["id"])["@odata.etag"]
        mark = self.mark()
        self.assertEqual(self.scoped.set_default_supplier(a["nip"]), SET_OK)
        writes = self.writes_since(mark)
        self.assertEqual([(w["method"], w["path"].rsplit("/", 2)[-2], w["body"], w["status"], w["if_match"]) for w in writes],
                         [("PATCH", a["id"], {"IsDefault": True}, 200, etag)])
        self.assertEqual(self.synthetic_defaults(), [a["id"]])
        self.assertTrue(self.gets_after_last_write(mark))  # odczyt weryfikujący
        self.assert_real_supplier_untouched()
        self.record(writes=[(w["method"], self.labels.get(w["path"].rsplit("/", 2)[-2]), w["body"]) for w in writes])

    def test_07_switch_the_default_from_a_to_b_sets_the_target_first(self):
        a, b = self.create_supplier("A2"), self.create_supplier("B2")
        self.assertEqual(self.scoped.set_default_supplier(a["nip"]), SET_OK)
        etags = {x["id"]: self.item_by_id(x["id"])["@odata.etag"] for x in (a, b)}
        mark = self.mark()
        self.assertEqual(self.scoped.set_default_supplier(b["nip"]), SET_OK)
        writes = self.writes_since(mark)
        self.assertEqual([(w["path"].rsplit("/", 2)[-2], w["body"], w["status"], w["if_match"]) for w in writes],
                         [(b["id"], {"IsDefault": True}, 200, etags[b["id"]]), (a["id"], {"IsDefault": False}, 200, etags[a["id"]])])
        self.assertEqual(self.synthetic_defaults(), [b["id"]])
        self.assertTrue(self.gets_after_last_write(mark))
        self.assertEqual(self.scoped.get_default_supplier()[0], int(b["nip"]))
        self.assert_real_supplier_untouched()
        self.record(order="najpierw B=true, potem A=false", writes=[(self.labels[w["path"].rsplit("/", 2)[-2]], w["body"]) for w in writes])

    def test_08_repair_when_two_synthetic_suppliers_are_default(self):
        self.clear_synthetic_defaults()
        a, b = self.create_supplier("A3"), self.create_supplier("B3")
        self.raw_set_default_flag(a, True)
        self.raw_set_default_flag(b, True)
        self.assertEqual(self.synthetic_defaults(), sorted([a["id"], b["id"]]))
        mark = self.mark()
        self.assertEqual(self.scoped.set_default_supplier(a["nip"]), SET_OK)
        writes = self.writes_since(mark)
        self.assertEqual([(w["path"].rsplit("/", 2)[-2], w["body"]) for w in writes], [(b["id"], {"IsDefault": False})])  # wskazany nie jest zapisywany
        self.assertEqual(self.synthetic_defaults(), [a["id"]])
        self.assert_real_supplier_untouched()
        self.record(repair="odznaczono tylko B; A (wskazany) bez zapisu")

    def test_09_idempotent_set_default_sends_no_write(self):
        a = self.create_supplier("A4")
        self.assertEqual(self.scoped.set_default_supplier(a["nip"]), SET_OK)
        mark = self.mark()
        self.assertEqual(self.scoped.set_default_supplier(a["nip"]), SET_OK)
        self.assertEqual(self.writes_since(mark), [])
        self.assertEqual(self.synthetic_defaults(), [a["id"]])
        self.assert_real_supplier_untouched()

    def test_10_missing_nip_sends_no_write(self):
        mark = self.mark()
        for nip in ("9990000000", "abc", ""):
            self.assertEqual(self.scoped.set_default_supplier(nip), NOT_FOUND)
        self.assertEqual(self.writes_since(mark), [])
        self.assert_real_supplier_untouched()

    def test_11_final_read_confirms_exactly_one_synthetic_default_and_the_real_default_is_unchanged(self):
        self.clear_synthetic_defaults()
        a, b, c = (self.create_supplier(x) for x in ("A5", "B5", "C5"))
        self.raw_set_default_flag(a, True)
        self.raw_set_default_flag(b, True)
        self.assertEqual(self.synthetic_defaults(), sorted([a["id"], b["id"]]))
        self.assertEqual(self.scoped.set_default_supplier(c["nip"]), SET_OK)
        self.assertEqual(self.synthetic_defaults(), [c["id"]])
        rows = [r for r in self.scoped.get_suppliers() if r[4] == 1]
        self.assertEqual([r[0] for r in rows], [int(c["nip"])])
        real = self.plain.get_default_supplier()  # widok bez ograniczenia (tylko odczyt): pierwszy wg ID to prawdziwy dostawca
        self.assertEqual(real[0], int(self.item_by_id(REAL_ID)["fields"]["Title"]))
        self.assert_real_supplier_untouched()
        self.record(final_synthetic_defaults=1)

    def test_12_update_of_a_default_supplier_keeps_the_flag(self):
        a = self.create_supplier("A6")
        self.assertEqual(self.scoped.set_default_supplier(a["nip"]), SET_OK)
        mark = self.mark()
        self.assertEqual(self.scoped.update_supplier(a["nip"], a["name"] + "-NOWA", "ul. D", "22-222"), UPDATE_OK)
        for write in self.writes_since(mark):
            self.assertNotIn("IsDefault", write["body"])
        self.assertIs(self.item_by_id(a["id"])["fields"]["IsDefault"], True)
        self.assertEqual(self.scoped.delete_supplier(a["nip"]), DEFAULT_REFUSED)
        self.assert_real_supplier_untouched()

    # ----- strażnik na żywo -----
    def test_13_the_http_guard_blocks_forbidden_requests_before_transmission(self):
        items_url = f"https://graph.microsoft.com/v1.0{self.base}"
        prod_url = f"https://graph.microsoft.com/v1.0/sites/{self.prod.site_id}/lists"
        fake_etag = '"00000000-0000-0000-0000-000000000001,1"'
        mark, blocked_before = self.mark(), len(self.blocked)
        attempts = [  # wszystkie nieszkodliwe nawet gdyby strażnik zawiódł (nieistniejące ID / odczyt PROD)
            ("PATCH nieistniejące ID spoza rejestru",
             lambda: requests.request("PATCH", f"{items_url}/99999999/fields", json={"IsDefault": False}, headers={"If-Match": fake_etag})),
            ("DELETE nieistniejące ID spoza rejestru",
             lambda: requests.request("DELETE", f"{items_url}/99999999", headers={"If-Match": fake_etag})),
            ("DELETE z If-Match: * (nieistniejące ID)",
             lambda: requests.request("DELETE", f"{items_url}/99999999", headers={"If-Match": "*"})),
            ("DELETE bez If-Match (nieistniejące ID)",
             lambda: requests.request("DELETE", f"{items_url}/99999999")),
            ("GET witryny PROD", lambda: requests.request("GET", prod_url)),
        ]
        for label, attempt in attempts:
            with self.subTest(label), self.assertRaises(AssertionError):
                attempt()
        self.assertEqual(len(self.blocked) - blocked_before, len(attempts))
        self.assertEqual([e for e in self.http_log[mark:] if e["method"] != "GET"], [])  # żadne z nich nie zostało wysłane
        self.record(blocked_live=[b["powód"] for b in self.blocked[blocked_before:]])

    # ----- sprzątanie i weryfikacja końcowa -----
    def test_99_cleanup_and_verify_everything_is_back_to_the_state_before(self):
        results = self.cleanup()
        self.assertTrue(results)
        self.assertEqual({v for v in results.values()}, {"usunięty", "już nie istnieje"}, results)
        for item_id in self.registry:
            with self.assertRaises(GraphError) as gone:
                self.item_by_id(item_id)
            self.assertEqual(gone.exception.status, 404, item_id)
        after, before = self.snapshot(), type(self).before
        self.assertEqual(after["real"], before["real"], "prawdziwy dostawca ID 1 różni się od stanu sprzed testów!")
        self.assertEqual(after["count"], before["count"])
        self.assertEqual(after["ids"], before["ids"])
        self.assertEqual(after["zz"], [])
        self.assertEqual(after["others"], before["others"])
        self.assertEqual(after["schema"], before["schema"])
        wrong = [e for e in self.http_log if e["method"] != "GET" and "…/Suppliers" not in e["path"]]
        self.assertEqual(wrong, [])
        self.assertEqual([e for e in self.http_log if e["method"] != "GET" and re.search(r"/items/1(/|$)", e["path"])], [])
        self.report["verification"] = {
            "real_supplier_after": after["real"], "real_supplier_unchanged": after["real"] == before["real"],
            "suppliers_count_before": before["count"], "suppliers_count_after": after["count"],
            "other_lists_unchanged": after["others"] == before["others"], "schema_unchanged": after["schema"] == before["schema"],
            "no_synthetic_left": after["zz"] == [], "created_ids": sorted(self.registry, key=int), "cleanup": results}


if __name__ == "__main__":
    unittest.main()
