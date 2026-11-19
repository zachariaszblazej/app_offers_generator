"""Test integracyjny zapisu klientów (etap 4A) na SharePoint DEV - WYŁĄCZNIE syntetyczne rekordy `ZZTEST-`.

Uruchomienie (wymaga logowania MSAL lub trwałego cache):
    $env:HANTECH_LIVE_SP_WRITE_TESTS = "1"
    python -m unittest tests.sharepoint_client_write_live_test -v

Zasady bezpieczeństwa (wymuszane przez strażnika HTTP `WriteGuard`, który blokuje żądanie PRZED wysłaniem):
* wyłącznie witryna DEV i wyłącznie lista Clients; żadnych żądań do PROD,
* POST tylko z CompanyName i Alias zaczynającymi się od `ZZTEST-` oraz syntetycznym NIP (Title) `[0]999xxxxxx`,
* PATCH i DELETE wyłącznie dla ID elementów utworzonych przez ten test (rejestr ID z odpowiedzi POST),
* PATCH wyłącznie z konkretnym If-Match (nigdy `*`),
* sprzątanie po dokładnych ID (z ponowną weryfikacją prefiksu przed DELETE); nic innego nie jest usuwane,
* przed testem i po nim porównywane są: liczność i ETagi wszystkich elementów czterech list oraz odcisk schematu list.
Awarie 429/503/brak połączenia są wstrzykiwane na poziomie HTTP (obiekty `requests.Response` / `ConnectionError`),
bo prawdziwego throttlingu nie da się wywołać na żądanie. Szczegółowy raport (bez tokenów) trafia poza repozytorium.
"""
import hashlib
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

from src.data.backends import BackendContext, SharePointBackend  # noqa: E402
from src.data.errors import ConflictMessage, ItemNotFoundError, ReadOnlyBackendError, SharePointError  # noqa: E402
from src.integrations.sharepoint import get_environment  # noqa: E402
from src.integrations.sharepoint.graph_client import GraphError  # noqa: E402
from src.integrations.sharepoint.migration import datadir  # noqa: E402
from src.integrations.sharepoint.reader import RetryingGraphClient  # noqa: E402
from src.integrations.sharepoint.session import SharePointSession  # noqa: E402
from src.integrations.sharepoint.writer import GraphWriter  # noqa: E402

LIVE = os.environ.get("HANTECH_LIVE_SP_WRITE_TESTS") == "1"
PREFIX = "ZZTEST-"
LOGIN_HOSTS = ("login.microsoftonline.com", "login.windows.net")
GRAPH_HOST = "graph.microsoft.com"
SYNTHETIC_TITLE = re.compile(r"^0?999\d{6,7}$")
EXPECTED_REAL_CLIENTS = 39
OTHER_LISTS = ("Suppliers", "Offers", "Wuzetkas")
CLIENT_COLUMNS = {"Title", "CompanyName", "AddressP1", "AddressP2", "Alias", "TerminRealizacji", "TerminPlatnosci",
                  "WarunkiDostawy", "WaznoscOferty", "Gwarancja", "Cena"}
ALIAS_TAKEN = (False, "Alias już istnieje dla innego klienta")
NIP_TAKEN = (False, "Klient z tym NIP już istnieje w bazie")
ADD_OK = (True, "Klient został pomyślnie dodany do bazy")
UPDATE_OK = (True, "Dane klienta zostały zaktualizowane")
EXT_OK = (True, "Zapisano dodatkowe pola klienta")
DELETE_OK = (True, "Klient został usunięty z bazy")
NOT_FOUND = (False, "Klient nie został znaleziony")


class WriteGuard:
    """Czysta logika dopuszczania żądań: zwraca None albo zgłasza AssertionError z powodem blokady."""

    def __init__(self, env, prod, created_ids):
        self.site = f"/v1.0/sites/{env.site_id}".lower()
        self.items = f"{self.site}/lists/{env.lists['Clients']}/items".lower()
        self.prod_markers = {prod.site_id.lower(), *(v.lower() for v in prod.lists.values())}
        self.created_ids = created_ids

    def check(self, method, url, body=None, headers=None):
        parsed = urlparse(url)
        host, path = parsed.netloc.lower(), parsed.path.lower()
        if host in LOGIN_HOSTS:
            return
        if host != GRAPH_HOST:
            raise AssertionError(f"ZABLOKOWANE: host {host}")
        if any(marker in path for marker in self.prod_markers):
            raise AssertionError("ZABLOKOWANE: identyfikator PROD")
        if not path.startswith(self.site):
            raise AssertionError(f"ZABLOKOWANE: ścieżka spoza witryny DEV: {path[:60]}")
        method = method.upper()
        if method == "GET":
            return
        if not path.startswith(self.items):
            raise AssertionError(f"ZABLOKOWANE: zapis poza listą Clients: {method} {path[-40:]}")
        rest = path[len(self.items):]
        if method == "POST":
            fields = (body or {}).get("fields") or {}
            if rest or not SYNTHETIC_TITLE.match(str(fields.get("Title", ""))):
                raise AssertionError("ZABLOKOWANE: POST bez syntetycznego Title")
            if not (str(fields.get("CompanyName", "")).startswith(PREFIX) and str(fields.get("Alias", "")).startswith(PREFIX)):
                raise AssertionError("ZABLOKOWANE: POST bez prefiksu ZZTEST- w CompanyName i Alias")
            return
        m = re.fullmatch(r"/(\d+)(/fields)?", rest)
        if not m or m.group(1) not in self.created_ids:
            raise AssertionError(f"ZABLOKOWANE: {method} elementu spoza rejestru testu: {rest}")
        if method == "PATCH":
            if not m.group(2) or not (headers or {}).get("If-Match") or (headers or {}).get("If-Match") == "*":
                raise AssertionError("ZABLOKOWANE: PATCH bez konkretnego If-Match")
            if set(body or {}) - CLIENT_COLUMNS:
                raise AssertionError("ZABLOKOWANE: PATCH nieznanego pola")
            return
        if method == "DELETE" and not m.group(2):
            return
        raise AssertionError(f"ZABLOKOWANE: {method} {rest}")


