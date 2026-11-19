"""Testy zapisu klientów w SharePointBackend (etap 4A) - offline, na atrapie Graph i tymczasowej bazie SQLite.

Uruchomienie: python -m unittest tests.sharepoint_client_write_test -v
Żadnych żądań sieciowych, żadnych zapisów do SharePoint ani do prawdziwej bazy użytkownika. Atrapa Graph odwzorowuje
zachowanie zmierzone na DEV (docs/sharepoint-graph-behavior.md): 400 invalidRequest przy kolizji unikalności (bez
wskazania pola, bez rozróżniania wielkości liter), 412 przy nieaktualnym If-Match, 404 dla nieistniejącego ID,
brak wymuszania pól wymaganych.
"""
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import tests.sharepoint_backend_test as spt  # noqa: E402  (moduł - bez duplikowania testów)
from src.data.errors import ConflictMessage, ItemNotFoundError, ReadOnlyBackendError, SharePointError  # noqa: E402
from src.integrations.sharepoint import environment_manager, get_environment  # noqa: E402
from src.integrations.sharepoint.graph_client import EnvironmentMismatchError  # noqa: E402
from src.integrations.sharepoint.migration.guard import MigrationGuardError  # noqa: E402
from src.integrations.sharepoint.writer import GraphWriteError, GraphWriter  # noqa: E402

UNAVAILABLE = (False, "Baza danych jest niedostępna lub nie istnieje.")
ALIAS_TAKEN = (False, "Alias już istnieje dla innego klienta")
NOT_FOUND = (False, "Klient nie został znaleziony")
ADD_OK = (True, "Klient został pomyślnie dodany do bazy")
UPDATE_OK = (True, "Dane klienta zostały zaktualizowane")
EXT_OK = (True, "Zapisano dodatkowe pola klienta")
DELETE_OK = (True, "Klient został usunięty z bazy")
UNIQUE_400 = {"status": 400, "code": "invalidRequest", "message": "One or more fields with unique constraints already has the provided value."}


class WriteCase(spt.SpTestCase):
    def clients(self):
        return self.graph.data["Clients"]

    def item(self, title):
        return next(i for i in self.clients() if i["fields"].get("Title") == title)

    def titles(self):
        return sorted(i["fields"]["Title"] for i in self.clients())

    def snapshot(self):
        return {name: [(i["id"], dict(i["fields"]), i.get("version", 1)) for i in items] for name, items in self.graph.data.items()}

    def methods(self):
        return [w["method"] for w in self.graph.writes]

    def assert_clients_equal(self):
        expected = sorted(self.addr(r) for r in self.sq.get_clients(True))
        self.assertEqual(sorted(self.sp.get_clients(True)), expected)

    def both(self, name, *args):
        expected = getattr(self.sq, name)(*args)
        actual = getattr(self.sp, name)(*args)
        self.assertEqual(actual, expected, f"{name}{args}")
        return actual


