"""Testy charakteryzujące obecne zachowanie src/data/database_service.py (etap 0).

Cel: zapisać DOKŁADNIE to, co serwis robi dziś (kształty krotek, wartości zwracane, komunikaty, konwencje
błędów), zanim wprowadzimy fasadę z wymiennymi backendami. Testy NIE oceniają, czy zachowanie jest dobre.
Testy oznaczone w opisie jako "LEGACY" dokumentują zachowania nieidealne, o których poprawie zdecydujemy
świadomie później (po zmianie zachowania odpowiedni test trzeba zaktualizować celowo).

Bezpieczeństwo: serwis jest przekierowany na tymczasową bazę SQLite w katalogu tymczasowym
(podmiana SettingsManager i folderów w module serwisu). Prawdziwa baza użytkownika, ustawienia
i SharePoint nie są używane; sprawdza to też test na końcu pliku.

Uruchomienie: python -m unittest tests.database_service_characterization_test -v
"""
import datetime
import json
import os
import sqlite3
import sys
import tempfile
import tkinter
import tkinter.messagebox
import unittest
from types import SimpleNamespace
from unittest import mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import src.data.database_service as dbs  # noqa: E402
from src.data.errors import DataAccessError, NumberingError  # noqa: E402
from src.utils.settings import settings_manager  # noqa: E402

ORIGINAL_POPUP_PREDICATE = dbs._should_show_db_error_popup
REAL_DB_PATH = settings_manager.get_database_path()


def _fingerprint(path):
    try:
        st = os.stat(path)
        return st.st_size, st.st_mtime_ns
    except OSError:
        return None


_REAL_DB_BEFORE = _fingerprint(REAL_DB_PATH)

CLIENTS_DDL = """CREATE TABLE "Clients" (
    "Nip" INTEGER, "CompanyName" TEXT NOT NULL, "AddressP1" TEXT NOT NULL, "AddressP2" TEXT NOT NULL,
    "Alias" TEXT NOT NULL UNIQUE, "TerminRealizacji" TEXT, "TerminPlatnosci" TEXT, "WarunkiDostawy" TEXT,
    "WaznoscOferty" TEXT, "Gwarancja" TEXT, "Cena" TEXT, PRIMARY KEY("Nip"))"""
SUPPLIERS_DDL = """CREATE TABLE "Suppliers" (
    "Nip" INTEGER, "CompanyName" TEXT NOT NULL, "AddressP1" TEXT NOT NULL, "AddressP2" TEXT NOT NULL,
    IsDefault INTEGER DEFAULT 0, PRIMARY KEY("Nip"))"""
OFFERS_DDL = """CREATE TABLE "Offers" (OfferYearNumber INTEGER NOT NULL, OfferOrderNumber INTEGER NOT NULL,
    OfferFilePath TEXT NOT NULL UNIQUE, OfferContext TEXT);
    CREATE UNIQUE INDEX Offers_Year_Order_UNQ ON Offers(OfferYearNumber, OfferOrderNumber)"""
WZ_DDL = """CREATE TABLE "Wuzetkas" (WzYearNumber INTEGER NOT NULL, WzOrderNumber INTEGER NOT NULL,
    WzFilePath TEXT NOT NULL UNIQUE, WzContext TEXT);
    CREATE UNIQUE INDEX Wuzetkas_Year_Order_UNQ ON Wuzetkas(WzYearNumber, WzOrderNumber)"""
OFFERS_LEGACY_DDL = """CREATE TABLE "Offers" (OfferOrderNumber INTEGER NOT NULL,
    OfferFilePath TEXT NOT NULL UNIQUE, OfferContext TEXT)"""
WZ_LEGACY_DDL = """CREATE TABLE "Wuzetkas" (WzOrderNumber INTEGER NOT NULL,
    WzFilePath TEXT NOT NULL UNIQUE, WzContext TEXT)"""


class DbTestCase(unittest.TestCase):
    """Przekierowuje serwis na tymczasową bazę; zapisuje wywołania messagebox zamiast je pokazywać."""

    legacy_offers = False
    legacy_wz = False
    tables = ("clients", "suppliers", "offers", "wz")

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = self.tmp.name.replace("\\", "/")
        self.db_path = f"{root}/test.db"
        self.offers_dir = f"{root}/offers"
        self.wz_dir = f"{root}/wz"
        self.cfg = SimpleNamespace(path=self.db_path, popups=False)
        self.popups = []

        self._create_db()

        manager = SimpleNamespace(get_database_path=lambda: self.cfg.path)
        patches = [
            mock.patch.object(dbs, "SettingsManager", mock.Mock(return_value=manager)),
            mock.patch.object(dbs, "get_offers_folder", lambda: self.offers_dir),
            mock.patch.object(dbs, "get_wz_folder", lambda: self.wz_dir),
            mock.patch.object(dbs, "print", lambda *a, **k: None, create=True),
            mock.patch.object(dbs, "_should_show_db_error_popup", lambda: self.cfg.popups),
            mock.patch.object(tkinter.messagebox, "showerror", lambda *a, **k: self.popups.append(("error",) + a)),
            mock.patch.object(tkinter.messagebox, "showwarning", lambda *a, **k: self.popups.append(("warning",) + a)),
            mock.patch.object(tkinter.messagebox, "showinfo", lambda *a, **k: self.popups.append(("info",) + a)),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        self.assertEqual(dbs.get_database_path(), self.db_path, "serwis nie jest przekierowany na bazę testową")

    def _create_db(self):
        conn = sqlite3.connect(self.db_path)
        ddl = []
        if "clients" in self.tables:
            ddl.append(CLIENTS_DDL)
        if "suppliers" in self.tables:
            ddl.append(SUPPLIERS_DDL)
        if "offers" in self.tables:
            ddl.append(OFFERS_LEGACY_DDL if self.legacy_offers else OFFERS_DDL)
        if "wz" in self.tables:
            ddl.append(WZ_LEGACY_DDL if self.legacy_wz else WZ_DDL)
        for statement in ddl:
            conn.executescript(statement)
        conn.commit()
        conn.close()

    # --- pomocnicze (bezpośredni dostęp do bazy testowej) ---
    def rows(self, sql, params=()):
        conn = sqlite3.connect(self.db_path)
        try:
            return conn.execute(sql, params).fetchall()
        finally:
            conn.close()

    def run_sql(self, sql, params=()):
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(sql, params)
            conn.commit()
        finally:
            conn.close()

    def add_client(self, nip=1234563218, name="Firma A", a1="ul. A 1", a2="00-001 Miasto", alias="ALFA", **ext):
        cols = ["Nip", "CompanyName", "AddressP1", "AddressP2", "Alias"] + list(ext)
        self.run_sql(f"INSERT INTO Clients ({','.join(cols)}) VALUES ({','.join('?' * len(cols))})",
                     [nip, name, a1, a2, alias] + list(ext.values()))

    def add_supplier(self, nip=3333333333, name="Dostawca", a1="ul. B 2", a2="58-300", default=0):
        self.run_sql("INSERT INTO Suppliers (Nip, CompanyName, AddressP1, AddressP2, IsDefault) VALUES (?,?,?,?,?)",
                     (nip, name, a1, a2, default))

    def add_offer(self, year=2026, order=1, path=None, ctx=None):
        path = path or f"{year}/{order}_OF_{year}_ALFA.docx"
        self.run_sql("INSERT INTO Offers (OfferYearNumber, OfferOrderNumber, OfferFilePath, OfferContext) VALUES (?,?,?,?)",
                     (year, order, path, ctx))

    def add_wz(self, year=2026, order=1, path=None, ctx=None):
        path = path or f"{year}/WZ_{order}_{year}_ALFA.docx"
        self.run_sql("INSERT INTO Wuzetkas (WzYearNumber, WzOrderNumber, WzFilePath, WzContext) VALUES (?,?,?,?)",
                     (year, order, path, ctx))

    def make_unavailable(self):
        self.cfg.path = f"{self.tmp.name.replace(chr(92), '/')}/missing.db"


# ======================================================================
# Dostępność, ścieżki, okienka błędów
# ======================================================================
class AvailabilityAndPathsTests(DbTestCase):
    def test_available_when_any_known_table_exists(self):
        self.assertTrue(dbs.is_database_available())

    def test_available_with_a_single_known_table(self):
        self.tables = ("wz",)
        os.remove(self.db_path)
        self._create_db()
        self.assertTrue(dbs.is_database_available())

    def test_unavailable_when_file_missing_and_file_is_not_created(self):
        self.make_unavailable()
        self.assertFalse(dbs.is_database_available())
        self.assertFalse(os.path.exists(self.cfg.path))

    def test_unavailable_for_empty_path(self):
        self.cfg.path = ""
        self.assertFalse(dbs.is_database_available())

    def test_unavailable_for_non_sqlite_file(self):
        with open(self.db_path, "wb") as f:
            f.write(b"to nie jest baza sqlite" * 50)
        self.assertFalse(dbs.is_database_available())

    def test_unavailable_when_no_known_tables(self):
        os.remove(self.db_path)
        conn = sqlite3.connect(self.db_path)
        conn.execute("CREATE TABLE Inna (x INTEGER)")
        conn.commit()
        conn.close()
        self.assertFalse(dbs.is_database_available())

    def test_get_database_path_returns_configured_absolute_path(self):
        self.assertEqual(dbs.get_database_path(), self.db_path)

    def test_get_database_path_makes_relative_path_absolute_against_project_root(self):
        self.cfg.path = "dane/baza.db"
        root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(dbs.__file__))))
        self.assertEqual(dbs.get_database_path(), os.path.abspath(os.path.join(root, "dane/baza.db")))

    def test_get_database_path_falls_back_to_default_when_setting_is_empty(self):
        self.cfg.path = ""
        self.assertEqual(dbs.get_database_path(), dbs.DEFAULT_APP_SETTINGS["database_path"])

    def test_get_database_path_falls_back_to_default_when_settings_fail(self):
        with mock.patch.object(dbs, "SettingsManager", side_effect=RuntimeError("ustawienia")):
            self.assertEqual(dbs.get_database_path(), dbs.DEFAULT_APP_SETTINGS["database_path"])

    def test_popup_predicate_requires_tk_root_and_enabled_flag(self):
        with mock.patch.object(tkinter, "_default_root", None):
            with mock.patch.object(dbs, "DB_POPUPS_ENABLED", True, create=True):
                self.assertFalse(ORIGINAL_POPUP_PREDICATE())  # brak korzenia Tk
        with mock.patch.object(tkinter, "_default_root", object()):
            with mock.patch.object(dbs, "DB_POPUPS_ENABLED", False, create=True):
                self.assertFalse(ORIGINAL_POPUP_PREDICATE())
            with mock.patch.object(dbs, "DB_POPUPS_ENABLED", True, create=True):
                self.assertTrue(ORIGINAL_POPUP_PREDICATE())


