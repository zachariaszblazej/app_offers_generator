"""Testy SharePointBackend (tylko odczyt) - offline, na atrapie Graph API i tymczasowej bazie SQLite.

Uruchomienie: python -m unittest tests.sharepoint_backend_test -v
Żadnych żądań sieciowych, żadnych zapisów do SharePoint ani do prawdziwej bazy użytkownika.
"""
import inspect
import json
import os
import re
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import src.data.backends.sharepoint_backend as sp_module  # noqa: E402
import src.data.database_service as dbs  # noqa: E402
import tests.database_service_characterization_test as base  # noqa: E402  (moduł - bez duplikowania testów)
from src.data.backends import BackendContext, DataBackend, SharePointBackend  # noqa: E402
from src.data.backends.sharepoint_backend import sqlite_like  # noqa: E402
from src.data.errors import DataAccessError, ReadOnlyBackendError  # noqa: E402
from src.integrations.sharepoint import get_environment  # noqa: E402
from src.integrations.sharepoint.config import GRAPH_BASE_URL  # noqa: E402
from src.integrations.sharepoint.graph_client import GraphClient, GraphError  # noqa: E402
from src.integrations.sharepoint.migration import mapping  # noqa: E402
from src.integrations.sharepoint.reader import RetryingGraphClient  # noqa: E402
from src.integrations.sharepoint.session import NotSignedInError, SharePointSession  # noqa: E402

DEV_ENV = get_environment("DEV")


# ---------------------------------------------------------------------------
# dane testowe (wyłącznie syntetyczne)
# ---------------------------------------------------------------------------
def ctx(**kw):
    return json.dumps(kw, ensure_ascii=False)


CLIENTS = [
    {"_rowid_": 1, "Nip": 1234563218, "CompanyName": "beta", "AddressP1": "ul. A 1", "AddressP2": "00-001\nMiasto",
     "Alias": "ALFA", "TerminRealizacji": "30 dni", "TerminPlatnosci": None, "WarunkiDostawy": "DAP\nlinia 2",
     "WaznoscOferty": None, "Gwarancja": None, "Cena": None},
    {"_rowid_": 2, "Nip": 1111111111, "CompanyName": "Alfa", "AddressP1": "ul. B", "AddressP2": "11-111",
     "Alias": "ALFA2", "TerminRealizacji": None, "TerminPlatnosci": None, "WarunkiDostawy": None,
     "WaznoscOferty": None, "Gwarancja": None, "Cena": None},
    {"_rowid_": 3, "Nip": 2222222222, "CompanyName": "Zeta", "AddressP1": "ul. C", "AddressP2": "22-222",
     "Alias": "ZETA", "TerminRealizacji": None, "TerminPlatnosci": "14 dni", "WarunkiDostawy": None,
     "WaznoscOferty": None, "Gwarancja": "24 mies.", "Cena": "netto"},
    {"_rowid_": 4, "Nip": 3333333333, "CompanyName": "Łódź żółć", "AddressP1": "ul. D", "AddressP2": "33-333",
     "Alias": "LODZ", "TerminRealizacji": None, "TerminPlatnosci": None, "WarunkiDostawy": None,
     "WaznoscOferty": None, "Gwarancja": None, "Cena": None},
    {"_rowid_": 5, "Nip": 123456789, "CompanyName": "Krótki NIP", "AddressP1": "ul. E", "AddressP2": "44-444",
     "Alias": "SHORT", "TerminRealizacji": None, "TerminPlatnosci": None, "WarunkiDostawy": None,
     "WaznoscOferty": None, "Gwarancja": None, "Cena": None},
    {"_rowid_": 6, "Nip": 4444444444, "CompanyName": "Alfa", "AddressP1": "ul. F", "AddressP2": "55-555",
     "Alias": "ALFA3", "TerminRealizacji": None, "TerminPlatnosci": None, "WarunkiDostawy": None,
     "WaznoscOferty": None, "Gwarancja": None, "Cena": None},
]
SUPPLIERS = [
    {"_rowid_": 1, "Nip": 3333333333, "CompanyName": "Dostawca B", "AddressP1": "ul. S1", "AddressP2": "66-666", "IsDefault": 0},
    {"_rowid_": 2, "Nip": 5555555555, "CompanyName": "Dostawca A", "AddressP1": "ul. S2", "AddressP2": "77-777", "IsDefault": 1},
    {"_rowid_": 3, "Nip": 6666666666, "CompanyName": "dostawca c", "AddressP1": "ul. S3", "AddressP2": "88-888", "IsDefault": None},
]
OFFERS = [
    {"_rowid_": 1, "OfferYearNumber": 2025, "OfferOrderNumber": 392, "OfferFilePath": "2025/392_OF_2025_ALFA.docx",
     "OfferContext": ctx(offer_number="392/OF/2025_ALFA", client_name="<w:r>Firma</w:r>", date="4 sierpnia 2025", products=[["1", "Żółć"]])},
    {"_rowid_": 2, "OfferYearNumber": 2025, "OfferOrderNumber": 5, "OfferFilePath": "2025/5_OF_2025_AxB.docx",
     "OfferContext": ctx(offer_number="5/OF/2025_AxB", date="1 stycznia 2025")},
    {"_rowid_": 3, "OfferYearNumber": 2026, "OfferOrderNumber": 5, "OfferFilePath": "2026/5_OF_2026_ZETA.docx",
     "OfferContext": ctx(offer_number="5/OF/2026_ZETA", date="2026-03-01T10:00:00", uwagi="linia 1\nlinia 2")},
    {"_rowid_": 4, "OfferYearNumber": 2026, "OfferOrderNumber": 300, "OfferFilePath": "2026/300_OF_2026_STEEL.docx", "OfferContext": None},
    {"_rowid_": 5, "OfferYearNumber": 2026, "OfferOrderNumber": 1, "OfferFilePath": "2026/1_OF_2026_ALFASTEEL.docx",
     "OfferContext": "{nie json"},
    {"_rowid_": 6, "OfferYearNumber": 2026, "OfferOrderNumber": 2, "OfferFilePath": "2026/2_OF_2026_ALFA.docx", "OfferContext": ""},
]
WZS = [
    {"_rowid_": 1, "WzYearNumber": 2025, "WzOrderNumber": 102, "WzFilePath": "2025/WZ_102_2025_ALFA.docx",
     "WzContext": ctx(wz_number="WZ_102_2025_ALFA", client_name="Firma A", date="4 sierpnia 2025")},
    {"_rowid_": 2, "WzYearNumber": 2026, "WzOrderNumber": 102, "WzFilePath": "2026/WZ_102_2026_ALFA.docx",
     "WzContext": ctx(wz_number="WZ_102_2026_ALFA", client_name="Firma B", date="04 08 2026")},
    {"_rowid_": 3, "WzYearNumber": 2026, "WzOrderNumber": 5, "WzFilePath": "2026/WZ_5_2026_ZETA.docx", "WzContext": None},
    {"_rowid_": 4, "WzYearNumber": 2026, "WzOrderNumber": 6, "WzFilePath": "2026/WZ_6_2026_ZETA.docx", "WzContext": "{zle"},
    {"_rowid_": 5, "WzYearNumber": 2026, "WzOrderNumber": 7, "WzFilePath": "2026/WZ_7_2026_ZETA.docx", "WzContext": ctx(wz_number="x")},
]
TABLES = {"Suppliers": SUPPLIERS, "Clients": CLIENTS, "Offers": OFFERS, "Wuzetkas": WZS}


