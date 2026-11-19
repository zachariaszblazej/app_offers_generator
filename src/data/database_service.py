"""
Database service - fasada warstwy danych.

Publiczne funkcje (nazwy, sygnatury, kształty zwracanych danych i konwencje błędów) pozostają takie same jak
dotychczas; implementacja jest delegowana do backendu danych (obecnie `SqliteBackend`). Dzięki temu widoki
i serwisy aplikacji nie zależą od konkretnego backendu.
"""
import tkinter.messagebox
import sys
import os

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.utils.config import DEFAULT_APP_SETTINGS, get_offers_folder, get_wz_folder
from src.utils.settings import SettingsManager
from src.data import path_utils
from src.data.backends import BackendContext, SqliteBackend
from src.data.errors import DataAccessError, NumberingError  # noqa: F401  (publiczne wyjątki warstwy danych)


def _should_show_db_error_popup() -> bool:
    """Return True if DB error popups should be shown now.
    We suppress them during early startup before the main menu is ready.
    The main app can enable popups by setting database_service.DB_POPUPS_ENABLED = True.
    """
    try:
        import tkinter as _tk
        # If there is no active Tk root yet, suppress
        if getattr(_tk, '_default_root', None) is None:
            return False
        return bool(globals().get('DB_POPUPS_ENABLED', False))
    except Exception:
        return False

def get_database_path():
    """Get the current database path from settings or fallback to config"""
    try:
        settings_manager = SettingsManager()
        db_path = settings_manager.get_database_path()

        print(f"DEBUG: Raw database path from settings: {db_path}")

        # If path is relative, make it absolute from the executable location
        if db_path and not os.path.isabs(db_path):
            if getattr(sys, 'frozen', False):
                # Running as PyInstaller executable - use executable directory
                base_dir = os.path.dirname(sys.executable)
                print(f"DEBUG: PyInstaller mode - base directory: {base_dir}")
            else:
                # Running in development - use project root
                base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
                print(f"DEBUG: Development mode - base directory: {base_dir}")
            db_path = os.path.abspath(os.path.join(base_dir, db_path))

        default_path = DEFAULT_APP_SETTINGS.get('database_path', '')
        final_path = db_path if db_path else default_path
        print(f"DEBUG: Final database path: {final_path}")
        print(f"DEBUG: Database file exists: {os.path.exists(final_path)}")

        return final_path
    except Exception as e:
        print(f"Warning: Could not get database path from settings: {e}")
        default_path = DEFAULT_APP_SETTINGS.get('database_path', '')
        print(f"DEBUG: Falling back to DEFAULT_APP_SETTINGS['database_path']: {default_path}")
        return default_path


# ------------------------------
# Backend (obecnie wyłącznie SQLite)
# ------------------------------
# Zależności są wywoływane przy każdym użyciu (późne wiązanie), więc zmiany ustawień i podmiany w testach działają.
_backend = SqliteBackend(
    db_path=lambda: get_database_path(),
    context=BackendContext(
        offers_folder=lambda: get_offers_folder(),
        wz_folder=lambda: get_wz_folder(),
        popups_enabled=lambda: _should_show_db_error_popup(),
        show_error=lambda title, message: tkinter.messagebox.showerror(title, message),
        log=lambda *args, **kwargs: print(*args, **kwargs),
    ),
)


def get_backend():
    """Zwraca aktywny backend danych."""
    return _backend


def is_database_available() -> bool:
    """Check if the configured database exists and is readable without creating it.
    Paths table is no longer required; we accept DBs that have any core tables.
    """
    return _backend.is_available()


# ------------------------------
# Paths helpers (niezależne od backendu; foldery z lokalnych ustawień)
# ------------------------------

def normalize_wz_db_path(path: str) -> str:
    """Normalize WZ file path to relative DB format 'YYYY/filename.docx'.
    Strips WZ root prefix if present; mirrors offers normalization.
    """
    return path_utils.normalize_wz_path(path, get_wz_folder())

def build_full_wz_path(rel_path: str) -> str:
    """Compose full absolute path from relative WzFilePath using Wz_Folder base.
    Be tolerant of legacy/mis-saved absolute paths without leading slash on POSIX.
    """
    return path_utils.build_full_wz_path(rel_path, get_wz_folder())


def normalize_offer_db_path(path: str) -> str:
    """Convert an absolute or mixed path to DB-stored relative format 'YYYY/filename.docx'.
    If already relative with a separator, return normalized.
    If only a filename is provided, return just filename (legacy tolerance).
    """
    return path_utils.normalize_offer_path(path, get_offers_folder())


def build_full_offer_path(rel_path: str) -> str:
    """Compose full absolute path from relative OfferFilePath using Offers_Folder base."""
    return path_utils.build_full_offer_path(rel_path, get_offers_folder())


# ------------------------------
# Clients
# ------------------------------

def get_clients_from_db(include_extended: bool = False):
    """Fetch all clients from the database.
    When include_extended=True, also return additional nullable text columns:
    TerminRealizacji, TerminPlatnosci, WarunkiDostawy, WaznoscOferty, Gwarancja, Cena
    """
    return _backend.get_clients(include_extended)


def get_client_by_nip(nip):
    """Get client data by NIP"""
    return _backend.get_client_by_nip(nip)


def validate_nip(nip):
    """Validate NIP format and uniqueness"""
    return _backend.validate_nip(nip)


def validate_alias(alias):
    """Validate alias format"""
    return _backend.validate_alias(alias)


