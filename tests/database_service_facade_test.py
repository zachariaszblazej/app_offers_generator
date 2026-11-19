"""Testy fasady database_service: delegowanie do backendu, zachowanie publicznego API, brak SQL w fasadzie.

Uruchomienie: python -m unittest tests.database_service_facade_test -v
Wszystkie testy działają na atrapach lub tymczasowych bazach SQLite, bez sieci i bez prawdziwej bazy użytkownika.
"""
import datetime
import inspect
import os
import sys
import unittest
from types import SimpleNamespace
from unittest import mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import src.data.backends.sqlite_backend as sqlite_backend_module  # noqa: E402
import src.data.database_service as dbs  # noqa: E402
import tests.database_service_characterization_test as base  # noqa: E402  (moduł, nie klasy - bez duplikowania testów)
from src.data.backends import BackendContext, DataBackend, SqliteBackend  # noqa: E402
from src.data.errors import NumberingError  # noqa: E402

SENTINEL = object()

# (funkcja fasady, args, kwargs, metoda backendu, oczekiwane argumenty wywołania backendu)
DELEGATION_TABLE = [
    ("is_database_available", (), {}, "is_available", ()),
    ("get_clients_from_db", (), {}, "get_clients", (False,)),
    ("get_clients_from_db", (), {"include_extended": True}, "get_clients", (True,)),
    ("get_client_by_nip", ("1",), {}, "get_client_by_nip", ("1",)),
    ("validate_nip", ("1",), {}, "validate_nip", ("1",)),
    ("validate_alias", ("A",), {}, "validate_alias", ("A",)),
    ("add_client_to_db", ("1", "F", "a", "b", "A"), {}, "add_client", ("1", "F", "a", "b", "A")),
    ("update_client_in_db", ("1", "F", "a", "b", "A"), {}, "update_client", ("1", "F", "a", "b", "A")),
    ("set_client_extended_fields", ("1", "x"), {}, "set_client_extended_fields", ("1", "x", None, None, None, None, None)),
    ("set_client_extended_fields", ("1",), {"cena": "c"}, "set_client_extended_fields", ("1", None, None, None, None, None, "c")),
    ("delete_client_from_db", ("1",), {}, "delete_client", ("1",)),
    ("get_suppliers_from_db", (), {}, "get_suppliers", ()),
    ("get_supplier_by_nip", ("1",), {}, "get_supplier_by_nip", ("1",)),
    ("get_default_supplier", (), {}, "get_default_supplier", ()),
    ("validate_supplier_nip", ("1",), {}, "validate_supplier_nip", ("1",)),
    ("add_supplier_to_db", ("1", "D", "a", "b"), {}, "add_supplier", ("1", "D", "a", "b")),
    ("update_supplier_in_db", ("1", "D", "a", "b"), {}, "update_supplier", ("1", "D", "a", "b")),
    ("delete_supplier_from_db", ("1",), {}, "delete_supplier", ("1",)),
    ("set_default_supplier", ("1",), {}, "set_default_supplier", ("1",)),
    ("get_next_offer_number", (), {}, "get_next_offer_number", ()),
    ("get_next_offer_number_for_year", (2026,), {}, "get_next_offer_number_for_year", (2026,)),
    ("save_offer_to_db", (1, "p"), {}, "save_offer", (1, "p", None)),
    ("save_offer_to_db", (1, "p", {"k": 1}), {}, "save_offer", (1, "p", {"k": 1})),
    ("get_offer_context_from_db", ("p",), {}, "get_offer_context", ("p",)),
    ("update_offer_context_in_db", ("p", {"k": 1}), {}, "update_offer_context", ("p", {"k": 1})),
    ("delete_offer_from_db", ("p",), {}, "delete_offer", ("p",)),
    ("find_offer_by_filename", ("f",), {}, "find_offer_by_filename", ("f",)),
    ("get_all_offer_file_paths", (), {}, "get_all_offer_file_paths", ()),
    ("get_next_wz_number", (2026,), {}, "get_next_wz_number", (2026,)),
    ("save_wz_to_db", (1, "p"), {}, "save_wz", (1, "p", None)),
    ("save_wz_to_db", (1, "p", {"k": 1}), {}, "save_wz", (1, "p", {"k": 1})),
    ("get_wz_context_from_db", ("p",), {}, "get_wz_context", ("p",)),
    ("update_wz_context_in_db", ("p", {"k": 1}), {}, "update_wz_context", ("p", {"k": 1})),
    ("get_all_wz", (), {}, "get_all_wz", ()),
    ("delete_wz", (1,), {}, "delete_wz", (1,)),
    ("delete_wz_by_file_path", ("p",), {}, "delete_wz_by_file_path", ("p",)),
    ("get_all_wz_file_paths", (), {}, "get_all_wz_file_paths", ()),
]