# ---------------------------------------------------------------------------
# zgodność z SQLite (te same wiadomości i ten sam stan danych)
# ---------------------------------------------------------------------------
class ClientWriteParityTests(WriteCase):
    def test_add_client_validation_messages_and_success_match_sqlite(self):
        self.both("add_client", "1234563218", "Inna", "a", "b", "INNY")  # duplikat NIP
        self.both("add_client", "0123456789", "F", "a", "b", "NEW1")  # duplikat NIP z zerem wiodącym
        for bad in ("123", "abc", "", "12345678901", "12345abcde"):
            self.both("add_client", bad, "F", "a", "b", "Z")
        for alias in ("", "   "):
            self.both("add_client", "5555555559", "F", "a", "b", alias)
        self.assertEqual(self.graph.writes, [])  # żadne z powyższych nie dotarło do POST
        self.assertEqual(self.both("add_client", "5555555559", "Nowy", "ul. N 1", "00-000 Test", "NOWY"), ADD_OK)
        self.assert_clients_equal()

    def test_added_client_is_readable_in_the_public_shape(self):
        self.sp.add_client("5555555559", "Nowy", "ul. N 1", "00-000", "NOWY")
        row = self.sp.get_client_by_nip("5555555559")
        self.assertEqual(row, (5555555559, "Nowy", "ul. N 1", "00-000", "NOWY"))
        self.assertEqual([type(v) for v in row], [int, str, str, str, str])
        self.assertEqual(self.sp.get_client_by_nip(5555555559), row)
        self.assertEqual(self.sp.validate_nip("5555555559"), (False, "Klient z tym NIP już istnieje w bazie"))
        self.assertIn(row + ("", "", "", "", "", ""), self.sp.get_clients(True))

    def test_update_client_matches_sqlite(self):
        self.both("update_client", "1234563218", "Nowa", "ul. N", "11-111", "BETA")
        self.both("update_client", "1234563218", "Nowa2", "ul. N2", "22-222", "BETA")  # własny alias bez zmian
        self.both("update_client", "2222222222", "Z", "a", "b", "ALFA")  # alias innego klienta
        self.both("update_client", "2222222222", "Z", "a", "b", "")  # pusty alias
        self.both("update_client", "2222222222", "Z", "a", "b", "   ")
        self.assert_clients_equal()

    def test_update_and_extended_fields_of_missing_client_are_errors_unlike_sqlite_and_write_nothing(self):
        before = self.snapshot()
        for nip in ("9999999999", "abc", "", None, "123"):
            self.assertEqual(self.sp.update_client(nip, "B", "a", "b", "NOWY"), NOT_FOUND, nip)
            self.assertEqual(self.sp.set_client_extended_fields(nip, "x"), NOT_FOUND, nip)
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(self.graph.writes, [])
        # SQLite (zachowanie historyczne bez zmian): cichy sukces
        self.assertEqual(self.sq.update_client("9999999999", "B", "a", "b", "NOWY"), UPDATE_OK)
        self.assertEqual(self.sq.set_client_extended_fields("9999999999", "x"), EXT_OK)

    def test_extended_fields_match_sqlite_including_empty_string_and_none(self):
        self.both("set_client_extended_fields", "1234563218", "30 dni", "", None, "14 dni", "24 mies.", "netto")
        self.assert_clients_equal()
        stored = self.item("1234563218")["fields"]
        self.assertNotIn("TerminPlatnosci", stored)  # "" i None => brak klucza (NULL)
        self.assertNotIn("WarunkiDostawy", stored)
        self.assertEqual(stored["TerminRealizacji"], "30 dni")
        self.both("set_client_extended_fields", "1234563218")  # wszystkie puste => wszystkie wyczyszczone
        self.assert_clients_equal()
        self.assertFalse(set(self.item("1234563218")["fields"]) & set(spt.sp_module.CLIENT_EXTENDED_FIELDS))

    def test_delete_client_matches_sqlite_for_every_client_and_for_unknown_nips(self):
        for nip in ("9999999999", "abc", "", None):
            self.both("delete_client", nip)
        for nip in (1234563218, 1111111111, 2222222222, 3333333333, "0123456789", 4444444444):
            self.both("delete_client", nip)
            self.assert_clients_equal()

    def test_delete_is_blocked_by_offers_with_the_same_alias_suffix_and_reports_the_count(self):
        self.assertEqual(self.sp.delete_client(2222222222), (False, "Nie można usunąć klienta - istnieją 1 ofert(y) dla tego klienta"))
        self.assertEqual(self.sp.delete_client(1234563218), (False, "Nie można usunąć klienta - istnieją 2 ofert(y) dla tego klienta"))
        self.assertEqual(self.methods(), [])  # blokada działa przed jakimkolwiek DELETE
        self.assertEqual(self.sq.delete_client(1234563218), self.sp.delete_client(1234563218))

    def test_unavailable_session_gives_the_same_message_for_all_four_operations_without_any_request(self):
        self.session.active = False
        for call in (lambda b: b.add_client("5555555559", "F", "a", "b", "Z"),
                     lambda b: b.update_client("1234563218", "F", "a", "b", "Z"),
                     lambda b: b.set_client_extended_fields("1234563218", "x"),
                     lambda b: b.delete_client("1234563218")):
            self.assertEqual(call(self.sp), UNAVAILABLE)
        self.assertEqual((self.graph.requests, self.graph.writes), ([], []))


