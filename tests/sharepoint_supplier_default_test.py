"""Testy set_default_supplier (etap 4B-3) - offline, na atrapie Graph; żadnych żądań sieciowych ani zapisów do SharePoint.

Uruchomienie: python -m unittest tests.sharepoint_supplier_default_test -v
Graph nie ma transakcji obejmującej wiele elementów, więc testy sprawdzają: kolejność zapisów (najpierw nowy domyślny,
potem odznaczenie starych), niezmiennik „nigdy zero domyślnych”, idempotencję i samonaprawę, odczyt weryfikujący oraz to,
że sukces nigdy nie jest zgłaszany przy niespójnym stanie (zamiast niego PartialFailureMessage lub ConflictMessage).
"""
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import tests.sharepoint_backend_test as spt  # noqa: E402  (moduł - bez duplikowania testów)
import tests.sharepoint_supplier_write_test as sw  # noqa: E402
from src.data.errors import ConflictMessage, PartialFailureMessage  # noqa: E402
from src.integrations.sharepoint.graph_client import GraphError  # noqa: E402
from src.integrations.sharepoint.session import NotSignedInError  # noqa: E402

OK = (True, "Dostawca został ustawiony jako domyślny")
NOT_FOUND = sw.NOT_FOUND
PLAIN, DEFAULT, THIRD = sw.PLAIN, sw.DEFAULT, sw.THIRD  # "Dostawca B", "Dostawca A" (domyślny), "dostawca c"


class DefaultCase(sw.SupplierCase):
    def setUp(self):
        super().setUp()
        self.history, self.reads_at_write = [], []
        self.id_title = {i["id"]: i["fields"]["Title"] for i in self.graph.data["Suppliers"]}
        self.graph.after_write = self.record

    def record(self, method, path, body):
        self.history.append(len(self.defaults()))  # liczba domyślnych tuż po każdym zapisie
        self.reads_at_write.append(len(self.graph.requests))

    def defaults(self):
        return sorted(i["fields"]["Title"] for i in self.graph.data["Suppliers"] if i["fields"].get("IsDefault"))

    def set_defaults(self, *titles):
        for item in self.graph.data["Suppliers"]:
            item["fields"]["IsDefault"] = item["fields"]["Title"] in titles

    def flag_writes(self):
        """Zapisy PATCH jako (Title dostawcy, treść)."""
        return [(self.id_title[int(w["path"].rsplit("/", 2)[-2])], w["json"]) for w in self.graph.writes if w["method"] == "PATCH"]

    def item_id(self, title):
        return self.supplier(title)["id"]

    def before_write(self, predicate, action):
        """Wykonuje `action` tuż przed zapisem spełniającym `predicate(method, url)` (np. zmiana elementu przez innego użytkownika)."""
        def http(method, url, **kwargs):
            if predicate(method, url):
                action()
            return self.graph.http(method, url, **kwargs)
        self.use_http(http)

    def patch_of(self, title):
        suffix = f"/items/{self.item_id(title)}/fields"
        return lambda method, url: method == "PATCH" and url.endswith(suffix)

    def fail_gets(self, when):
        real_get = self.graph.get

        def get(path, params=None):
            if when(path, params):
                raise GraphError("brak połączenia (test)", status=None)
            return real_get(path, params)
        self.graph.get = get


