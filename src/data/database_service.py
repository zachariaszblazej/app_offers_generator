"""
Database service for managing data operations
"""
import sqlite3
import json
import tkinter.messagebox
import sys
import os
import datetime

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.utils.config import DATABASE_PATH
from src.utils.settings import SettingsManager
import re

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
        
        final_path = db_path if db_path else DATABASE_PATH
        print(f"DEBUG: Final database path: {final_path}")
        print(f"DEBUG: Database file exists: {os.path.exists(final_path)}")
        
        return final_path
    except Exception as e:
        print(f"Warning: Could not get database path from settings: {e}")
        print(f"DEBUG: Falling back to DATABASE_PATH: {DATABASE_PATH}")
        return DATABASE_PATH


def get_clients_from_db(include_extended: bool = False):
    """Fetch all clients from the database.
    When include_extended=True, also return additional nullable text columns:
    TerminRealizacji, TerminPlatnosci, WarunkiDostawy, WaznoscOferty, Gwarancja, Cena
    """
    try:
        db_path = get_database_path()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        if include_extended:
            cursor.execute(
                """
                SELECT Nip, CompanyName, AddressP1, AddressP2, Alias,
                       COALESCE(TerminRealizacji, ''),
                       COALESCE(TerminPlatnosci, ''),
                       COALESCE(WarunkiDostawy, ''),
                       COALESCE(WaznoscOferty, ''),
                       COALESCE(Gwarancja, ''),
                       COALESCE(Cena, '')
                FROM Clients
                ORDER BY CompanyName
                """
            )
        else:
            cursor.execute("SELECT Nip, CompanyName, AddressP1, AddressP2, Alias FROM Clients ORDER BY CompanyName")
        clients = cursor.fetchall()
        conn.close()
        return clients
    except sqlite3.Error as e:
        tkinter.messagebox.showerror("Database Error", f"Error accessing database: {e}")
        return []


def get_suppliers_from_db():
    """Get all suppliers from the database"""
    try:
        conn = sqlite3.connect(get_database_path())
        cursor = conn.cursor()
        cursor.execute("SELECT Nip, CompanyName, AddressP1, AddressP2, COALESCE(IsDefault, 0) FROM Suppliers ORDER BY CompanyName")
        suppliers = cursor.fetchall()
        conn.close()
        return suppliers
    except sqlite3.Error as e:
        tkinter.messagebox.showerror("Database Error", f"Error accessing database: {e}")
        return []


def get_next_offer_number():
    """Get the next offer order number from the database"""
    try:
        db_path = get_database_path()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT MAX(OfferOrderNumber) FROM Offers")
        result = cursor.fetchone()[0]
        conn.close()
        
        # If no offers exist, start with 1, otherwise increment
        return 1 if result is None else result + 1
    except sqlite3.Error as e:
        tkinter.messagebox.showerror("Database Error", f"Error accessing database: {e}")
        return 1

def get_next_offer_number_for_year(year: int):
    """Get next offer sequential number for a given year (requires OfferYearNumber column).
    Legacy fallback removed intentionally – database must be migrated.
    """
    try:
        conn = sqlite3.connect(get_database_path())
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(Offers)")
        cols = [r[1] for r in cursor.fetchall()]
        if 'OfferYearNumber' not in cols:
            conn.close()
            raise RuntimeError("Missing OfferYearNumber column – migrate database first")
        cursor.execute("SELECT MAX(OfferOrderNumber) FROM Offers WHERE OfferYearNumber = ?", (year,))
        result = cursor.fetchone()[0]
        conn.close()
        return 1 if result is None else result + 1
    except Exception as e:
        tkinter.messagebox.showerror("Database Error", f"Offer yearly numbering error: {e}")
        return 1