def build_graph_data(tables, start_id=2):
    """Elementy list SharePoint wg zatwierdzonego mapowania migracji; SharePoint pomija pola puste (null i "")."""
    data = {}
    for name, records in mapping.map_all(tables).items():
        items = []
        for offset, rec in enumerate(records):
            fields = {k: v for k, v in rec.fields.items() if v is not None and v != ""}
            items.append({"id": start_id + offset, "fields": fields})
        data[name] = items
    return data


class FakeGraph:
    """Atrapa odczytu Graph: $select, $expand=fields($select=...), $top, $filter (eq/startswith bez rozróżniania wielkości liter),
    paginacja przez @odata.nextLink. Obsługuje wyłącznie GET."""

    def __init__(self, data, env=DEV_ENV, page_cap=None):
        self.data, self.env, self.page_cap = data, env, page_cap
        self.requests, self._cursors = [], {}
        self._list_by_id = {v: k for k, v in env.lists.items()}

    def get(self, path_or_url, params=None):
        self.requests.append(("GET", path_or_url, dict(params or {})))
        if path_or_url.startswith("http"):
            token = re.search(r"\$skiptoken=(\d+)", path_or_url).group(1)
            list_name, remaining, fields, top = self._cursors[int(token)]
        else:
            m = re.fullmatch(r"/sites/.+?/lists/([0-9a-f-]+)/items", path_or_url)
            assert m, f"nieobsługiwana ścieżka: {path_or_url}"
            list_name = self._list_by_id[m.group(1)]
            params = params or {}
            fields = re.fullmatch(r"fields\(\$select=(.+)\)", params["$expand"]).group(1).split(",")
            remaining = self._apply_filter(list(self.data[list_name]), params.get("$filter"))
            top = int(params["$top"])
        size = min(top, self.page_cap or top)
        page, rest = remaining[:size], remaining[size:]
        result = {"value": [{"id": str(i["id"]), "fields": {k: v for k, v in i["fields"].items() if k in fields}} for i in page]}
        if rest:
            token = len(self._cursors) + 1
            self._cursors[token] = (list_name, rest, fields, top)
            result["@odata.nextLink"] = f"{GRAPH_BASE_URL}/sites/x/lists/y/items?$skiptoken={token}"
        return result

    @staticmethod
    def _apply_filter(items, flt):
        if not flt:
            return items
        m = re.fullmatch(r"fields/(\w+) eq '(.*)'", flt, re.S)
        if m:
            field, value = m.group(1), m.group(2).replace("''", "'")
            return [i for i in items if str(i["fields"].get(field, "")).lower() == value.lower()]
        m = re.fullmatch(r"startswith\(fields/(\w+),'(.*)'\)", flt, re.S)
        if m:
            field, value = m.group(1), m.group(2).replace("''", "'")
            return [i for i in items if str(i["fields"].get(field, "")).lower().startswith(value.lower())]
        raise AssertionError(f"nieobsługiwany filtr: {flt}")