class WriteGuardLogicTests(unittest.TestCase):
    """Zawsze uruchamiane (offline): strażnik musi blokować wszystko poza rekordami testu."""

    def setUp(self):
        self.env, self.prod = get_environment("DEV"), get_environment("PROD")
        self.created = {"41"}
        self.guard = WriteGuard(self.env, self.prod, self.created)
        base = f"https://graph.microsoft.com/v1.0/sites/{self.env.site_id}/lists/{self.env.lists['Clients']}/items"
        self.base = base

    def blocked(self, method, url, body=None, headers=None):
        with self.assertRaises(AssertionError):
            self.guard.check(method, url, body, headers)

    def test_allows_only_the_test_records(self):
        ok_post = {"fields": {"Title": "9990000011", "CompanyName": "ZZTEST-A", "Alias": "ZZTEST-A"}}
        self.guard.check("POST", self.base, ok_post)
        self.guard.check("PATCH", f"{self.base}/41/fields", {"Alias": "ZZTEST-B"}, {"If-Match": '"e,1"'})
        self.guard.check("DELETE", f"{self.base}/41")
        self.guard.check("GET", f"{self.base}/2")
        self.guard.check("POST", "https://login.microsoftonline.com/x/oauth2/v2.0/token")

    def test_blocks_writes_to_real_records_and_unknown_ids(self):
        for real_id in ("2", "3", "40", "42", "999"):
            self.blocked("DELETE", f"{self.base}/{real_id}")
            self.blocked("PATCH", f"{self.base}/{real_id}/fields", {"Alias": "X"}, {"If-Match": '"e,1"'})

    def test_blocks_non_synthetic_posts(self):
        for fields in ({"Title": "1234563218", "CompanyName": "ZZTEST-A", "Alias": "ZZTEST-A"},
                       {"Title": "9990000011", "CompanyName": "Prawdziwa Firma", "Alias": "ZZTEST-A"},
                       {"Title": "9990000011", "CompanyName": "ZZTEST-A", "Alias": "ALFA"},
                       {"CompanyName": "ZZTEST-A", "Alias": "ZZTEST-A"}):
            self.blocked("POST", self.base, {"fields": fields})
        self.blocked("POST", f"{self.base}/41", {"fields": {"Title": "9990000011", "CompanyName": "ZZTEST-A", "Alias": "ZZTEST-A"}})

    def test_blocks_patch_without_a_concrete_if_match_and_unknown_fields(self):
        self.blocked("PATCH", f"{self.base}/41/fields", {"Alias": "ZZTEST-B"}, {})
        self.blocked("PATCH", f"{self.base}/41/fields", {"Alias": "ZZTEST-B"}, {"If-Match": "*"})
        self.blocked("PATCH", f"{self.base}/41/fields", {"Nieznane": "x"}, {"If-Match": '"e,1"'})
        self.blocked("PATCH", f"{self.base}/41", {"Alias": "ZZTEST-B"}, {"If-Match": '"e,1"'})

    def test_blocks_other_lists_prod_other_sites_and_hosts(self):
        for name in ("Suppliers", "Offers", "Wuzetkas"):
            other = f"https://graph.microsoft.com/v1.0/sites/{self.env.site_id}/lists/{self.env.lists[name]}/items"
            self.blocked("DELETE", f"{other}/41")
            self.blocked("POST", other, {"fields": {"Title": "9990000011", "CompanyName": "ZZTEST-A", "Alias": "ZZTEST-A"}})
        prod_url = f"https://graph.microsoft.com/v1.0/sites/{self.prod.site_id}/lists/{self.prod.lists['Clients']}/items"
        self.blocked("GET", prod_url)
        self.blocked("DELETE", f"{prod_url}/41")
        self.blocked("GET", "https://graph.microsoft.com/v1.0/me/drive")
        self.blocked("GET", "https://example.com/x")
        self.blocked("POST", f"https://graph.microsoft.com/v1.0/sites/{self.env.site_id}/lists")