# Sygnatury publicznych funkcji sprzed refaktoryzacji (git eae8c8e) - API nie może się zmienić.
EXPECTED_SIGNATURES = {
    "add_client_to_db": "(nip, company_name, address_p1, address_p2, alias)",
    "add_supplier_to_db": "(nip, company_name, address_p1, address_p2)",
    "build_full_offer_path": "(rel_path: str) -> str",
    "build_full_wz_path": "(rel_path: str) -> str",
    "delete_client_from_db": "(nip)",
    "delete_offer_from_db": "(offer_file_path)",
    "delete_supplier_from_db": "(nip)",
    "delete_wz": "(wz_id)",
    "delete_wz_by_file_path": "(wz_file_path: str)",
    "find_offer_by_filename": "(filename)",
    "get_all_offer_file_paths": "()",
    "get_all_wz": "()",
    "get_all_wz_file_paths": "()",
    "get_client_by_nip": "(nip)",
    "get_clients_from_db": "(include_extended: bool = False)",
    "get_database_path": "()",
    "get_default_supplier": "()",
    "get_next_offer_number": "()",
    "get_next_offer_number_for_year": "(year: int)",
    "get_next_wz_number": "(year: int)",
    "get_offer_context_from_db": "(offer_file_path)",
    "get_supplier_by_nip": "(nip)",
    "get_suppliers_from_db": "()",
    "get_wz_context_from_db": "(wz_file_path)",
    "is_database_available": "() -> bool",
    "normalize_offer_db_path": "(path: str) -> str",
    "normalize_wz_db_path": "(path: str) -> str",
    "save_offer_to_db": "(offer_order_number, offer_file_path, offer_context=None)",
    "save_wz_to_db": "(wz_order_number, wz_file_path, wz_context=None)",
    "set_client_extended_fields": "(nip, termin_realizacji=None, termin_platnosci=None, warunki_dostawy=None, waznosc_oferty=None, gwarancja=None, cena=None)",
    "set_default_supplier": "(nip)",
    "update_client_in_db": "(nip, company_name, address_p1, address_p2, alias)",
    "update_offer_context_in_db": "(offer_file_path, offer_context)",
    "update_supplier_in_db": "(nip, company_name, address_p1, address_p2)",
    "update_wz_context_in_db": "(wz_file_path, wz_context)",
    "validate_alias": "(alias)",
    "validate_nip": "(nip)",
    "validate_supplier_nip": "(nip)",
}


class FacadeDelegationTests(unittest.TestCase):
    def test_every_facade_function_delegates_to_the_matching_backend_method(self):
        for name, args, kwargs, method, expected in DELEGATION_TABLE:
            with self.subTest(function=name, args=args, kwargs=kwargs):
                backend = mock.MagicMock(spec=DataBackend)
                getattr(backend, method).return_value = SENTINEL
                with mock.patch.object(dbs, "_backend", backend):
                    result = getattr(dbs, name)(*args, **kwargs)
                self.assertIs(result, SENTINEL, "fasada musi zwracać wynik backendu bez zmian")
                getattr(backend, method).assert_called_once_with(*expected)
                for other in DataBackend.__abstractmethods__ - {method}:
                    getattr(backend, other).assert_not_called()

    def test_delegation_table_covers_every_backend_method(self):
        self.assertEqual({row[3] for row in DELEGATION_TABLE}, set(DataBackend.__abstractmethods__))

    def test_backend_exceptions_pass_through_the_facade(self):
        backend = mock.MagicMock(spec=DataBackend)
        backend.get_next_wz_number.side_effect = NumberingError("x")
        with mock.patch.object(dbs, "_backend", backend):
            with self.assertRaises(NumberingError):
                dbs.get_next_wz_number(2026)

    def test_database_service_class_uses_facade_functions(self):
        backend = mock.MagicMock(spec=DataBackend)
        backend.get_all_wz.return_value = [("x",)]
        backend.delete_wz_by_file_path.return_value = (True, "ok")
        with mock.patch.object(dbs, "_backend", backend), mock.patch.object(dbs, "get_database_path", lambda: "x.db"):
            service = dbs.DatabaseService()
            self.assertEqual(service.get_all_wz(), [("x",)])
            self.assertIs(service.delete_wz_by_file_path("p"), True)
        backend.get_all_wz.assert_called_once_with()
        backend.delete_wz_by_file_path.assert_called_once_with("p")