# ---------------------------------------------------------------------------
# różnice względem SQLite wynikające z SharePoint (udokumentowane)
# ---------------------------------------------------------------------------
class DocumentedDifferencesTests(WriteCase):
    def test_duplicate_alias_is_reported_as_a_validation_error_before_any_write(self):
        result = self.sp.add_client("5555555559", "Nowy", "a", "b", "ALFA")
        self.assertEqual(result, ALIAS_TAKEN)
        self.assertEqual(self.graph.writes, [])
        self.assertEqual(self.sq.add_client("5555555559", "Nowy", "a", "b", "ALFA")[0], False)  # SQLite: też odmowa (inny tekst)

    def test_alias_differing_only_by_case_is_a_conflict_in_sharepoint(self):
        # w SQLite UNIQUE rozróżnia wielkość liter i oba aliasy byłyby przyjęte
        self.assertEqual(self.sp.add_client("5555555559", "Nowy", "a", "b", "alfa"), ALIAS_TAKEN)
        self.assertEqual(self.sp.add_client("5555555559", "Nowy", "a", "b", "Alfa"), ALIAS_TAKEN)
        self.assertEqual(self.sp.add_client("5555555559", "Nowy", "a", "b", "łódź"), ADD_OK)
        self.assertEqual(self.sp.add_client("5555555558", "Nowy2", "a", "b", "ŁÓDŹ"), ALIAS_TAKEN)  # także znaki spoza ASCII
        self.assertEqual(self.methods(), ["POST"])
        self.assertTrue(self.sq.add_client("5555555559", "Nowy", "a", "b", "alfa")[0])

    def test_update_to_alias_of_another_client_differing_by_case_is_refused(self):
        self.assertEqual(self.sp.update_client("2222222222", "Z", "a", "b", "alfa"), ALIAS_TAKEN)
        self.assertEqual(self.graph.writes, [])

    def test_changing_the_case_of_the_own_alias_is_allowed(self):
        self.assertEqual(self.sp.update_client("2222222222", "Zeta", "ul. C", "22-222", "zeta"), UPDATE_OK)
        self.assertEqual(self.item("2222222222")["fields"]["Alias"], "zeta")
        self.assertEqual(self.methods(), ["PATCH"])

    def test_address_line_two_never_stores_new_lines_like_the_migration(self):
        self.sp.add_client("5555555559", "Nowy", "a", "00-001\nMiasto\r\nKraj", "NOWY")
        self.assertEqual(self.item("5555555559")["fields"]["AddressP2"], "00-001, Miasto, Kraj")
        self.assertEqual(self.graph.writes[0]["json"]["fields"]["AddressP2"], "00-001, Miasto, Kraj")

    def test_empty_values_are_not_sent_and_read_back_as_empty_text(self):
        self.assertEqual(self.sp.add_client("5555555559", "Nowy", "ul. N", "", "NOWY"), ADD_OK)
        sent = self.graph.writes[0]["json"]["fields"]
        self.assertEqual(sent, {"Title": "5555555559", "CompanyName": "Nowy", "AddressP1": "ul. N", "Alias": "NOWY"})
        self.assertEqual(self.sp.get_client_by_nip("5555555559"), (5555555559, "Nowy", "ul. N", "", "NOWY"))

    def test_leading_zero_nip_is_kept_as_ten_character_text_and_found_by_int(self):
        self.assertEqual(self.sp.add_client("0123456780", "Z zerem", "a", "b", "ZERO"), ADD_OK)
        self.assertEqual(self.item("0123456780")["fields"]["Title"], "0123456780")
        self.assertEqual(self.sp.get_client_by_nip("0123456780")[0], 123456780)
        self.assertEqual(self.sp.get_client_by_nip(123456780)[0], 123456780)
        self.assertEqual(self.sp.add_client("0123456780", "Inny", "a", "b", "ZERO2"), (False, "Klient z tym NIP już istnieje w bazie"))
        self.assertEqual(self.sp.validate_nip("0123456780"), (False, "Klient z tym NIP już istnieje w bazie"))

    def test_unicode_digits_are_not_a_valid_nip(self):
        self.assertEqual(self.sp.add_client("²²²²²²²²²²", "F", "a", "b", "Z"), (False, "NIP musi składać się z dokładnie 10 cyfr"))
        self.assertEqual(self.sp.validate_nip("²²²²²²²²²²"), (False, "NIP musi składać się z dokładnie 10 cyfr"))
        self.assertEqual(self.sp.validate_supplier_nip("²²²²²²²²²²"), (False, "NIP musi składać się z dokładnie 10 cyfr"))


# ---------------------------------------------------------------------------
# konflikty wykryte dopiero przez POST (wyścig z innym użytkownikiem)
# ---------------------------------------------------------------------------
class PostConflictTests(WriteCase):
    def test_nip_taken_after_the_check_is_reported_by_a_verification_read(self):
        with mock.patch.object(self.sp, "validate_nip", return_value=(True, "NIP jest prawidłowy")):
            result = self.sp.add_client("1234563218", "Inna", "a", "b", "INNY")
        self.assertEqual(result, (False, "Klient z tym NIP już istnieje w bazie"))
        self.assertEqual(self.methods(), ["POST"])  # jedna próba, bez ponowienia
        self.assertEqual(len(self.clients()), 6)

    def test_alias_taken_after_the_check_is_reported_by_a_verification_read(self):
        with mock.patch.object(self.sp, "_alias_in_use", return_value=False):
            result = self.sp.add_client("5555555559", "Nowy", "a", "b", "alfa")
        self.assertEqual(result, ALIAS_TAKEN)
        self.assertEqual(self.methods(), ["POST"])
        self.assertEqual(len(self.clients()), 6)

    def test_unique_error_without_a_visible_cause_gives_a_generic_validation_message(self):
        self.graph.faults.append({"kind": "status", **UNIQUE_400})
        result = self.sp.add_client("5555555559", "Nowy", "a", "b", "NOWY")
        self.assertFalse(result[0])
        self.assertIn("naruszenie unikalności", result[1])
        self.assertEqual(self.methods(), ["POST"])

    def test_other_400_errors_are_returned_as_a_plain_error_message(self):
        self.graph.faults.append({"kind": "status", "status": 400, "code": "invalidRequest", "message": "Field 'X' is not recognized"})
        ok, message = self.sp.add_client("5555555559", "Nowy", "a", "b", "NOWY")
        self.assertFalse(ok)
        self.assertTrue(message.startswith("Błąd podczas dodawania klienta:"), message)
        self.assertIn("not recognized", message)

    def test_update_to_alias_taken_after_the_check_is_reported_as_alias_conflict(self):
        with mock.patch.object(self.sp, "_alias_in_use", return_value=False):
            self.assertEqual(self.sp.update_client("2222222222", "Z", "a", "b", "alfa"), ALIAS_TAKEN)
        self.assertEqual(self.item("2222222222")["fields"]["Alias"], "ZETA")