def sha256_json(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def fake_response(status, code, message, headers=None, url=""):
    resp = requests.Response()
    resp.status_code = status
    resp._content = json.dumps({"error": {"code": code, "message": message}}).encode("utf-8")
    resp.headers.update(headers or {})
    resp.encoding = "utf-8"
    resp.url = url
    return resp


@unittest.skipUnless(LIVE, "Test na żywo - ustaw HANTECH_LIVE_SP_WRITE_TESTS=1 (SharePoint DEV, rekordy ZZTEST-).")
class LiveClientWriteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.env, cls.prod = get_environment("DEV"), get_environment("PROD")
        assert cls.env.name == "DEV" and not cls.env.is_prod
        cls.created_ids, cls.faults, cls.http_log, cls.current = set(), [], [], "setup"
        cls.guard = WriteGuard(cls.env, cls.prod, cls.created_ids)
        cls.report = {"started": time.strftime("%Y-%m-%d %H:%M:%S"), "environment": "DEV", "tests": {}}
        cls.run_tag = time.strftime("%H%M%S")
        cls.run_num = int(time.time()) % 10000
        cls.nip_seq = 0
        cls.tag_seq = 0
        cls.clock_skew = 0.0
        cls._install_http_guard()

        cls.session = SharePointSession()
        if not cls.session.resume():
            cls.session.sign_in(interactive_log=print)
        cls.reader = RetryingGraphClient(cls.env, cls.session.get_token())
        cls.raw_writer = GraphWriter(cls.env, cls.session.get_token())
        cls.popups, cls.logs = [], []
        context = BackendContext(offers_folder=lambda: "", wz_folder=lambda: "", popups_enabled=lambda: False,
                                 show_error=lambda title, message: cls.popups.append((title, message)),
                                 log=lambda *a, **k: cls.logs.append(a))
        cls.backend = SharePointBackend(context, cls.session, cls.env, clock=lambda: time.monotonic() + cls.clock_skew)
        cls.base = f"/sites/{cls.env.site_id}/lists/{cls.env.lists['Clients']}/items"
        cls.before = cls.snapshot()
        cls.cleaned = False

    @classmethod
    def tearDownClass(cls):
        try:
            if not cls.cleaned:
                cls.cleanup()
        finally:
            cls._uninstall_http_guard()
            cls.report["finished"] = time.strftime("%Y-%m-%d %H:%M:%S")
            cls.report["http_requests"] = dict(Counter(f"{e['method']} {e['status']}" for e in cls.http_log if "status" in e))
            cls.report["http_log"] = cls.http_log
            out_dir = datadir.assert_outside_repo(datadir.migration_dir())
            os.makedirs(out_dir, exist_ok=True)
            path = os.path.join(out_dir, f"backend_write_4a_{time.strftime('%Y%m%d%H%M%S')}.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump(cls.report, f, ensure_ascii=False, indent=1)
            print(f"\nRaport szczegółowy (poza repozytorium): {path}")

    def setUp(self):
        type(self).current = self._testMethodName

    # ------------------------------------------------------------------
    # strażnik HTTP, wstrzykiwanie awarii i dziennik żądań (bez tokenów)
    # ------------------------------------------------------------------
    @classmethod
    def _install_http_guard(cls):
        original = requests.Session.request

        def guarded(session, method, url, *args, **kwargs):
            method = method.upper()
            host = urlparse(url).netloc.lower()
            body, headers = kwargs.get("json"), kwargs.get("headers") or {}
            cls.guard.check(method, url, body, headers)  # AssertionError => żądanie NIE zostaje wysłane
            if host in LOGIN_HOSTS:
                return original(session, method, url, *args, **kwargs)
            path = urlparse(url).path
            entry = {"test": cls.current, "method": method,
                     "path": re.sub(r"^/v1\.0/sites/[^/]+/lists/[0-9a-f-]+", "…/Clients", path)}
            if method != "GET":
                entry["if_match"] = headers.get("If-Match")
                entry["body_keys"] = sorted((body or {}).get("fields", body or {}))
            fault = cls.faults[0] if method != "GET" and cls.faults and cls.faults[0]["method"] == method else None
            if fault:
                cls.faults.pop(0)
                entry["injected"] = fault["kind"]
                if fault["kind"] == "raise":
                    entry["status"] = None
                    cls.http_log.append(entry)
                    raise requests.ConnectionError("brak połączenia (wstrzyknięte w teście)")
                if fault["kind"] == "status":
                    entry["status"], entry["code"] = fault["status"], fault.get("code", "generalException")
                    cls.http_log.append(entry)
                    return fake_response(fault["status"], entry["code"], "wstrzyknięte w teście", fault.get("headers"), url)
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
                cls.created_ids.add(str(response.json()["id"]))
                entry["created_id"] = str(response.json()["id"])
            cls.http_log.append(entry)
            if fault and fault["kind"] == "lose":
                entry["injected"] = "lose (operacja wykonana, odpowiedź utracona)"
                raise requests.ConnectionError("odpowiedź utracona (wstrzyknięte w teście)")
            return response

        cls._guard_patch = mock.patch.object(requests.Session, "request", guarded)
        cls._guard_patch.start()

    @classmethod
    def _uninstall_http_guard(cls):
        cls._guard_patch.stop()

    # ------------------------------------------------------------------
    # pomocnicze
    # ------------------------------------------------------------------
    @classmethod
    def snapshot(cls):
        """Liczność i ETagi wszystkich elementów (zmiana czegokolwiek zmienia ETag) + odcisk schematu każdej listy."""
        data = {"lists": {}, "schema": {}}
        for name in ("Suppliers", "Clients", "Offers", "Wuzetkas"):
            list_path = f"/sites/{cls.env.site_id}/lists/{cls.env.lists[name]}"
            items = cls.reader.get_all(f"{list_path}/items", {"$select": "id", "$top": "999"})
            data["lists"][name] = sorted((str(i["id"]), i.get("@odata.etag")) for i in items)
            columns = cls.reader.get_all(f"{list_path}/columns", {"$top": "200"})
            data["schema"][name] = sha256_json(sorted(columns, key=lambda c: c.get("name", "")))
        clients = cls.reader.get_all(cls.base, {"$expand": "fields", "$top": "999"})
        data["real_clients"] = {str(i["id"]): (i.get("@odata.etag"), i["fields"]) for i in clients
                                if not str((i.get("fields") or {}).get("CompanyName", "")).startswith(PREFIX)}
        return data

    @classmethod
    def count_clients(cls):
        return len(cls.reader.get_all(cls.base, {"$select": "id", "$top": "999"}))

    @classmethod
    def item_by_title(cls, title):
        found = cls.reader.get(cls.base, {"$filter": f"fields/Title eq '{title}'", "$expand": "fields", "$top": "5"})["value"]
        return found[0] if found else None

    @classmethod
    def next_nip(cls, leading_zero=False):
        """Syntetyczny NIP `999xxxxxxx` (lub `0999xxxxxx`): 4 cyfry z czasu uruchomienia + licznik, zawsze 10 znaków."""
        cls.nip_seq += 1
        if leading_zero:
            return f"0999{cls.run_num:04d}{cls.nip_seq:02d}"
        return f"999{cls.run_num:04d}{cls.nip_seq:03d}"

    @classmethod
    def variant(cls, alias):
        """Ten sam alias różniący się wyłącznie wielkością liter (prefiks `ZZTEST-` zostaje bez zmian)."""
        return PREFIX + alias[len(PREFIX):].swapcase()

    def create(self, **override):
        """Dodaje klienta przez backend (prawdziwy POST); zwraca słownik z danymi i ID elementu."""
        nip = override.pop("nip", None) or self.next_nip()
        type(self).tag_seq += 1
        tag = override.pop("tag", None) or f"{PREFIX}4A-{self.run_tag}-{type(self).tag_seq}"
        data = {"nip": nip, "company": tag, "address1": "ul. Testowa 1", "address2": "00-000 Testowo", "alias": tag}
        data.update(override)
        result = self.backend.add_client(data["nip"], data["company"], data["address1"], data["address2"], data["alias"])
        self.assertEqual(result, ADD_OK, result)
        item = self.item_by_title(nip)
        self.assertIsNotNone(item)
        self.assertIn(str(item["id"]), self.created_ids)
        data["id"] = str(item["id"])
        return data

    def writes_since(self, index):
        return [e for e in self.http_log[index:] if e["method"] != "GET" and e.get("test") == self.current]

    def mark(self):
        return len(self.http_log)

    def skip_cooldown(self):
        type(self).clock_skew += 20

    @classmethod
    def cleanup(cls):
        """Usuwa wyłącznie elementy z rejestru testu (dokładne ID), po ponownej weryfikacji prefiksu i syntetycznego Title."""
        cls.current = "cleanup"
        results = {}
        for item_id in sorted(cls.created_ids, key=int):
            try:
                got = cls.reader.get(f"{cls.base}/{item_id}", {"$expand": "fields($select=Title,CompanyName,Alias)"})
            except GraphError as e:
                results[item_id] = "już nie istnieje" if e.status == 404 else f"błąd odczytu {e.status}"
                continue
            fields = got.get("fields") or {}
            if not (str(fields.get("CompanyName", "")).startswith(PREFIX) and SYNTHETIC_TITLE.match(str(fields.get("Title", "")))):
                results[item_id] = "POMINIĘTO (to nie jest rekord testowy)"
                continue
            try:
                GraphWriter(cls.env, cls.session.get_token()).delete_item("Clients", item_id)
                results[item_id] = "usunięty"
            except GraphError as e:
                results[item_id] = f"BŁĄD usuwania: HTTP {e.status}"
        cls.report["cleanup"] = results
        cls.cleaned = True
        return results

    def record(self, **facts):
        self.report["tests"].setdefault(self._testMethodName, {}).update(facts)

    # ------------------------------------------------------------------
    # testy
    # ------------------------------------------------------------------
    def test_00_preflight_state_is_clean(self):
        before = type(self).before
        self.assertEqual(len(before["lists"]["Clients"]), EXPECTED_REAL_CLIENTS)
        self.assertEqual(len(before["real_clients"]), EXPECTED_REAL_CLIENTS)
        self.assertEqual({n: len(before["lists"][n]) for n in OTHER_LISTS}, {"Suppliers": 1, "Offers": 417, "Wuzetkas": 227})
        leftovers = [i for i in self.reader.get_all(self.base, {"$expand": "fields($select=Title,CompanyName)", "$top": "999"})
                     if str(i["fields"].get("CompanyName", "")).startswith(PREFIX) or SYNTHETIC_TITLE.match(str(i["fields"].get("Title", "")))]
        self.assertEqual(leftovers, [], "Pozostałości po poprzednich testach - przerwano bez usuwania obcych elementów.")
        self.assertTrue(self.backend.is_available())
        self.record(clients_before=EXPECTED_REAL_CLIENTS, other_lists_before={n: len(before["lists"][n]) for n in OTHER_LISTS})

    def test_01_add_client_and_read_it_back_by_nip(self):
        mark = self.mark()
        c = self.create()
        self.assertEqual(self.backend.get_client_by_nip(c["nip"]), (int(c["nip"]), c["company"], c["address1"], c["address2"], c["alias"]))
        self.assertEqual(self.backend.get_client_by_nip(int(c["nip"]))[0], int(c["nip"]))
        self.assertIn((int(c["nip"]), c["company"], c["address1"], c["address2"], c["alias"]), self.backend.get_clients())
        self.assertEqual(self.backend.validate_nip(c["nip"]), NIP_TAKEN)
        stored = self.reader.get(f"{self.base}/{c['id']}", {"$expand": "fields"})
        self.assertEqual({k: v for k, v in stored["fields"].items() if k in CLIENT_COLUMNS},
                         {"Title": c["nip"], "CompanyName": c["company"], "AddressP1": c["address1"],
                          "AddressP2": c["address2"], "Alias": c["alias"]})
        self.assertRegex(stored["@odata.etag"], r'^"[0-9a-f-]{36},\d+"$')
        posts = [e for e in self.writes_since(mark) if e["method"] == "POST"]
        self.assertEqual([(e["status"], sorted(e["body_keys"])) for e in posts],
                         [(201, ["AddressP1", "AddressP2", "Alias", "CompanyName", "Title"])])
        self.assertEqual(self.count_clients(), EXPECTED_REAL_CLIENTS + len(self.created_ids))
        self.record(post_status=201, etag_after_create=stored["@odata.etag"])

    def test_02_leading_zero_nip_is_kept_and_conflicts(self):
        c = self.create(nip=self.next_nip(leading_zero=True))
        self.assertTrue(c["nip"].startswith("0"))
        self.assertEqual(self.item_by_title(c["nip"])["fields"]["Title"], c["nip"])
        self.assertEqual(self.backend.get_client_by_nip(c["nip"])[0], int(c["nip"]))
        self.assertEqual(self.backend.get_client_by_nip(int(c["nip"]))[0], int(c["nip"]))  # bez zera wiodącego
        mark = self.mark()
        self.assertEqual(self.backend.add_client(c["nip"], f"{PREFIX}DRUGI", "a", "b", f"{PREFIX}DRUGI-{self.run_tag}"), NIP_TAKEN)
        self.assertEqual(self.backend.validate_nip(c["nip"]), NIP_TAKEN)
        self.assertEqual(self.writes_since(mark), [])  # wykryte przed jakimkolwiek POST
        self.record(leading_zero_nip=c["nip"], conflict="wykryty odczytem przed POST")

    def test_03_identical_nip_conflict(self):
        c = self.create()
        mark, count = self.mark(), self.count_clients()
        self.assertEqual(self.backend.add_client(c["nip"], f"{PREFIX}INNY", "a", "b", f"{PREFIX}INNY-{self.run_tag}"), NIP_TAKEN)
        self.assertEqual(self.writes_since(mark), [])
        self.assertEqual(self.count_clients(), count)

    def test_04_alias_conflicts_exact_and_case_insensitive(self):
        c = self.create()
        mark, count = self.mark(), self.count_clients()
        for alias in (c["alias"], self.variant(c["alias"]), self.variant(self.variant(c["alias"]))):
            self.assertEqual(self.backend.add_client(self.next_nip(), f"{PREFIX}X", "a", "b", alias), ALIAS_TAKEN, alias)
        self.assertEqual(self.writes_since(mark), [])
        self.assertEqual(self.count_clients(), count)
        other = self.create()
        self.assertEqual(self.backend.update_client(other["nip"], other["company"], "a", "b", self.variant(c["alias"])), ALIAS_TAKEN)
        self.assertEqual(self.backend.update_client(other["nip"], other["company"], "a", "b", c["alias"]), ALIAS_TAKEN)
        self.record(alias_conflicts="dokładny i różniący się wielkością liter - wykryte odczytem przed zapisem")

    def test_05_conflicts_detected_only_by_post_use_a_verification_read(self):
        c = self.create()
        count, created_before = self.count_clients(), set(self.created_ids)
        mark = self.mark()
        with mock.patch.object(self.backend, "_alias_in_use", return_value=False):
            result = self.backend.add_client(self.next_nip(), f"{PREFIX}Y", "a", "b", self.variant(c["alias"]))
        self.assertEqual(result, ALIAS_TAKEN)
        with mock.patch.object(self.backend, "validate_nip", return_value=(True, "ok")):
            result_nip = self.backend.add_client(c["nip"], f"{PREFIX}Z", "a", "b", f"{PREFIX}Z-{self.run_tag}")
        self.assertEqual(result_nip, NIP_TAKEN)
        posts = [e for e in self.writes_since(mark) if e["method"] == "POST"]
        self.assertEqual([(e["status"], e["code"]) for e in posts], [(400, "invalidRequest")] * 2)
        self.assertTrue(all("unique constraints" in e["message"] for e in posts))
        self.assertEqual(self.count_clients(), count)
        self.assertEqual(set(self.created_ids), created_before)
        self.record(post_conflict_status=400, post_conflict_code="invalidRequest", post_conflict_message=posts[0]["message"])

    def test_06_update_ordinary_and_extended_fields_with_etag(self):
        c = self.create()
        mark = self.mark()
        etag0 = self.item_by_title(c["nip"])["@odata.etag"]
        self.assertEqual(self.backend.update_client(c["nip"], c["company"] + "-B", "ul. Nowa 2", "11-111 Nowo", self.variant(c["alias"])), UPDATE_OK)
        self.assertEqual(self.backend.get_client_by_nip(c["nip"]), (int(c["nip"]), c["company"] + "-B", "ul. Nowa 2", "11-111 Nowo", self.variant(c["alias"])))
        self.assertEqual(self.backend.set_client_extended_fields(c["nip"], "30 dni", "14 dni", "DAP\nlinia 2", "7 dni", "24 mies.", "netto"), EXT_OK)
        row = [r for r in self.backend.get_clients(True) if r[0] == int(c["nip"])][0]
        self.assertEqual(row[5:], ("30 dni", "14 dni", "DAP\nlinia 2", "7 dni", "24 mies.", "netto"))
        self.assertEqual(self.backend.set_client_extended_fields(c["nip"], "", None, "DAP\nlinia 2"), EXT_OK)
        row = [r for r in self.backend.get_clients(True) if r[0] == int(c["nip"])][0]
        self.assertEqual(row[5:], ("", "", "DAP\nlinia 2", "", "", ""))
        stored = self.reader.get(f"{self.base}/{c['id']}", {"$expand": "fields"})["fields"]
        self.assertFalse({"TerminRealizacji", "TerminPlatnosci", "WaznoscOferty", "Gwarancja", "Cena"} & set(stored))  # puste = brak klucza
        self.assertEqual(self.backend.update_client(c["nip"], c["company"] + "-B", "ul. Nowa 2", "", self.variant(c["alias"])), UPDATE_OK)
        self.assertEqual(self.backend.get_client_by_nip(c["nip"])[3], "")
        self.assertEqual(self.backend.update_client(c["nip"], c["company"] + "-B", "ul. Nowa 2", "", self.variant(c["alias"])), UPDATE_OK)  # bez zmian
        patches = [e for e in self.writes_since(mark) if e["method"] == "PATCH"]
        self.assertEqual([e["status"] for e in patches], [200, 200, 200, 200])  # ostatnie wywołanie nic nie wysłało
        for e in patches:
            self.assertRegex(e["if_match"], r'^"[0-9a-f-]{36},\d+"$')
        self.assertEqual(patches[0]["if_match"], etag0)
        etags = [patches[0]["if_match"]] + [p["etag"] for p in patches[:-1]]
        self.assertEqual([p["if_match"] for p in patches], etags)  # każdy zapis używa ETagu poprzedniego zapisu
        self.record(patch_status=200, if_match_chain=[p["if_match"] for p in patches], etag_after=patches[-1]["etag"])

    def test_07_update_and_extended_fields_of_a_missing_item_are_errors_without_any_write(self):
        count, mark = self.count_clients(), self.mark()
        missing = self.next_nip()
        self.assertEqual(self.backend.update_client(missing, f"{PREFIX}N", "a", "b", f"{PREFIX}N-{self.run_tag}"), NOT_FOUND)
        self.assertEqual(self.backend.set_client_extended_fields(missing, "x"), NOT_FOUND)
        self.assertEqual(self.writes_since(mark), [])
        self.assertEqual(self.count_clients(), count)
        self.assertIsNone(self.item_by_title(missing))
        with self.assertRaises(ItemNotFoundError):  # PATCH po ID, którego nie ma: prawdziwe 404 itemNotFound
            self._patch_missing_id()
        self.record(update_and_extended_of_missing="(False, 'Klient nie został znaleziony') bez żądania zapisu")

    def test_07b_item_deleted_between_lookup_and_patch_gives_real_404_and_not_found(self):
        c = self.create()
        self.backend.get_client_by_nip(c["nip"])  # ETag zapamiętany, więc PATCH naprawdę zostanie wysłany
        snapshot = self.backend._find_client(c["nip"])
        self.raw_writer.delete_item("Clients", c["id"])  # „inny użytkownik” usuwa klienta po wyszukaniu
        self.assertIsNone(self.item_by_title(c["nip"]))
        mark = self.mark()
        with mock.patch.object(self.backend, "_find_client", return_value=snapshot):
            self.assertEqual(self.backend.update_client(c["nip"], c["company"] + "-X", "a", "b", c["alias"]), NOT_FOUND)
            self.assertEqual(self.backend.set_client_extended_fields(c["nip"], "30 dni"), NOT_FOUND)
        patches = [e for e in self.writes_since(mark) if e["method"] == "PATCH"]
        self.assertEqual([(e["status"], e["code"]) for e in patches], [(404, "itemNotFound")] * 2)
        self.assertEqual([e["path"].rsplit("/", 2)[-2] for e in patches], [c["id"]] * 2)
        self.assertIsNone(self.item_by_title(c["nip"]))  # nic nie zostało odtworzone
        self.record(patch_404_status=404, patch_404_code="itemNotFound")

    def _patch_missing_id(self):
        # test-level strażnik dopuszcza tylko ID z rejestru, więc dodajemy ID nieistniejącego elementu na czas tego jednego żądania
        self.created_ids.add("99999999")
        try:
            self.backend._write(lambda w: w.update_item_fields("Clients", "99999999", {"Alias": f"{PREFIX}Q"}, '"x,1"'), item_scope=True)
        finally:
            self.created_ids.discard("99999999")

    def test_08_etag_conflict_412_is_reported_and_not_retried(self):
        c = self.create()
        self.backend.get_client_by_nip(c["nip"])  # użytkownik „widzi” klienta (ETag zapamiętany)
        seen = self.item_by_title(c["nip"])
        other = self.raw_writer.update_item_fields("Clients", c["id"], {"AddressP1": "zmiana przez innego użytkownika"}, seen["@odata.etag"])
        self.assertNotEqual(other.etag, seen["@odata.etag"])
        mark = self.mark()
        result = self.backend.update_client(c["nip"], c["company"] + "-MOJ", "moja zmiana", c["address2"], c["alias"])
        self.assertFalse(result[0])
        self.assertIsInstance(result[1], ConflictMessage)
        self.assertIn("zmienione przez innego użytkownika", result[1])
        patches = [e for e in self.writes_since(mark) if e["method"] == "PATCH"]
        self.assertEqual([(e["status"], e["code"], e["if_match"]) for e in patches], [(412, "resourceModified", seen["@odata.etag"])])
        after = self.item_by_title(c["nip"])
        self.assertEqual(after["fields"]["AddressP1"], "zmiana przez innego użytkownika")  # dane innego użytkownika nietknięte
        self.assertEqual(after["fields"]["CompanyName"], c["company"])
        self.assertEqual(after["@odata.etag"], other.etag)
        retry = self.backend.update_client(c["nip"], c["company"] + "-MOJ", "moja zmiana", c["address2"], c["alias"])
        self.assertEqual(retry, UPDATE_OK)  # po odświeżeniu odczytu zapis przechodzi
        self.assertEqual(self.item_by_title(c["nip"])["fields"]["CompanyName"], c["company"] + "-MOJ")
        self.record(conflict_status=412, conflict_code="resourceModified", stale_if_match=seen["@odata.etag"], current_etag=other.etag)

    def test_09_delete_exact_item_and_refuse_wrong_ids(self):
        a, b = self.create(), self.create()
        mark, count = self.mark(), self.count_clients()
        self.assertEqual(self.backend.delete_client("9990000000"), NOT_FOUND)
        self.assertEqual(self.backend.delete_client("abc"), NOT_FOUND)
        self.assertEqual(self.writes_since(mark), [])
        with self.assertRaises(SharePointError) as refused:  # ID elementu b z NIP-em elementu a
            self.backend._delete_verified("Clients", b["id"], a["nip"])
        self.assertIn("Odmowa usunięcia", str(refused.exception))
        with self.assertRaises(ItemNotFoundError):
            self.backend._delete_verified("Clients", "99999999", a["nip"])
        for list_name in ("Offers", "Suppliers", "Wuzetkas"):
            with self.assertRaises(SharePointError):
                self.backend._delete_verified(list_name, b["id"], b["nip"])
        self.assertEqual(self.writes_since(mark), [])  # żadnego DELETE
        self.assertEqual(self.count_clients(), count)
        self.assertEqual(self.backend.delete_client(a["nip"]), DELETE_OK)
        deletes = [e for e in self.writes_since(mark) if e["method"] == "DELETE"]
        self.assertEqual([(e["status"], e["path"].rsplit("/", 1)[-1]) for e in deletes], [(204, a["id"])])
        with self.assertRaises(GraphError) as gone:
            self.reader.get(f"{self.base}/{a['id']}")
        self.assertEqual(gone.exception.status, 404)
        self.assertIsNotNone(self.item_by_title(b["nip"]))  # sąsiedni element nietknięty
        self.assertEqual(self.count_clients(), count - 1)
        self.assertEqual(self.backend.delete_client(a["nip"]), NOT_FOUND)
        self.record(delete_status=204, deleted_id=a["id"], other_item_untouched=b["id"])

    def test_10_throttling_503_and_connection_errors(self):
        # 429 na POST: ponowienie po Retry-After (1 s) i sukces
        self.faults.append({"method": "POST", "kind": "status", "status": 429, "code": "activityLimitReached", "headers": {"Retry-After": "1"}})
        mark = self.mark()
        c = self.create()
        posts = [e for e in self.writes_since(mark) if e["method"] == "POST"]
        self.assertEqual([e["status"] for e in posts], [429, 201])
        # 503 na POST: bez ponowienia, nic nie powstaje
        count, mark = self.count_clients(), self.mark()
        nip = self.next_nip()
        self.faults.append({"method": "POST", "kind": "status", "status": 503})
        ok, message = self.backend.add_client(nip, f"{PREFIX}503", "a", "b", f"{PREFIX}503-{self.run_tag}")
        self.assertFalse(ok)
        self.assertIn("HTTP 503", message)
        self.assertEqual([e["status"] for e in self.writes_since(mark)], [503])
        self.skip_cooldown()
        self.assertIsNone(self.item_by_title(nip))
        # brak połączenia na POST: bez ponowienia, nic nie powstaje
        mark = self.mark()
        self.faults.append({"method": "POST", "kind": "raise"})
        ok, message = self.backend.add_client(nip, f"{PREFIX}NET", "a", "b", f"{PREFIX}NET-{self.run_tag}")
        self.assertFalse(ok)
        self.assertIn("Brak połączenia", message)
        self.assertEqual([e["status"] for e in self.writes_since(mark)], [None])
        self.skip_cooldown()
        self.assertEqual(self.count_clients(), count)
        # utracona odpowiedź POST: element powstał, odczyt weryfikujący go odnajduje, bez drugiego POST
        mark = self.mark()
        lost_nip = self.next_nip()
        self.faults.append({"method": "POST", "kind": "lose"})
        lost = self.backend.add_client(lost_nip, f"{PREFIX}LOST", "a", "b", f"{PREFIX}LOST-{self.run_tag}")
        self.assertEqual(lost, ADD_OK)
        self.assertEqual([e["status"] for e in self.writes_since(mark)], [201])
        self.assertEqual(self.count_clients(), count + 1)
        self.assertEqual(self.backend.set_client_extended_fields(lost_nip, "po utracie odpowiedzi"), EXT_OK)
        # 503 i brak połączenia na PATCH: bez zmian i bez ponowienia
        item_before = self.item_by_title(c["nip"])
        for fault in ({"kind": "status", "status": 503}, {"kind": "raise"}):
            mark = self.mark()
            self.faults.append({"method": "PATCH", **fault})
            ok, message = self.backend.update_client(c["nip"], c["company"] + "-X", "a", "b", c["alias"])
            self.assertFalse(ok)
            self.assertEqual(len([e for e in self.writes_since(mark) if e["method"] == "PATCH"]), 1)
            self.skip_cooldown()
        after = self.item_by_title(c["nip"])
        self.assertEqual((after["@odata.etag"], after["fields"]), (item_before["@odata.etag"], item_before["fields"]))
        # 503 na DELETE: element zostaje
        self.faults.append({"method": "DELETE", "kind": "status", "status": 503})
        ok, message = self.backend.delete_client(c["nip"])
        self.assertFalse(ok)
        self.assertIsNotNone(self.item_by_title(c["nip"]))
        self.skip_cooldown()
        self.record(injected="429(Retry-After=1)->201, 503 POST, connection POST, lost-response POST, 503/connection PATCH, 503 DELETE")

    def test_11_remaining_write_operations_are_still_rejected_without_requests(self):
        mark = self.mark()
        for name, args in (("add_supplier", ("1234567890", "D", "a", "b")), ("save_offer", (1, "2026/a.docx", {})),
                           ("save_wz", (1, "2026/a.docx", {})), ("get_next_offer_number_for_year", (2026,)),
                           ("delete_wz", (1,)), ("delete_offer", ("2026/a.docx",))):
            with self.assertRaises(ReadOnlyBackendError):
                getattr(self.backend, name)(*args)
        self.assertEqual([e for e in self.http_log[mark:] if e.get("test") == self.current], [])

    def test_99_cleanup_and_verify_nothing_else_changed(self):
        results = self.cleanup()
        self.assertTrue(results)
        self.assertEqual({v for v in results.values()}, {"usunięty", "już nie istnieje"}, results)
        self.assertEqual(self.count_clients(), EXPECTED_REAL_CLIENTS)
        for item_id in self.created_ids:
            with self.assertRaises(GraphError) as gone:
                self.reader.get(f"{self.base}/{item_id}")
            self.assertEqual(gone.exception.status, 404)
        after = self.snapshot()
        before = type(self).before
        self.assertEqual(after["schema"], before["schema"])  # schematy list bez zmian
        for name in OTHER_LISTS:
            self.assertEqual(after["lists"][name], before["lists"][name], f"lista {name} zmieniona")
        self.assertEqual(after["real_clients"], before["real_clients"])  # 39 prawdziwych klientów: identyczne ETagi i pola
        self.assertEqual(len(after["lists"]["Clients"]), EXPECTED_REAL_CLIENTS)
        non_graph_writes = [e for e in self.http_log if e["method"] != "GET" and "…/Clients" not in e["path"]]
        self.assertEqual(non_graph_writes, [])
        self.report["verification"] = {
            "clients_after": len(after["lists"]["Clients"]), "other_lists_unchanged": True, "schema_unchanged": True,
            "real_clients_unchanged": True, "created_ids": sorted(self.created_ids, key=int), "cleanup": results}


if __name__ == "__main__":
    unittest.main()
