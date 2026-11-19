"""Testy infrastruktury etapu 4B-1 (wspólnej dla Clients i Suppliers) - offline, na atrapie Graph.

Uruchomienie: python -m unittest tests.sharepoint_infrastructure_test -v
Zakres: pamięć ETagów rozdzielona per lista, lista zapisu GraphWriter, DELETE z wymaganym konkretnym ETagiem,
PartialFailureMessage oraz normalizacja pustego tekstu w odczytach Suppliers. Żadnych żądań sieciowych i żadnych
operacji CRUD dla Suppliers (te nadal zgłaszają ReadOnlyBackendError).
"""
import inspect
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import src.data.backends.sharepoint_backend as sp_module  # noqa: E402
import src.integrations.sharepoint.writer as writer_module  # noqa: E402
import tests.sharepoint_backend_test as spt  # noqa: E402  (moduł - bez duplikowania testów)
import tests.sharepoint_client_write_test as cwt  # noqa: E402
from src.data.errors import (  # noqa: E402
    ConcurrencyConflictError, ConflictMessage, ItemNotFoundError, PartialFailureMessage, ReadOnlyBackendError,
    SharePointError)
from src.integrations.sharepoint import environment_manager, get_environment  # noqa: E402
from src.integrations.sharepoint.graph_client import EnvironmentMismatchError  # noqa: E402
from src.integrations.sharepoint.migration.guard import MigrationGuardError  # noqa: E402
from src.integrations.sharepoint.writer import WRITABLE_LISTS, GraphWriteError, GraphWriter  # noqa: E402

SHARED_NIP = "3333333333"  # ten sam NIP jest jednocześnie klientem i dostawcą w danych testowych


class InfraCase(cwt.WriteCase):
    def supplier(self, title):
        return next(i for i in self.graph.data["Suppliers"] if i["fields"].get("Title") == title)

    def client(self, title):
        return next(i for i in self.graph.data["Clients"] if i["fields"].get("Title") == title)

    def use_http(self, http):
        """Podmienia warstwę HTTP zapisu (np. aby zasymulować zmianę elementu przez innego użytkownika tuż przed DELETE)."""
        self.sp._writer_factory = lambda: GraphWriter(spt.DEV_ENV, self.session.get_token(), http=http, sleep=self.sleeps.append)