# ---------------------------------------------------------------------------
# ETag, If-Match i konflikt współbieżności (412)
# ---------------------------------------------------------------------------
class EtagTests(WriteCase):
    def test_update_uses_the_etag_seen_at_the_last_read_in_if_match(self):
        self.sp.get_clients()
        read_etag = self.graph._etag(self.item("2222222222"))
        self.assertEqual(self.sp.update_client("2222222222", "Nowa", "ul. N", "00-000", "ZETA"), UPDATE_OK)
        self.assertEqual([(w["method"], w["if_match"]) for w in self.graph.writes], [("PATCH", read_etag)])
        self.assertTrue(self.graph.writes[0]["path"].endswith(f"/items/{self.item('2222222222')['id']}/fields"))
        self.assertEqual(self.graph.writes[0]["json"], {"CompanyName": "Nowa", "AddressP1": "ul. N", "AddressP2": "00-000"})  # tylko zmiany

    def test_without_a_previous_read_the_etag_comes_from_the_lookup_just_before_the_write(self):
        etag = self.graph._etag(self.item("2222222222"))
        self.assertEqual(self.sp.update_client("2222222222", "Nowa", "a", "b", "ZETA"), UPDATE_OK)
        self.assertEqual(self.graph.writes[0]["if_match"], etag)
        self.assertNotIn(self.graph.writes[0]["if_match"], (None, "*"))

    def test_change_by_another_user_since_the_read_gives_a_conflict_and_no_retry(self):
        self.sp.get_client_by_nip(2222222222)  # użytkownik "widzi" klienta
        other = self.item("2222222222")  # inny użytkownik zmienia ten element
        other["fields"]["AddressP1"] = "ul. Zmieniona przez kogoś innego"
        other["version"] = other.get("version", 1) + 1
        result = self.sp.update_client("2222222222", "Moja nazwa", "ul. C", "22-222", "ZETA")
        self.assertFalse(result[0])
        self.assertIsInstance(result[1], ConflictMessage)
        self.assertTrue(result[1].conflict)
        self.assertIn("zmienione przez innego użytkownika", result[1])
        self.assertEqual(self.methods(), ["PATCH"])  # dokładnie jedna próba
        self.assertEqual(self.item("2222222222")["fields"]["AddressP1"], "ul. Zmieniona przez kogoś innego")  # dane innego użytkownika nietknięte
        self.assertEqual(self.item("2222222222")["fields"]["CompanyName"], "Zeta")

    def test_after_a_conflict_the_next_attempt_reads_fresh_data_and_can_succeed(self):
        self.sp.get_client_by_nip(2222222222)
        self.item("2222222222")["version"] = 5
        first = self.sp.update_client("2222222222", "Moja nazwa", "ul. C", "22-222", "ZETA")
        self.assertIsInstance(first[1], ConflictMessage)
        self.assertEqual(self.sp.update_client("2222222222", "Moja nazwa", "ul. C", "22-222", "ZETA"), UPDATE_OK)
        self.assertEqual(self.item("2222222222")["fields"]["CompanyName"], "Moja nazwa")
        self.assertEqual(self.methods(), ["PATCH", "PATCH"])

    def test_extended_fields_also_report_a_conflict(self):
        self.sp.get_clients(True)
        self.item("1111111111")["version"] = 9
        result = self.sp.set_client_extended_fields("1111111111", "30 dni")
        self.assertFalse(result[0])
        self.assertIsInstance(result[1], ConflictMessage)
        self.assertNotIn("TerminRealizacji", self.item("1111111111")["fields"])
        self.assertEqual(self.methods(), ["PATCH"])

    def test_the_ui_two_step_save_chains_etags_from_responses_without_false_conflicts(self):
        self.assertEqual(self.sp.add_client("5555555559", "Nowy", "a", "b", "NOWY"), ADD_OK)
        created_etag = self.graph._etag(self.item("5555555559"))
        self.assertEqual(self.sp.set_client_extended_fields("5555555559", "30 dni", "14 dni"), EXT_OK)
        self.assertEqual(self.graph.writes[1]["if_match"], created_etag)  # ETag z odpowiedzi POST
        self.assertEqual(self.sp.update_client("5555555559", "Nowy2", "a", "b", "NOWY"), UPDATE_OK)
        self.assertEqual(self.sp.set_client_extended_fields("5555555559", "30 dni", "14 dni", None, None, None, "brutto"), EXT_OK)
        self.assertEqual(self.methods(), ["POST", "PATCH", "PATCH", "PATCH"])
        etags = [w["if_match"] for w in self.graph.writes[1:]]
        self.assertEqual(len(set(etags)), 3)  # każdy zapis używa ETagu poprzedniego zapisu
        self.assertEqual(self.item("5555555559")["version"], 4)

    def test_nothing_is_sent_when_nothing_changes(self):
        row = self.sp.get_client_by_nip(2222222222)
        self.assertEqual(self.sp.update_client("2222222222", row[1], row[2], row[3], row[4]), UPDATE_OK)
        self.assertEqual(self.graph.writes, [])
        self.assertEqual(self.sp.set_client_extended_fields("2222222222", "30 dni", "14 dni", None, None, "24 mies.", "netto"), EXT_OK)
        before = len(self.graph.writes)
        self.assertEqual(before, 1)
        self.assertEqual(self.sp.set_client_extended_fields("2222222222", "30 dni", "14 dni", "", "", "24 mies.", "netto"), EXT_OK)
        self.assertEqual(len(self.graph.writes), before)  # puste "" i None to ta sama pusta wartość - brak nowej wersji

    def test_stale_cache_is_dropped_when_the_item_was_replaced(self):
        self.sp.get_clients()
        old = self.item("2222222222")
        self.clients().remove(old)  # inny użytkownik usunął i dodał klienta z tym samym NIP (inne ID)
        self.clients().append({"id": 500, "fields": dict(old["fields"]), "version": 1})
        self.assertEqual(self.sp.update_client("2222222222", "Nowa", "ul. C", "22-222", "ZETA"), UPDATE_OK)
        self.assertEqual(self.graph.writes[0]["if_match"], self.graph._etag({"id": 500, "version": 1}))

    def test_update_of_an_item_deleted_since_the_lookup_gives_not_found(self):
        item = self.sp._find_client("2222222222")
        self.clients().remove(self.item("2222222222"))
        self.assertEqual(self.sp._patch_client(item, {"CompanyName": "X"}, "ok"), NOT_FOUND)
        self.assertEqual(self.methods(), ["PATCH"])

    def _vanishing_lookup(self, title):
        """Wyszukanie znajduje klienta, ale zanim wykona się zapis, inny użytkownik go usuwa."""
        real_find = self.sp._find_client

        def find_then_delete(t, *args, **kwargs):
            found = real_find(t, *args, **kwargs)
            self.clients().remove(self.item(title))
            return found
        return mock.patch.object(self.sp, "_find_client", side_effect=find_then_delete)

    def test_client_deleted_between_lookup_and_write_gives_not_found_for_both_methods(self):
        for call in (lambda: self.sp.update_client("2222222222", "Nowa", "a", "b", "ZETA"),
                     lambda: self.sp.set_client_extended_fields("2222222222", "30 dni")):
            self.setUp()  # świeże dane i atrapa
            self.sp.get_clients()  # ETag znany, więc PATCH naprawdę trafia do atrapy i dostaje 404
            with self._vanishing_lookup("2222222222"):
                self.assertEqual(call(), NOT_FOUND)
            self.assertEqual(self.methods(), ["PATCH"])  # jedna próba, bez ponowienia
            self.assertNotIn("2222222222", self.titles())
            self.assertEqual(self.sp.get_client_by_nip(2222222222), None)

    def test_http_404_from_patch_gives_not_found_for_both_methods_and_drops_the_cached_etag(self):
        for call in (lambda: self.sp.update_client("2222222222", "Nowa", "a", "b", "ZETA"),
                     lambda: self.sp.set_client_extended_fields("2222222222", "30 dni")):
            self.setUp()
            self.sp.get_clients()
            self.graph.faults.append({"kind": "status", "status": 404, "code": "itemNotFound"})
            before = self.snapshot()
            self.assertEqual(call(), NOT_FOUND)
            self.assertEqual(self.methods(), ["PATCH"])
            self.assertEqual(self.snapshot(), before)  # atrapa nic nie zmieniła
            self.assertNotIn("2222222222", self.sp._etags)

    def test_missing_client_on_first_lookup_makes_no_write_request_for_both_methods(self):
        self.sp.get_clients()
        self.clients().remove(self.item("2222222222"))  # klient znika po odczycie listy, przed zapisem
        self.assertEqual(self.sp.update_client("2222222222", "Nowa", "a", "b", "ZETA"), NOT_FOUND)
        self.assertEqual(self.sp.set_client_extended_fields("2222222222", "30 dni"), NOT_FOUND)
        self.assertEqual(self.graph.writes, [])

    def test_not_found_is_not_a_conflict_message(self):
        self.setUp()
        self.sp.get_clients()
        self.graph.faults.append({"kind": "status", "status": 404, "code": "itemNotFound"})
        ok, message = self.sp.update_client("2222222222", "Nowa", "a", "b", "ZETA")
        self.assertNotIsInstance(message, ConflictMessage)