class FakeSession:
    def __init__(self, active=True):
        self.active, self.invalidated, self.token = active, 0, "TOKEN-NIE-DO-LOGOW"

    def is_active(self):
        return self.active

    def get_token(self):
        if not self.active:
            raise NotSignedInError("Sesja SharePoint wygasła - zaloguj się ponownie.")
        return self.token

    def invalidate_token(self):
        self.invalidated += 1


class SpTestCase(base.DbTestCase):
    """Baza SQLite z tymi samymi danymi co atrapa Graph oraz oba backendy z identycznym kontekstem."""

    graph_data = None
    page_cap = None

    def setUp(self):
        super().setUp()
        for table, rows in TABLES.items():
            for row in rows:
                cols = [c for c in row if c != "_rowid_"]
                self.run_sql(f"INSERT INTO {table} ({','.join(cols)}) VALUES ({','.join('?' * len(cols))})", [row[c] for c in cols])
        self.sp_popups, self.sp_logs, self.clock = [], [], {"now": 1000.0}
        self.graph = FakeGraph(self.graph_data or build_graph_data(TABLES), page_cap=self.page_cap)
        self.session = FakeSession()
        context = BackendContext(
            offers_folder=lambda: self.offers_dir, wz_folder=lambda: self.wz_dir,
            popups_enabled=lambda: self.cfg.popups,
            show_error=lambda title, message: self.sp_popups.append(("error", title, message)),
            log=lambda *a, **k: self.sp_logs.append(a))
        self.sp = SharePointBackend(context, self.session, DEV_ENV, client_factory=lambda: self.graph,
                                    clock=lambda: self.clock["now"])
        self.sq = dbs.get_backend()

    @staticmethod
    def addr(row):  # zatwierdzona transformacja migracji dla Clients.AddressP2
        return row if row is None else row[:3] + (mapping.newline_to_comma(row[3]),) + row[4:]