# ---------------------------------------------------------------------------
# pamięć ETagów: klucz (lista, Title)
# ---------------------------------------------------------------------------
class EtagCacheTests(InfraCase):
    def setUp(self):
        super().setUp()
        self.supplier(SHARED_NIP)["version"] = 7  # różne wersje => różne ETagi dla tego samego NIP-u
        self.client_key, self.supplier_key = ("Clients", SHARED_NIP), ("Suppliers", SHARED_NIP)

    def test_keys_are_list_and_title_and_the_same_nip_coexists_in_both_lists(self):
        self.sp.get_clients()
        self.sp.get_suppliers()
        self.assertIn(self.client_key, self.sp._etags)
        self.assertIn(self.supplier_key, self.sp._etags)
        self.assertTrue(all(isinstance(k, tuple) and len(k) == 2 and k[0] in ("Clients", "Suppliers") for k in self.sp._etags))
        client_item, supplier_item = self.client(SHARED_NIP), self.supplier(SHARED_NIP)
        self.assertEqual(self.sp._etags[self.client_key], (str(client_item["id"]), self.graph._etag(client_item)))
        self.assertEqual(self.sp._etags[self.supplier_key], (str(supplier_item["id"]), self.graph._etag(supplier_item)))
        self.assertNotEqual(self.sp._etags[self.client_key][1], self.sp._etags[self.supplier_key][1])

    def test_supplier_reads_never_overwrite_client_etags_and_vice_versa(self):
        self.sp.get_clients()
        client_entry = self.sp._etags[self.client_key]
        self.sp.get_suppliers()
        self.sp.get_supplier_by_nip(SHARED_NIP)
        self.assertEqual(self.sp._etags[self.client_key], client_entry)
        supplier_entry = self.sp._etags[self.supplier_key]
        self.sp.get_clients(True)
        self.sp.get_client_by_nip(SHARED_NIP)
        self.assertEqual(self.sp._etags[self.supplier_key], supplier_entry)
        self.assertEqual(self.sp._etags[self.client_key], client_entry)

    def test_single_item_reads_only_touch_their_own_list(self):
        self.sp.get_supplier_by_nip(SHARED_NIP)
        self.assertEqual(list(self.sp._etags), [self.supplier_key])
        self.sp.get_client_by_nip(SHARED_NIP)
        self.assertEqual(set(self.sp._etags), {self.supplier_key, self.client_key})

    def test_a_full_read_replaces_only_the_entries_of_its_own_list(self):
        self.sp.get_clients()
        self.sp.get_suppliers()
        client_keys = {k for k in self.sp._etags if k[0] == "Clients"}
        self.graph.data["Suppliers"].remove(self.supplier("5555555555"))  # usunięty przez innego użytkownika
        self.graph.data["Clients"].remove(self.client("1111111111"))
        self.sp.get_suppliers()
        self.assertNotIn(("Suppliers", "5555555555"), self.sp._etags)
        self.assertEqual({k for k in self.sp._etags if k[0] == "Clients"}, client_keys)  # klienci nietknięci
        self.sp.get_clients()
        self.assertNotIn(("Clients", "1111111111"), self.sp._etags)
        self.assertIn(self.supplier_key, self.sp._etags)

    def test_invalidation_is_independent_per_list(self):
        self.sp.get_clients()
        self.sp.get_suppliers()
        self.sp._forget_etag("Clients", SHARED_NIP)
        self.assertNotIn(self.client_key, self.sp._etags)
        self.assertIn(self.supplier_key, self.sp._etags)
        self.sp._remember_etag("Clients", SHARED_NIP, 5, '"x,1"')
        self.sp._forget_etag("Suppliers", SHARED_NIP)
        self.assertIn(self.client_key, self.sp._etags)
        self.assertNotIn(self.supplier_key, self.sp._etags)
        self.sp._forget_etag("Suppliers", "nie-ma-takiego")  # brak wpisu nie jest błędem

    def test_a_conflict_on_a_client_drops_only_the_client_etag(self):
        self.sp.get_clients()
        self.sp.get_suppliers()
        supplier_entry = self.sp._etags[self.supplier_key]
        self.client(SHARED_NIP)["version"] = 9  # inny użytkownik zmienił klienta
        result = self.sp.update_client(SHARED_NIP, "Inna nazwa", "ul. D", "33-333", "LODZ")
        self.assertIsInstance(result[1], ConflictMessage)
        self.assertNotIn(self.client_key, self.sp._etags)
        self.assertEqual(self.sp._etags[self.supplier_key], supplier_entry)

    def test_deleting_a_client_drops_only_the_client_etag(self):
        self.sp.get_clients()
        self.sp.get_suppliers()
        self.client(SHARED_NIP)["fields"]["Alias"] = "LODZ-BEZ-OFERT"
        self.assertEqual(self.sp.delete_client(SHARED_NIP), cwt.DELETE_OK)
        self.assertNotIn(self.client_key, self.sp._etags)
        self.assertIn(self.supplier_key, self.sp._etags)

    def test_client_update_uses_the_client_etag_and_not_the_supplier_one(self):
        self.sp.get_suppliers()
        self.sp.get_clients()
        client_etag = self.graph._etag(self.client(SHARED_NIP))
        self.assertNotEqual(client_etag, self.graph._etag(self.supplier(SHARED_NIP)))
        self.assertEqual(self.sp.update_client(SHARED_NIP, "Nowa nazwa", "ul. D", "33-333", "LODZ"), cwt.UPDATE_OK)
        self.assertEqual(self.graph.writes[0]["if_match"], client_etag)
        self.assertNotEqual(self.sp._etags[self.client_key][1], client_etag)  # po zapisie: ETag z odpowiedzi
        self.assertEqual(self.sp._etags[self.supplier_key][1], self.graph._etag(self.supplier(SHARED_NIP)))

    def test_an_etag_is_used_only_for_the_same_item_id(self):
        self.sp.get_clients()
        item = self.client(SHARED_NIP)
        self.assertEqual(self.sp._cached_etag("Clients", SHARED_NIP, item["id"]), self.graph._etag(item))
        self.assertIsNone(self.sp._cached_etag("Clients", SHARED_NIP, item["id"] + 1000))
        self.assertIsNone(self.sp._cached_etag("Suppliers", SHARED_NIP, item["id"]))  # nie z tej listy

    def test_only_clients_and_suppliers_have_an_etag_cache(self):
        for list_name in ("Offers", "Wuzetkas", "Nieznana"):
            with self.subTest(list_name=list_name):
                with self.assertRaises(ValueError):
                    self.sp._remember_etag(list_name, "x", 1, '"e,1"')
                with self.assertRaises(ValueError):
                    self.sp._forget_etag(list_name, "x")
        self.assertEqual(self.sp._etags, {})

    def test_reading_suppliers_sends_no_write_requests(self):
        self.sp.get_suppliers()
        self.sp.get_supplier_by_nip(SHARED_NIP)
        self.sp.get_default_supplier()
        self.assertEqual(self.graph.writes, [])