# ---------------------------------------------------------------------------
# zachowanie podstawowe
# ---------------------------------------------------------------------------
class SetDefaultBehaviorTests(DefaultCase):
    def test_switches_the_default_by_setting_the_target_first_and_then_clearing_the_old_one(self):
        etags = {t: self.graph._etag(self.supplier(t)) for t in (PLAIN, DEFAULT)}
        self.assertEqual(self.sp.set_default_supplier(PLAIN), OK)
        self.assertEqual(self.defaults(), [PLAIN])
        self.assertEqual(self.flag_writes(), [(PLAIN, {"IsDefault": True}), (DEFAULT, {"IsDefault": False})])
        self.assertEqual([w["if_match"] for w in self.graph.writes], [etags[PLAIN], etags[DEFAULT]])  # ETagi ze świeżego odczytu
        self.assertGreater(len(self.graph.requests), self.reads_at_write[-1])  # odczyt weryfikujący po ostatnim zapisie
        self.assert_only_suppliers_written()

    def test_there_is_never_a_state_without_a_default_during_the_switch(self):
        self.sp.set_default_supplier(PLAIN)
        self.assertEqual(self.history, [2, 1])  # po pierwszym zapisie dwóch domyślnych (bezpieczne), po drugim jeden; nigdy 0

    def test_results_and_final_default_match_sqlite(self):
        for nip in (PLAIN, THIRD, DEFAULT, "9999999999", "abc", "", PLAIN):
            self.both("set_default_supplier", nip)
            self.assertEqual(self.sp.get_default_supplier(), self.sq.get_default_supplier(), nip)
        self.assertEqual(sorted(self.sp.get_suppliers()), sorted(self.sq.get_suppliers()))

    def test_missing_nip_gives_not_found_and_changes_nothing(self):
        before = self.snapshot()
        for nip in ("9999999999", "abc", "", None, "123", 12345678901):
            self.assertEqual(self.sp.set_default_supplier(nip), NOT_FOUND, nip)
        self.assertEqual(self.graph.writes, [])
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(self.defaults(), [DEFAULT])  # dotychczasowy domyślny zostaje

    def test_already_the_only_default_is_idempotent_without_any_write(self):
        self.assertEqual(self.sp.set_default_supplier(DEFAULT), OK)
        self.assertEqual(self.graph.writes, [])
        self.assertEqual(len(self.graph.requests), 1)  # jeden świeży odczyt listy i nic więcej
        self.assertEqual(self.sp.set_default_supplier(DEFAULT), OK)

    def test_a_repeated_call_after_success_writes_nothing(self):
        self.sp.set_default_supplier(PLAIN)
        self.graph.writes.clear()
        self.assertEqual(self.sp.set_default_supplier(PLAIN), OK)
        self.assertEqual(self.graph.writes, [])

    def test_with_no_default_at_all_the_target_becomes_the_default(self):
        self.set_defaults()
        self.assertEqual(self.sp.set_default_supplier(THIRD), OK)
        self.assertEqual(self.defaults(), [THIRD])
        self.assertEqual(self.flag_writes(), [(THIRD, {"IsDefault": True})])
        self.assertEqual(self.history, [1])

    def test_several_defaults_including_the_target_are_repaired_without_patching_the_target(self):
        self.set_defaults(PLAIN, DEFAULT, THIRD)
        self.assertEqual(self.sp.set_default_supplier(DEFAULT), OK)
        self.assertEqual(self.defaults(), [DEFAULT])
        self.assertEqual(self.flag_writes(), [(PLAIN, {"IsDefault": False}), (THIRD, {"IsDefault": False})])  # wg ID
        self.assertEqual(min(self.history), 1)

    def test_several_defaults_without_the_target_sets_it_first_and_then_clears_every_other(self):
        self.set_defaults(DEFAULT, THIRD)
        self.assertEqual(self.sp.set_default_supplier(PLAIN), OK)
        self.assertEqual(self.defaults(), [PLAIN])
        self.assertEqual(self.flag_writes(), [(PLAIN, {"IsDefault": True}), (DEFAULT, {"IsDefault": False}), (THIRD, {"IsDefault": False})])
        self.assertEqual(self.history, [3, 2, 1])

    def test_the_decision_is_based_on_a_fresh_read_not_on_the_etag_cache(self):
        self.sp.get_suppliers()  # pamięć ETagów zawiera stan sprzed zmian innego użytkownika
        self.set_defaults(THIRD)  # inny użytkownik przełączył domyślnego na THIRD
        self.supplier(THIRD)["version"] = 6
        self.supplier(DEFAULT)["version"] = 4
        self.assertEqual(self.sp.set_default_supplier(PLAIN), OK)
        self.assertEqual(self.flag_writes(), [(PLAIN, {"IsDefault": True}), (THIRD, {"IsDefault": False})])  # DEFAULT nietknięty
        self.assertEqual(self.graph.writes[1]["if_match"], '"00000000-0000-0000-0000-000000000004,6"')  # świeży ETag, nie z pamięci

    def test_stale_cached_etags_are_never_used_for_the_flag_writes(self):
        for title in (PLAIN, DEFAULT):
            self.sp._remember_etag("Suppliers", title, self.item_id(title), '"stale,1"')
        self.assertEqual(self.sp.set_default_supplier(PLAIN), OK)
        self.assertNotIn('"stale,1"', [w["if_match"] for w in self.graph.writes])

    def test_the_etag_cache_is_refreshed_for_the_written_items_only(self):
        self.sp.get_clients()
        self.sp.get_suppliers()
        third_entry = self.sp._etags[("Suppliers", THIRD)]
        client_entry = self.sp._etags[("Clients", PLAIN)]
        self.assertEqual(self.sp.set_default_supplier(PLAIN), OK)
        for title in (PLAIN, DEFAULT):
            self.assertEqual(self.sp._etags[("Suppliers", title)][1], self.graph._etag(self.supplier(title)))
        self.assertEqual(self.sp._etags[("Suppliers", THIRD)], third_entry)
        self.assertEqual(self.sp._etags[("Clients", PLAIN)], client_entry)
        self.assertEqual(self.sp.update_supplier(PLAIN, "Zmiana po przełączeniu", "ul. S1", "66-666"), sw.UPDATE_OK)  # bez fałszywego 412

    def test_payloads_contain_only_a_boolean_flag_and_every_write_has_a_concrete_if_match(self):
        self.set_defaults(DEFAULT, THIRD)
        self.sp.set_default_supplier(PLAIN)
        for write in self.graph.writes:
            self.assertEqual(write["method"], "PATCH")
            self.assertEqual(list(write["json"]), ["IsDefault"])
            self.assertIn(write["json"]["IsDefault"], (True, False))
            self.assertIsInstance(write["json"]["IsDefault"], bool)  # nigdy null
            self.assertTrue(write["if_match"])
            self.assertNotEqual(write["if_match"].strip(), "*")

    def test_other_lists_and_the_client_with_the_same_nip_are_untouched(self):
        clients_before = self.snapshot()["Clients"]
        self.sp.set_default_supplier(PLAIN)  # PLAIN to także NIP klienta
        self.assertEqual(self.snapshot()["Clients"], clients_before)
        self.assert_only_suppliers_written()

    def test_after_the_switch_the_old_default_can_be_deleted_and_the_new_one_cannot(self):
        self.sp.set_default_supplier(PLAIN)
        self.assertEqual(self.sp.delete_supplier(PLAIN), sw.DEFAULT_REFUSED)
        self.assertEqual(self.sp.delete_supplier(DEFAULT), sw.DELETE_OK)
        self.assertEqual(self.sp.get_default_supplier()[0], int(PLAIN))

    def test_unavailable_session_sends_nothing(self):
        self.session.active = False
        self.assertEqual(self.sp.set_default_supplier(PLAIN), sw.UNAVAILABLE)
        self.assertEqual((self.graph.requests, self.graph.writes), ([], []))

    def test_other_operations_do_not_change_the_default_flags(self):
        self.sp.add_supplier(sw.NEW_NIP, "Nowy", "a", "b")
        self.sp.update_supplier(DEFAULT, "Zmieniony", "a", "b")
        self.sp.update_supplier(PLAIN, "Zmieniony", "a", "b")
        self.assertEqual(self.defaults(), [DEFAULT])