# ---------------------------------------------------------------------------
# zgodność wyników SQLite i SharePoint (na tych samych danych)
# ---------------------------------------------------------------------------
class ParityTests(SpTestCase):
    def test_get_clients_basic_and_extended_match_sqlite_with_address_transformation(self):
        for extended in (False, True):
            with self.subTest(extended=extended):
                expected = [self.addr(r) for r in self.sq.get_clients(extended)]
                actual = self.sp.get_clients(extended)
                self.assertEqual(sorted(actual, key=lambda r: (r[1], r[0])), sorted(expected, key=lambda r: (r[1], r[0])))
                names = [r[1] for r in actual]
                self.assertEqual(names, sorted(names))  # ORDER BY CompanyName (kody znaków)
                self.assertEqual(len(actual[0]), 11 if extended else 5)

    def test_binary_ordering_matches_sqlite_uppercase_before_lowercase_and_polish_last(self):
        names = [r[1] for r in self.sp.get_clients()]
        self.assertEqual(names, [r[1] for r in self.sq.get_clients()])
        self.assertEqual(names, ["Alfa", "Alfa", "Krótki NIP", "Zeta", "beta", "Łódź żółć"])

    def test_get_client_by_nip_matches_sqlite_for_many_inputs(self):
        for nip in (1234563218, "1234563218", 1111111111, "0123456789", 123456789, "123456789", 9999999999, "9999999999",
                    "abc", "", None, "12345678901", 12345678901, "  1111111111", "1111111111 "):
            with self.subTest(nip=nip):
                self.assertEqual(self.sp.get_client_by_nip(nip), self.addr(self.sq.get_client_by_nip(nip)))

    def test_validate_functions_match_sqlite(self):
        for nip in ("123", "abc", "", "1234563218", "5555555555", "0123456789", "9999999999", "12345678901"):
            with self.subTest(nip=nip):
                self.assertEqual(self.sp.validate_nip(nip), self.sq.validate_nip(nip))
                self.assertEqual(self.sp.validate_supplier_nip(nip), self.sq.validate_supplier_nip(nip))
        for alias in ("", "  ", "ALFA", "A_B C&D"):
            self.assertEqual(self.sp.validate_alias(alias), self.sq.validate_alias(alias))

    def test_suppliers_match_sqlite(self):
        self.assertEqual(self.sp.get_suppliers(), self.sq.get_suppliers())
        for nip in (3333333333, "5555555555", "6666666666", "1", "abc", None):
            self.assertEqual(self.sp.get_supplier_by_nip(nip), self.sq.get_supplier_by_nip(nip), nip)
        self.assertEqual(self.sp.get_default_supplier(), self.sq.get_default_supplier())
        self.assertEqual(self.sp.get_default_supplier()[4], 1)

    def test_no_default_supplier(self):
        self.run_sql("UPDATE Suppliers SET IsDefault = 0")
        for item in self.graph.data["Suppliers"]:
            item["fields"]["IsDefault"] = False
        self.assertIsNone(self.sp.get_default_supplier())
        self.assertEqual(self.sp.get_default_supplier(), self.sq.get_default_supplier())

    def test_offer_paths_and_order_match_sqlite(self):
        sp, sq = self.sp.get_all_offer_file_paths(), self.sq.get_all_offer_file_paths()
        order = {r["OfferFilePath"]: r["OfferOrderNumber"] for r in OFFERS}
        self.assertEqual(sorted(sp, key=lambda p: (-order[p], p)), sorted(sq, key=lambda p: (-order[p], p)))
        self.assertEqual([order[p] for p in sp], sorted((order[p] for p in sp), reverse=True))  # numer malejąco, bez roku
        self.assertEqual(sp[0], "2025/392_OF_2025_ALFA.docx")

    def test_offer_contexts_match_sqlite_for_every_record_and_full_paths(self):
        for row in OFFERS:
            for path in (row["OfferFilePath"], f"{self.offers_dir}/{row['OfferFilePath']}"):
                with self.subTest(path=path):
                    self.sp_popups.clear()
                    self.popups.clear()
                    self.assertEqual(self.sp.get_offer_context(path), self.sq.get_offer_context(path))
                    self.assertEqual([p[1:] for p in self.sp_popups], [p[1:] for p in self.popups])
        self.assertIsNone(self.sp.get_offer_context("2026/nie_ma.docx"))

    def test_offer_context_text_is_preserved_exactly(self):
        item = next(i for i in self.graph.data["Offers"] if "392_OF" in i["fields"]["OfferFilePath"])
        self.assertEqual(item["fields"]["OfferContext"], OFFERS[0]["OfferContext"])
        self.assertEqual(self.sp.get_offer_context("2025/392_OF_2025_ALFA.docx"), json.loads(OFFERS[0]["OfferContext"]))

    def test_find_offer_by_filename_matches_sqlite(self):
        for name in ("2_OF_2026_ALFA.docx", "ALFA.docx", "alfa.docx", "A.DOCX", "x.docx", "", "5_OF_2025_AxB.docx",
                     "5_OF_2025_A_B.docx", "%", "2026/5_OF_2026_ZETA.docx", "STEEL.docx", "_OF_2026_ZETA.docx"):
            with self.subTest(filename=name):
                self.assertEqual(self.sp.find_offer_by_filename(name), self.sq.find_offer_by_filename(name))

    def test_wz_lists_and_contexts_match_sqlite(self):
        sp, sq = self.sp.get_all_wz(), self.sq.get_all_wz()
        self.assertEqual(sorted(sp, key=lambda r: (-r[0], r[5])), sorted(sq, key=lambda r: (-r[0], r[5])))
        self.assertEqual([r[0] for r in sp], sorted((r[0] for r in sp), reverse=True))
        self.assertTrue(all(len(r) == 6 and r[4] == "Utworzone" for r in sp))
        paths_sp, paths_sq = self.sp.get_all_wz_file_paths(), self.sq.get_all_wz_file_paths()
        order = {r["WzFilePath"]: r["WzOrderNumber"] for r in WZS}
        self.assertEqual(sorted(paths_sp, key=lambda p: (-order[p], p)), sorted(paths_sq, key=lambda p: (-order[p], p)))
        for row in WZS:
            for path in (row["WzFilePath"], f"{self.wz_dir}/{row['WzFilePath']}"):
                with self.subTest(path=path):
                    self.sp_popups.clear()
                    self.popups.clear()
                    self.assertEqual(self.sp.get_wz_context(path), self.sq.get_wz_context(path))
                    self.assertEqual([p[1:] for p in self.sp_popups], [p[1:] for p in self.popups])

    def test_get_all_wz_keeps_historical_current_year_numbering_and_na_values(self):
        import datetime
        rows = {r[0]: r for r in self.sp.get_all_wz() if r[0] != 102}
        self.assertEqual(rows[5][1], f"WZ_5_{datetime.datetime.now().year}")
        self.assertEqual(rows[5][2:4], ("N/A", "N/A"))   # brak kontekstu
        self.assertEqual(rows[6][2:4], ("N/A", "N/A"))   # niepoprawny JSON

    def test_returned_types_are_native_and_nip_is_int(self):
        for row in self.sp.get_clients(True):
            self.assertIsInstance(row[0], int)
            self.assertTrue(all(isinstance(v, str) for v in row[1:]))
        self.assertIsInstance(self.sp.get_client_by_nip("0123456789")[0], int)
        self.assertEqual(self.sp.get_client_by_nip("0123456789")[0], 123456789)
        for row in self.sp.get_suppliers():
            self.assertIsInstance(row[0], int)
            self.assertIn(row[4], (0, 1))
            self.assertIsInstance(row[4], int)
        self.assertIsInstance(self.sp.find_offer_by_filename("2_OF_2026_ALFA.docx")[0], int)
        self.assertIsInstance(self.sp.get_all_wz()[0][0], int)

    def test_case_insensitive_filter_does_not_cause_a_case_insensitive_match(self):
        # SharePoint zwraca element dla innej wielkości liter, ale kontrakt (SQLite: = jest wrażliwe) nakazuje "brak"
        self.assertIsNone(self.sp.get_offer_context("2025/392_of_2025_alfa.docx"))
        self.assertIsNone(self.sq.get_offer_context("2025/392_of_2025_alfa.docx"))
        self.assertTrue(any("$filter" in r[2] for r in self.graph.requests))