# ---------------------------------------------------------------------------
# GraphWriter: lista zapisu {Clients, Suppliers}
# ---------------------------------------------------------------------------
class WriterScopeTests(unittest.TestCase):
    def writer(self, env=None):
        self.fake = spt.FakeGraph(spt.build_graph_data(spt.TABLES))
        return GraphWriter(env or spt.DEV_ENV, "TOKEN-NIE-DO-LOGOW", http=self.fake.http, sleep=lambda s: None)

    def test_the_allowlist_is_exactly_clients_and_suppliers(self):
        self.assertEqual(WRITABLE_LISTS, frozenset({"Clients", "Suppliers"}))
        self.assertEqual(self.writer()._writable, WRITABLE_LISTS)

    def test_create_update_and_delete_work_for_clients_and_for_suppliers(self):
        w = self.writer()
        for list_name, title in (("Clients", "9990000001"), ("Suppliers", "9990000002")):
            with self.subTest(list_name=list_name):
                created = w.create_item(list_name, {"Title": title, "CompanyName": "ZZTEST-A"})
                updated = w.update_item_fields(list_name, created.item_id, {"AddressP1": "ul. T"}, created.etag)
                self.assertNotEqual(updated.etag, created.etag)
                w.delete_item(list_name, created.item_id, updated.etag)
        paths = [(x["method"], x["path"].split("/lists/")[1].split("/")[0]) for x in self.fake.writes]
        self.assertEqual({p[1] for p in paths}, {spt.DEV_ENV.lists["Clients"], spt.DEV_ENV.lists["Suppliers"]})
        self.assertEqual([m for m, _ in paths], ["POST", "PATCH", "DELETE"] * 2)

    def test_offers_wuzetkas_and_any_other_list_are_refused_before_any_request(self):
        w = self.writer()
        for list_name in ("Offers", "Wuzetkas", "Nieznana", "suppliers", "Clients ", ""):
            with self.subTest(list_name=list_name):
                with self.assertRaises(GraphWriteError):
                    w.create_item(list_name, {"Title": "9990000001"})
                with self.assertRaises(GraphWriteError):
                    w.update_item_fields(list_name, "2", {"Alias": "x"}, '"e,1"')
                with self.assertRaises(GraphWriteError):
                    w.delete_item(list_name, "2", '"e,1"')
        self.assertEqual(self.fake.writes, [])

    def test_prod_is_refused_for_both_lists_without_any_request(self):
        w = self.writer(env=get_environment("PROD"))
        for list_name in ("Clients", "Suppliers"):
            with self.subTest(list_name=list_name), self.assertRaises((MigrationGuardError, EnvironmentMismatchError)):
                w.create_item(list_name, {"Title": "9990000001"})
        w = self.writer()
        environment_manager.set_active("PROD")
        self.addCleanup(environment_manager.reset)
        for list_name in ("Clients", "Suppliers"):
            with self.subTest(list_name=list_name, active="PROD"), self.assertRaises((MigrationGuardError, EnvironmentMismatchError)):
                w.delete_item(list_name, "2", '"e,1"')
        self.assertEqual(self.fake.writes, [])

    def test_the_backend_cannot_widen_the_allowlist(self):
        self.assertNotIn("writable_lists", inspect.getsource(sp_module))
        self.assertEqual(writer_module.WRITABLE_LISTS, WRITABLE_LISTS)