class DefaultReadWarningTests(DefaultCase):
    def test_several_defaults_return_the_first_by_id_log_only_ids_and_write_nothing(self):
        self.set_defaults(DEFAULT, THIRD)
        expected_first = (int(DEFAULT), "Dostawca A", "ul. S2", "77-777", 1)
        self.assertEqual(self.sp.get_default_supplier(), expected_first)
        self.assertEqual(len(self.sp_logs), 1)
        text = self.sp_logs[0][0]
        self.assertIn(f"{self.item_id(DEFAULT)}, {self.item_id(THIRD)}", text)
        for private in (PLAIN, DEFAULT, THIRD, "Dostawca", "dostawca"):
            self.assertNotIn(private, text)  # bez NIP i nazw
        self.assertEqual(self.graph.writes, [])

    def test_one_or_no_default_logs_nothing(self):
        self.assertEqual(self.sp.get_default_supplier()[0], int(DEFAULT))
        self.set_defaults()
        self.assertIsNone(self.sp.get_default_supplier())
        self.assertEqual(self.sp_logs, [])


# ---------------------------------------------------------------------------
# awarie i konflikty w kolejnych krokach
# ---------------------------------------------------------------------------
class StepBFailureTests(DefaultCase):
    """Błędy przy ustawianiu wskazanego dostawcy (pierwszy zapis): stan SharePoint nie powinien się zmienić."""

    def assert_unchanged(self):
        self.assertEqual(self.defaults(), [DEFAULT])

    def test_412_is_a_conflict_without_retry_and_without_clearing_the_old_default(self):
        self.before_write(self.patch_of(PLAIN), lambda: self.supplier(PLAIN).update(version=7))  # ktoś zmienił element po odczycie
        self.sp.get_suppliers()
        result = self.sp.set_default_supplier(PLAIN)
        self.assertFalse(result[0])
        self.assertIsInstance(result[1], ConflictMessage)
        self.assertNotIsInstance(result[1], PartialFailureMessage)
        self.assertEqual(self.flag_writes(), [(PLAIN, {"IsDefault": True})])  # jedna próba
        self.assertEqual(self.sleeps, [])
        self.assert_unchanged()
        self.assertNotIn(("Suppliers", PLAIN), self.sp._etags)

    def test_404_means_not_found_and_changes_nothing(self):
        self.before_write(self.patch_of(PLAIN), lambda: self.graph.data["Suppliers"].remove(self.supplier(PLAIN)))
        self.assertEqual(self.sp.set_default_supplier(PLAIN), NOT_FOUND)
        self.assertEqual(len(self.graph.writes), 1)
        self.assert_unchanged()

    def test_429_follows_the_retry_policy_and_then_succeeds(self):
        self.graph.faults.append({"kind": "status", "status": 429, "headers": {"Retry-After": "2"}})
        self.assertEqual(self.sp.set_default_supplier(PLAIN), OK)
        self.assertEqual(self.flag_writes(), [(PLAIN, {"IsDefault": True}), (PLAIN, {"IsDefault": True}), (DEFAULT, {"IsDefault": False})])
        self.assertEqual(self.sleeps, [2.0])
        self.assertEqual(self.graph.writes[0]["if_match"], self.graph.writes[1]["if_match"])

    def test_exhausted_429_is_a_plain_error_and_changes_nothing(self):
        self.graph.faults += [{"kind": "status", "status": 429}] * 3
        ok, message = self.sp.set_default_supplier(PLAIN)
        self.assertFalse(ok)
        self.assertIn("HTTP 429", message)
        self.assertTrue(message.startswith("Błąd podczas ustawiania domyślnego dostawcy:"), message)
        self.assertNotIsInstance(message, (ConflictMessage, PartialFailureMessage))
        self.assertEqual(len(self.graph.writes), 3)
        self.assert_unchanged()

    def test_ambiguous_failure_that_was_not_applied_is_reported_as_not_saved_and_not_retried(self):
        for fault in ({"kind": "status", "status": 503}, {"kind": "raise"}):
            with self.subTest(fault=fault):
                self.graph.writes.clear()
                self.graph.faults.append(fault)
                ok, message = self.sp.set_default_supplier(PLAIN)
                self.assertFalse(ok)
                self.assertNotIsInstance(message, (ConflictMessage, PartialFailureMessage))
                self.assertIn("nie została zapisana", message)
                self.assertEqual(self.flag_writes(), [(PLAIN, {"IsDefault": True})])  # bez ponowienia i bez odznaczania starego
                self.assert_unchanged()
                self.clock["now"] += 16

    def test_lost_response_that_was_applied_continues_with_clearing_and_never_repeats_the_first_write(self):
        self.graph.faults.append({"kind": "lose"})
        self.assertEqual(self.sp.set_default_supplier(PLAIN), OK)
        self.assertEqual(self.flag_writes(), [(PLAIN, {"IsDefault": True}), (DEFAULT, {"IsDefault": False})])
        self.assertEqual(self.defaults(), [PLAIN])

    def test_ambiguous_failure_with_a_failing_verification_read_is_a_partial_failure_and_stops(self):
        self.graph.faults.append({"kind": "raise"})
        self.fail_gets(lambda path, params: bool(self.graph.writes) and path.endswith(f"/items/{self.item_id(PLAIN)}"))
        result = self.sp.set_default_supplier(PLAIN)
        self.assertFalse(result[0])
        self.assertIsInstance(result[1], PartialFailureMessage)
        self.assertIn("Stan w SharePoint jest nieznany", result[1])
        self.assertEqual(len(self.graph.writes), 1)  # nic więcej nie zostało wysłane w ciemno

    def test_ambiguous_failure_when_the_target_disappeared_gives_not_found(self):
        def remove_and_lose(method, url, **kwargs):
            self.graph.data["Suppliers"].remove(self.supplier(PLAIN))
            raise spt.requests.ConnectionError("utrata połączenia (test)")
        self.use_http(remove_and_lose)
        self.assertEqual(self.sp.set_default_supplier(PLAIN), NOT_FOUND)

    def test_session_expiry_before_the_first_write_is_a_plain_error(self):
        with mock.patch.object(self.sp, "_writer", side_effect=NotSignedInError("Sesja SharePoint wygasła - zaloguj się ponownie.")):
            ok, message = self.sp.set_default_supplier(PLAIN)
        self.assertFalse(ok)
        self.assertIn("zaloguj się ponownie", message)
        self.assertEqual(self.graph.writes, [])
        self.assert_unchanged()