# ---------------------------------------------------------------------------
# paginacja
# ---------------------------------------------------------------------------
class PaginationTests(SpTestCase):
    page_cap = 7

    @classmethod
    def many(cls):
        rows = [{"_rowid_": i, "OfferYearNumber": 2026, "OfferOrderNumber": i, "OfferFilePath": f"2026/{i}_OF_2026_ALFA.docx",
                 "OfferContext": ctx(n=i)} for i in range(1, 61)]
        return build_graph_data({**TABLES, "Offers": rows})

    graph_data = None

    def setUp(self):
        type(self).graph_data = self.many()
        super().setUp()

    def test_all_records_are_returned_exactly_once_across_pages(self):
        paths = self.sp.get_all_offer_file_paths()
        self.assertEqual(len(paths), 60)
        self.assertEqual(len(set(paths)), 60)
        self.assertEqual(set(paths), {f"2026/{i}_OF_2026_ALFA.docx" for i in range(1, 61)})
        pages = [r for r in self.graph.requests if r[1].startswith("http")]
        self.assertEqual(len(pages), 8)  # 60 elementów po 7 => 9 stron (1 żądanie początkowe + 8 nextLink)
        self.assertEqual(self.sp.page_requests, 9)

    def test_first_request_selects_only_needed_fields_and_has_no_nextlink(self):
        self.sp.get_all_offer_file_paths()
        method, path, params = self.graph.requests[0]
        self.assertEqual(params["$select"], "id")
        self.assertEqual(params["$expand"], "fields($select=OfferOrderNumber,OfferFilePath)")
        self.assertNotIn("OfferContext", params["$expand"])  # kontekst tylko na żądanie
        self.assertEqual(params["$top"], "999")

    def test_find_by_filename_scans_all_pages(self):
        self.assertEqual(self.sp.find_offer_by_filename("60_OF_2026_ALFA.docx"), (60, "2026/60_OF_2026_ALFA.docx"))

    def test_pagination_results_equal_unpaginated_results(self):
        self.graph.page_cap = None
        unpaged = {n: getattr(self.sp, n)() for n in ("get_all_offer_file_paths", "get_all_wz", "get_clients", "get_suppliers")}
        self.graph.page_cap = 3
        paged = {n: getattr(self.sp, n)() for n in unpaged}
        self.assertEqual(paged, unpaged)

    def test_page_limit_prevents_endless_pagination(self):
        class Endless(FakeGraph):
            def get(self, path_or_url, params=None):
                return {"value": [], "@odata.nextLink": f"{GRAPH_BASE_URL}/sites/x/lists/y/items?$skiptoken=1"}

        self.sp._client_factory = lambda: Endless({})
        with mock.patch.object(sp_module, "MAX_PAGES", 5):
            self.assertEqual(self.sp.get_all_offer_file_paths(), [])
        self.assertTrue(any("limit stron" in str(a) for a in self.sp_logs))


