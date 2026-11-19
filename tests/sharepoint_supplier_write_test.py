"""Testy zapisu dostawców w SharePointBackend (etap 4B-2: add, update, delete) - offline, na atrapie Graph.

Uruchomienie: python -m unittest tests.sharepoint_supplier_write_test -v
Żadnych żądań sieciowych, żadnych zapisów do SharePoint ani do prawdziwej bazy użytkownika. Atrapa odwzorowuje zachowanie
zmierzone na DEV (docs/sharepoint-graph-behavior.md, sonda 4B-0): 400 invalidRequest przy kolizji NIP, 412 przy
nieaktualnym If-Match także dla DELETE, 404 dla nieistniejącego ID, domyślne IsDefault=false przy tworzeniu.
Zmiana dostawcy domyślnego (set_default_supplier) jest testowana osobno: tests/sharepoint_supplier_default_test.py.
"""
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import requests  # noqa: E402

import src.data.backends.sharepoint_backend as sp_module  # noqa: E402
import tests.sharepoint_backend_test as spt  # noqa: E402  (moduł - bez duplikowania testów)
import tests.sharepoint_infrastructure_test as inf  # noqa: E402
from src.data.errors import ConflictMessage, ReadOnlyBackendError  # noqa: E402
from src.integrations.sharepoint.graph_client import GraphError  # noqa: E402

UNAVAILABLE = (False, "Baza danych jest niedostępna lub nie istnieje.")
NOT_FOUND = (False, "Dostawca nie został znaleziony")
NIP_TAKEN = (False, "Dostawca z tym NIP już istnieje w bazie")
DEFAULT_REFUSED = (False, "Nie można usunąć domyślnego dostawcy. Najpierw ustaw innego dostawcę jako domyślny.")
ADD_OK = (True, "Dostawca został pomyślnie dodany do bazy")
UPDATE_OK = (True, "Dane dostawcy zostały zaktualizowane")
DELETE_OK = (True, "Dostawca został usunięty z bazy")
NEW_NIP = "7777777777"
# dane testowe: 3333333333 "Dostawca B" (niedomyślny), 5555555555 "Dostawca A" (DOMYŚLNY), 6666666666 "dostawca c" (niedomyślny)
PLAIN, DEFAULT, THIRD = "3333333333", "5555555555", "6666666666"


class SupplierCase(inf.InfraCase):
    def suppliers_writes(self):
        list_id = spt.DEV_ENV.lists["Suppliers"]
        return [w for w in self.graph.writes if f"/lists/{list_id}/" in w["path"]]

    def payloads(self, method):
        return [w["json"] for w in self.graph.writes if w["method"] == method]

    def default_flags(self):
        return {i["fields"]["Title"]: i["fields"].get("IsDefault") for i in self.graph.data["Suppliers"]}

    def assert_only_suppliers_written(self):
        self.assertEqual(len(self.suppliers_writes()), len(self.graph.writes))

    def assert_no_is_default_true_sent(self):
        for body in self.payloads("POST") + self.payloads("PATCH"):
            fields = body.get("fields", body)
            self.assertIsNot(fields.get("IsDefault"), True)