class StepCFailureTests(DefaultCase):
    """Błędy przy odznaczaniu dotychczasowego domyślnego: wskazany jest już domyślny, więc stan to częściowe niepowodzenie."""

    BOTH = sorted([PLAIN, DEFAULT])  # dwóch domyślnych: nowy i stary

    def assert_partial(self, result, cause=None):
        ok, message = result
        self.assertFalse(ok)
        self.assertIsInstance(message, PartialFailureMessage)
        self.assertTrue(message.partial)
        self.assertNotIsInstance(message, ConflictMessage)
        for needle in ("Dostawca B", "Dostawca A", "więcej niż jeden domyślny", "operacja naprawi stan"):
            self.assertIn(needle, message)
        if cause:
            self.assertIn(cause, message)
        self.assertEqual(self.defaults(), self.BOTH)

    def test_failures_while_clearing_the_old_default_are_partial_and_never_a_success(self):
        cases = {
            "412": (lambda: self.before_write(self.patch_of(DEFAULT), lambda: self.supplier(DEFAULT).update(version=9)), "konflikt wersji", []),
            "503": (lambda: None, "HTTP 503", [{"kind": "pass"}, {"kind": "status", "status": 503}]),
            "connection": (lambda: None, "Brak połączenia", [{"kind": "pass"}, {"kind": "raise"}]),
            "429x3": (lambda: None, "HTTP 429", [{"kind": "pass"}] + [{"kind": "status", "status": 429}] * 3),
        }
        for name, (prepare, cause, faults) in cases.items():
            with self.subTest(case=name):
                self.setUp()
                prepare()
                self.graph.faults += faults
                result = self.sp.set_default_supplier(PLAIN)
                self.assert_partial(result, cause)
                targets = [t for t, _ in self.flag_writes()]
                self.assertEqual(targets.count(PLAIN), 1)  # wskazany nie jest zapisywany ponownie
                self.assertEqual(targets[0], PLAIN)
                self.assertTrue(all(t == DEFAULT for t in targets[1:]))

    def test_partial_failure_is_repaired_by_calling_set_default_again(self):
        self.graph.faults += [{"kind": "pass"}, {"kind": "status", "status": 503}]
        self.assert_partial(self.sp.set_default_supplier(PLAIN))
        self.clock["now"] += 16
        self.graph.writes.clear()
        self.assertEqual(self.sp.set_default_supplier(PLAIN), OK)  # wskazany już domyślny: tylko odznaczenie starego
        self.assertEqual(self.flag_writes(), [(DEFAULT, {"IsDefault": False})])
        self.assertEqual(self.defaults(), [PLAIN])

    def test_partial_failure_can_also_be_repaired_by_choosing_the_old_default_again(self):
        self.graph.faults += [{"kind": "pass"}, {"kind": "raise"}]
        self.assert_partial(self.sp.set_default_supplier(PLAIN))
        self.clock["now"] += 16
        self.assertEqual(self.sp.set_default_supplier(DEFAULT), OK)
        self.assertEqual(self.defaults(), [DEFAULT])

    def test_the_old_default_deleted_meanwhile_is_not_a_failure(self):
        old = self.supplier(DEFAULT)
        self.before_write(self.patch_of(DEFAULT), lambda: self.graph.data["Suppliers"].remove(old))  # fake odpowie 404
        self.assertEqual(self.sp.set_default_supplier(PLAIN), OK)
        self.assertEqual(self.defaults(), [PLAIN])

    def test_a_412_when_someone_else_already_cleared_the_flag_is_resolved_by_a_read(self):
        def other_user_clears():
            self.supplier(DEFAULT)["fields"]["IsDefault"] = False
            self.supplier(DEFAULT)["version"] = 5
        self.before_write(self.patch_of(DEFAULT), other_user_clears)
        self.assertEqual(self.sp.set_default_supplier(PLAIN), OK)
        self.assertEqual(self.defaults(), [PLAIN])

    def test_a_lost_response_on_the_clearing_write_is_confirmed_by_a_read_without_a_second_write(self):
        self.graph.faults += [{"kind": "pass"}, {"kind": "lose"}]
        self.assertEqual(self.sp.set_default_supplier(PLAIN), OK)
        self.assertEqual(self.flag_writes(), [(PLAIN, {"IsDefault": True}), (DEFAULT, {"IsDefault": False})])

    def test_a_failure_in_the_middle_stops_and_reports_the_remaining_defaults(self):
        self.set_defaults(DEFAULT, THIRD)
        self.graph.faults += [{"kind": "pass"}, {"kind": "status", "status": 503}]  # nowy ustawiony; odznaczenie pierwszego zawodzi
        ok, message = self.sp.set_default_supplier(PLAIN)
        self.assertFalse(ok)
        self.assertIsInstance(message, PartialFailureMessage)
        self.assertIn("oraz 1 kolejnych", message)
        self.assertEqual(self.flag_writes(), [(PLAIN, {"IsDefault": True}), (DEFAULT, {"IsDefault": False})])  # THIRD nie był ruszany
        self.assertEqual(self.defaults(), sorted([PLAIN, DEFAULT, THIRD]))
        self.clock["now"] += 16
        self.assertEqual(self.sp.set_default_supplier(PLAIN), OK)  # naprawa
        self.assertEqual(self.defaults(), [PLAIN])

    def test_the_last_of_several_failing_is_reported_without_a_remainder(self):
        self.set_defaults(DEFAULT, THIRD)
        self.graph.faults += [{"kind": "pass"}, {"kind": "pass"}, {"kind": "status", "status": 503}]
        ok, message = self.sp.set_default_supplier(PLAIN)
        self.assertIsInstance(message, PartialFailureMessage)
        self.assertNotIn("kolejnych", message)
        self.assertEqual(self.defaults(), sorted([PLAIN, THIRD]))

    def test_company_names_with_literal_newlines_are_shown_on_one_line(self):
        self.supplier(DEFAULT)["fields"]["CompanyName"] = "Firma\\nStara"
        self.graph.faults += [{"kind": "pass"}, {"kind": "status", "status": 503}]
        message = self.sp.set_default_supplier(PLAIN)[1]
        self.assertIn("Firma Stara", message)
        self.assertNotIn("\\n", message)