class PathHelpersTests(DbTestCase):
    def test_normalize_offer_path_strips_offers_root(self):
        self.assertEqual(dbs.normalize_offer_db_path(f"{self.offers_dir}/2026/1_OF_2026_A.docx"),
                         "2026/1_OF_2026_A.docx")

    def test_normalize_offer_path_converts_backslashes_and_strips_leading_slash(self):
        self.assertEqual(dbs.normalize_offer_db_path("2026\\1_OF_2026_A.docx"), "2026/1_OF_2026_A.docx")
        self.assertEqual(dbs.normalize_offer_db_path("/2026/x.docx"), "2026/x.docx")

    def test_normalize_offer_path_empty_and_filename_only(self):
        self.assertEqual(dbs.normalize_offer_db_path(""), "")
        self.assertEqual(dbs.normalize_offer_db_path("plik.docx"), "plik.docx")

    def test_normalize_offer_path_does_not_extract_year_from_foreign_absolute_path(self):
        # LEGACY: ścieżka spoza folderu ofert (bez prefiksu) jest zwracana praktycznie bez zmian
        self.assertEqual(dbs.normalize_offer_db_path("D:/inne/2026/x.docx"), "D:/inne/2026/x.docx")

    def test_build_full_offer_path(self):
        self.assertEqual(dbs.build_full_offer_path("2026/x.docx"), os.path.join(self.offers_dir, "2026/x.docx"))
        self.assertEqual(dbs.build_full_offer_path(""), self.offers_dir)

    def test_normalize_wz_path_strips_root_and_keeps_year_filename(self):
        self.assertEqual(dbs.normalize_wz_db_path(f"{self.wz_dir}/2026/WZ_1_2026_A.docx"), "2026/WZ_1_2026_A.docx")

    def test_normalize_wz_path_extracts_last_year_filename_from_foreign_path(self):
        self.assertEqual(dbs.normalize_wz_db_path("D:\\skad\\2025\\WZ_2_2025_B.docx"), "2025/WZ_2_2025_B.docx")

    def test_normalize_wz_path_fallbacks(self):
        self.assertEqual(dbs.normalize_wz_db_path(""), "")
        self.assertEqual(dbs.normalize_wz_db_path("plik.docx"), "plik.docx")
        self.assertEqual(dbs.normalize_wz_db_path("podkatalog/plik.docx"), "podkatalog/plik.docx")

    def test_build_full_wz_path(self):
        self.assertEqual(dbs.build_full_wz_path("2026/x.docx"), os.path.join(self.wz_dir, "2026/x.docx"))
        self.assertEqual(dbs.build_full_wz_path(""), self.wz_dir)

    def test_build_full_wz_path_keeps_absolute_path(self):
        absolute = os.path.abspath(os.path.join(self.tmp.name, "gdzies", "x.docx"))
        self.assertEqual(dbs.build_full_wz_path(absolute), absolute)

    def test_build_full_wz_path_legacy_path_that_already_contains_base_gets_leading_slash(self):
        # LEGACY: ścieżka "zawierająca bazę, ale bez wiodącego /" dostaje wiodący slash (obsługa POSIX)
        with mock.patch.object(dbs, "get_wz_folder", lambda: "/dane/wz"):
            self.assertEqual(dbs.build_full_wz_path("dane/wz/2026/x.docx"), "/dane/wz/2026/x.docx")


# ======================================================================
# Clients
# ======================================================================
class ClientReadTests(DbTestCase):
    def test_get_clients_basic_shape_is_five_tuple_with_int_nip(self):
        self.add_client(nip=1234563218, name="Firma A", a1="ul. A 1", a2="00-001", alias="ALFA")
        self.assertEqual(dbs.get_clients_from_db(), [(1234563218, "Firma A", "ul. A 1", "00-001", "ALFA")])
        self.assertIsInstance(dbs.get_clients_from_db()[0][0], int)

    def test_get_clients_extended_shape_is_eleven_tuple_and_null_becomes_empty_string(self):
        self.add_client(alias="ALFA", TerminRealizacji="30 dni", Cena=None)
        row = dbs.get_clients_from_db(include_extended=True)[0]
        self.assertEqual(len(row), 11)
        self.assertEqual(row, (1234563218, "Firma A", "ul. A 1", "00-001 Miasto", "ALFA", "30 dni", "", "", "", "", ""))

    def test_get_clients_is_ordered_by_company_name_binary_collation(self):
        # LEGACY: sortowanie binarne - wielkie litery przed małymi, litery polskie na końcu
        for i, name in enumerate(["beta", "Alfa", "Zeta", "Łódź"], start=1):
            self.add_client(nip=1000000000 + i, name=name, alias=f"A{i}")
        self.assertEqual([c[1] for c in dbs.get_clients_from_db()], ["Alfa", "Zeta", "beta", "Łódź"])

    def test_get_clients_empty_database(self):
        self.assertEqual(dbs.get_clients_from_db(), [])

    def test_get_clients_unavailable_database_returns_empty_list_without_popup(self):
        self.make_unavailable()
        self.assertEqual(dbs.get_clients_from_db(), [])
        self.assertEqual(self.popups, [])

    def test_get_clients_sql_error_returns_empty_list_and_popup_only_when_popups_enabled(self):
        self.tables = ("suppliers",)
        os.remove(self.db_path)
        self._create_db()
        self.assertEqual(dbs.get_clients_from_db(), [])
        self.assertEqual(self.popups, [])
        self.cfg.popups = True
        self.assertEqual(dbs.get_clients_from_db(), [])
        self.assertEqual(len(self.popups), 1)
        self.assertEqual(self.popups[0][:2], ("error", "Database Error"))

    def test_get_client_by_nip_found_returns_five_tuple(self):
        self.add_client()
        self.assertEqual(dbs.get_client_by_nip(1234563218), (1234563218, "Firma A", "ul. A 1", "00-001 Miasto", "ALFA"))

    def test_get_client_by_nip_accepts_string_nip_through_column_affinity(self):
        self.add_client()
        self.assertEqual(dbs.get_client_by_nip("1234563218")[4], "ALFA")

    def test_get_client_by_nip_missing_or_unavailable_returns_none(self):
        self.assertIsNone(dbs.get_client_by_nip("1111111111"))
        self.make_unavailable()
        self.assertIsNone(dbs.get_client_by_nip("1234563218"))

    def test_get_client_by_nip_sql_error_shows_popup_unconditionally_and_returns_none(self):
        # LEGACY: ten odczyt pokazuje okienko także gdy popupy są wyłączone
        self.tables = ("suppliers",)
        os.remove(self.db_path)
        self._create_db()
        self.assertIsNone(dbs.get_client_by_nip("1234563218"))
        self.assertEqual([p[:2] for p in self.popups], [("error", "Database Error")])