# ---------------------------------------------------------------------------
# add_supplier
# ---------------------------------------------------------------------------
class AddSupplierTests(SupplierCase):
    def test_creates_the_supplier_with_is_default_false_and_text_fields(self):
        self.assertEqual(self.sp.add_supplier(NEW_NIP, "Nowy dostawca", "ul. N 1", "00-000 Test"), ADD_OK)
        payload = self.payloads("POST")
        self.assertEqual(payload, [{"fields": {"Title": NEW_NIP, "CompanyName": "Nowy dostawca", "AddressP1": "ul. N 1",
                                               "AddressP2": "00-000 Test", "IsDefault": False}}])
        self.assertIs(payload[0]["fields"]["IsDefault"], False)  # jawne false, nie 0
        self.assertEqual(self.sp.get_supplier_by_nip(NEW_NIP), (int(NEW_NIP), "Nowy dostawca", "ul. N 1", "00-000 Test", 0))
        self.assertEqual(self.methods(), ["POST"])
        self.assert_only_suppliers_written()

    def test_the_new_supplier_never_changes_the_default_flags_of_existing_suppliers(self):
        before = self.default_flags()
        self.sp.add_supplier(NEW_NIP, "Nowy", "a", "b")
        after = self.default_flags()
        self.assertEqual({k: v for k, v in after.items() if k != NEW_NIP}, before)
        self.assertIs(after[NEW_NIP], False)
        self.assertEqual(self.sp.get_default_supplier()[0], int(DEFAULT))

    def test_no_null_or_empty_text_is_sent(self):
        self.assertEqual(self.sp.add_supplier(NEW_NIP, "Nowy", None, ""), ADD_OK)
        fields = self.payloads("POST")[0]["fields"]
        self.assertEqual(fields, {"Title": NEW_NIP, "CompanyName": "Nowy", "IsDefault": False})
        self.assertTrue(all(v is not None and v != "" for v in fields.values()))
        self.assertEqual(self.sp.get_supplier_by_nip(NEW_NIP), (int(NEW_NIP), "Nowy", "", "", 0))  # odczyt: '' jak w SQLite

    def test_company_name_and_addresses_are_stored_as_given_without_newline_conversion(self):
        # dla dostawców (inaczej niż Clients.AddressP2) nie ma transformacji; nazwa z literalnym "\n" z UI zostaje bez zmian
        self.sp.add_supplier(NEW_NIP, "Firma\\nOddział", "ul. A", "00-001 Miasto")
        self.assertEqual(self.supplier(NEW_NIP)["fields"]["CompanyName"], "Firma\\nOddział")
        self.assertEqual(self.supplier(NEW_NIP)["fields"]["AddressP2"], "00-001 Miasto")

    def test_validation_and_success_messages_match_sqlite(self):
        for nip in ("123", "abc", "", "12345678901", "12345abcde"):
            self.both("add_supplier", nip, "F", "a", "b")
        self.both("add_supplier", PLAIN, "Inny", "a", "b")  # duplikat NIP
        self.assertEqual(self.graph.writes, [])
        self.assertEqual(self.both("add_supplier", NEW_NIP, "Nowy", "ul. N", "00-000"), ADD_OK)
        self.assertEqual(sorted(self.sp.get_suppliers()), sorted(self.sq.get_suppliers()))

    def test_duplicate_nip_is_refused_before_any_post_and_changes_nothing(self):
        before = self.snapshot()
        self.assertEqual(self.sp.add_supplier(PLAIN, "Inna nazwa", "x", "y"), NIP_TAKEN)
        self.assertEqual(self.sp.add_supplier(DEFAULT, "Inna nazwa", "x", "y"), NIP_TAKEN)
        self.assertEqual(self.graph.writes, [])
        self.assertEqual(self.snapshot(), before)  # istniejący dostawca nie został zmodyfikowany

    def test_leading_zero_nip_duplicate_is_detected_without_post(self):
        self.assertEqual(self.sp.add_supplier("0123456780", "Z zerem", "a", "b"), ADD_OK)
        self.assertEqual(self.supplier("0123456780")["fields"]["Title"], "0123456780")
        self.assertEqual(self.sp.get_supplier_by_nip(123456780)[0], 123456780)
        self.assertEqual(self.sp.add_supplier("0123456780", "Inny", "a", "b"), NIP_TAKEN)
        self.assertEqual(self.methods(), ["POST"])

    def test_a_supplier_nip_is_independent_of_the_same_nip_in_clients(self):
        self.assertEqual(self.sp.validate_supplier_nip("2222222222"), (True, "NIP jest prawidłowy"))  # to klient, nie dostawca
        self.assertEqual(self.sp.add_supplier("2222222222", "Dostawca o NIP klienta", "a", "b"), ADD_OK)
        self.assertEqual(len(self.graph.data["Clients"]), 6)

    def test_post_400_after_the_check_is_resolved_by_a_verification_read(self):
        with mock.patch.object(self.sp, "validate_supplier_nip", return_value=(True, "NIP jest prawidłowy")):
            self.assertEqual(self.sp.add_supplier(PLAIN, "Wyścig", "a", "b"), NIP_TAKEN)
        self.assertEqual(self.methods(), ["POST"])  # jedna próba
        self.assertEqual(len(self.graph.data["Suppliers"]), 3)
        self.assertEqual(self.supplier(PLAIN)["fields"]["CompanyName"], "Dostawca B")  # istniejący nietknięty

    def test_unique_400_without_a_visible_duplicate_gives_a_generic_message(self):
        self.graph.faults.append({"kind": "status", **inf.cwt.UNIQUE_400})
        ok, message = self.sp.add_supplier(NEW_NIP, "Nowy", "a", "b")
        self.assertFalse(ok)
        self.assertIn("naruszenie unikalności", message)
        self.assertEqual(self.methods(), ["POST"])
        self.assertEqual(len(self.graph.data["Suppliers"]), 3)

    def test_other_400_errors_are_plain_errors(self):
        self.graph.faults.append({"kind": "status", "status": 400, "code": "invalidRequest", "message": "Field 'X' is not recognized"})
        ok, message = self.sp.add_supplier(NEW_NIP, "Nowy", "a", "b")
        self.assertFalse(ok)
        self.assertTrue(message.startswith("Błąd podczas dodawania dostawcy:"), message)

    def test_lost_post_response_with_an_existing_record_is_a_success_without_a_second_post(self):
        self.graph.faults.append({"kind": "lose"})  # rekord powstał, odpowiedź nie dotarła
        self.assertEqual(self.sp.add_supplier(NEW_NIP, "Nowy", "ul. N", "00-000"), ADD_OK)
        self.assertEqual(self.methods(), ["POST"])
        self.assertEqual(sum(1 for i in self.graph.data["Suppliers"] if i["fields"]["Title"] == NEW_NIP), 1)
        self.assertIs(self.supplier(NEW_NIP)["fields"]["IsDefault"], False)
        self.assertEqual(self.sp._etags[("Suppliers", NEW_NIP)][1], self.graph._etag(self.supplier(NEW_NIP)))
        self.assertNotIn(("Clients", NEW_NIP), self.sp._etags)

    def test_lost_post_response_without_a_record_is_an_error_and_not_retried(self):
        for fault in ({"kind": "raise"}, {"kind": "status", "status": 503}, {"kind": "status", "status": 504}):
            with self.subTest(fault=fault):
                self.graph.writes.clear()
                self.graph.faults.append(fault)
                ok, message = self.sp.add_supplier(NEW_NIP, "Nowy", "a", "b")
                self.assertFalse(ok)
                self.assertTrue(message.startswith("Błąd podczas dodawania dostawcy:"), message)
                self.assertEqual(self.methods(), ["POST"])  # POST nigdy nie jest ponawiany
                self.assertEqual(len(self.graph.data["Suppliers"]), 3)
                self.clock["now"] += 16

    def test_an_unconfirmed_record_with_other_data_is_not_taken_for_ours(self):
        with mock.patch.object(self.sp, "validate_supplier_nip", return_value=(True, "ok")):
            self.graph.faults.append({"kind": "raise"})
            result = self.sp.add_supplier(PLAIN, "Inna firma", "a", "b")  # NIP zajęty przez kogoś innego
        self.assertEqual(result, NIP_TAKEN)
        self.assertEqual(self.methods(), ["POST"])
        self.assertEqual(self.supplier(PLAIN)["fields"]["CompanyName"], "Dostawca B")

    def test_a_failing_verification_read_gives_the_original_error_without_a_second_post(self):
        real_get = self.graph.get

        def get_failing_after_post(path, params=None):
            if self.graph.writes:
                raise GraphError("brak połączenia (test)", status=None)
            return real_get(path, params)
        self.graph.get = get_failing_after_post
        self.graph.faults.append({"kind": "raise"})
        ok, message = self.sp.add_supplier(NEW_NIP, "Nowy", "a", "b")
        self.assertFalse(ok)
        self.assertIn("Brak połączenia", message)
        self.assertEqual(self.methods(), ["POST"])

    def test_429_is_the_only_automatic_retry_because_the_request_was_not_processed(self):
        self.graph.faults.append({"kind": "status", "status": 429, "headers": {"Retry-After": "2"}})
        self.assertEqual(self.sp.add_supplier(NEW_NIP, "Nowy", "a", "b"), ADD_OK)
        self.assertEqual(self.methods(), ["POST", "POST"])
        self.assertEqual(self.sleeps, [2.0])
        self.assertEqual(sum(1 for i in self.graph.data["Suppliers"] if i["fields"]["Title"] == NEW_NIP), 1)

    def test_unavailable_session_sends_nothing(self):
        self.session.active = False
        self.assertEqual(self.sp.add_supplier(NEW_NIP, "Nowy", "a", "b"), UNAVAILABLE)
        self.assertEqual((self.graph.requests, self.graph.writes), ([], []))

    def test_is_default_true_is_never_sent(self):
        self.sp.add_supplier(NEW_NIP, "Nowy", "a", "b")
        self.assert_no_is_default_true_sent()