# ---------------------------------------------------------------------------
# kontekst na żądanie, filtry, NIP, odporność na nietypowe dane
# ---------------------------------------------------------------------------
class OnDemandAndFilterTests(SpTestCase):
    def test_context_is_fetched_per_request_by_exact_path_filter(self):
        self.sp.get_offer_context("2025/392_OF_2025_ALFA.docx")
        method, path, params = self.graph.requests[-1]
        self.assertEqual(params["$filter"], "fields/OfferFilePath eq '2025/392_OF_2025_ALFA.docx'")
        self.assertIn("OfferContext", params["$expand"])
        self.assertEqual(len(self.graph.requests), 1)

    def test_lists_do_not_download_contexts(self):
        self.sp.get_all_offer_file_paths()
        self.sp.find_offer_by_filename("x.docx")
        self.sp.get_clients(True)
        for method, path, params in self.graph.requests:
            self.assertNotIn("Context", params["$expand"])

    def test_nip_is_padded_to_ten_characters_in_filter(self):
        self.sp.get_client_by_nip(123456789)
        self.assertEqual(self.graph.requests[-1][2]["$filter"], "fields/Title eq '0123456789'")

    def test_apostrophes_in_path_are_escaped_in_filter(self):
        self.sp.get_offer_context("2026/o'brien.docx")
        self.assertEqual(self.graph.requests[-1][2]["$filter"], "fields/OfferFilePath eq '2026/o''brien.docx'")

    def test_inputs_that_cannot_exist_make_no_request(self):
        for bad in ("abc", "", None, "12345678901"):
            self.assertIsNone(self.sp.get_client_by_nip(bad))
        self.assertEqual(self.graph.requests, [])

    def test_items_with_malformed_title_are_skipped_and_logged(self):
        self.graph.data["Clients"].append({"id": 99, "fields": {"Title": "ZZTEST-1", "CompanyName": "X", "AddressP1": "a",
                                                                 "AddressP2": "b", "Alias": "ZZTEST"}})
        rows = self.sp.get_clients()
        self.assertEqual(len(rows), len(CLIENTS))
        self.assertTrue(any("nieprawidłowym tytule" in str(a) for a in self.sp_logs))

    def test_numbers_returned_as_floats_by_graph_are_converted_to_int(self):
        for item in self.graph.data["Wuzetkas"]:
            item["fields"]["WzOrderNumber"] = float(item["fields"]["WzOrderNumber"])
        rows = self.sp.get_all_wz()
        self.assertTrue(all(isinstance(r[0], int) for r in rows))

    def test_missing_file_record_is_returned_like_any_other(self):
        row = next(r for r in self.sp.get_all_wz() if r[0] == 7)
        self.assertEqual(row[5], os.path.join(self.wz_dir, "2026/WZ_7_2026_ZETA.docx"))
        self.assertEqual(self.sp.get_wz_context("2026/WZ_7_2026_ZETA.docx"), {"wz_number": "x"})

    def test_sqlite_like_semantics(self):
        self.assertTrue(sqlite_like("%A.docx", "2026/1_OF_2026_a.docx"))
        self.assertTrue(sqlite_like("%A_B.docx", "x_AxB.docx"))
        self.assertFalse(sqlite_like("%A.docx", "x_B.docx"))
        self.assertTrue(sqlite_like("%", ""))
        self.assertFalse(sqlite_like("%ł.docx", "x_Ł.docx"))  # LIKE ignoruje wielkość liter tylko dla ASCII


# ---------------------------------------------------------------------------
# konwencje błędów
# ---------------------------------------------------------------------------
class ErrorConventionTests(SpTestCase):
    def failing(self, status=500):
        def factory():
            raise GraphError(f"HTTP {status}", status=status)
        self.sp._client_factory = factory

    def test_list_reads_return_empty_and_popup_only_when_enabled(self):
        self.failing()
        for method in (self.sp.get_clients, self.sp.get_suppliers):
            self.assertEqual(method(), [])
        self.assertEqual(self.sp_popups, [])
        self.cfg.popups = True
        self.sp._down_until = 0
        self.assertEqual(self.sp.get_clients(), [])
        self.assertEqual(self.sp_popups[0][1], "Database Error")
        self.assertIn("Error accessing database", self.sp_popups[0][2])

    def test_single_reads_popup_unconditionally_and_return_none(self):
        self.failing()
        self.assertIsNone(self.sp.get_client_by_nip("1234563218"))
        self.sp._down_until = 0
        self.assertIsNone(self.sp.get_wz_context("2026/a.docx"))
        self.sp._down_until = 0
        self.assertEqual(self.sp.get_all_wz(), [])
        self.assertEqual(len(self.sp_popups), 3)

    def test_validate_nip_reports_error_text(self):
        self.failing()
        ok, msg = self.sp.validate_nip("1234563218")
        self.assertFalse(ok)
        self.assertTrue(msg.startswith("Błąd sprawdzania NIP:"), msg)

    def test_find_offer_swallows_errors_and_path_lists_log_them(self):
        self.failing()
        self.assertIsNone(self.sp.find_offer_by_filename("x.docx"))
        self.sp._down_until = 0
        self.assertEqual(self.sp.get_all_offer_file_paths(), [])
        self.sp._down_until = 0
        self.assertEqual(self.sp.get_all_wz_file_paths(), [])
        self.assertEqual(self.sp_popups, [])
        self.assertEqual(len([a for a in self.sp_logs if "Database error in" in str(a)]), 2)

    def test_not_signed_in_behaves_like_unavailable_database(self):
        self.session.active = False
        self.assertFalse(self.sp.is_available())
        self.assertEqual(self.sp.get_clients(), [])
        self.assertIsNone(self.sp.get_client_by_nip("1234563218"))
        self.assertIsNone(self.sp.get_offer_context("2026/a.docx"))
        self.assertEqual(self.sp.get_all_wz(), [])
        self.assertEqual(self.sp.validate_supplier_nip("1234567890"), (False, "Baza danych jest niedostępna"))
        self.assertEqual(self.graph.requests, [])

    def test_expired_session_during_call_is_reported_not_raised(self):
        self.sp._client_factory = None
        self.session.get_token = mock.Mock(side_effect=NotSignedInError("Sesja SharePoint wygasła - zaloguj się ponownie."))
        ok, msg = self.sp.validate_nip("1234563218")
        self.assertFalse(ok)
        self.assertIn("zaloguj się ponownie", msg)

    def test_unauthorized_invalidates_token_and_server_errors_start_a_cooldown(self):
        self.failing(401)
        self.sp.get_clients()
        self.assertEqual(self.session.invalidated, 1)
        self.failing(503)
        self.sp.get_clients()
        self.assertFalse(self.sp.is_available())
        self.clock["now"] += sp_module.FAILURE_COOLDOWN_SECONDS + 1
        self.assertTrue(self.sp.is_available())

    def test_successful_call_clears_failure_state(self):
        self.failing(503)
        self.sp.get_clients()
        self.assertFalse(self.sp.is_available())
        self.sp._client_factory = lambda: self.graph
        self.clock["now"] += 100
        self.sp.get_clients()
        self.assertTrue(self.sp.is_available())

    def test_forbidden_does_not_start_a_cooldown(self):
        self.failing(403)
        self.sp.get_clients()
        self.assertTrue(self.sp.is_available())

    def test_environment_mismatch_is_never_swallowed(self):
        from src.integrations.sharepoint.graph_client import EnvironmentMismatchError

        def factory():
            raise EnvironmentMismatchError("niezgodne środowisko")
        self.sp._client_factory = factory
        with self.assertRaises(EnvironmentMismatchError):
            self.sp.get_clients()

    def test_is_available_makes_no_requests(self):
        for _ in range(50):
            self.sp.is_available()
        self.assertEqual(self.graph.requests, [])