class StepDVerificationTests(DefaultCase):
    """Odczyt weryfikujący po zapisach: sukces tylko, gdy jedynym domyślnym jest wskazany dostawca."""

    def after_second_write(self, action):
        def hook(method, path, body):
            self.record(method, path, body)
            if len(self.history) == 2:
                action()
        self.graph.after_write = hook

    def test_another_user_setting_a_different_default_meanwhile_is_a_partial_failure(self):
        self.after_second_write(lambda: self.supplier(THIRD)["fields"].update(IsDefault=True))
        ok, message = self.sp.set_default_supplier(PLAIN)
        self.assertFalse(ok)
        self.assertIsInstance(message, PartialFailureMessage)
        self.assertIn("2 domyślnych dostawców", message)
        self.assertEqual(self.defaults(), sorted([PLAIN, THIRD]))

    def test_another_user_resetting_the_target_meanwhile_is_a_conflict(self):
        self.after_second_write(lambda: self.supplier(PLAIN)["fields"].update(IsDefault=False))
        ok, message = self.sp.set_default_supplier(PLAIN)
        self.assertFalse(ok)
        self.assertIsInstance(message, ConflictMessage)

    def test_the_target_deleted_meanwhile_is_a_partial_failure(self):
        self.after_second_write(lambda: self.graph.data["Suppliers"].remove(self.supplier(PLAIN)))
        ok, message = self.sp.set_default_supplier(PLAIN)
        self.assertFalse(ok)
        self.assertIsInstance(message, PartialFailureMessage)
        self.assertIn("usunięty", message)

    def test_a_failing_verification_read_is_a_partial_failure_not_a_success(self):
        self.fail_gets(lambda path, params: len(self.graph.writes) >= 2 and path.endswith("/items"))
        ok, message = self.sp.set_default_supplier(PLAIN)
        self.assertFalse(ok)
        self.assertIsInstance(message, PartialFailureMessage)
        self.assertIn("nie udało się potwierdzić końcowego stanu", message)
        self.assertEqual(self.defaults(), [PLAIN])  # zmiany zostały wykonane, ale nie potwierdzone

    def test_success_is_reported_only_after_a_read_that_confirms_a_single_default(self):
        self.assertEqual(self.sp.set_default_supplier(PLAIN), OK)
        self.assertEqual(self.defaults(), [PLAIN])
        self.assertGreater(len(self.graph.requests), self.reads_at_write[-1])