class PublicApiTests(unittest.TestCase):
    def test_public_functions_and_signatures_are_unchanged(self):
        public = {n: f for n, f in vars(dbs).items()
                  if inspect.isfunction(f) and not n.startswith("_") and f.__module__ == dbs.__name__}
        actual = {n: str(inspect.signature(f)) for n, f in public.items() if n != "get_backend"}
        self.assertEqual(actual, EXPECTED_SIGNATURES)

    def test_expected_public_names_used_by_the_application_are_still_importable(self):
        for name in ("DatabaseService", "get_backend", "_should_show_db_error_popup"):
            self.assertTrue(callable(getattr(dbs, name)), name)
        # główna aplikacja ustawia ten przełącznik po starcie UI (DB_POPUPS_ENABLED) - czytany z globals fasady
        with mock.patch.object(dbs, "DB_POPUPS_ENABLED", True, create=True):
            self.assertIn("DB_POPUPS_ENABLED", vars(dbs))

    def test_database_service_class_methods_unchanged(self):
        methods = sorted(m for m in vars(dbs.DatabaseService) if not m.startswith("__"))
        self.assertEqual(methods, ["delete_wz", "delete_wz_by_file_path", "get_all_wz"])


class NipTypeContractTests(base.DbTestCase):
    def test_nip_stays_int_in_public_api_shapes(self):
        # kontrakt: NIP w krotkach publicznego API to int (konwersja do tekstu to sprawa przyszłego backendu SharePoint)
        self.add_client(nip=1234563218)
        self.add_supplier(nip=3333333333, default=1)
        self.assertIsInstance(dbs.get_clients_from_db()[0][0], int)
        self.assertIsInstance(dbs.get_client_by_nip("1234563218")[0], int)
        self.assertIsInstance(dbs.get_suppliers_from_db()[0][0], int)
        self.assertIsInstance(dbs.get_supplier_by_nip("3333333333")[0], int)
        self.assertIsInstance(dbs.get_default_supplier()[0], int)


class ArchitectureGuardTests(unittest.TestCase):
    def test_facade_contains_no_sql_and_no_sqlite_import(self):
        source = inspect.getsource(dbs)
        for forbidden in ("import sqlite3", ".execute(", "SELECT ", "INSERT INTO", "UPDATE ", "DELETE FROM", "cursor"):
            self.assertNotIn(forbidden, source, forbidden)

    def test_sqlite_backend_does_not_depend_on_tkinter_or_settings(self):
        source = inspect.getsource(sqlite_backend_module)
        for forbidden in ("import tkinter", "from tkinter", "messagebox", "SettingsManager", "settings_manager"):
            self.assertNotIn(forbidden, source, forbidden)

    def test_facade_uses_sqlite_backend_and_exposes_it(self):
        self.assertIsInstance(dbs.get_backend(), SqliteBackend)
        self.assertIsInstance(dbs.get_backend(), DataBackend)

    def test_sqlite_backend_implements_the_whole_contract(self):
        self.assertEqual(SqliteBackend.__abstractmethods__, frozenset())
        context = BackendContext(lambda: "", lambda: "", lambda: False, lambda t, m: None, lambda *a: None)
        self.assertIsInstance(SqliteBackend(lambda: "x.db", context), DataBackend)

    def test_backend_dependencies_are_resolved_at_call_time(self):
        with mock.patch.object(dbs, "get_database_path", lambda: "C:/na/pewno/nie/istnieje.db"):
            self.assertFalse(dbs.is_database_available())


class CallersAbortOnNumberingErrorTests(base.DbTestCase):
    """Wywołujący (generowanie oferty i WZ) przerywają działanie i nie tworzą dokumentu z błędnym numerem."""

    def test_offer_number_generation_aborts_with_error_popup(self):
        from src.services import offer_generator_service as ogs
        self.make_unavailable()
        result = ogs.generate_offer_number(datetime.datetime(2026, 1, 1), "ALFA")
        self.assertEqual(result, (None, None, None))
        self.assertEqual(len(self.popups), 1)
        self.assertEqual(self.popups[0][:2], ("error", "Error"))
        self.assertIn("Failed to generate offer number", self.popups[0][2])
        self.assertIn("Offer yearly numbering error", self.popups[0][2])

    def test_wz_generation_aborts_before_creating_any_document_or_record(self):
        from src.core import wz_generator_app as wga
        self.make_unavailable()
        fake = SimpleNamespace(
            validate_form=lambda: True,
            ui=SimpleNamespace(get_all_data=lambda: {"date": "04 08 2026"}, selected_client_alias="ALFA",
                               selected_supplier_alias="X"),
            product_table=SimpleNamespace(get_all_products=lambda: [["1"]]),
            nav_manager=mock.Mock(), source_frame=None,
        )
        with mock.patch.object(wga, "generate_wz_document") as generate, mock.patch.object(wga, "save_wz_to_db") as save:
            wga.WzGeneratorApp.generate_wz(fake)
        generate.assert_not_called()
        save.assert_not_called()
        self.assertEqual(len(self.popups), 1)
        self.assertIn("Wystąpił błąd podczas generowania WZ", self.popups[0][2])
        self.assertIn("WZ yearly numbering error", self.popups[0][2])
        fake.nav_manager.show_frame.assert_not_called()


if __name__ == "__main__":
    unittest.main()