# ---------------------------------------------------------------------------
# DELETE wymaga konkretnego ETagu
# ---------------------------------------------------------------------------
class DeleteWriterTests(unittest.TestCase):
    def setUp(self):
        self.fake = spt.FakeGraph(spt.build_graph_data(spt.TABLES))
        self.sleeps = []
        self.w = GraphWriter(spt.DEV_ENV, "TOKEN-NIE-DO-LOGOW", http=self.fake.http, sleep=self.sleeps.append)
        self.item = self.fake.data["Clients"][0]
        self.etag = self.fake._etag(self.item)

    def delete(self, etag, item=None):
        return self.w.delete_item("Clients", (item or self.item)["id"], etag)

    def test_a_concrete_etag_is_required_no_missing_empty_or_star(self):
        for etag in (None, "", "   ", "*", " * ", 123, b'"e,1"', ["x"], '"e,1"\r\nX-Evil: 1', '"e,1"\n'):
            with self.subTest(etag=etag), self.assertRaises(GraphWriteError):
                self.delete(etag)
        self.assertEqual(self.fake.writes, [])
        self.assertIn(self.item, self.fake.data["Clients"])

    def test_delete_without_the_etag_argument_is_not_possible(self):
        with self.assertRaises(TypeError):
            self.w.delete_item("Clients", self.item["id"])
        self.assertEqual(self.fake.writes, [])

    def test_the_etag_is_sent_in_if_match_and_204_is_success(self):
        self.assertIsNone(self.delete(self.etag))
        self.assertEqual([(x["method"], x["if_match"]) for x in self.fake.writes], [("DELETE", self.etag)])
        self.assertNotIn(self.item, self.fake.data["Clients"])

    def test_status_200_is_also_accepted_as_success(self):
        self.fake.http = lambda *a, **k: spt.FakeResponse(200, {})
        w = GraphWriter(spt.DEV_ENV, "t", http=self.fake.http, sleep=lambda s: None)
        self.assertIsNone(w.delete_item("Clients", 2, '"e,1"'))

    def test_404_means_the_item_does_not_exist(self):
        with self.assertRaises(GraphWriteError) as caught:
            self.w.delete_item("Clients", 999999, '"e,1"')
        self.assertEqual((caught.exception.status, caught.exception.code), (404, "itemNotFound"))
        self.assertFalse(caught.exception.ambiguous)
        self.assertEqual(len(self.fake.writes), 1)

    def test_412_is_a_conflict_without_retry_and_without_a_fallback_delete(self):
        self.item["version"] = 5  # element zmienił się po odczycie
        with self.assertRaises(GraphWriteError) as caught:
            self.delete(self.etag)
        self.assertEqual((caught.exception.status, caught.exception.code), (412, "resourceModified"))
        self.assertFalse(caught.exception.ambiguous)
        self.assertEqual([x["if_match"] for x in self.fake.writes], [self.etag])  # jedno żądanie, bez `*` i bez If-Match
        self.assertEqual(self.sleeps, [])
        self.assertIn(self.item, self.fake.data["Clients"])  # element nie został usunięty

    def test_an_injected_412_is_not_retried_either(self):
        self.fake.faults.append({"kind": "status", "status": 412, "code": "resourceModified"})
        with self.assertRaises(GraphWriteError) as caught:
            self.delete(self.etag)
        self.assertEqual(caught.exception.status, 412)
        self.assertEqual(len(self.fake.writes), 1)
        self.assertEqual(self.sleeps, [])

    def test_429_keeps_the_existing_retry_policy(self):
        self.fake.faults.append({"kind": "status", "status": 429, "headers": {"Retry-After": "2"}})
        self.delete(self.etag)
        self.assertEqual([x["method"] for x in self.fake.writes], ["DELETE", "DELETE"])
        self.assertEqual(self.sleeps, [2.0])
        self.assertTrue(all(x["if_match"] == self.etag for x in self.fake.writes))  # ponowienie z tym samym ETagiem
        self.fake.data["Clients"].append(self.item)
        self.fake.faults += [{"kind": "status", "status": 429}] * 3
        self.fake.writes.clear()
        with self.assertRaises(GraphWriteError) as caught:
            self.delete(self.etag)
        self.assertEqual((caught.exception.status, len(self.fake.writes)), (429, 3))

    def test_5xx_and_connection_errors_are_not_retried_and_are_ambiguous(self):
        for fault in ({"kind": "status", "status": 503}, {"kind": "status", "status": 504}, {"kind": "raise"}):
            with self.subTest(fault=fault):
                self.fake.writes.clear()
                self.fake.faults.append(fault)
                with self.assertRaises(GraphWriteError) as caught:
                    self.delete(self.etag)
                self.assertTrue(caught.exception.ambiguous)
                self.assertEqual(len(self.fake.writes), 1)
        self.assertEqual(self.sleeps, [])

    def test_error_messages_do_not_contain_the_token(self):
        self.fake.faults.append({"kind": "status", "status": 503})
        with self.assertRaises(GraphWriteError) as caught:
            self.delete(self.etag)
        self.assertNotIn("TOKEN-NIE-DO-LOGOW", str(caught.exception))
        self.assertNotIn("TOKEN-NIE-DO-LOGOW", repr(self.fake.writes))