# ---------------------------------------------------------------------------
# tylko odczyt, DEV-only, brak przekierowania do SQLite
# ---------------------------------------------------------------------------
class ReadOnlyAndSafetyTests(SpTestCase):
    WRITE_CALLS = [
        ("add_client", ("1234563218", "F", "a", "b", "A")), ("update_client", ("1234563218", "F", "a", "b", "A")),
        ("set_client_extended_fields", ("1234563218", "x")), ("delete_client", ("1234563218",)),
        ("add_supplier", ("1234563218", "D", "a", "b")), ("update_supplier", ("1234563218", "D", "a", "b")),
        ("delete_supplier", ("1234563218",)), ("set_default_supplier", ("1234563218",)),
        ("get_next_offer_number", ()), ("get_next_offer_number_for_year", (2026,)),
        ("save_offer", (1, "2026/a.docx", {"k": 1})), ("update_offer_context", ("2026/a.docx", {})),
        ("delete_offer", ("2026/a.docx",)), ("get_next_wz_number", (2026,)), ("save_wz", (1, "2026/a.docx", {})),
        ("update_wz_context", ("2026/a.docx", {})), ("delete_wz", (1,)), ("delete_wz_by_file_path", ("2026/a.docx",)),
    ]

    def test_every_write_update_delete_and_numbering_method_is_rejected(self):
        self.assertEqual(len(self.WRITE_CALLS), 18)
        before = self.rows("SELECT (SELECT COUNT(*) FROM Clients), (SELECT COUNT(*) FROM Offers), (SELECT COUNT(*) FROM Wuzetkas)")
        for name, args in self.WRITE_CALLS:
            with self.subTest(method=name), self.assertRaises(ReadOnlyBackendError) as caught:
                getattr(self.sp, name)(*args)
            self.assertIn(name, str(caught.exception))
            self.assertIn("tryb tylko do odczytu", str(caught.exception))
        self.assertEqual(self.graph.requests, [])  # żadnych żądań
        self.assertEqual(self.rows("SELECT (SELECT COUNT(*) FROM Clients), (SELECT COUNT(*) FROM Offers), (SELECT COUNT(*) FROM Wuzetkas)"), before)
        self.assertEqual(self.popups, [])

    def test_rejected_operations_do_not_fall_back_to_sqlite(self):
        before = self.rows("SELECT * FROM Clients ORDER BY Nip")
        with self.assertRaises(ReadOnlyBackendError):
            self.sp.add_client("5555555559", "Nowy", "a", "b", "NOWY")
        self.assertEqual(self.rows("SELECT * FROM Clients ORDER BY Nip"), before)

    def test_all_contract_methods_are_covered_by_read_or_rejection(self):
        read_methods = {"is_available", "get_clients", "get_client_by_nip", "validate_nip", "validate_alias", "get_suppliers",
                        "get_supplier_by_nip", "get_default_supplier", "validate_supplier_nip", "get_offer_context",
                        "find_offer_by_filename", "get_all_offer_file_paths", "get_wz_context", "get_all_wz",
                        "get_all_wz_file_paths"}
        self.assertEqual(read_methods | {n for n, _ in self.WRITE_CALLS}, set(DataBackend.__abstractmethods__))

    def test_only_dev_environment_is_accepted(self):
        prod = get_environment("PROD")
        with self.assertRaises(DataAccessError):
            SharePointBackend(BackendContext(lambda: "", lambda: "", lambda: False, lambda t, m: None, lambda *a: None),
                              FakeSession(), prod)

    def test_backend_source_contains_no_write_http_calls_and_no_sqlite(self):
        source = inspect.getsource(sp_module)
        for forbidden in ("requests.", ".post(", ".patch(", ".put(", ".delete(", "sqlite3", "tkinter", "DELETE", "PATCH"):
            self.assertNotIn(forbidden, source, forbidden)

    def test_facade_default_backend_is_still_sqlite_and_does_not_know_sharepoint(self):
        self.assertEqual(type(dbs.get_backend()).__name__, "SqliteBackend")
        self.assertNotIn("SharePoint", inspect.getsource(dbs))

    def test_real_client_exposes_only_get(self):
        for name in ("post", "patch", "put", "delete", "request"):
            self.assertFalse(hasattr(RetryingGraphClient, name), name)