# ---------------------------------------------------------------------------
# usuwanie wyłącznie po dokładnym, zweryfikowanym ID
# ---------------------------------------------------------------------------
class DeleteSafetyTests(WriteCase):
    def test_delete_removes_exactly_the_verified_item_and_nothing_else(self):
        target = self.item("2222222222")
        target["fields"]["Alias"] = "ZETA-BEZ-OFERT"  # brak ofert => usuwanie dozwolone
        others = [(i["id"], dict(i["fields"]), i.get("version", 1)) for i in self.clients() if i is not target]
        self.assertEqual(self.sp.delete_client(2222222222), DELETE_OK)
        self.assertEqual([(w["method"], w["path"].rsplit("/", 1)[-1]) for w in self.graph.writes], [("DELETE", str(target["id"]))])
        self.assertEqual(self.graph.writes[0]["if_match"], self.graph._etag(target))  # konkretny ETag z odczytu weryfikującego
        self.assertEqual([(i["id"], dict(i["fields"]), i.get("version", 1)) for i in self.clients()], others)
        self.assertEqual(self.sp.get_client_by_nip(2222222222), None)

    def test_delete_of_a_wrong_or_unknown_nip_deletes_nothing(self):
        before = self.snapshot()
        for nip in ("9999999999", "abc", "", None, "123", 12345678901):
            self.assertEqual(self.sp.delete_client(nip), NOT_FOUND)
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(self.graph.writes, [])

    def test_verified_delete_refuses_an_id_whose_title_does_not_match(self):
        other = self.item("3333333333")
        before = self.snapshot()
        with self.assertRaises(SharePointError) as caught:
            self.sp._delete_verified("Clients", other["id"], "1111111111")  # ID innego klienta
        self.assertIn("Odmowa usunięcia", str(caught.exception))
        self.assertEqual(self.graph.writes, [])
        self.assertEqual(self.snapshot(), before)

    def test_verified_delete_refuses_non_numeric_ids_and_other_lists_without_any_request(self):
        for list_name, item_id in (("Clients", "abc"), ("Clients", "1; DROP"), ("Clients", "../2"), ("Clients", ""),
                                   ("Suppliers", "abc"), ("Suppliers", "../2"), ("Offers", "2"), ("Wuzetkas", "2"),
                                   ("Nieznana", "2")):
            with self.subTest(list_name=list_name, item_id=item_id), self.assertRaises(SharePointError) as caught:
                self.sp._delete_verified(list_name, item_id, "1111111111")
            self.assertIn("Odmowa usunięcia", str(caught.exception))
        self.assertEqual((self.graph.requests, self.graph.writes), ([], []))

    def test_delete_of_an_unknown_item_id_reports_not_found_and_changes_nothing(self):
        before = self.snapshot()
        with self.assertRaises(ItemNotFoundError):
            self.sp._delete_verified("Clients", 999999, "1111111111")
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(self.graph.writes, [])

    def test_item_vanishing_between_lookup_and_delete_gives_not_found(self):
        target = self.item("2222222222")
        target["fields"]["Alias"] = "ZETA-BEZ-OFERT"
        real_find = self.sp._find_client
        item = real_find("2222222222", ("Title", "Alias"))

        def find_then_remove(title, fields=None):
            self.clients().remove(target)
            return item
        with mock.patch.object(self.sp, "_find_client", side_effect=find_then_remove):
            self.assertEqual(self.sp.delete_client(2222222222), NOT_FOUND)
        self.assertEqual(self.graph.writes, [])  # weryfikujący odczyt po ID zakończył operację przed DELETE