class ClientValidationTests(DbTestCase):
    def test_validate_nip_rejects_non_digits_and_wrong_length(self):
        msg = "NIP musi składać się z dokładnie 10 cyfr"
        self.assertEqual(dbs.validate_nip("12345abcde"), (False, msg))
        self.assertEqual(dbs.validate_nip("123456789"), (False, msg))
        self.assertEqual(dbs.validate_nip("12345678901"), (False, msg))
        self.assertEqual(dbs.validate_nip(""), (False, msg))

    def test_validate_nip_accepts_free_nip_and_rejects_duplicate(self):
        self.assertEqual(dbs.validate_nip("1234563218"), (True, "NIP jest prawidłowy"))
        self.add_client()
        self.assertEqual(dbs.validate_nip("1234563218"), (False, "Klient z tym NIP już istnieje w bazie"))

    def test_validate_nip_requires_string_argument(self):
        # LEGACY: int powoduje AttributeError (UI zawsze przekazuje tekst)
        with self.assertRaises(AttributeError):
            dbs.validate_nip(1234563218)

    def test_validate_nip_creates_missing_database_file_and_reports_sql_error(self):
        # LEGACY: brak sprawdzenia dostępności - sqlite3.connect tworzy pusty plik bazy
        self.make_unavailable()
        ok, msg = dbs.validate_nip("1234563218")
        self.assertFalse(ok)
        self.assertTrue(msg.startswith("Błąd sprawdzania NIP:"), msg)
        self.assertTrue(os.path.exists(self.cfg.path))

    def test_validate_alias_only_checks_non_empty(self):
        self.assertEqual(dbs.validate_alias(""), (False, "Alias nie może być pusty"))
        self.assertEqual(dbs.validate_alias("   "), (False, "Alias nie może być pusty"))
        self.assertEqual(dbs.validate_alias("A_B C&D"), (True, "Alias jest prawidłowy"))

    def test_validate_alias_does_not_check_uniqueness(self):
        self.add_client(alias="ALFA")
        self.assertEqual(dbs.validate_alias("ALFA"), (True, "Alias jest prawidłowy"))


class ClientWriteTests(DbTestCase):
    def test_add_client_success_message_and_stored_row(self):
        result = dbs.add_client_to_db("1234563218", "Firma A", "ul. A 1", "00-001", "ALFA")
        self.assertEqual(result, (True, "Klient został pomyślnie dodany do bazy"))
        self.assertEqual(self.rows("SELECT Nip, CompanyName, AddressP1, AddressP2, Alias, TerminRealizacji FROM Clients"),
                         [(1234563218, "Firma A", "ul. A 1", "00-001", "ALFA", None)])

    def test_add_client_with_leading_zero_nip_is_stored_as_int_without_zero(self):
        # LEGACY: kolumna INTEGER gubi zero wiodące, ale wyszukiwanie po tekście nadal działa
        self.assertTrue(dbs.add_client_to_db("0123456789", "F", "a", "b", "Z")[0])
        self.assertEqual(self.rows("SELECT Nip FROM Clients"), [(123456789,)])
        self.assertEqual(dbs.get_client_by_nip("0123456789")[0], 123456789)

    def test_add_client_rejects_bad_nip_without_inserting(self):
        self.assertEqual(dbs.add_client_to_db("123", "F", "a", "b", "Z"),
                         (False, "NIP musi składać się z dokładnie 10 cyfr"))
        self.assertEqual(self.rows("SELECT COUNT(*) FROM Clients"), [(0,)])

    def test_add_client_rejects_duplicate_nip(self):
        self.add_client()
        self.assertEqual(dbs.add_client_to_db("1234563218", "Inna", "a", "b", "INNY"),
                         (False, "Klient z tym NIP już istnieje w bazie"))

    def test_add_client_rejects_empty_alias(self):
        self.assertEqual(dbs.add_client_to_db("1234563218", "F", "a", "b", "  "), (False, "Alias nie może być pusty"))

    def test_add_client_duplicate_alias_returns_sql_error_message(self):
        self.add_client(alias="ALFA")
        ok, msg = dbs.add_client_to_db("1111111111", "Inna", "a", "b", "ALFA")
        self.assertFalse(ok)
        self.assertTrue(msg.startswith("Błąd podczas dodawania klienta:"), msg)
        self.assertIn("Alias", msg)

    def test_add_client_aliases_differing_only_by_case_are_both_accepted(self):
        # LEGACY: UNIQUE w SQLite rozróżnia wielkość liter (w SharePoint kolidowałyby)
        self.assertTrue(dbs.add_client_to_db("1111111111", "A", "a", "b", "AlfaStal")[0])
        self.assertTrue(dbs.add_client_to_db("2222222222", "B", "a", "b", "ALFASTAL")[0])
        self.assertEqual(self.rows("SELECT COUNT(*) FROM Clients"), [(2,)])

    def test_add_client_unavailable_database(self):
        self.make_unavailable()
        self.assertEqual(dbs.add_client_to_db("1234563218", "F", "a", "b", "Z"),
                         (False, "Baza danych jest niedostępna lub nie istnieje."))

    def test_update_client_success_changes_fields_but_not_nip(self):
        self.add_client(alias="ALFA")
        self.assertEqual(dbs.update_client_in_db("1234563218", "Nowa", "ul. N", "11-111", "BETA"),
                         (True, "Dane klienta zostały zaktualizowane"))
        self.assertEqual(self.rows("SELECT Nip, CompanyName, AddressP1, AddressP2, Alias FROM Clients"),
                         [(1234563218, "Nowa", "ul. N", "11-111", "BETA")])

    def test_update_client_allows_keeping_own_alias(self):
        self.add_client(alias="ALFA")
        self.assertTrue(dbs.update_client_in_db("1234563218", "Nowa", "a", "b", "ALFA")[0])

    def test_update_client_rejects_alias_of_another_client(self):
        self.add_client(nip=1111111111, alias="ALFA")
        self.add_client(nip=2222222222, alias="BETA")
        self.assertEqual(dbs.update_client_in_db("2222222222", "B", "a", "b", "ALFA"),
                         (False, "Alias już istnieje dla innego klienta"))

    def test_update_client_rejects_empty_alias(self):
        self.add_client()
        self.assertEqual(dbs.update_client_in_db("1234563218", "B", "a", "b", ""), (False, "Alias nie może być pusty"))

    def test_update_client_missing_client_reports_success(self):
        # LEGACY: brak sprawdzenia rowcount - aktualizacja nieistniejącego klienta zwraca sukces
        self.assertEqual(dbs.update_client_in_db("9999999999", "B", "a", "b", "NOWY"),
                         (True, "Dane klienta zostały zaktualizowane"))
        self.assertEqual(self.rows("SELECT COUNT(*) FROM Clients"), [(0,)])

    def test_update_client_unavailable_database(self):
        self.make_unavailable()
        self.assertEqual(dbs.update_client_in_db("1234563218", "B", "a", "b", "X"),
                         (False, "Baza danych jest niedostępna lub nie istnieje."))

    def test_set_extended_fields_writes_values_and_converts_empty_string_and_none_to_null(self):
        self.add_client()
        result = dbs.set_client_extended_fields("1234563218", "30 dni", "", None, "14 dni", "24 mies.", "netto")
        self.assertEqual(result, (True, "Zapisano dodatkowe pola klienta"))
        self.assertEqual(self.rows("SELECT TerminRealizacji, TerminPlatnosci, WarunkiDostawy, WaznoscOferty, Gwarancja, Cena FROM Clients"),
                         [("30 dni", None, None, "14 dni", "24 mies.", "netto")])

    def test_set_extended_fields_missing_client_is_silent_success(self):
        # LEGACY
        self.assertEqual(dbs.set_client_extended_fields("9999999999", "x"), (True, "Zapisano dodatkowe pola klienta"))

    def test_set_extended_fields_unavailable_database(self):
        self.make_unavailable()
        self.assertEqual(dbs.set_client_extended_fields("1234563218"), (False, "Baza danych jest niedostępna lub nie istnieje."))

    def test_client_save_is_two_separate_writes(self):
        # LEGACY: UI zapisuje klienta przez add_client_to_db + set_client_extended_fields (dwie transakcje)
        dbs.add_client_to_db("1234563218", "F", "a", "b", "ALFA")
        self.assertEqual(self.rows("SELECT TerminRealizacji FROM Clients"), [(None,)])
        dbs.set_client_extended_fields("1234563218", "30 dni")
        self.assertEqual(self.rows("SELECT TerminRealizacji FROM Clients"), [("30 dni",)])