# ---------------------------------------------------------------------------
# klient z ponowieniami i sesja
# ---------------------------------------------------------------------------
class RetryingClientTests(unittest.TestCase):
    def client(self, sleeps, attempts=4):
        return RetryingGraphClient(DEV_ENV, "tok", max_attempts=attempts, sleep=sleeps.append)

    def patched(self, *results):
        return mock.patch.object(GraphClient, "get", side_effect=list(results))

    def test_retry_after_header_is_honoured_for_429(self):
        sleeps = []
        with self.patched(GraphError("429", status=429, retry_after="3"), {"value": []}) as get:
            self.assertEqual(self.client(sleeps).get("/x"), {"value": []})
        self.assertEqual(sleeps, [3.0])
        self.assertEqual(get.call_count, 2)

    def test_503_uses_short_exponential_backoff(self):
        sleeps = []
        with self.patched(GraphError("503", status=503), GraphError("503", status=503), {"ok": 1}):
            self.assertEqual(self.client(sleeps).get("/x"), {"ok": 1})
        self.assertEqual(sleeps, [1, 2])

    def test_retries_are_bounded(self):
        sleeps = []
        with self.patched(*[GraphError("503", status=503)] * 10) as get:
            with self.assertRaises(GraphError):
                self.client(sleeps).get("/x")
        self.assertEqual(get.call_count, 4)
        self.assertEqual(len(sleeps), 3)

    def test_retry_after_is_capped_and_non_numeric_value_falls_back_to_backoff(self):
        sleeps = []
        with self.patched(GraphError("429", status=429, retry_after="9999"), GraphError("429", status=429, retry_after="Wed, 21 Oct 2026"), {}):
            self.client(sleeps).get("/x")
        self.assertEqual(sleeps, [30.0, 2])

    def test_client_errors_are_not_retried(self):
        for status in (400, 401, 403, 404):
            sleeps = []
            with self.patched(GraphError("x", status=status)) as get:
                with self.assertRaises(GraphError):
                    self.client(sleeps).get("/x")
            self.assertEqual((get.call_count, sleeps), (1, []), status)

    def test_connection_errors_are_retried_a_limited_number_of_times(self):
        sleeps = []
        with self.patched(GraphError("połączenie", status=None), {"ok": 1}):
            self.assertEqual(self.client(sleeps).get("/x"), {"ok": 1})
        self.assertEqual(sleeps, [1])


class SessionTests(unittest.TestCase):
    def make(self, silent=None):
        self.now = 1000.0
        self.sleeps = []
        calls = {"acquire": 0}

        def acquire(interactive_log=None):
            calls["acquire"] += 1
            return {"access_token": "T-INTERAKTYWNY", "expires_in": 3600}
        self.calls = calls
        return SharePointSession(acquire=acquire, acquire_silent=silent or (lambda: None), clock=lambda: self.now)

    def test_not_active_before_sign_in_and_sign_in_makes_it_active(self):
        s = self.make()
        self.assertFalse(s.is_active())
        with self.assertRaises(NotSignedInError):
            s.get_token()
        s.sign_in()
        self.assertTrue(s.is_active())
        self.assertEqual(s.get_token(), "T-INTERAKTYWNY")
        self.assertEqual(self.calls["acquire"], 1)

    def test_expired_token_is_refreshed_silently_without_interactive_login(self):
        s = self.make(silent=lambda: {"access_token": "T-CICHY", "expires_in": 3600})
        s.sign_in()
        self.now += 3600
        self.assertEqual(s.get_token(), "T-CICHY")
        self.assertEqual(self.calls["acquire"], 1)  # logowanie interaktywne tylko raz

    def test_failed_silent_refresh_ends_the_session_instead_of_opening_a_browser(self):
        s = self.make(silent=lambda: None)
        s.sign_in()
        self.now += 3600
        with self.assertRaises(NotSignedInError):
            s.get_token()
        self.assertFalse(s.is_active())
        self.assertEqual(self.calls["acquire"], 1)

    def test_invalidate_forces_silent_refresh_and_sign_out_clears_the_token(self):
        s = self.make(silent=lambda: {"access_token": "T2", "expires_in": 3600})
        s.sign_in()
        s.invalidate_token()
        self.assertEqual(s.get_token(), "T2")
        s.sign_out()
        self.assertFalse(s.is_active())

    def test_token_is_not_exposed_in_repr_or_errors(self):
        s = self.make()
        s.sign_in()
        self.assertNotIn("T-INTERAKTYWNY", repr(s))
        self.assertNotIn("T-INTERAKTYWNY", repr(vars(s).get("_acquire")))


if __name__ == "__main__":
    unittest.main()