# ---------------------------------------------------------------------------
# update_supplier
# ---------------------------------------------------------------------------
class UpdateSupplierTests(SupplierCase):
    def test_updates_the_three_allowed_fields_with_a_concrete_if_match(self):
        etag = self.graph._etag(self.supplier(PLAIN))
        self.assertEqual(self.sp.update_supplier(PLAIN, "Nowa nazwa", "ul. Nowa 2", "11-111 Nowo"), UPDATE_OK)
        self.assertEqual(self.payloads("PATCH"), [{"CompanyName": "Nowa nazwa", "AddressP1": "ul. Nowa 2", "AddressP2": "11-111 Nowo"}])
        self.assertEqual([(w["method"], w["if_match"]) for w in self.graph.writes], [("PATCH", etag)])
        self.assertNotIn(self.graph.writes[0]["if_match"], (None, "*", ""))
        self.assertEqual(self.sp.get_supplier_by_nip(PLAIN), (int(PLAIN), "Nowa nazwa", "ul. Nowa 2", "11-111 Nowo", 0))
        self.assertEqual(self.supplier(PLAIN)["fields"]["Title"], PLAIN)  # NIP bez zmian

    def test_is_default_is_never_in_the_payload_and_the_flag_is_untouched(self):
        flags = self.default_flags()
        for nip in (PLAIN, DEFAULT, THIRD):
            self.assertEqual(self.sp.update_supplier(nip, f"Zmiana {nip}", "ul. Z", "99-999"), UPDATE_OK)
        for body in self.payloads("PATCH"):
            self.assertNotIn("IsDefault", body)
            self.assertNotIn("Title", body)
            self.assertLessEqual(set(body), {"CompanyName", "AddressP1", "AddressP2"})
        self.assertEqual(self.default_flags(), flags)
        self.assertIs(self.supplier(DEFAULT)["fields"]["IsDefault"], True)  # domyślny pozostaje domyślnym
        self.assert_only_suppliers_written()

    def test_only_changed_fields_are_sent_and_nothing_when_nothing_changed(self):
        self.assertEqual(self.sp.update_supplier(PLAIN, "Tylko nazwa", "ul. S1", "66-666"), UPDATE_OK)
        self.assertEqual(self.payloads("PATCH"), [{"CompanyName": "Tylko nazwa"}])
        self.graph.writes.clear()
        self.assertEqual(self.sp.update_supplier(PLAIN, "Tylko nazwa", "ul. S1", "66-666"), UPDATE_OK)
        self.assertEqual(self.graph.writes, [])  # brak nowej wersji elementu

    def test_clearing_a_field_sends_null_for_that_field_only(self):
        self.assertEqual(self.sp.update_supplier(PLAIN, "Dostawca B", "ul. S1", ""), UPDATE_OK)
        self.assertEqual(self.payloads("PATCH"), [{"AddressP2": None}])
        self.assertEqual(self.sp.get_supplier_by_nip(PLAIN)[3], "")

    def test_results_and_state_match_sqlite(self):
        self.both("update_supplier", PLAIN, "Nowa", "ul. N", "11-111")
        self.both("update_supplier", DEFAULT, "Inna", "ul. I", "22-222")
        self.both("update_supplier", "9999999999", "x", "y", "z")
        self.both("update_supplier", "abc", "x", "y", "z")
        self.assertEqual(sorted(self.sp.get_suppliers()), sorted(self.sq.get_suppliers()))
        self.assertEqual(self.sp.get_default_supplier()[0], self.sq.get_default_supplier()[0])

    def test_missing_supplier_gives_not_found_without_any_write(self):
        before = self.snapshot()
        for nip in ("9999999999", "abc", "", None, "123"):
            self.assertEqual(self.sp.update_supplier(nip, "x", "y", "z"), NOT_FOUND, nip)
        self.assertEqual(self.graph.writes, [])
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(self.sq.update_supplier("9999999999", "x", "y", "z"), NOT_FOUND)  # SQLite ma tę samą konwencję

    def test_a_forbidden_field_can_never_reach_the_writer(self):
        item = self.sp._find_supplier(PLAIN)
        for desired in ({"IsDefault": True}, {"IsDefault": False}, {"Title": "1111111111"}, {"CompanyName": "x", "IsDefault": None}):
            with self.subTest(desired=desired), self.assertRaises(sp_module.DataAccessError):
                self.sp._patch_item("Suppliers", item, desired, "ok", conflict_message="c", not_found_message="n")
        self.assertEqual(self.graph.writes, [])

    # --- ETag, 412, 404 ---
    def test_the_etag_from_the_last_read_is_used_and_a_change_by_another_user_gives_a_conflict(self):
        self.sp.get_supplier_by_nip(PLAIN)  # użytkownik „widzi” dostawcę
        seen = self.graph._etag(self.supplier(PLAIN))
        other = self.supplier(PLAIN)
        other["fields"]["AddressP1"] = "zmiana przez innego użytkownika"
        other["version"] = other.get("version", 1) + 1
        result = self.sp.update_supplier(PLAIN, "Moja nazwa", "ul. S1", "66-666")
        self.assertFalse(result[0])
        self.assertIsInstance(result[1], ConflictMessage)
        self.assertIn("zmienione przez innego użytkownika", result[1])
        self.assertEqual([(w["method"], w["if_match"]) for w in self.graph.writes], [("PATCH", seen)])  # jedna próba, bez retry
        self.assertEqual(self.supplier(PLAIN)["fields"]["CompanyName"], "Dostawca B")
        self.assertEqual(self.supplier(PLAIN)["fields"]["AddressP1"], "zmiana przez innego użytkownika")
        self.assertNotIn(("Suppliers", PLAIN), self.sp._etags)  # pamięć ETagu unieważniona
        self.assertEqual(self.sleeps, [])
        self.assertEqual(self.sp.update_supplier(PLAIN, "Moja nazwa", "ul. S1", "66-666"), UPDATE_OK)  # po odczycie przechodzi

    def test_without_a_previous_read_the_etag_comes_from_the_lookup_just_before_the_write(self):
        etag = self.graph._etag(self.supplier(PLAIN))
        self.assertEqual(self.sp.update_supplier(PLAIN, "Nowa", "ul. S1", "66-666"), UPDATE_OK)
        self.assertEqual(self.graph.writes[0]["if_match"], etag)

    def test_http_404_from_the_write_gives_not_found_and_drops_the_etag(self):
        self.sp.get_suppliers()
        self.graph.faults.append({"kind": "status", "status": 404, "code": "itemNotFound"})
        self.assertEqual(self.sp.update_supplier(PLAIN, "Nowa", "a", "b"), NOT_FOUND)
        self.assertEqual(self.methods(), ["PATCH"])
        self.assertNotIn(("Suppliers", PLAIN), self.sp._etags)

    def test_a_supplier_deleted_between_lookup_and_write_gives_not_found(self):
        self.sp.get_suppliers()
        real_find = self.sp._find_supplier

        def find_then_delete(title, *args, **kwargs):
            found = real_find(title, *args, **kwargs)
            self.graph.data["Suppliers"].remove(self.supplier(title))
            return found
        with mock.patch.object(self.sp, "_find_supplier", side_effect=find_then_delete):
            self.assertEqual(self.sp.update_supplier(PLAIN, "Nowa", "a", "b"), NOT_FOUND)
        self.assertEqual(self.methods(), ["PATCH"])

    def test_etag_cache_is_updated_after_each_successful_write_and_stays_per_list(self):
        self.sp.get_clients()
        client_entry = self.sp._etags[("Clients", PLAIN)]
        self.assertEqual(self.sp.update_supplier(PLAIN, "Pierwsza", "ul. S1", "66-666"), UPDATE_OK)
        first = self.sp._etags[("Suppliers", PLAIN)][1]
        self.assertEqual(first, self.graph._etag(self.supplier(PLAIN)))
        self.assertEqual(self.sp.update_supplier(PLAIN, "Druga", "ul. S1", "66-666"), UPDATE_OK)
        self.assertEqual(self.graph.writes[1]["if_match"], first)  # kolejny zapis używa ETagu poprzedniego zapisu
        self.assertEqual(self.sp._etags[("Clients", PLAIN)], client_entry)  # klient o tym samym NIP nietknięty

    # --- niejednoznaczna odpowiedź PATCH ---
    def test_lost_patch_response_that_was_applied_is_confirmed_by_a_read_without_a_second_patch(self):
        self.sp.get_suppliers()
        self.graph.faults.append({"kind": "lose"})  # zmiana zapisana, odpowiedź utracona
        self.assertEqual(self.sp.update_supplier(PLAIN, "Nowa", "ul. S1", "66-666"), UPDATE_OK)
        self.assertEqual(self.methods(), ["PATCH"])
        self.assertEqual(self.supplier(PLAIN)["fields"]["CompanyName"], "Nowa")
        self.assertEqual(self.sp._etags[("Suppliers", PLAIN)][1], self.graph._etag(self.supplier(PLAIN)))  # ETag z odczytu
        etag_from_verification = self.graph._etag(self.supplier(PLAIN))
        self.assertEqual(self.sp.update_supplier(PLAIN, "Jeszcze nowsza", "ul. S1", "66-666"), UPDATE_OK)  # bez fałszywego 412
        self.assertEqual(self.graph.writes[1]["if_match"], etag_from_verification)

    def test_ambiguous_failure_that_was_not_applied_is_reported_as_not_saved_and_not_retried(self):
        for fault in ({"kind": "raise"}, {"kind": "status", "status": 503}):
            with self.subTest(fault=fault):
                self.graph.writes.clear()
                self.graph.faults.append(fault)
                before = self.snapshot()
                ok, message = self.sp.update_supplier(PLAIN, "Nowa", "ul. S1", "66-666")
                self.assertFalse(ok)
                self.assertNotIsInstance(message, ConflictMessage)
                self.assertTrue(message.startswith("Błąd podczas aktualizacji dostawcy:"), message)
                self.assertIn("nie została zapisana", message)  # odczyt weryfikujący to potwierdził
                self.assertEqual(self.methods(), ["PATCH"])
                self.assertEqual(self.snapshot(), before)
                self.assertNotIn(("Suppliers", PLAIN), self.sp._etags)
                self.clock["now"] += 16
        self.assertEqual(self.sp.update_supplier(PLAIN, "Nowa", "ul. S1", "66-666"), UPDATE_OK)

    def test_ambiguous_failure_when_someone_else_changed_the_item_is_a_conflict(self):
        item = self.supplier(PLAIN)

        def other_user_then_connection_loss(method, url, **kwargs):
            if method == "PATCH":
                item["fields"]["CompanyName"] = "Zmieniona przez kogoś innego"
                item["version"] = item.get("version", 1) + 1
                raise requests.ConnectionError("utrata połączenia (test)")
            return self.graph.http(method, url, **kwargs)
        self.use_http(other_user_then_connection_loss)
        result = self.sp.update_supplier(PLAIN, "Nowa", "ul. S1", "66-666")
        self.assertFalse(result[0])
        self.assertIsInstance(result[1], ConflictMessage)
        self.assertEqual(item["fields"]["CompanyName"], "Zmieniona przez kogoś innego")  # cudze dane nietknięte

    def test_ambiguous_failure_when_the_item_disappeared_gives_not_found(self):
        item = self.supplier(PLAIN)

        def delete_then_connection_loss(method, url, **kwargs):
            if method == "PATCH":
                self.graph.data["Suppliers"].remove(item)
                raise requests.ConnectionError("utrata połączenia (test)")
            return self.graph.http(method, url, **kwargs)
        self.use_http(delete_then_connection_loss)
        self.assertEqual(self.sp.update_supplier(PLAIN, "Nowa", "a", "b"), NOT_FOUND)

    def test_a_failing_verification_read_gives_the_original_error_without_a_second_patch(self):
        real_get = self.graph.get

        def get_failing_after_patch(path, params=None):
            if self.graph.writes:
                raise GraphError("brak połączenia (test)", status=None)
            return real_get(path, params)
        self.graph.get = get_failing_after_patch
        self.graph.faults.append({"kind": "raise"})
        ok, message = self.sp.update_supplier(PLAIN, "Nowa", "a", "b")
        self.assertFalse(ok)
        self.assertIn("Brak połączenia", message)
        self.assertEqual(self.methods(), ["PATCH"])
        self.assertNotIn(("Suppliers", PLAIN), self.sp._etags)

    def test_429_keeps_the_retry_policy_and_other_statuses_are_not_retried(self):
        self.graph.faults.append({"kind": "status", "status": 429, "headers": {"Retry-After": "2"}})
        self.assertEqual(self.sp.update_supplier(PLAIN, "Nowa", "a", "b"), UPDATE_OK)
        self.assertEqual(self.methods(), ["PATCH", "PATCH"])
        self.assertTrue(all(w["if_match"] == self.graph.writes[0]["if_match"] for w in self.graph.writes))
        self.assertEqual(self.sleeps, [2.0])

    def test_unavailable_session_sends_nothing(self):
        self.session.active = False
        self.assertEqual(self.sp.update_supplier(PLAIN, "x", "y", "z"), UNAVAILABLE)
        self.assertEqual((self.graph.requests, self.graph.writes), ([], []))