class ClientDeleteTests(DbTestCase):
    def test_delete_client_success(self):
        self.add_client()
        self.assertEqual(dbs.delete_client_from_db("1234563218"), (True, "Klient został usunięty z bazy"))
        self.assertEqual(self.rows("SELECT COUNT(*) FROM Clients"), [(0,)])

    def test_delete_client_missing(self):
        self.assertEqual(dbs.delete_client_from_db("9999999999"), (False, "Klient nie został znaleziony"))

    def test_delete_client_blocked_when_offer_file_name_ends_with_alias(self):
        self.add_client(alias="ALFA")
        self.add_offer(path="2026/1_OF_2026_ALFA.docx")
        self.add_offer(order=2, path="2026/2_OF_2026_ALFA.docx")
        self.assertEqual(dbs.delete_client_from_db("1234563218"),
                         (False, "Nie można usunąć klienta - istnieją 2 ofert(y) dla tego klienta"))
        self.assertEqual(self.rows("SELECT COUNT(*) FROM Clients"), [(1,)])

    def test_delete_client_not_blocked_by_wz_documents(self):
        self.add_client(alias="ALFA")
        self.add_wz(path="2026/WZ_1_2026_ALFA.docx")
        self.assertTrue(dbs.delete_client_from_db("1234563218")[0])

    def test_delete_client_block_is_a_suffix_match_so_other_alias_can_block_it(self):
        # LEGACY: alias "STEEL" jest blokowany przez ofertę klienta "ALFASTEEL" (dopasowanie końcówki nazwy pliku)
        self.add_client(alias="STEEL")
        self.add_offer(path="2026/1_OF_2026_ALFASTEEL.docx")
        ok, msg = dbs.delete_client_from_db("1234563218")
        self.assertFalse(ok)
        self.assertIn("1 ofert(y)", msg)

    def test_delete_client_block_is_case_insensitive(self):
        # LEGACY: LIKE w SQLite ignoruje wielkość liter ASCII
        self.add_client(alias="steel")
        self.add_offer(path="2026/1_OF_2026_STEEL.docx")
        self.assertFalse(dbs.delete_client_from_db("1234563218")[0])

    def test_delete_client_block_treats_underscore_in_alias_as_wildcard(self):
        # LEGACY: "_" w aliasie to w LIKE dowolny znak - alias "A_B" blokuje ofertę klienta "AxB"
        self.add_client(alias="A_B")
        self.add_offer(path="2026/1_OF_2026_AxB.docx")
        self.assertFalse(dbs.delete_client_from_db("1234563218")[0])

    def test_delete_client_unavailable_database(self):
        self.make_unavailable()
        self.assertEqual(dbs.delete_client_from_db("1234563218"), (False, "Baza danych jest niedostępna lub nie istnieje."))


# ======================================================================
# Suppliers
# ======================================================================
class SupplierReadTests(DbTestCase):
    def test_get_suppliers_shape_and_int_is_default(self):
        self.add_supplier(default=1)
        self.assertEqual(dbs.get_suppliers_from_db(), [(3333333333, "Dostawca", "ul. B 2", "58-300", 1)])

    def test_get_suppliers_null_is_default_becomes_zero(self):
        self.run_sql("INSERT INTO Suppliers (Nip, CompanyName, AddressP1, AddressP2, IsDefault) VALUES (1,'D','a','b',NULL)")
        self.assertEqual(dbs.get_suppliers_from_db()[0][4], 0)

    def test_get_suppliers_ordered_by_company_name_binary(self):
        for i, name in enumerate(["beta", "Alfa"], start=1):
            self.add_supplier(nip=i, name=name)
        self.assertEqual([s[1] for s in dbs.get_suppliers_from_db()], ["Alfa", "beta"])

    def test_get_suppliers_empty_and_unavailable(self):
        self.assertEqual(dbs.get_suppliers_from_db(), [])
        self.make_unavailable()
        self.assertEqual(dbs.get_suppliers_from_db(), [])
        self.assertEqual(self.popups, [])

    def test_get_suppliers_sql_error_popup_only_when_enabled(self):
        self.tables = ("clients",)
        os.remove(self.db_path)
        self._create_db()
        self.assertEqual(dbs.get_suppliers_from_db(), [])
        self.assertEqual(self.popups, [])
        self.cfg.popups = True
        dbs.get_suppliers_from_db()
        self.assertEqual(len(self.popups), 1)

    def test_get_supplier_by_nip(self):
        self.add_supplier(default=1)
        self.assertEqual(dbs.get_supplier_by_nip("3333333333"), (3333333333, "Dostawca", "ul. B 2", "58-300", 1))
        self.assertIsNone(dbs.get_supplier_by_nip("1"))
        self.make_unavailable()
        self.assertIsNone(dbs.get_supplier_by_nip("3333333333"))

    def test_get_supplier_by_nip_sql_error_popup_is_unconditional(self):
        # LEGACY
        self.tables = ("clients",)
        os.remove(self.db_path)
        self._create_db()
        self.assertIsNone(dbs.get_supplier_by_nip("1"))
        self.assertEqual(len(self.popups), 1)

    def test_get_default_supplier(self):
        self.assertIsNone(dbs.get_default_supplier())
        self.add_supplier(nip=1, name="Zwykły", default=0)
        self.add_supplier(nip=2, name="Domyślny", default=1)
        self.assertEqual(dbs.get_default_supplier(), (2, "Domyślny", "ul. B 2", "58-300", 1))

    def test_get_default_supplier_returns_first_row_when_several_are_default(self):
        # LEGACY: baza nie wymusza jednego domyślnego dostawcy
        self.add_supplier(nip=1, name="Pierwszy", default=1)
        self.add_supplier(nip=2, name="Drugi", default=1)
        self.assertEqual(dbs.get_default_supplier()[1], "Pierwszy")

    def test_get_default_supplier_unavailable(self):
        self.make_unavailable()
        self.assertIsNone(dbs.get_default_supplier())


class SupplierWriteTests(DbTestCase):
    def test_validate_supplier_nip(self):
        msg = "NIP musi składać się z dokładnie 10 cyfr"
        self.assertEqual(dbs.validate_supplier_nip("12"), (False, msg))
        self.assertEqual(dbs.validate_supplier_nip("3333333333"), (True, "NIP jest prawidłowy"))
        self.add_supplier()
        self.assertEqual(dbs.validate_supplier_nip("3333333333"), (False, "Dostawca z tym NIP już istnieje w bazie"))
        self.make_unavailable()
        self.assertEqual(dbs.validate_supplier_nip("3333333333"), (False, "Baza danych jest niedostępna"))

    def test_add_supplier_success_and_default_flag_zero(self):
        self.assertEqual(dbs.add_supplier_to_db("3333333333", "D", "a", "b"),
                         (True, "Dostawca został pomyślnie dodany do bazy"))
        self.assertEqual(self.rows("SELECT Nip, IsDefault FROM Suppliers"), [(3333333333, 0)])

    def test_add_supplier_rejects_duplicate_bad_nip_and_unavailable(self):
        self.add_supplier()
        self.assertEqual(dbs.add_supplier_to_db("3333333333", "D", "a", "b"),
                         (False, "Dostawca z tym NIP już istnieje w bazie"))
        self.assertEqual(dbs.add_supplier_to_db("1", "D", "a", "b"),
                         (False, "NIP musi składać się z dokładnie 10 cyfr"))
        self.make_unavailable()
        self.assertEqual(dbs.add_supplier_to_db("1111111111", "D", "a", "b"),
                         (False, "Baza danych jest niedostępna lub nie istnieje."))

    def test_update_supplier_success_and_missing(self):
        self.add_supplier()
        self.assertEqual(dbs.update_supplier_in_db("3333333333", "Nowy", "ul. N", "11-111"),
                         (True, "Dane dostawcy zostały zaktualizowane"))
        self.assertEqual(self.rows("SELECT CompanyName, AddressP1, AddressP2 FROM Suppliers"), [("Nowy", "ul. N", "11-111")])
        # w odróżnieniu od klientów: brak rekordu daje błąd
        self.assertEqual(dbs.update_supplier_in_db("1", "x", "y", "z"), (False, "Dostawca nie został znaleziony"))

    def test_update_supplier_does_not_change_default_flag(self):
        self.add_supplier(default=1)
        dbs.update_supplier_in_db("3333333333", "Nowy", "a", "b")
        self.assertEqual(self.rows("SELECT IsDefault FROM Suppliers"), [(1,)])

    def test_delete_supplier_success_missing_and_unavailable(self):
        self.add_supplier(default=0)
        self.assertEqual(dbs.delete_supplier_from_db("3333333333"), (True, "Dostawca został usunięty z bazy"))
        self.assertEqual(dbs.delete_supplier_from_db("3333333333"), (False, "Dostawca nie został znaleziony"))
        self.make_unavailable()
        self.assertEqual(dbs.delete_supplier_from_db("3333333333"), (False, "Baza danych jest niedostępna lub nie istnieje."))

    def test_delete_default_supplier_is_blocked(self):
        self.add_supplier(default=1)
        self.assertEqual(dbs.delete_supplier_from_db("3333333333"),
                         (False, "Nie można usunąć domyślnego dostawcy. Najpierw ustaw innego dostawcę jako domyślny."))
        self.assertEqual(self.rows("SELECT COUNT(*) FROM Suppliers"), [(1,)])

    def test_set_default_supplier_switches_the_single_default(self):
        self.add_supplier(nip=1, name="A", default=1)
        self.add_supplier(nip=2, name="B", default=0)
        self.assertEqual(dbs.set_default_supplier("2"), (True, "Dostawca został ustawiony jako domyślny"))
        self.assertEqual(self.rows("SELECT Nip, IsDefault FROM Suppliers ORDER BY Nip"), [(1, 0), (2, 1)])

    def test_set_default_supplier_missing_nip_keeps_previous_default(self):
        # zmiana jest wycofywana (brak commit), więc dotychczasowy domyślny pozostaje
        self.add_supplier(nip=1, name="A", default=1)
        self.assertEqual(dbs.set_default_supplier("999"), (False, "Dostawca nie został znaleziony"))
        self.assertEqual(self.rows("SELECT Nip, IsDefault FROM Suppliers"), [(1, 1)])

    def test_set_default_supplier_unavailable(self):
        self.make_unavailable()
        self.assertEqual(dbs.set_default_supplier("1"), (False, "Baza danych jest niedostępna lub nie istnieje."))