# ---------------------------------------------------------------------------
# GraphWriter: ograniczenia samego klienta zapisu
# ---------------------------------------------------------------------------
class WriterGuardTests(unittest.TestCase):
    def writer(self, env=None, http=None):
        self.fake = spt.FakeGraph(spt.build_graph_data(spt.TABLES))
        return GraphWriter(env or spt.DEV_ENV, "TOKEN-NIE-DO-LOGOW", http=http or self.fake.http, sleep=lambda s: None)

    def test_only_clients_and_suppliers_are_writable(self):
        w = self.writer()
        for list_name in ("Offers", "Wuzetkas", "Nieznana", "clients", ""):
            with self.subTest(list_name=list_name):
                with self.assertRaises(GraphWriteError):
                    w.create_item(list_name, {"Title": "x"})
                with self.assertRaises(GraphWriteError):
                    w.update_item_fields(list_name, "2", {"Title": "x"}, '"e,1"')
                with self.assertRaises(GraphWriteError):
                    w.delete_item(list_name, "2", '"e,1"')
        self.assertEqual(self.fake.writes, [])

    def test_update_requires_a_concrete_etag(self):
        w = self.writer()
        for etag in (None, "", "   ", "*"):
            with self.subTest(etag=etag), self.assertRaises(GraphWriteError):
                w.update_item_fields("Clients", "2", {"Alias": "X"}, etag)
        self.assertEqual(self.fake.writes, [])

    def test_ids_and_field_names_are_validated_before_any_request(self):
        w = self.writer()
        for item_id in ("abc", "2/../3", "2?x=1", "", None, "２"):
            with self.subTest(item_id=item_id), self.assertRaises(GraphWriteError):
                w.delete_item("Clients", item_id, '"e,1"')
        for fields in ({}, None, {"@odata.type": "x"}, {"a b": 1}, {"Title": object()}, {"Title": ["x"]}):
            with self.subTest(fields=fields), self.assertRaises(GraphWriteError):
                w.create_item("Clients", fields)
        self.assertEqual(self.fake.writes, [])

    def test_prod_environment_is_refused_without_any_request(self):
        w = self.writer(env=get_environment("PROD"))
        with self.assertRaises((MigrationGuardError, EnvironmentMismatchError)):
            w.create_item("Clients", {"Title": "9990000001"})
        self.assertEqual(self.fake.writes, [])

    def test_writes_are_refused_while_the_application_runs_in_prod(self):
        w = self.writer()
        environment_manager.set_active("PROD")
        self.addCleanup(environment_manager.reset)
        with self.assertRaises((MigrationGuardError, EnvironmentMismatchError)):
            w.create_item("Clients", {"Title": "9990000001"})
        self.assertEqual(self.fake.writes, [])

    def test_bearer_token_is_only_in_the_authorization_header(self):
        w = self.writer()
        w.create_item("Clients", {"Title": "9990000001", "CompanyName": "ZZTEST-A", "Alias": "ZZTEST-A"})
        self.assertTrue(self.fake.writes[0]["auth_present"])
        self.assertNotIn("TOKEN-NIE-DO-LOGOW", repr(self.fake.writes))