# ---------------------------------------------------------------------------
# delete_supplier
# ---------------------------------------------------------------------------
class DeleteSupplierTests(SupplierCase):
    def test_deletes_a_non_default_supplier_after_verifying_id_title_and_etag(self):
        target = self.supplier(PLAIN)
        others = [(i["id"], dict(i["fields"]), i.get("version", 1)) for i in self.graph.data["Suppliers"] if i is not target]
        clients_before = self.snapshot()["Clients"]
        etag = self.graph._etag(target)
        self.assertEqual(self.sp.delete_supplier(PLAIN), DELETE_OK)
        by_id = [r for r in self.graph.requests if r[0] == "GET" and r[1].endswith(f"/items/{target['id']}")]
        self.assertEqual(len(by_id), 1)  # ponowna weryfikacja po dokładnym ID
        self.assertEqual(by_id[0][2], {"$expand": "fields($select=Title,IsDefault)"})
        self.assertEqual([(w["method"], w["path"].rsplit("/", 1)[-1], w["if_match"]) for w in self.graph.writes],
                         [("DELETE", str(target["id"]), etag)])
        self.assertEqual([(i["id"], dict(i["fields"]), i.get("version", 1)) for i in self.graph.data["Suppliers"]], others)
        self.assertEqual(self.snapshot()["Clients"], clients_before)  # klient o tym samym NIP nietknięty
        self.assertIsNone(self.sp.get_supplier_by_nip(PLAIN))
        self.assert_only_suppliers_written()

    def test_a_default_supplier_cannot_be_deleted(self):
        before = self.snapshot()
        self.assertEqual(self.sp.delete_supplier(DEFAULT), DEFAULT_REFUSED)
        self.assertEqual(self.graph.writes, [])
        self.assertEqual(self.snapshot(), before)

    def test_every_default_is_protected_when_there_are_several(self):
        self.supplier(THIRD)["fields"]["IsDefault"] = True
        for nip in (DEFAULT, THIRD):
            self.assertEqual(self.sp.delete_supplier(nip), DEFAULT_REFUSED)
        self.assertEqual(self.graph.writes, [])

    def test_becoming_default_between_lookup_and_verification_is_refused_before_any_delete(self):
        real_find = self.sp._find_supplier

        def find_then_become_default(title, *args, **kwargs):
            found = real_find(title, *args, **kwargs)  # w odczycie: niedomyślny
            self.supplier(title)["fields"]["IsDefault"] = True  # ktoś ustawia go jako domyślnego
            return found
        with mock.patch.object(self.sp, "_find_supplier", side_effect=find_then_become_default):
            self.assertEqual(self.sp.delete_supplier(PLAIN), DEFAULT_REFUSED)
        self.assertEqual(self.graph.writes, [])
        self.assertIn(self.supplier(PLAIN), self.graph.data["Suppliers"])

    def test_the_etag_comes_from_the_verification_read_not_from_the_first_lookup(self):
        real_find = self.sp._find_supplier

        def find_then_bump(title, *args, **kwargs):
            found = real_find(title, *args, **kwargs)
            self.supplier(title)["version"] = 9  # zmiana nieistotna dla usunięcia, przed odczytem weryfikującym
            return found
        with mock.patch.object(self.sp, "_find_supplier", side_effect=find_then_bump):
            self.assertEqual(self.sp.delete_supplier(PLAIN), DELETE_OK)
        self.assertEqual(self.graph.writes[0]["if_match"], '"00000000-0000-0000-0000-000000000002,9"')

    def test_missing_supplier_gives_not_found_and_matches_sqlite(self):
        before = self.snapshot()
        for nip in ("9999999999", "abc", "", None, "123", 12345678901):
            self.assertEqual(self.sp.delete_supplier(nip), NOT_FOUND, nip)
        self.assertEqual(self.graph.writes, [])
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(self.sq.delete_supplier("9999999999"), NOT_FOUND)

    def test_results_match_sqlite_for_every_supplier(self):
        for nip in (DEFAULT, PLAIN, THIRD, PLAIN):
            self.both("delete_supplier", nip)
        self.assertEqual(sorted(self.sp.get_suppliers()), sorted(self.sq.get_suppliers()))

    def test_a_wrong_title_for_the_id_is_refused_before_any_delete(self):
        wrong = sp_module._Item(self.supplier(DEFAULT)["id"], {"Title": PLAIN, "IsDefault": False}, None)
        with mock.patch.object(self.sp, "_find_supplier", return_value=wrong):
            ok, message = self.sp.delete_supplier(PLAIN)
        self.assertFalse(ok)
        self.assertIn("Odmowa usunięcia", message)
        self.assertEqual(self.graph.writes, [])
        self.assertEqual(len(self.graph.data["Suppliers"]), 3)

    def test_missing_etag_in_the_verification_read_refuses_to_delete(self):
        real_get = self.graph.get

        def get_without_etag(path, params=None):
            data = real_get(path, params)
            if isinstance(data, dict) and "fields" in data and "value" not in data:
                data = {k: v for k, v in data.items() if k not in ("@odata.etag", "eTag")}
            return data
        self.graph.get = get_without_etag
        ok, message = self.sp.delete_supplier(PLAIN)
        self.assertFalse(ok)
        self.assertIn("brak ETagu", message)
        self.assertEqual(self.graph.writes, [])

    def test_delete_always_carries_a_concrete_if_match(self):
        self.sp.delete_supplier(PLAIN)
        self.sp.delete_supplier(THIRD)
        self.assertEqual(self.methods(), ["DELETE", "DELETE"])
        for write in self.graph.writes:
            self.assertTrue(write["if_match"])
            self.assertNotEqual(write["if_match"].strip(), "*")

    # --- 412 / 404 / 429 / błędy sieciowe ---
    def test_412_between_verification_and_delete_is_a_conflict_without_retry(self):
        target = self.supplier(PLAIN)

        def modify_then_delete(method, url, **kwargs):
            if method == "DELETE":
                target["version"] = target.get("version", 1) + 1
            return self.graph.http(method, url, **kwargs)
        self.sp.get_suppliers()
        self.use_http(modify_then_delete)
        result = self.sp.delete_supplier(PLAIN)
        self.assertFalse(result[0])
        self.assertIsInstance(result[1], ConflictMessage)
        self.assertIn("nie został usunięty", result[1])
        self.assertEqual(self.methods(), ["DELETE"])  # jedno żądanie, bez ponowienia i bez wariantu bez If-Match
        self.assertEqual(self.sleeps, [])
        self.assertIn(target, self.graph.data["Suppliers"])
        self.assertNotIn(("Suppliers", PLAIN), self.sp._etags)

    def test_404_on_delete_gives_not_found(self):
        target = self.supplier(PLAIN)

        def remove_then_delete(method, url, **kwargs):
            if method == "DELETE":
                self.graph.data["Suppliers"].remove(target)
            return self.graph.http(method, url, **kwargs)
        self.use_http(remove_then_delete)
        self.assertEqual(self.sp.delete_supplier(PLAIN), NOT_FOUND)
        self.assertEqual(self.methods(), ["DELETE"])

    def test_item_that_vanished_before_the_verification_read_gives_not_found_without_delete(self):
        real_find = self.sp._find_supplier

        def find_then_remove(title, *args, **kwargs):
            found = real_find(title, *args, **kwargs)
            self.graph.data["Suppliers"].remove(self.supplier(title))
            return found
        with mock.patch.object(self.sp, "_find_supplier", side_effect=find_then_remove):
            self.assertEqual(self.sp.delete_supplier(PLAIN), NOT_FOUND)
        self.assertEqual(self.graph.writes, [])

    def test_429_follows_the_retry_policy_with_the_same_etag(self):
        self.graph.faults.append({"kind": "status", "status": 429, "headers": {"Retry-After": "2"}})
        self.assertEqual(self.sp.delete_supplier(PLAIN), DELETE_OK)
        self.assertEqual(self.methods(), ["DELETE", "DELETE"])
        self.assertEqual(self.sleeps, [2.0])
        self.assertEqual(len({w["if_match"] for w in self.graph.writes}), 1)

    def test_exhausted_429_reports_an_error_and_keeps_the_item(self):
        self.graph.faults += [{"kind": "status", "status": 429}] * 3
        ok, message = self.sp.delete_supplier(PLAIN)
        self.assertFalse(ok)
        self.assertIn("HTTP 429", message)
        self.assertEqual(self.methods(), ["DELETE"] * 3)
        self.assertIn(self.supplier(PLAIN), self.graph.data["Suppliers"])

    def test_5xx_and_network_errors_never_trigger_a_second_delete(self):
        for fault in ({"kind": "status", "status": 503}, {"kind": "status", "status": 504}, {"kind": "raise"}):
            with self.subTest(fault=fault):
                self.graph.writes.clear()
                self.graph.faults.append(fault)
                ok, message = self.sp.delete_supplier(PLAIN)
                self.assertFalse(ok)
                self.assertTrue(message.startswith("Błąd podczas usuwania dostawcy:"), message)
                self.assertEqual(self.methods(), ["DELETE"])
                self.assertEqual(self.sleeps, [])
                self.assertIn(self.supplier(PLAIN), self.graph.data["Suppliers"])
                self.assertNotIn(("Suppliers", PLAIN), self.sp._etags)
                self.clock["now"] += 16

    def test_lost_delete_response_then_a_retry_reports_not_found_instead_of_deleting_blindly(self):
        self.graph.faults.append({"kind": "lose"})  # usunięte, odpowiedź utracona
        self.assertFalse(self.sp.delete_supplier(PLAIN)[0])
        self.assertNotIn(PLAIN, [i["fields"]["Title"] for i in self.graph.data["Suppliers"]])
        self.clock["now"] += 16
        self.assertEqual(self.sp.delete_supplier(PLAIN), NOT_FOUND)
        self.assertEqual(self.methods(), ["DELETE"])  # drugiego DELETE nie było

    # --- niezależność ETagów ---
    def test_etag_caches_of_clients_and_suppliers_are_independent_on_delete(self):
        self.sp.get_clients()
        self.sp.get_suppliers()
        client_entry = self.sp._etags[("Clients", PLAIN)]
        self.assertEqual(self.sp.delete_supplier(PLAIN), DELETE_OK)
        self.assertNotIn(("Suppliers", PLAIN), self.sp._etags)
        self.assertEqual(self.sp._etags[("Clients", PLAIN)], client_entry)
        self.assertIn(("Suppliers", DEFAULT), self.sp._etags)

    def test_deleting_the_same_nip_as_a_client_and_as_a_supplier_uses_each_own_etag(self):
        self.supplier(PLAIN)["version"] = 4
        client = self.client(PLAIN)
        client["version"] = 8
        self.sp.get_clients()
        self.sp.get_suppliers()
        supplier_etag, client_etag = self.graph._etag(self.supplier(PLAIN)), self.graph._etag(client)
        self.assertNotEqual(supplier_etag, client_etag)
        self.assertEqual(self.sp.delete_supplier(PLAIN), DELETE_OK)
        self.assertEqual(self.graph.writes[0]["if_match"], supplier_etag)
        self.assertEqual(self.sp.delete_client(PLAIN), inf.cwt.DELETE_OK)
        self.assertEqual(self.graph.writes[1]["if_match"], client_etag)

    def test_unavailable_session_sends_nothing(self):
        self.session.active = False
        self.assertEqual(self.sp.delete_supplier(PLAIN), UNAVAILABLE)
        self.assertEqual((self.graph.requests, self.graph.writes), ([], []))