class DeleteVerifiedBackendTests(InfraCase):
    def test_verified_delete_sends_the_etag_from_the_verification_read_for_clients_and_suppliers(self):
        for list_name, nip in (("Clients", "2222222222"), ("Suppliers", "3333333333")):
            with self.subTest(list_name=list_name):
                item = next(i for i in self.graph.data[list_name] if i["fields"]["Title"] == nip)
                etag = self.graph._etag(item)
                self.graph.writes.clear()
                self.sp._delete_verified(list_name, item["id"], nip)
                self.assertEqual([(w["method"], w["if_match"]) for w in self.graph.writes], [("DELETE", etag)])
                self.assertNotIn(item, self.graph.data[list_name])

    def test_a_change_between_verification_and_delete_gives_412_and_nothing_is_deleted(self):
        target = self.client("2222222222")

        def modify_then_delete(method, url, **kwargs):
            if method == "DELETE":
                target["version"] = target.get("version", 1) + 1  # ktoś zmienił element po odczycie weryfikującym
            return self.graph.http(method, url, **kwargs)
        self.use_http(modify_then_delete)
        with self.assertRaises(ConcurrencyConflictError):
            self.sp._delete_verified("Clients", target["id"], "2222222222")
        self.assertIn(target, self.graph.data["Clients"])
        self.assertEqual(len(self.graph.writes), 1)  # bez ponowienia

    def test_delete_client_reports_a_conflict_message_on_412_and_drops_the_etag(self):
        target = self.client("2222222222")
        target["fields"]["Alias"] = "ZETA-BEZ-OFERT"
        self.sp.get_clients()

        def modify_then_delete(method, url, **kwargs):
            if method == "DELETE":
                target["version"] = target.get("version", 1) + 1
            return self.graph.http(method, url, **kwargs)
        self.use_http(modify_then_delete)
        result = self.sp.delete_client(2222222222)
        self.assertFalse(result[0])
        self.assertIsInstance(result[1], ConflictMessage)
        self.assertNotIn(("Clients", "2222222222"), self.sp._etags)
        self.assertIn(target, self.graph.data["Clients"])
        self.assertEqual(self.methods(), ["DELETE"])

    def test_item_removed_between_verification_and_delete_gives_not_found(self):
        target = self.client("2222222222")
        target["fields"]["Alias"] = "ZETA-BEZ-OFERT"

        def remove_then_delete(method, url, **kwargs):
            if method == "DELETE":
                self.graph.data["Clients"].remove(target)
            return self.graph.http(method, url, **kwargs)
        self.use_http(remove_then_delete)
        self.assertEqual(self.sp.delete_client(2222222222), cwt.NOT_FOUND)
        with self.assertRaises(ItemNotFoundError):
            self.sp._delete_verified("Clients", target["id"], "2222222222")

    def test_missing_etag_in_the_verification_read_refuses_to_delete(self):
        real_get = self.graph.get

        def get_without_etag(path, params=None):
            data = real_get(path, params)
            if isinstance(data, dict) and "fields" in data and "value" not in data:
                data = {k: v for k, v in data.items() if k not in ("@odata.etag", "eTag")}
            return data
        self.graph.get = get_without_etag
        with self.assertRaises(SharePointError) as caught:
            self.sp._delete_verified("Clients", self.client("2222222222")["id"], "2222222222")
        self.assertIn("brak ETagu", str(caught.exception))
        self.assertEqual(self.graph.writes, [])  # żadnego DELETE, także bez If-Match

    def test_503_on_delete_is_reported_without_retry_and_the_item_stays(self):
        target = self.client("2222222222")
        target["fields"]["Alias"] = "ZETA-BEZ-OFERT"
        self.graph.faults.append({"kind": "status", "status": 503})
        ok, message = self.sp.delete_client(2222222222)
        self.assertFalse(ok)
        self.assertNotIsInstance(message, ConflictMessage)
        self.assertEqual(self.methods(), ["DELETE"])
        self.assertIn(target, self.graph.data["Clients"])

    def test_verified_delete_still_refuses_other_lists_and_bad_ids_without_requests(self):
        for list_name, item_id in (("Offers", "2"), ("Wuzetkas", "2"), ("Nieznana", "2"), ("Suppliers", "abc"), ("Clients", "")):
            with self.subTest(list_name=list_name, item_id=item_id), self.assertRaises(SharePointError):
                self.sp._delete_verified(list_name, item_id, "x")
        self.assertEqual((self.graph.requests, self.graph.writes), ([], []))