# ======================================================================
# Offers
# ======================================================================
class OfferNumberingTests(DbTestCase):
    def test_next_number_for_year_starts_at_one_and_increments(self):
        self.assertEqual(dbs.get_next_offer_number_for_year(2026), 1)
        self.add_offer(2026, 1)
        self.add_offer(2026, 7)
        self.assertEqual(dbs.get_next_offer_number_for_year(2026), 8)

    def test_next_number_is_independent_per_year(self):
        self.add_offer(2025, 392)
        self.add_offer(2026, 5)
        self.assertEqual(dbs.get_next_offer_number_for_year(2025), 393)
        self.assertEqual(dbs.get_next_offer_number_for_year(2026), 6)
        self.assertEqual(dbs.get_next_offer_number_for_year(2027), 1)

    def test_next_number_does_not_fill_gaps(self):
        self.add_offer(2026, 1)
        self.add_offer(2026, 5)
        self.assertEqual(dbs.get_next_offer_number_for_year(2026), 6)

    def test_next_number_legacy_schema_without_year_column_raises_numbering_error(self):
        # ZMIANA ZATWIERDZONA (etap 1): wcześniej zwracało 1 z popupem; teraz przerywa operację
        self.legacy_offers = True
        os.remove(self.db_path)
        self._create_db()
        with self.assertRaises(NumberingError) as ctx:
            dbs.get_next_offer_number_for_year(2026)
        self.assertIn("Offer yearly numbering error", str(ctx.exception))
        self.assertIn("Missing OfferYearNumber column", str(ctx.exception))
        self.assertEqual(self.popups, [])  # komunikat pokazuje wywołujący (generate_offer_number)

    def test_next_number_unavailable_database_raises_numbering_error(self):
        # ZMIANA ZATWIERDZONA (etap 1): niedostępna baza nie daje numeru 1
        self.make_unavailable()
        with self.assertRaises(NumberingError) as ctx:
            dbs.get_next_offer_number_for_year(2026)
        self.assertIn("Database unavailable", str(ctx.exception))
        self.assertEqual(self.popups, [])
        self.assertFalse(os.path.exists(self.cfg.path))

    def test_next_number_error_is_a_data_access_error_and_plain_exception(self):
        # wywołujący (generate_offer_number / generate_wz) łapią Exception
        self.make_unavailable()
        with self.assertRaises(DataAccessError):
            dbs.get_next_offer_number_for_year(2026)
        self.assertTrue(issubclass(NumberingError, Exception))

    def test_global_next_number_unused_function(self):
        self.assertEqual(dbs.get_next_offer_number(), 1)
        self.add_offer(2025, 392)
        self.add_offer(2026, 5)
        self.assertEqual(dbs.get_next_offer_number(), 393)  # globalny MAX, bez uwzględnienia roku
        self.make_unavailable()
        self.assertEqual(dbs.get_next_offer_number(), 1)


class SaveOfferTests(DbTestCase):
    def test_save_offer_returns_true_and_stores_row(self):
        ctx = {"date": "2026-03-01T10:00:00", "client_name": "Firma A"}
        self.assertIs(dbs.save_offer_to_db(5, "2026/5_OF_2026_ALFA.docx", ctx), True)
        year, order, path, stored = self.rows("SELECT * FROM Offers")[0]
        self.assertEqual((year, order, path), (2026, 5, "2026/5_OF_2026_ALFA.docx"))
        self.assertEqual(json.loads(stored), ctx)

    def test_save_offer_stores_relative_path_for_path_under_offers_root(self):
        dbs.save_offer_to_db(1, f"{self.offers_dir}/2026/1_OF_2026_A.docx", {"date": "2026-01-01"})
        self.assertEqual(self.rows("SELECT OfferFilePath FROM Offers"), [("2026/1_OF_2026_A.docx",)])

    def test_year_comes_from_iso_date_in_context(self):
        dbs.save_offer_to_db(1, "x1.docx", {"date": "2024-12-31T00:00:00"})
        self.assertEqual(self.rows("SELECT OfferYearNumber FROM Offers"), [(2024,)])

    def test_year_comes_from_year_inside_text_date(self):
        dbs.save_offer_to_db(1, "x1.docx", {"date": "4 sierpnia 2025"})
        self.assertEqual(self.rows("SELECT OfferYearNumber FROM Offers"), [(2025,)])

    def test_year_falls_back_to_year_folder_of_absolute_path(self):
        dbs.save_offer_to_db(1, "D:/inne/2025/x.docx", {"client_name": "x"})
        self.assertEqual(self.rows("SELECT OfferYearNumber FROM Offers"), [(2025,)])

    def test_year_falls_back_to_current_year_for_relative_path_and_no_date(self):
        # LEGACY: wzorzec roku wymaga separatora przed rokiem, więc "2025/x.docx" nie jest rozpoznawane
        dbs.save_offer_to_db(1, "2025/x.docx", {"client_name": "x"})
        self.assertEqual(self.rows("SELECT OfferYearNumber FROM Offers"), [(datetime.datetime.now().year,)])

    def test_datetime_object_in_context_date_is_ignored_for_year(self):
        # LEGACY: rok jest wyliczany tylko z tekstowej daty
        dbs.save_offer_to_db(1, "x1.docx", {"date": datetime.datetime(2024, 5, 5)})
        self.assertEqual(self.rows("SELECT OfferYearNumber FROM Offers"), [(datetime.datetime.now().year,)])

    def test_none_and_empty_context_store_null(self):
        dbs.save_offer_to_db(1, "2026/a.docx", None)
        dbs.save_offer_to_db(2, "2026/b.docx", {})  # LEGACY: pusty słownik traktowany jak brak kontekstu
        self.assertEqual(self.rows("SELECT OfferContext FROM Offers"), [(None,), (None,)])

    def test_context_is_stored_as_json_without_ascii_escaping_and_default_str(self):
        ctx = {"date": "2026-01-01", "client_name": "Żółć", "when": datetime.datetime(2026, 1, 2, 3, 4, 5)}
        dbs.save_offer_to_db(1, "2026/a.docx", ctx)
        raw = self.rows("SELECT OfferContext FROM Offers")[0][0]
        self.assertIn("Żółć", raw)
        self.assertEqual(json.loads(raw)["when"], "2026-01-02 03:04:05")

    def test_word_xml_tags_are_stripped_from_client_and_supplier_names_only(self):
        ctx = {"date": "2026-01-01", "client_name": "<w:r><w:t>Firma</w:t></w:r>",
               "supplier_name": "<w:r>Dost</w:r>", "uwagi": "<w:r>zostaje</w:r>"}
        dbs.save_offer_to_db(1, "2026/a.docx", ctx)
        stored = json.loads(self.rows("SELECT OfferContext FROM Offers")[0][0])
        self.assertEqual(stored["client_name"], "Firma")
        self.assertEqual(stored["supplier_name"], "Dost")
        self.assertEqual(stored["uwagi"], "<w:r>zostaje</w:r>")

    def test_save_does_not_mutate_callers_context(self):
        ctx = {"date": "2026-01-01", "client_name": "<w:r>x</w:r>"}
        dbs.save_offer_to_db(1, "2026/a.docx", ctx)
        self.assertEqual(ctx["client_name"], "<w:r>x</w:r>")

    def test_duplicate_year_and_order_returns_false_with_unconditional_popup(self):
        dbs.save_offer_to_db(1, "2026/a.docx", {"date": "2026-01-01"})
        self.assertIs(dbs.save_offer_to_db(1, "2026/b.docx", {"date": "2026-01-01"}), False)
        self.assertEqual(len(self.popups), 1)
        self.assertEqual(self.popups[0][:2], ("error", "Database Error"))
        self.assertIn("uniqueness violation", self.popups[0][2])

    def test_duplicate_file_path_is_reported_with_the_same_year_order_message(self):
        # LEGACY: komunikat mówi o parze (rok, numer), także gdy zduplikowana jest ścieżka pliku
        dbs.save_offer_to_db(1, "2026/a.docx", {"date": "2026-01-01"})
        self.assertIs(dbs.save_offer_to_db(2, "2026/a.docx", {"date": "2026-01-01"}), False)
        self.assertIn("(OfferYearNumber, OfferOrderNumber) uniqueness violation", self.popups[-1][2])

    def test_save_offer_with_missing_database_file_returns_false_with_popup(self):
        self.make_unavailable()
        self.assertIs(dbs.save_offer_to_db(1, "2026/a.docx", {"date": "2026-01-01"}), False)
        self.assertIn("Error saving offer to database", self.popups[0][2])
        self.assertFalse(os.path.exists(self.cfg.path))