def save_offer_to_db(offer_order_number, offer_file_path, offer_context=None):
    """Save offer (assumes OfferYearNumber column already exists and composite UNIQUE set)."""
    try:
        conn = sqlite3.connect(get_database_path())
        cursor = conn.cursor()

        # Determine offer year from context or path
        offer_year = None
        if offer_context:
            raw_date = offer_context.get('date')
            if isinstance(raw_date, str):
                if re.match(r'^\d{4}-', raw_date):
                    offer_year = int(raw_date[:4])
                else:
                    m = re.search(r'(19|20)\d{2}', raw_date)
                    if m:
                        offer_year = int(m.group(0))
        if offer_year is None:
            m2 = re.search(r'[\\/](19|20)\d{2}[\\/]', offer_file_path)
            if m2:
                offer_year = int(m2.group(0).strip('/\\'))
        if offer_year is None:
            offer_year = datetime.datetime.now().year

        context_json = None
        if offer_context:
            context_json = json.dumps(offer_context, default=str, ensure_ascii=False)

        cursor.execute("INSERT INTO Offers (OfferYearNumber, OfferOrderNumber, OfferFilePath, OfferContext) VALUES (?, ?, ?, ?)",
                       (offer_year, offer_order_number, offer_file_path, context_json))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError as ie:
        tkinter.messagebox.showerror("Database Error", f"(OfferYearNumber, OfferOrderNumber) uniqueness violation: {ie}")
        return False
    except sqlite3.Error as e:
        tkinter.messagebox.showerror("Database Error", f"Error saving offer to database: {e}")
        return False


def get_offer_context_from_db(offer_file_path):
    """Get offer context from database by file path"""
    try:
        conn = sqlite3.connect(get_database_path())
        cursor = conn.cursor()
        cursor.execute("SELECT OfferContext FROM Offers WHERE OfferFilePath = ?", (offer_file_path,))
        result = cursor.fetchone()
        conn.close()
        
        if result and result[0]:
            # Parse JSON context
            return json.loads(result[0])
        return None
    except sqlite3.Error as e:
        tkinter.messagebox.showerror("Database Error", f"Error retrieving offer context: {e}")
        return None
    except json.JSONDecodeError as e:
        tkinter.messagebox.showerror("Data Error", f"Error parsing offer context: {e}")
        return None


def update_offer_context_in_db(offer_file_path, offer_context):
    """Update offer context in database"""
    try:
        conn = sqlite3.connect(get_database_path())
        cursor = conn.cursor()
        
        # Convert context to JSON
        context_json = json.dumps(offer_context, default=str, ensure_ascii=False)
        
        cursor.execute("UPDATE Offers SET OfferContext = ? WHERE OfferFilePath = ?", 
                      (context_json, offer_file_path))
        conn.commit()
        conn.close()
        return True
    except sqlite3.Error as e:
        tkinter.messagebox.showerror("Database Error", f"Error updating offer context: {e}")
        return False


def get_wz_context_from_db(wz_file_path):
    """Get WZ context from database by file path"""
    try:
        conn = sqlite3.connect(get_database_path())
        cursor = conn.cursor()
        cursor.execute("SELECT WzContext FROM Wuzetkas WHERE WzFilePath = ?", (wz_file_path,))
        result = cursor.fetchone()
        conn.close()
        
        if result and result[0]:
            # Parse JSON context
            return json.loads(result[0])
        return None
    except sqlite3.Error as e:
        tkinter.messagebox.showerror("Database Error", f"Error retrieving WZ context: {e}")
        return None
    except json.JSONDecodeError as e:
        tkinter.messagebox.showerror("Data Error", f"Error parsing WZ context: {e}")
        return None


def update_wz_context_in_db(wz_file_path, wz_context):
    """Update WZ context in database"""
    try:
        conn = sqlite3.connect(get_database_path())
        cursor = conn.cursor()
        
        # Convert context to JSON
        context_json = json.dumps(wz_context, default=str, ensure_ascii=False)
        
        cursor.execute("UPDATE Wuzetkas SET WzContext = ? WHERE WzFilePath = ?", 
                      (context_json, wz_file_path))
        conn.commit()
        conn.close()
        return True
    except sqlite3.Error as e:
        tkinter.messagebox.showerror("Database Error", f"Error updating WZ context: {e}")
        return False


def validate_nip(nip):
    """Validate NIP format and uniqueness"""
    # Check if NIP has exactly 10 digits
    if not nip.isdigit() or len(nip) != 10:
        return False, "NIP musi składać się z dokładnie 10 cyfr"
    
    # Check if NIP already exists in database
    try:
        conn = sqlite3.connect(get_database_path())
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM Clients WHERE Nip = ?", (nip,))
        count = cursor.fetchone()[0]
        conn.close()
        
        if count > 0:
            return False, "Klient z tym NIP już istnieje w bazie"
        
        return True, "NIP jest prawidłowy"
    except sqlite3.Error as e:
        return False, f"Błąd sprawdzania NIP: {e}"