# ---------------------------------------------------------------------------
# PartialFailureMessage
# ---------------------------------------------------------------------------
class PartialFailureMessageTests(unittest.TestCase):
    def test_it_is_recognizable_as_a_partial_failure(self):
        msg = PartialFailureMessage("Częściowe niepowodzenie")
        self.assertTrue(msg.partial)
        self.assertIs(PartialFailureMessage.partial, True)
        self.assertIsInstance(msg, PartialFailureMessage)

    def test_it_behaves_like_ordinary_text_in_result_tuples(self):
        msg = PartialFailureMessage("Dostawca ustawiony, ale nie odznaczono poprzedniego")
        self.assertIsInstance(msg, str)
        self.assertEqual(msg, "Dostawca ustawiony, ale nie odznaczono poprzedniego")
        self.assertEqual((False, msg), (False, "Dostawca ustawiony, ale nie odznaczono poprzedniego"))
        self.assertIn("nie odznaczono", msg)
        self.assertTrue(msg.startswith("Dostawca"))
        self.assertEqual(f"Błąd: {msg}", "Błąd: Dostawca ustawiony, ale nie odznaczono poprzedniego")
        self.assertEqual(hash(msg), hash(str(msg)))

    def test_it_is_distinct_from_a_conflict_and_from_plain_text(self):
        partial, conflict = PartialFailureMessage("x"), ConflictMessage("x")
        self.assertEqual(partial, conflict)  # to samo brzmienie, ale inna klasa i inny znacznik
        self.assertNotIsInstance(partial, ConflictMessage)
        self.assertNotIsInstance(conflict, PartialFailureMessage)
        self.assertFalse(getattr(partial, "conflict", False))
        self.assertFalse(getattr(conflict, "partial", False))
        self.assertFalse(getattr("zwykły tekst", "partial", False))
        self.assertTrue(issubclass(PartialFailureMessage, str) and not issubclass(PartialFailureMessage, ConflictMessage))

    def test_empty_and_unicode_messages_keep_the_marker(self):
        for text in ("", "Zażółć gęślą jaźń", "linia 1\nlinia 2"):
            self.assertTrue(PartialFailureMessage(text).partial)

    def test_it_is_used_only_by_set_default_supplier_and_not_by_other_crud_operations(self):
        self.assertIn("PartialFailureMessage", inspect.getsource(sp_module.SharePointBackend.set_default_supplier)
                      + inspect.getsource(sp_module.SharePointBackend._partial_default_message))
        for name in ("add_client", "update_client", "delete_client", "set_client_extended_fields", "add_supplier",
                     "update_supplier", "delete_supplier", "_patch_item"):
            self.assertNotIn("PartialFailureMessage", inspect.getsource(getattr(sp_module.SharePointBackend, name)), name)