class OfferContextTests(DbTestCase):
    def test_get_context_by_relative_and_full_path(self):
        self.add_offer(path="2026/1_OF_2026_A.docx", ctx=json.dumps({"k": "v"}))
        self.assertEqual(dbs.get_offer_context_from_db("2026/1_OF_2026_A.docx"), {"k": "v"})
        self.assertEqual(dbs.get_offer_context_from_db(f"{self.offers_dir}/2026/1_OF_2026_A.docx"), {"k": "v"})

    def test_get_context_missing_null_or_unavailable_returns_none(self):
        self.add_offer(path="2026/null.docx", ctx=None)
        self.assertIsNone(dbs.get_offer_context_from_db("2026/nie_ma.docx"))
        self.assertIsNone(dbs.get_offer_context_from_db("2026/null.docx"))
        self.make_unavailable()
        self.assertIsNone(dbs.get_offer_context_from_db("2026/null.docx"))

    def test_get_context_invalid_json_returns_none_with_data_error_popup(self):
        self.add_offer(path="2026/bad.docx", ctx="{nie json")
        self.assertIsNone(dbs.get_offer_context_from_db("2026/bad.docx"))
        self.assertEqual(self.popups[0][:2], ("error", "Data Error"))

    def test_update_context_overwrites_and_returns_true(self):
        self.add_offer(path="2026/a.docx", ctx=json.dumps({"old": 1}))
        self.assertIs(dbs.update_offer_context_in_db("2026/a.docx", {"new": "Żółć"}), True)
        raw = self.rows("SELECT OfferContext FROM Offers")[0][0]
        self.assertEqual(json.loads(raw), {"new": "Żółć"})
        self.assertIn("Żółć", raw)

    def test_update_context_for_missing_offer_still_returns_true(self):
        # LEGACY: brak sprawdzenia rowcount
        self.assertIs(dbs.update_offer_context_in_db("2026/nie_ma.docx", {"a": 1}), True)
        self.assertEqual(self.rows("SELECT COUNT(*) FROM Offers"), [(0,)])

    def test_update_context_does_not_strip_xml_tags(self):
        # LEGACY: w odróżnieniu od save_offer_to_db aktualizacja zapisuje tagi XML bez czyszczenia
        self.add_offer(path="2026/a.docx", ctx="{}")
        dbs.update_offer_context_in_db("2026/a.docx", {"client_name": "<w:r>X</w:r>"})
        self.assertIn("<w:r>", self.rows("SELECT OfferContext FROM Offers")[0][0])

    def test_update_context_serializes_non_json_values_with_str(self):
        self.add_offer(path="2026/a.docx", ctx="{}")
        dbs.update_offer_context_in_db("2026/a.docx", {"d": datetime.date(2026, 1, 2)})
        self.assertEqual(json.loads(self.rows("SELECT OfferContext FROM Offers")[0][0]), {"d": "2026-01-02"})

    def test_update_context_unavailable_returns_false(self):
        self.make_unavailable()
        self.assertIs(dbs.update_offer_context_in_db("2026/a.docx", {}), False)

    def test_update_context_sql_error_returns_false_and_popup_only_when_enabled(self):
        self.tables = ("clients",)
        os.remove(self.db_path)
        self._create_db()
        self.assertIs(dbs.update_offer_context_in_db("2026/a.docx", {}), False)
        self.assertEqual(self.popups, [])
        self.cfg.popups = True
        dbs.update_offer_context_in_db("2026/a.docx", {})
        self.assertEqual(len(self.popups), 1)


class OfferQueryAndDeleteTests(DbTestCase):
    def test_delete_offer_by_relative_and_full_path(self):
        self.add_offer(2026, 1, "2026/1_OF_2026_A.docx")
        self.add_offer(2026, 2, "2026/2_OF_2026_A.docx")
        self.assertEqual(dbs.delete_offer_from_db("2026/1_OF_2026_A.docx"), (True, "Oferta została usunięta z bazy danych"))
        self.assertEqual(dbs.delete_offer_from_db(f"{self.offers_dir}/2026/2_OF_2026_A.docx")[0], True)
        self.assertEqual(self.rows("SELECT COUNT(*) FROM Offers"), [(0,)])

    def test_delete_offer_missing_and_unavailable(self):
        self.assertEqual(dbs.delete_offer_from_db("2026/nie_ma.docx"), (False, "Oferta nie została znaleziona w bazie danych"))
        self.make_unavailable()
        self.assertEqual(dbs.delete_offer_from_db("2026/a.docx"), (False, "Baza danych jest niedostępna lub nie istnieje."))

    def test_find_offer_by_filename_returns_order_number_and_path(self):
        self.add_offer(2026, 4, "2026/4_OF_2026_ALFA.docx")
        self.assertEqual(dbs.find_offer_by_filename("4_OF_2026_ALFA.docx"), (4, "2026/4_OF_2026_ALFA.docx"))
        self.assertIsNone(dbs.find_offer_by_filename("nie_ma.docx"))

    def test_find_offer_by_filename_is_a_case_insensitive_suffix_match_returning_first_row(self):
        # LEGACY: "A.docx" pasuje także do "…_BA.docx"; zwracany jest pierwszy znaleziony wiersz
        self.add_offer(2026, 1, "2026/1_OF_2026_A.docx")
        self.add_offer(2026, 2, "2026/2_OF_2026_BA.docx")
        self.assertEqual(dbs.find_offer_by_filename("a.docx"), (1, "2026/1_OF_2026_A.docx"))

    def test_find_offer_by_filename_unavailable(self):
        self.make_unavailable()
        self.assertIsNone(dbs.find_offer_by_filename("x.docx"))

    def test_get_all_offer_paths_are_sorted_by_order_number_desc_ignoring_year(self):
        # LEGACY: sortowanie tylko po numerze, więc rok 2025 (392) wyprzedza rok 2026 (300 i 5)
        self.add_offer(2025, 392, "2025/392_OF_2025_A.docx")
        self.add_offer(2026, 5, "2026/5_OF_2026_A.docx")
        self.add_offer(2026, 300, "2026/300_OF_2026_A.docx")
        self.assertEqual(dbs.get_all_offer_file_paths(),
                         ["2025/392_OF_2025_A.docx", "2026/300_OF_2026_A.docx", "2026/5_OF_2026_A.docx"])

    def test_get_all_offer_paths_empty_and_unavailable(self):
        self.assertEqual(dbs.get_all_offer_file_paths(), [])
        self.make_unavailable()
        self.assertEqual(dbs.get_all_offer_file_paths(), [])