def add_client_to_db(nip, company_name, address_p1, address_p2, alias):
    """Add a new client to the database"""
    return _backend.add_client(nip, company_name, address_p1, address_p2, alias)


def update_client_in_db(nip, company_name, address_p1, address_p2, alias):
    """Update client data (NIP cannot be changed)"""
    return _backend.update_client(nip, company_name, address_p1, address_p2, alias)


def set_client_extended_fields(nip, termin_realizacji=None, termin_platnosci=None,
                               warunki_dostawy=None, waznosc_oferty=None,
                               gwarancja=None, cena=None):
    """Update extended nullable text fields for a client by NIP.
    All parameters are optional; missing values will be set to NULL.
    """
    return _backend.set_client_extended_fields(nip, termin_realizacji, termin_platnosci,
                                               warunki_dostawy, waznosc_oferty, gwarancja, cena)


def delete_client_from_db(nip):
    """Delete client from database"""
    return _backend.delete_client(nip)


# ------------------------------
# Suppliers
# ------------------------------

def get_suppliers_from_db():
    """Get all suppliers from the database"""
    return _backend.get_suppliers()


def get_supplier_by_nip(nip):
    """Get supplier data by NIP"""
    return _backend.get_supplier_by_nip(nip)


def get_default_supplier():
    """Get the current default supplier"""
    return _backend.get_default_supplier()


def validate_supplier_nip(nip):
    """Validate NIP format and uniqueness for suppliers"""
    return _backend.validate_supplier_nip(nip)


def add_supplier_to_db(nip, company_name, address_p1, address_p2):
    """Add a new supplier to the database"""
    return _backend.add_supplier(nip, company_name, address_p1, address_p2)


def update_supplier_in_db(nip, company_name, address_p1, address_p2):
    """Update supplier data (NIP cannot be changed)"""
    return _backend.update_supplier(nip, company_name, address_p1, address_p2)


def delete_supplier_from_db(nip):
    """Delete supplier from database"""
    return _backend.delete_supplier(nip)


def set_default_supplier(nip):
    """Set supplier as default (only one can be default at a time)"""
    return _backend.set_default_supplier(nip)


# ------------------------------
# Offers
# ------------------------------

def get_next_offer_number():
    """Get the next offer order number from the database"""
    return _backend.get_next_offer_number()


def get_next_offer_number_for_year(year: int):
    """Get next offer sequential number for a given year (requires OfferYearNumber column).
    Raises NumberingError on database errors/unavailability (never returns a fallback number).
    """
    return _backend.get_next_offer_number_for_year(year)


def save_offer_to_db(offer_order_number, offer_file_path, offer_context=None):
    """Save offer (assumes OfferYearNumber column already exists and composite UNIQUE set)."""
    return _backend.save_offer(offer_order_number, offer_file_path, offer_context)


def get_offer_context_from_db(offer_file_path):
    """Get offer context from database by file path (accepts full or relative)."""
    return _backend.get_offer_context(offer_file_path)


def update_offer_context_in_db(offer_file_path, offer_context):
    """Update offer context in database (accepts full or relative path)."""
    return _backend.update_offer_context(offer_file_path, offer_context)


def delete_offer_from_db(offer_file_path):
    """Delete offer from database based on file path (accepts full or relative)."""
    return _backend.delete_offer(offer_file_path)


def find_offer_by_filename(filename):
    """Find offer in database by filename (matches end of relative path)."""
    return _backend.find_offer_by_filename(filename)


def get_all_offer_file_paths():
    """Get all offer file paths from database (relative paths)."""
    return _backend.get_all_offer_file_paths()


# ------------------------------
# WZ (Wuzetka)
# ------------------------------

def get_next_wz_number(year: int):
    """Get next WZ sequential number for a given year (requires WzYearNumber column).
    Raises NumberingError on database errors/unavailability (never returns a fallback number).
    """
    return _backend.get_next_wz_number(year)


def save_wz_to_db(wz_order_number, wz_file_path, wz_context=None):
    """Save WZ (assumes WzYearNumber column exists after migration)."""
    return _backend.save_wz(wz_order_number, wz_file_path, wz_context)


def get_wz_context_from_db(wz_file_path):
    """Get WZ context from database by file path (accepts full or relative)."""
    return _backend.get_wz_context(wz_file_path)


def update_wz_context_in_db(wz_file_path, wz_context):
    """Update WZ context in database (accepts full or relative path)."""
    return _backend.update_wz_context(wz_file_path, wz_context)


def get_all_wz():
    """Get all WZ from database"""
    return _backend.get_all_wz()


def delete_wz(wz_id):
    """Delete WZ from database"""
    return _backend.delete_wz(wz_id)


def delete_wz_by_file_path(wz_file_path: str):
    """Delete a single WZ row using its unique file path (safer with year-based numbering)."""
    return _backend.delete_wz_by_file_path(wz_file_path)


def get_all_wz_file_paths():
    """Get all WZ file paths from database"""
    return _backend.get_all_wz_file_paths()


class DatabaseService:
    """Database service class for WZ operations"""
    
    def __init__(self):
        self.db_path = get_database_path()
    
    def get_all_wz(self):
        """Get all WZ from database"""
        return get_all_wz()
    
    def delete_wz(self, wz_id):
        """Delete WZ from database"""
        success, message = delete_wz(wz_id)
        if not success:
            raise Exception(message)
        return success

    def delete_wz_by_file_path(self, wz_file_path: str):
        """Delete WZ using its file path (preferred)."""
        success, message = delete_wz_by_file_path(wz_file_path)
        if not success:
            raise Exception(message)
        return success