# ---------------------------------------------------------------------------
# normalizacja pustego tekstu w odczytach Suppliers
# ---------------------------------------------------------------------------
class SupplierTextNormalizationTests(InfraCase):
    def test_none_and_missing_text_fields_are_returned_as_empty_strings(self):
        item = self.supplier("6666666666")
        for field in ("CompanyName", "AddressP1", "AddressP2"):
            item["fields"].pop(field, None)
        row = self.sp.get_supplier_by_nip("6666666666")
        self.assertEqual(row, (6666666666, "", "", "", 0))
        self.assertIn(row, self.sp.get_suppliers())

    def test_get_default_supplier_normalizes_text_too(self):
        for other in self.graph.data["Suppliers"]:
            other["fields"]["IsDefault"] = False
        item = self.supplier("6666666666")
        item["fields"].pop("AddressP2", None)
        item["fields"].pop("CompanyName", None)
        item["fields"]["IsDefault"] = True
        self.assertEqual(self.sp.get_default_supplier(), (6666666666, "", "ul. S3", "", 1))

    def test_public_shape_and_types_are_unchanged(self):
        self.supplier("6666666666")["fields"].pop("AddressP1", None)
        for row in self.sp.get_suppliers():
            self.assertIsInstance(row, tuple)
            self.assertEqual(len(row), 5)
            self.assertEqual([type(v) for v in row], [int, str, str, str, int])
            self.assertIs(type(row[4]), int)  # int, nie bool

    def test_is_default_absent_false_and_true(self):
        self.supplier("3333333333")["fields"].pop("IsDefault", None)
        self.supplier("5555555555")["fields"]["IsDefault"] = True
        self.supplier("6666666666")["fields"]["IsDefault"] = False
        flags = {r[0]: r[4] for r in self.sp.get_suppliers()}
        self.assertEqual(flags, {3333333333: 0, 5555555555: 1, 6666666666: 0})

    def test_empty_names_sort_first_like_the_binary_collation(self):
        self.supplier("6666666666")["fields"].pop("CompanyName", None)
        self.assertEqual(self.sp.get_suppliers()[0][0], 6666666666)
        self.assertEqual([r[1] for r in self.sp.get_suppliers()], ["", "Dostawca A", "Dostawca B"])

    def test_values_that_are_present_are_returned_unchanged(self):
        # parytet z SQLite dla danych bez pustych pól
        self.assertEqual(self.sp.get_suppliers(), self.sq.get_suppliers())
        self.assertEqual(self.sp.get_default_supplier(), self.sq.get_default_supplier())
        self.assertEqual(self.sp.get_supplier_by_nip(5555555555), self.sq.get_supplier_by_nip(5555555555))

    def test_client_normalization_from_4a_is_unchanged(self):
        self.client("2222222222")["fields"].pop("AddressP2", None)
        self.assertEqual(self.sp.get_client_by_nip(2222222222)[3], "")


if __name__ == "__main__":
    unittest.main()