# ---------------------------------------------------------------------------
# zakres etapu
# ---------------------------------------------------------------------------
class ScopeTests(SupplierCase):
    def test_operations_outside_the_supplier_scope_are_still_rejected_and_send_nothing(self):
        for name, args in (("save_offer", (1, "2026/a.docx", {})), ("get_next_wz_number", (2026,)), ("delete_wz", (1,))):
            with self.assertRaises(ReadOnlyBackendError):
                getattr(self.sp, name)(*args)
        self.assertEqual((self.graph.requests, self.graph.writes), ([], []))

    def test_no_supplier_operation_ever_writes_outside_the_suppliers_list_or_touches_sqlite(self):
        sqlite_before = (self.rows("SELECT * FROM Suppliers ORDER BY Nip"), self.rows("SELECT * FROM Clients ORDER BY Nip"))
        self.sp.add_supplier(NEW_NIP, "Nowy", "a", "b")
        self.sp.update_supplier(NEW_NIP, "Zmieniony", "a", "b")
        self.sp.delete_supplier(NEW_NIP)
        self.assertEqual(self.methods(), ["POST", "PATCH", "DELETE"])
        self.assert_only_suppliers_written()
        self.assert_no_is_default_true_sent()
        self.assertEqual((self.rows("SELECT * FROM Suppliers ORDER BY Nip"), self.rows("SELECT * FROM Clients ORDER BY Nip")),
                         sqlite_before)

    def test_the_full_lifecycle_leaves_the_default_supplier_untouched(self):
        default_item = self.supplier(DEFAULT)
        snapshot = (default_item["id"], dict(default_item["fields"]), default_item.get("version", 1))
        self.sp.add_supplier(NEW_NIP, "Nowy", "a", "b")
        self.sp.update_supplier(NEW_NIP, "Zmieniony", "a", "b")
        self.sp.update_supplier(DEFAULT, "Zmieniony domyślny", "a", "b")
        self.sp.delete_supplier(NEW_NIP)
        self.sp.delete_supplier(DEFAULT)  # odmowa
        self.assertEqual(self.sp.get_default_supplier()[0], int(DEFAULT))
        self.assertEqual(sum(1 for f in self.default_flags().values() if f), 1)
        changed = self.supplier(DEFAULT)
        self.assertEqual(changed["fields"]["IsDefault"], snapshot[1]["IsDefault"])


if __name__ == "__main__":
    unittest.main()