# ======================================================================
# Wuzetkas
# ======================================================================
class WzNumberingTests(DbTestCase):
    def test_next_number_per_year(self):
        self.assertEqual(dbs.get_next_wz_number(2026), 1)
        self.add_wz(2025, 181)
        self.add_wz(2026, 3)
        self.assertEqual(dbs.get_next_wz_number(2025), 182)
        self.assertEqual(dbs.get_next_wz_number(2026), 4)
        self.assertEqual(dbs.get_next_wz_number(2027), 1)

    def test_next_number_legacy_schema_raises_numbering_error(self):
        # ZMIANA ZATWIERDZONA (etap 1): wcześniej zwracało 1 z popupem; teraz przerywa operację
        self.legacy_wz = True
        os.remove(self.db_path)
        self._create_db()
        with self.assertRaises(NumberingError) as ctx:
            dbs.get_next_wz_number(2026)
        self.assertIn("WZ yearly numbering error", str(ctx.exception))
        self.assertIn("Missing WzYearNumber column", str(ctx.exception))
        self.assertEqual(self.popups, [])

    def test_next_number_unavailable_raises_numbering_error(self):
        # ZMIANA ZATWIERDZONA (etap 1): wcześniej cicho zwracało 1; teraz przerywa operację
        self.make_unavailable()
        with self.assertRaises(NumberingError) as ctx:
            dbs.get_next_wz_number(2026)
        self.assertIn("Database unavailable", str(ctx.exception))
        self.assertEqual(self.popups, [])
        self.assertFalse(os.path.exists(self.cfg.path))


class SaveWzTests(DbTestCase):
    def test_save_wz_returns_tuple_and_stores_row(self):
        ctx = {"date": "04 08 2025", "client_name": "Firma"}
        self.assertEqual(dbs.save_wz_to_db(7, "2025/WZ_7_2025_ALFA.docx", ctx), (True, "WZ zostało zapisane do bazy danych"))
        year, order, path, stored = self.rows("SELECT * FROM Wuzetkas")[0]
        self.assertEqual((year, order, path), (2025, 7, "2025/WZ_7_2025_ALFA.docx"))
        self.assertEqual(json.loads(stored), ctx)

    def test_year_from_context_date_uses_first_year_like_token(self):
        dbs.save_wz_to_db(1, "2026/WZ_1.docx", {"date": "4 sierpnia 2024"})
        self.assertEqual(self.rows("SELECT WzYearNumber FROM Wuzetkas"), [(2024,)])

    def test_iso_context_date_is_ignored_for_year(self):
        # LEGACY: warunek d[-4:].isdigit() odrzuca format ISO (kończy się na "-DD"), rok bierze się ze ścieżki
        dbs.save_wz_to_db(1, "D:/x/2023/WZ_1.docx", {"date": "2025-08-04"})
        self.assertEqual(self.rows("SELECT WzYearNumber FROM Wuzetkas"), [(2023,)])

    def test_year_from_absolute_path_then_current_year(self):
        dbs.save_wz_to_db(1, "D:/x/2022/WZ_1.docx", {"client_name": "x"})
        dbs.save_wz_to_db(2, "WZ_2.docx", {"client_name": "x"})
        years = [r[0] for r in self.rows("SELECT WzYearNumber FROM Wuzetkas ORDER BY WzOrderNumber")]
        self.assertEqual(years, [2022, datetime.datetime.now().year])

    def test_path_is_forced_to_year_slash_filename(self):
        dbs.save_wz_to_db(1, "WZ_1_2026_A.docx", {"date": "04 08 2026"})
        dbs.save_wz_to_db(2, f"{self.wz_dir}/2026/WZ_2_2026_A.docx", {"date": "04 08 2026"})
        self.assertEqual([r[0] for r in self.rows("SELECT WzFilePath FROM Wuzetkas ORDER BY WzOrderNumber")],
                         ["2026/WZ_1_2026_A.docx", "2026/WZ_2_2026_A.docx"])

    def test_xml_tags_stripped_from_names_and_not_serializable_value_raises_type_error(self):
        dbs.save_wz_to_db(1, "2026/a.docx", {"date": "04 08 2026", "client_name": "<w:r>Firma</w:r>"})
        self.assertEqual(json.loads(self.rows("SELECT WzContext FROM Wuzetkas")[0][0])["client_name"], "Firma")
        # LEGACY: w odróżnieniu od ofert brak default=str, a łapany jest tylko sqlite3.Error
        with self.assertRaises(TypeError):
            dbs.save_wz_to_db(2, "2026/b.docx", {"date": "04 08 2026", "when": datetime.datetime(2026, 1, 1)})

    def test_none_context_stores_null(self):
        dbs.save_wz_to_db(1, "2026/a.docx", None)
        self.assertEqual(self.rows("SELECT WzContext FROM Wuzetkas"), [(None,)])

    def test_duplicates_return_error_tuple_without_popup(self):
        dbs.save_wz_to_db(1, "2026/a.docx", {"date": "04 08 2026"})
        ok, msg = dbs.save_wz_to_db(1, "2026/b.docx", {"date": "04 08 2026"})
        self.assertFalse(ok)
        self.assertTrue(msg.startswith("Błąd podczas zapisywania WZ do bazy:"), msg)
        self.assertEqual(self.popups, [])
        ok2, _ = dbs.save_wz_to_db(2, "2026/a.docx", {"date": "04 08 2026"})
        self.assertFalse(ok2)

    def test_unavailable_database(self):
        self.make_unavailable()
        self.assertEqual(dbs.save_wz_to_db(1, "2026/a.docx", {}), (False, "Baza danych jest niedostępna lub nie istnieje."))

    def test_legacy_schema_without_year_column_inserts_without_year(self):
        self.legacy_wz = True
        os.remove(self.db_path)
        self._create_db()
        self.assertTrue(dbs.save_wz_to_db(1, "2026/a.docx", {"date": "04 08 2026"})[0])
        self.assertEqual(self.rows("SELECT WzOrderNumber, WzFilePath FROM Wuzetkas"), [(1, "2026/a.docx")])


class WzContextTests(DbTestCase):
    def test_get_and_update_context_roundtrip(self):
        self.add_wz(path="2026/a.docx", ctx=json.dumps({"k": 1}))
        self.assertEqual(dbs.get_wz_context_from_db("2026/a.docx"), {"k": 1})
        self.assertEqual(dbs.get_wz_context_from_db(f"{self.wz_dir}/2026/a.docx"), {"k": 1})
        self.assertIs(dbs.update_wz_context_in_db("2026/a.docx", {"k": "Żółć"}), True)
        self.assertEqual(dbs.get_wz_context_from_db("2026/a.docx"), {"k": "Żółć"})

    def test_get_context_missing_null_and_unavailable(self):
        self.add_wz(path="2026/null.docx", ctx=None)
        self.assertIsNone(dbs.get_wz_context_from_db("2026/nie_ma.docx"))
        self.assertIsNone(dbs.get_wz_context_from_db("2026/null.docx"))
        self.make_unavailable()
        self.assertIsNone(dbs.get_wz_context_from_db("2026/null.docx"))

    def test_get_context_invalid_json_returns_none_with_popup(self):
        self.add_wz(path="2026/bad.docx", ctx="{zle")
        self.assertIsNone(dbs.get_wz_context_from_db("2026/bad.docx"))
        self.assertEqual(self.popups[0][:2], ("error", "Data Error"))

    def test_get_context_sql_error_popup_is_unconditional(self):
        # LEGACY
        self.tables = ("clients",)
        os.remove(self.db_path)
        self._create_db()
        self.assertIsNone(dbs.get_wz_context_from_db("2026/a.docx"))
        self.assertEqual(self.popups[0][:2], ("error", "Database Error"))

    def test_update_context_for_missing_wz_still_returns_true(self):
        # LEGACY
        self.assertIs(dbs.update_wz_context_in_db("2026/nie_ma.docx", {"a": 1}), True)

    def test_update_context_unavailable_false_and_sql_error_popup_unconditional(self):
        self.make_unavailable()
        self.assertIs(dbs.update_wz_context_in_db("2026/a.docx", {}), False)
        self.cfg.path = self.db_path
        self.tables = ("clients",)
        os.remove(self.db_path)
        self._create_db()
        self.assertIs(dbs.update_wz_context_in_db("2026/a.docx", {}), False)
        self.assertEqual(self.popups[0][:2], ("error", "Database Error"))