# ---------------------------------------------------------------------------
# błędy 429, 503 i brak połączenia
# ---------------------------------------------------------------------------
class WriteFailureTests(WriteCase):
    NEW = ("5555555559", "Nowy", "ul. N", "00-000", "NOWY")

    def test_429_is_retried_with_retry_after_and_then_succeeds(self):
        self.graph.faults.append({"kind": "status", "status": 429, "code": "activityLimitReached", "headers": {"Retry-After": "2"}})
        self.assertEqual(self.sp.add_client(*self.NEW), ADD_OK)
        self.assertEqual(self.methods(), ["POST", "POST"])
        self.assertEqual(self.sleeps, [2.0])
        self.assertEqual(self.titles().count("5555555559"), 1)

    def test_retry_after_is_capped_and_attempts_are_limited(self):
        self.graph.faults += [{"kind": "status", "status": 429, "headers": {"Retry-After": "9999"}}] * 3
        ok, message = self.sp.add_client(*self.NEW)
        self.assertFalse(ok)
        self.assertIn("HTTP 429", message)
        self.assertTrue(message.startswith("Błąd podczas dodawania klienta:"), message)
        self.assertEqual(self.methods(), ["POST"] * 3)
        self.assertEqual(self.sleeps, [30.0, 30.0])
        self.assertNotIn("5555555559", self.titles())

    def test_exhausted_429_starts_the_short_unavailability_cooldown(self):
        self.graph.faults += [{"kind": "status", "status": 429}] * 3
        self.sp.add_client(*self.NEW)
        self.assertFalse(self.sp.is_available())
        self.assertEqual(self.sp.update_client("2222222222", "X", "a", "b", "ZETA"), UNAVAILABLE)
        self.clock["now"] += 16
        self.assertTrue(self.sp.is_available())

    def test_503_on_post_is_not_retried_and_nothing_is_created(self):
        self.graph.faults.append({"kind": "status", "status": 503})
        ok, message = self.sp.add_client(*self.NEW)
        self.assertFalse(ok)
        self.assertIn("HTTP 503", message)
        self.assertEqual(self.methods(), ["POST"])
        self.assertNotIn("5555555559", self.titles())

    def test_connection_failure_on_post_returns_an_error_without_a_duplicate_post(self):
        self.graph.faults.append({"kind": "raise"})
        ok, message = self.sp.add_client(*self.NEW)
        self.assertFalse(ok)
        self.assertIn("Brak połączenia", message)
        self.assertEqual(self.methods(), ["POST"])
        self.assertNotIn("5555555559", self.titles())

    def test_lost_post_response_is_recovered_by_a_verification_read_without_a_second_post(self):
        self.graph.faults.append({"kind": "lose"})  # element utworzony, ale odpowiedź nie dotarła
        self.assertEqual(self.sp.add_client(*self.NEW), ADD_OK)
        self.assertEqual(self.methods(), ["POST"])
        self.assertEqual(self.titles().count("5555555559"), 1)
        self.assertEqual(self.sp.set_client_extended_fields("5555555559", "30 dni"), EXT_OK)  # ETag z odczytu weryfikującego

    def test_a_different_item_with_the_same_title_is_not_mistaken_for_our_post(self):
        with mock.patch.object(self.sp, "validate_nip", return_value=(True, "ok")):
            self.graph.faults.append({"kind": "raise"})
            ok, _ = self.sp.add_client("1234563218", "Inna nazwa", "a", "b", "INNY")  # NIP zajęty przez kogoś innego
        self.assertFalse(ok)
        self.assertEqual(len(self.clients()), 6)

    def test_503_and_connection_failure_on_patch_change_nothing_and_are_not_retried(self):
        for fault in ({"kind": "status", "status": 503}, {"kind": "raise"}):
            self.graph.writes.clear()
            self.graph.faults.append(fault)
            before = self.snapshot()
            ok, message = self.sp.update_client("2222222222", "Nowa", "a", "b", "ZETA")
            self.assertFalse(ok)
            self.assertTrue(message.startswith("Błąd podczas aktualizacji klienta:"), message)
            self.assertEqual(self.methods(), ["PATCH"])
            self.assertEqual(self.snapshot(), before)
            self.clock["now"] += 16

    def test_lost_patch_response_does_not_cause_a_false_conflict_on_retry(self):
        self.sp.get_clients()
        self.graph.faults.append({"kind": "lose"})  # zmiana zapisana, odpowiedź utracona
        ok, message = self.sp.update_client("2222222222", "Nowa", "ul. C", "22-222", "ZETA")
        self.assertFalse(ok)
        self.assertNotIsInstance(message, ConflictMessage)
        self.assertEqual(self.item("2222222222")["fields"]["CompanyName"], "Nowa")
        self.clock["now"] += 16
        self.assertEqual(self.sp.update_client("2222222222", "Nowa", "ul. C", "22-222", "ZETA"), UPDATE_OK)  # brak zmian => sukces
        self.assertEqual(self.methods(), ["PATCH"])

    def test_503_and_connection_failure_on_delete_leave_the_item_and_report_an_error(self):
        self.item("2222222222")["fields"]["Alias"] = "ZETA-BEZ-OFERT"
        for fault in ({"kind": "status", "status": 503}, {"kind": "raise"}):
            self.graph.faults.append(fault)
            ok, message = self.sp.delete_client(2222222222)
            self.assertFalse(ok)
            self.assertTrue(message.startswith("Błąd podczas usuwania klienta:"), message)
            self.assertIn("2222222222", self.titles())
            self.clock["now"] += 16
        self.assertEqual(self.methods(), ["DELETE", "DELETE"])

    def test_lost_delete_response_then_retry_reports_not_found(self):
        self.item("2222222222")["fields"]["Alias"] = "ZETA-BEZ-OFERT"
        self.graph.faults.append({"kind": "lose"})
        self.assertFalse(self.sp.delete_client(2222222222)[0])
        self.assertNotIn("2222222222", self.titles())
        self.clock["now"] += 16
        self.assertEqual(self.sp.delete_client(2222222222), NOT_FOUND)

    def test_sign_in_loss_gives_the_unavailable_message_and_never_a_request(self):
        self.session.active = False
        self.assertEqual(self.sp.add_client(*self.NEW), UNAVAILABLE)
        self.assertEqual((self.graph.requests, self.graph.writes), ([], []))

    def test_expired_session_during_a_write_is_reported_without_crashing(self):
        with mock.patch.object(self.session, "get_token", side_effect=spt.NotSignedInError("Sesja SharePoint wygasła - zaloguj się ponownie.")):
            ok, message = self.sp.add_client(*self.NEW)
        self.assertFalse(ok)
        self.assertIn("zaloguj się ponownie", message)

    def test_401_invalidates_the_token_and_is_reported(self):
        self.graph.faults.append({"kind": "status", "status": 401, "code": "InvalidAuthenticationToken"})
        ok, message = self.sp.add_client(*self.NEW)
        self.assertFalse(ok)
        self.assertEqual(self.session.invalidated, 1)
        self.assertEqual(self.methods(), ["POST"])

    def test_no_token_ever_appears_in_messages_logs_or_popups(self):
        self.graph.faults += [{"kind": "status", "status": 503}, {"kind": "raise"}, {"kind": "status", "status": 429}] + \
                             [{"kind": "status", "status": 429}] * 2
        texts = [str(self.sp.add_client(*self.NEW)), str(self.sp.add_client("5555555558", "N", "a", "b", "N2"))]
        texts += [str(self.sp_popups), str(self.sp_logs)]
        self.assertNotIn(self.session.token, "\n".join(texts))


class StillReadOnlyTests(WriteCase):
    def test_supplier_offer_wz_and_numbering_operations_never_reach_the_writer(self):
        calls = [("get_next_offer_number", ()),
                 ("save_offer", (1, "2026/a.docx", {})), ("delete_offer", ("2026/a.docx",)),
                 ("save_wz", (1, "2026/a.docx", {})), ("get_next_offer_number_for_year", (2026,)),
                 ("get_next_wz_number", (2026,)), ("update_wz_context", ("2026/a.docx", {}))]
        for name, args in calls:
            with self.subTest(method=name), self.assertRaises(ReadOnlyBackendError):
                getattr(self.sp, name)(*args)
        self.assertEqual((self.graph.requests, self.graph.writes), ([], []))


if __name__ == "__main__":
    unittest.main()