def validate_alias(alias):
    """Validate alias format"""
    # Underscore now allowed
    
    if not alias.strip():
        return False, "Alias nie może być pusty"
    
    return True, "Alias jest prawidłowy"


def add_client_to_db(nip, company_name, address_p1, address_p2, alias):
    """Add a new client to the database"""
    try:
        # Validate NIP
        nip_valid, nip_message = validate_nip(nip)
        if not nip_valid:
            return False, nip_message
        
        # Validate alias
        alias_valid, alias_message = validate_alias(alias)
        if not alias_valid:
            return False, alias_message
        
        # Insert client
        conn = sqlite3.connect(get_database_path())
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO Clients (Nip, CompanyName, AddressP1, AddressP2, Alias) 
            VALUES (?, ?, ?, ?, ?)
        """, (nip, company_name, address_p1, address_p2, alias))
        conn.commit()
        conn.close()
        
        return True, "Klient został pomyślnie dodany do bazy"
    except sqlite3.Error as e:
        return False, f"Błąd podczas dodawania klienta: {e}"


def validate_supplier_nip(nip):
    """Validate NIP format and uniqueness for suppliers"""
    # Check if NIP has exactly 10 digits
    if not nip.isdigit() or len(nip) != 10:
        return False, "NIP musi składać się z dokładnie 10 cyfr"
    
    # Check if NIP already exists in supplier database
    try:
        conn = sqlite3.connect(get_database_path())
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM Suppliers WHERE Nip = ?", (nip,))
        count = cursor.fetchone()[0]
        conn.close()
        
        if count > 0:
            return False, "Dostawca z tym NIP już istnieje w bazie"
        
        return True, "NIP jest prawidłowy"
    except sqlite3.Error as e:
        return False, f"Błąd sprawdzania NIP: {e}"


def add_supplier_to_db(nip, company_name, address_p1, address_p2):
    """Add a new supplier to the database"""
    try:
        # Validate NIP
        nip_valid, nip_message = validate_supplier_nip(nip)
        if not nip_valid:
            return False, nip_message
        
        # Insert supplier
        conn = sqlite3.connect(get_database_path())
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO Suppliers (Nip, CompanyName, AddressP1, AddressP2) 
            VALUES (?, ?, ?, ?)
        """, (nip, company_name, address_p1, address_p2))
        conn.commit()
        conn.close()
        
        return True, "Dostawca został pomyślnie dodany do bazy"
    except sqlite3.Error as e:
        return False, f"Błąd podczas dodawania dostawcy: {e}"


def get_client_by_nip(nip):
    """Get client data by NIP"""
    try:
        conn = sqlite3.connect(get_database_path())
        cursor = conn.cursor()
        cursor.execute("SELECT Nip, CompanyName, AddressP1, AddressP2, Alias FROM Clients WHERE Nip = ?", (nip,))
        client = cursor.fetchone()
        conn.close()
        return client
    except sqlite3.Error as e:
        tkinter.messagebox.showerror("Database Error", f"Error accessing database: {e}")
        return None


def update_client_in_db(nip, company_name, address_p1, address_p2, alias):
    """Update client data (NIP cannot be changed)"""
    try:
        # Validate alias (but allow current alias to remain the same)
        conn = sqlite3.connect(get_database_path())
        cursor = conn.cursor()
        
        # Check if alias is used by another client
        cursor.execute("SELECT COUNT(*) FROM Clients WHERE Alias = ? AND Nip != ?", (alias, nip))
        count = cursor.fetchone()[0]
        
        if count > 0:
            conn.close()
            return False, "Alias już istnieje dla innego klienta"
        
        # Validate alias format
        alias_valid, alias_message = validate_alias(alias)
        if not alias_valid:
            conn.close()
            return False, alias_message
        
        # Update client
        cursor.execute("""
            UPDATE Clients 
            SET CompanyName = ?, AddressP1 = ?, AddressP2 = ?, Alias = ?
            WHERE Nip = ?
        """, (company_name, address_p1, address_p2, alias, nip))
        conn.commit()
        conn.close()
        
        return True, "Dane klienta zostały zaktualizowane"
    except sqlite3.Error as e:
        return False, f"Błąd podczas aktualizacji klienta: {e}"