class GetAllWzTests(DbTestCase):
    def test_tuple_shape_formatting_and_values(self):
        ctx = json.dumps({"client_name": "Firma A", "date": "4 sierpnia 2025"})
        self.add_wz(2025, 102, "2025/WZ_102_2025_ALFA.docx", ctx)
        rows = dbs.get_all_wz()
        self.assertEqual(len(rows), 1)
        wz_id, number, date, client, status, full_path = rows[0]
        self.assertEqual(wz_id, 102)
        self.assertEqual(number, f"WZ_102_{datetime.datetime.now().year}")
        self.assertEqual((date, client, status), ("4 sierpnia 2025", "Firma A", "Utworzone"))
        self.assertEqual(full_path, os.path.join(self.wz_dir, "2025/WZ_102_2025_ALFA.docx"))

    def test_displayed_number_uses_current_year_not_the_year_of_the_document(self):
        # LEGACY: WZ z 2025 jest wyświetlane z bieżącym rokiem
        self.add_wz(2025, 5, "2025/WZ_5_2025_A.docx", "{}")
        self.assertEqual(dbs.get_all_wz()[0][1], f"WZ_5_{datetime.datetime.now().year}")

    def test_missing_invalid_or_partial_context_gives_na(self):
        self.add_wz(2026, 1, "2026/a.docx", None)
        self.add_wz(2026, 2, "2026/b.docx", "{nie json")
        self.add_wz(2026, 3, "2026/c.docx", json.dumps({"date": "1 stycznia 2026"}))
        by_id = {r[0]: r for r in dbs.get_all_wz()}
        self.assertEqual(by_id[1][2:5], ("N/A", "N/A", "Utworzone"))
        self.assertEqual(by_id[2][2:4], ("N/A", "N/A"))
        self.assertEqual(by_id[3][2:4], ("1 stycznia 2026", "N/A"))

    def test_ordered_by_order_number_desc_across_years_and_id_is_not_unique(self):
        # LEGACY: "ID" to numer porządkowy, powtarza się między latami
        self.add_wz(2025, 102, "2025/WZ_102_2025_A.docx", "{}")
        self.add_wz(2026, 102, "2026/WZ_102_2026_A.docx", "{}")
        self.add_wz(2026, 5, "2026/WZ_5_2026_A.docx", "{}")
        rows = dbs.get_all_wz()
        self.assertEqual([r[0] for r in rows], [102, 102, 5])
        self.assertEqual(sorted(r[5] for r in rows[:2]),
                         sorted([os.path.join(self.wz_dir, "2025/WZ_102_2025_A.docx"),
                                 os.path.join(self.wz_dir, "2026/WZ_102_2026_A.docx")]))

    def test_empty_unavailable_and_sql_error(self):
        self.assertEqual(dbs.get_all_wz(), [])
        self.make_unavailable()
        self.assertEqual(dbs.get_all_wz(), [])
        self.assertEqual(self.popups, [])
        self.cfg.path = self.db_path
        self.tables = ("clients",)
        os.remove(self.db_path)
        self._create_db()
        self.assertEqual(dbs.get_all_wz(), [])
        self.assertEqual(self.popups[0][:2], ("error", "Database Error"))  # bezwarunkowe okienko


class WzDeleteTests(DbTestCase):
    def test_delete_by_file_path_deletes_exactly_one_row(self):
        self.add_wz(2025, 102, "2025/WZ_102_2025_A.docx")
        self.add_wz(2026, 102, "2026/WZ_102_2026_A.docx")
        self.assertEqual(dbs.delete_wz_by_file_path(f"{self.wz_dir}/2026/WZ_102_2026_A.docx"),
                         (True, "WZ zostało usunięte z bazy danych"))
        self.assertEqual(self.rows("SELECT WzFilePath FROM Wuzetkas"), [("2025/WZ_102_2025_A.docx",)])

    def test_delete_by_file_path_missing_and_unavailable(self):
        self.assertEqual(dbs.delete_wz_by_file_path("2026/nie_ma.docx"), (False, "WZ nie zostało znalezione w bazie (po ścieżce)"))
        self.make_unavailable()
        self.assertEqual(dbs.delete_wz_by_file_path("2026/a.docx"), (False, "Baza danych jest niedostępna lub nie istnieje."))

    def test_delete_by_order_number_removes_rows_from_all_years(self):
        # LEGACY (funkcja nieużywana przez UI): usuwa WZ o tym numerze z KAŻDEGO roku
        self.add_wz(2025, 102, "2025/WZ_102_2025_A.docx")
        self.add_wz(2026, 102, "2026/WZ_102_2026_A.docx")
        self.add_wz(2026, 5, "2026/WZ_5_2026_A.docx")
        self.assertEqual(dbs.delete_wz(102), (True, "WZ zostało usunięte z bazy danych"))
        self.assertEqual(self.rows("SELECT WzOrderNumber FROM Wuzetkas"), [(5,)])

    def test_delete_by_order_number_missing_and_unavailable(self):
        self.assertEqual(dbs.delete_wz(999), (False, "WZ nie zostało znalezione w bazie danych"))
        self.make_unavailable()
        self.assertEqual(dbs.delete_wz(1), (False, "Baza danych jest niedostępna lub nie istnieje."))

    def test_get_all_wz_file_paths_sorted_desc_and_creates_missing_database(self):
        # LEGACY (funkcja nieużywana): brak sprawdzenia dostępności - tworzy pusty plik bazy i zwraca []
        self.add_wz(2025, 102, "2025/a.docx")
        self.add_wz(2026, 5, "2026/b.docx")
        self.assertEqual(dbs.get_all_wz_file_paths(), ["2025/a.docx", "2026/b.docx"])
        self.make_unavailable()
        self.assertEqual(dbs.get_all_wz_file_paths(), [])
        self.assertTrue(os.path.exists(self.cfg.path))


class DatabaseServiceClassTests(DbTestCase):
    def test_get_all_wz_delegates_to_function(self):
        self.add_wz(2026, 1, "2026/a.docx", json.dumps({"client_name": "K"}))
        self.assertEqual(dbs.DatabaseService().get_all_wz(), dbs.get_all_wz())

    def test_delete_by_file_path_returns_true_or_raises_generic_exception(self):
        self.add_wz(2026, 1, "2026/a.docx")
        service = dbs.DatabaseService()
        self.assertIs(service.delete_wz_by_file_path("2026/a.docx"), True)
        with self.assertRaises(Exception) as ctx:
            service.delete_wz_by_file_path("2026/a.docx")
        self.assertEqual(str(ctx.exception), "WZ nie zostało znalezione w bazie (po ścieżce)")

    def test_delete_wz_returns_true_or_raises_generic_exception(self):
        self.add_wz(2026, 7, "2026/a.docx")
        service = dbs.DatabaseService()
        self.assertIs(service.delete_wz(7), True)
        with self.assertRaises(Exception) as ctx:
            service.delete_wz(7)
        self.assertEqual(str(ctx.exception), "WZ nie zostało znalezione w bazie danych")

    def test_db_path_is_captured_at_construction(self):
        service = dbs.DatabaseService()
        self.assertEqual(service.db_path, self.db_path)


# ======================================================================
# Zachowania przekrojowe i zabezpieczenia testów
# ======================================================================
class CrossCuttingTests(DbTestCase):
    def test_connections_leave_no_journal_files_and_do_not_lock_the_database(self):
        self.add_client()
        dbs.add_client_to_db("1111111111", "F", "a", "b", "BETA")
        dbs.get_clients_from_db()
        dbs.delete_client_from_db("1111111111")
        self.assertEqual(sorted(os.listdir(self.tmp.name)), ["test.db"])
        self.run_sql("INSERT INTO Suppliers (Nip, CompanyName, AddressP1, AddressP2) VALUES (1,'D','a','b')")

    def test_error_conventions_summary(self):
        """Konwencje zwrotów przy niedostępnej bazie: lista -> [], pojedynczy odczyt -> None,
        zapis -> (False, komunikat) albo False (konteksty/oferty); numeracja roczna -> NumberingError."""
        self.make_unavailable()
        self.assertEqual(dbs.get_clients_from_db(), [])
        self.assertIsNone(dbs.get_client_by_nip("1"))
        self.assertEqual(dbs.add_client_to_db("1234563218", "F", "a", "b", "A")[0], False)
        self.assertIs(dbs.update_offer_context_in_db("a", {}), False)
        with self.assertRaises(NumberingError):  # ZMIANA ZATWIERDZONA (etap 1): wcześniej zwracało 1
            dbs.get_next_wz_number(2026)

    def test_all_functions_in_this_module_use_the_test_database_only(self):
        self.assertEqual(dbs.get_database_path(), self.db_path)
        self.assertNotEqual(os.path.normcase(os.path.abspath(self.db_path)),
                            os.path.normcase(os.path.abspath(REAL_DB_PATH or "")))


class RealDatabaseIsUntouchedTests(unittest.TestCase):
    def test_real_user_database_fingerprint_is_unchanged_by_these_tests(self):
        # uruchamia się na końcu (kolejność alfabetyczna klas) - zabezpieczenie przed pomyłką w konfiguracji testów
        self.assertEqual(_fingerprint(REAL_DB_PATH), _REAL_DB_BEFORE)


def tearDownModule():
    assert _fingerprint(REAL_DB_PATH) == _REAL_DB_BEFORE, "prawdziwa baza użytkownika została zmieniona!"


if __name__ == "__main__":
    unittest.main()