# ---------------------------------------------------------------------------
# własności: nigdy zero domyślnych, nigdy sukces przy niespójnym stanie
# ---------------------------------------------------------------------------
class SetDefaultInvariantTests(DefaultCase):
    FAULTS = ({"kind": "status", "status": 503}, {"kind": "raise"}, {"kind": "lose"}, {"kind": "status", "status": 404},
              {"kind": "status", "status": 412, "code": "resourceModified"}, {"kind": "status", "status": 429})

    def test_for_every_failure_position_and_initial_state_the_outcome_is_consistent(self):
        for initial in ((DEFAULT,), (DEFAULT, THIRD), ()):
            for position in range(4):
                for fault in self.FAULTS:
                    with self.subTest(initial=initial, position=position, fault=fault["kind"] + str(fault.get("status", ""))):
                        self.setUp()
                        self.set_defaults(*initial)
                        self.graph.faults += [{"kind": "pass"}] * position + [dict(fault)] * (3 if fault.get("status") == 429 else 1)
                        ok, message = self.sp.set_default_supplier(PLAIN)
                        final = self.defaults()
                        if ok:  # sukces tylko przy stanie docelowym
                            self.assertEqual(final, [PLAIN])
                        if initial:  # po zapisie nigdy zero domyślnych
                            self.assertTrue(all(count >= 1 for count in self.history), self.history)
                            self.assertTrue(final)
                        if not ok and final != sorted(initial):  # stan się zmienił, ale operacja nie jest zakończona
                            self.assertIsInstance(message, PartialFailureMessage)

    def test_no_failure_position_ever_produces_a_write_to_another_list_or_a_null_flag(self):
        for position in range(3):
            self.setUp()
            self.graph.faults += [{"kind": "pass"}] * position + [{"kind": "raise"}]
            self.sp.set_default_supplier(PLAIN)
            self.assert_only_suppliers_written()
            for write in self.graph.writes:
                self.assertIn(write["json"], ({"IsDefault": True}, {"IsDefault": False}))


if __name__ == "__main__":
    unittest.main()