def delete_client_from_db(nip):
    """Delete client from database"""
    try:
        conn = sqlite3.connect(get_database_path())
        cursor = conn.cursor()
        
        # First get client's alias
        cursor.execute("SELECT Alias FROM Clients WHERE Nip = ?", (nip,))
        result = cursor.fetchone()
        
        if not result:
            conn.close()
            return False, "Klient nie został znaleziony"
        
        client_alias = result[0]
        
        # Check if client has any offers by looking for alias in file path
        cursor.execute("SELECT COUNT(*) FROM Offers WHERE OfferFilePath LIKE ?", (f"%_{client_alias}.docx",))
        offer_count = cursor.fetchone()[0]
        
        if offer_count > 0:
            conn.close()
            return False, f"Nie można usunąć klienta - istnieją {offer_count} ofert(y) dla tego klienta"
        
        # Delete client
        cursor.execute("DELETE FROM Clients WHERE Nip = ?", (nip,))
        
        if cursor.rowcount == 0:
            conn.close()
            return False, "Klient nie został znaleziony"
        
        conn.commit()
        conn.close()
        
        return True, "Klient został usunięty z bazy"
    except sqlite3.Error as e:
        return False, f"Błąd podczas usuwania klienta: {e}"


def set_client_extended_fields(nip, termin_realizacji=None, termin_platnosci=None,
                               warunki_dostawy=None, waznosc_oferty=None,
                               gwarancja=None, cena=None):
    """Update extended nullable text fields for a client by NIP.
    All parameters are optional; missing values will be set to NULL.
    """
    try:
        conn = sqlite3.connect(get_database_path())
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE Clients
            SET TerminRealizacji = ?,
                TerminPlatnosci = ?,
                WarunkiDostawy = ?,
                WaznoscOferty = ?,
                Gwarancja = ?,
                Cena = ?
            WHERE Nip = ?
            """,
            (
                termin_realizacji if termin_realizacji != '' else None,
                termin_platnosci if termin_platnosci != '' else None,
                warunki_dostawy if warunki_dostawy != '' else None,
                waznosc_oferty if waznosc_oferty != '' else None,
                gwarancja if gwarancja != '' else None,
                cena if cena != '' else None,
                nip,
            ),
        )
        conn.commit()
        conn.close()
        return True, "Zapisano dodatkowe pola klienta"
    except sqlite3.Error as e:
        return False, f"Błąd zapisu dodatkowych pól klienta: {e}"


def get_supplier_by_nip(nip):
    """Get supplier data by NIP"""
    try:
        conn = sqlite3.connect(get_database_path())
        cursor = conn.cursor()
        cursor.execute("SELECT Nip, CompanyName, AddressP1, AddressP2, COALESCE(IsDefault, 0) FROM Suppliers WHERE Nip = ?", (nip,))
        supplier = cursor.fetchone()
        conn.close()
        return supplier
    except sqlite3.Error as e:
        tkinter.messagebox.showerror("Database Error", f"Error accessing database: {e}")
        return None


def update_supplier_in_db(nip, company_name, address_p1, address_p2):
    """Update supplier data (NIP cannot be changed)"""
    try:
        conn = sqlite3.connect(get_database_path())
        cursor = conn.cursor()
        
        # Update supplier
        cursor.execute("""
            UPDATE Suppliers 
            SET CompanyName = ?, AddressP1 = ?, AddressP2 = ?
            WHERE Nip = ?
        """, (company_name, address_p1, address_p2, nip))
        
        if cursor.rowcount == 0:
            conn.close()
            return False, "Dostawca nie został znaleziony"
        
        conn.commit()
        conn.close()
        
        return True, "Dane dostawcy zostały zaktualizowane"
    except sqlite3.Error as e:
        return False, f"Błąd podczas aktualizacji dostawcy: {e}"


def delete_supplier_from_db(nip):
    """Delete supplier from database"""
    try:
        conn = sqlite3.connect(get_database_path())
        cursor = conn.cursor()
        
        # Check if supplier is default supplier
        cursor.execute("SELECT IsDefault FROM Suppliers WHERE Nip = ?", (nip,))
        result = cursor.fetchone()
        if result and result[0] == 1:
            conn.close()
            return False, "Nie można usunąć domyślnego dostawcy. Najpierw ustaw innego dostawcę jako domyślny."
        
        # For suppliers, we could check if they have any related data
        # For now, we'll allow deletion (suppliers don't appear in offer file names)
        
        # Delete supplier
        cursor.execute("DELETE FROM Suppliers WHERE Nip = ?", (nip,))
        
        if cursor.rowcount == 0:
            conn.close()
            return False, "Dostawca nie został znaleziony"
        
        conn.commit()
        conn.close()
        
        return True, "Dostawca został usunięty z bazy"
    except sqlite3.Error as e:
        return False, f"Błąd podczas usuwania dostawcy: {e}"


def set_default_supplier(nip):
    """Set supplier as default (only one can be default at a time)"""
    try:
        conn = sqlite3.connect(get_database_path())
        cursor = conn.cursor()
        
        # First, remove default status from all suppliers
        cursor.execute("UPDATE Suppliers SET IsDefault = 0")
        
        # Then set the specified supplier as default
        cursor.execute("UPDATE Suppliers SET IsDefault = 1 WHERE Nip = ?", (nip,))
        
        if cursor.rowcount == 0:
            conn.close()
            return False, "Dostawca nie został znaleziony"
        
        conn.commit()
        conn.close()
        
        return True, "Dostawca został ustawiony jako domyślny"
    except sqlite3.Error as e:
        return False, f"Błąd podczas ustawiania domyślnego dostawcy: {e}"


def get_default_supplier():
    """Get the current default supplier"""
    try:
        conn = sqlite3.connect(get_database_path())
        cursor = conn.cursor()
        cursor.execute("SELECT Nip, CompanyName, AddressP1, AddressP2, IsDefault FROM Suppliers WHERE IsDefault = 1")
        supplier = cursor.fetchone()
        conn.close()
        return supplier
    except sqlite3.Error as e:
        tkinter.messagebox.showerror("Database Error", f"Error accessing database: {e}")
        return None


def delete_offer_from_db(offer_file_path):
    """Delete offer from database based on file path"""
    try:
        conn = sqlite3.connect(get_database_path())
        cursor = conn.cursor()
        
        # Delete offer by file path
        cursor.execute("DELETE FROM Offers WHERE OfferFilePath = ?", (offer_file_path,))
        
        if cursor.rowcount == 0:
            conn.close()
            return False, "Oferta nie została znaleziona w bazie danych"
        
        conn.commit()
        conn.close()
        
        return True, "Oferta została usunięta z bazy danych"
    except sqlite3.Error as e:
        return False, f"Błąd podczas usuwania oferty z bazy: {e}"


def find_offer_by_filename(filename):
    """Find offer in database by filename"""
    try:
        conn = sqlite3.connect(get_database_path())
        cursor = conn.cursor()
        
        # Search for offer by filename (using LIKE to match the end of the path)
        cursor.execute("SELECT OfferOrderNumber, OfferFilePath FROM Offers WHERE OfferFilePath LIKE ?", 
                      (f"%{filename}",))
        result = cursor.fetchone()
        conn.close()
        
        return result
    except sqlite3.Error as e:
        return None


def get_all_offer_file_paths():
    """Get all offer file paths from database"""
    try:
        conn = sqlite3.connect(get_database_path())
        cursor = conn.cursor()
        
        # Get all offer file paths from database
        cursor.execute("SELECT OfferFilePath FROM Offers ORDER BY OfferOrderNumber DESC")
        results = cursor.fetchall()
        conn.close()
        
        # Return list of file paths
        return [result[0] for result in results] if results else []
    except sqlite3.Error as e:
        print(f"Database error in get_all_offer_file_paths: {e}")
        return []


def migrate_offers_folder_path(old_base: str, new_base: str) -> dict:
    """Migrate OfferFilePath entries when offers folder location changes.

    For each record in Offers:
      - Extract the trailing "<year>/<filename>.docx" (year = 4 digits) if present.
      - Build candidate path under new_base.
      - If the file exists at new path, update OfferFilePath to new_base/year/filename.

    Args:
        old_base: Previous offers folder absolute (or as stored) path.
        new_base: New offers folder absolute path.

    Returns:
        dict summary with counts: {'checked': int, 'updated': int, 'skipped_not_found': int, 'errors': int}
    """
    import re
    summary = {
        'checked': 0,
        'updated': 0,
        'skipped_not_found': 0,
        'errors': 0,
        'skipped_files': [],   # list of original paths whose new target not found
        'error_files': []      # list of original paths that caused DB update errors
    }
    try:
        conn = sqlite3.connect(get_database_path())
        cursor = conn.cursor()
        cursor.execute("SELECT rowid, OfferFilePath FROM Offers")
        rows = cursor.fetchall()
        for rowid, path in rows:
            summary['checked'] += 1
            if not isinstance(path, str):
                continue
            # Find year + filename pattern at end
            m = re.search(r"(\d{4}/[^/\\]+\.docx)$", path)
            if not m:
                continue  # pattern not found, skip silently
            tail = m.group(1)  # year/filename.docx
            new_full = os.path.join(new_base, tail)
            # Normalize paths
            new_full_norm = os.path.normpath(new_full)
            if os.path.exists(new_full_norm):
                try:
                    cursor.execute("UPDATE Offers SET OfferFilePath = ? WHERE rowid = ?", (new_full_norm, rowid))
                    summary['updated'] += 1
                except Exception:
                    summary['errors'] += 1
                    summary['error_files'].append(path)
            else:
                summary['skipped_not_found'] += 1
                summary['skipped_files'].append(path)
        conn.commit()
        conn.close()
    except Exception:
        summary['errors'] += 1
    return summary

def migrate_wz_folder_path(old_base: str, new_base: str) -> dict:
    """Migrate WzFilePath entries when WZ folder location changes.

    For each record in Wuzetkas:
      - Extract trailing "<year>/<filename>.docx" (year=4 digits) pattern.
      - Build candidate new path new_base/year/filename.
      - If file exists at new path, update WzFilePath.

    Returns summary dict like offers migration.
    """
    import re
    summary = {
        'checked': 0,
        'updated': 0,
        'skipped_not_found': 0,
        'errors': 0,
        'skipped_files': [],
        'error_files': []
    }
    try:
        conn = sqlite3.connect(get_database_path())
        cursor = conn.cursor()
        cursor.execute("SELECT rowid, WzFilePath FROM Wuzetkas")
        rows = cursor.fetchall()
        for rowid, path in rows:
            summary['checked'] += 1
            if not isinstance(path, str):
                continue
            m = re.search(r"(\d{4}[\\/][^/\\]+\.docx)$", path)
            if not m:
                continue
            tail = m.group(1)
            new_full = os.path.join(new_base, tail)
            new_full_norm = os.path.normpath(new_full)
            if os.path.exists(new_full_norm):
                try:
                    cursor.execute("UPDATE Wuzetkas SET WzFilePath = ? WHERE rowid = ?", (new_full_norm, rowid))
                    summary['updated'] += 1
                except Exception:
                    summary['errors'] += 1
                    summary['error_files'].append(path)
            else:
                summary['skipped_not_found'] += 1
                summary['skipped_files'].append(path)
        conn.commit()
        conn.close()
    except Exception:
        summary['errors'] += 1
    return summary


# WZ (Wuzetka) related functions

def get_next_wz_number(year: int):
    """Get next WZ sequential number for a given year (requires WzYearNumber column)."""
    try:
        conn = sqlite3.connect(get_database_path())
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(Wuzetkas)")
        cols = [r[1] for r in cursor.fetchall()]
        if 'WzYearNumber' not in cols:
            conn.close()
            raise RuntimeError("Missing WzYearNumber column – migrate database first")
        cursor.execute("SELECT MAX(WzOrderNumber) FROM Wuzetkas WHERE WzYearNumber = ?", (year,))
        result = cursor.fetchone()[0]
        conn.close()
        return 1 if result is None else result + 1
    except Exception as e:
        tkinter.messagebox.showerror("Database Error", f"WZ yearly numbering error: {e}")
        return 1


def save_wz_to_db(wz_order_number, wz_file_path, wz_context=None):
    """Save WZ (assumes WzYearNumber column exists after migration)."""
    try:
        conn = sqlite3.connect(get_database_path())
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(Wuzetkas)")
        cols = [r[1] for r in cursor.fetchall()]

        # Determine year
        wz_year = None
        if wz_context:
            d = wz_context.get('date')
            if isinstance(d, str) and len(d) >= 4 and d[-4:].isdigit():
                # try parse last 4 digits as year (format might differ)
                import re as _re
                m = _re.search(r'(19|20)\d{2}', d)
                if m:
                    wz_year = int(m.group(0))
        if wz_year is None:
            # Try to derive from year subfolder in path ( .../<year>/WZ_seq_year_alias.docx )
            import re as _re
            m2 = _re.search(r'[\\/](19|20)\d{2}[\\/]', wz_file_path)
            if m2:
                try:
                    wz_year = int(m2.group(0).strip('/\\'))
                except ValueError:
                    wz_year = None
        if wz_year is None:
            import datetime as _dt
            wz_year = _dt.datetime.now().year

        context_json = None
        if wz_context:
            context_json = json.dumps(wz_context, ensure_ascii=False)

        if 'WzYearNumber' in cols:
            cursor.execute("INSERT INTO Wuzetkas (WzYearNumber, WzOrderNumber, WzFilePath, WzContext) VALUES (?, ?, ?, ?)",
                           (wz_year, wz_order_number, wz_file_path, context_json))
        else:
            cursor.execute("INSERT INTO Wuzetkas (WzOrderNumber, WzFilePath, WzContext) VALUES (?, ?, ?)",
                           (wz_order_number, wz_file_path, context_json))
        conn.commit()
        conn.close()
        return True, "WZ zostało zapisane do bazy danych"
    except sqlite3.Error as e:
        return False, f"Błąd podczas zapisywania WZ do bazy: {e}"


def get_all_wz():
    """Get all WZ from database"""
    try:
        conn = sqlite3.connect(get_database_path())
        cursor = conn.cursor()
        
        # Get WZ with extracted client info from context
        cursor.execute("""
            SELECT WzOrderNumber, WzFilePath, WzContext, WzOrderNumber as ID
            FROM Wuzetkas 
            ORDER BY WzOrderNumber DESC
        """)
        
        wz_data = []
        for row in cursor.fetchall():
            wz_number = row[0]
            file_path = row[1]
            context_json = row[2]
            wz_id = row[3]
            
            # Extract additional info from context
            client_name = "N/A"
            date = "N/A"
            
            if context_json:
                try:
                    context = json.loads(context_json)
                    client_name = context.get('client_name', 'N/A')
                    date = context.get('date', 'N/A')
                except:
                    pass
            
            # Generate WZ number format if not in proper format
            if isinstance(wz_number, int):
                import datetime
                year = datetime.datetime.now().year
                formatted_wz_number = f"WZ_{wz_number}_{year}"
            else:
                formatted_wz_number = str(wz_number)
            
            wz_data.append((wz_id, formatted_wz_number, date, client_name, "Utworzone", file_path))
        
        conn.close()
        return wz_data
        
    except sqlite3.Error as e:
        tkinter.messagebox.showerror("Database Error", f"Error accessing database: {e}")
        return []


def delete_wz(wz_id):
    """Delete WZ from database"""
    try:
        conn = sqlite3.connect(get_database_path())
        cursor = conn.cursor()
        
        # Delete WZ by ID
        cursor.execute("DELETE FROM Wuzetkas WHERE WzOrderNumber = ?", (wz_id,))
        
        if cursor.rowcount == 0:
            conn.close()
            return False, "WZ nie zostało znalezione w bazie danych"
        
        conn.commit()
        conn.close()
        
        return True, "WZ zostało usunięte z bazy danych"
    except sqlite3.Error as e:
        return False, f"Błąd podczas usuwania WZ z bazy: {e}"


def delete_wz_by_file_path(wz_file_path: str):
    """Delete a single WZ row using its unique file path (safer with year-based numbering)."""
    try:
        conn = sqlite3.connect(get_database_path())
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Wuzetkas WHERE WzFilePath = ?", (wz_file_path,))
        if cursor.rowcount == 0:
            conn.close()
            return False, "WZ nie zostało znalezione w bazie (po ścieżce)"
        conn.commit()
        conn.close()
        return True, "WZ zostało usunięte z bazy danych"
    except sqlite3.Error as e:
        return False, f"Błąd podczas usuwania WZ (po ścieżce): {e}"


def get_all_wz_file_paths():
    """Get all WZ file paths from database"""
    try:
        conn = sqlite3.connect(get_database_path())
        cursor = conn.cursor()
        
        # Get all WZ file paths from database
        cursor.execute("SELECT WzFilePath FROM Wuzetkas ORDER BY WzOrderNumber DESC")
        results = cursor.fetchall()
        conn.close()
        
        # Return list of file paths
        return [result[0] for result in results] if results else []
    except sqlite3.Error as e:
        print(f"Database error in get_all_wz_file_paths: {e}")
        return []


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
