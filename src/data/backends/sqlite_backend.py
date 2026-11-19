"""Backend SQLite: dotychczasowa implementacja operacji na danych aplikacji (przeniesiona bez zmiany zachowania).

Zachowania historyczne (m.in. zwroty sukcesu dla nieistniejących rekordów, dopasowanie przez LIKE, tworzenie
pustego pliku bazy przez część funkcji, bezwarunkowe okienka błędów) są celowo zachowane - opisują je testy
charakteryzujące. Jedyna zmiana względem poprzedniej wersji: `get_next_offer_number_for_year` i
`get_next_wz_number` zgłaszają `NumberingError` zamiast zwracać 1 przy błędzie lub niedostępnej bazie.
"""
import datetime
import json
import os
import re
import sqlite3
from typing import Callable

from src.data import path_utils
from src.data.backends.base import BackendContext, DataBackend
from src.data.errors import NumberingError


class SqliteBackend(DataBackend):
    def __init__(self, db_path: Callable[[], str], context: BackendContext):
        self._db_path = db_path
        self._ctx = context

    # ------------------------------------------------------------------
    # pomocnicze
    # ------------------------------------------------------------------
    def _norm_offer(self, path):
        return path_utils.normalize_offer_path(path, self._ctx.offers_folder())

    def _norm_wz(self, path):
        return path_utils.normalize_wz_path(path, self._ctx.wz_folder())

    def _file_missing(self):
        path = self._db_path()
        return not path or not os.path.exists(path)

    def is_available(self) -> bool:
        """Plik istnieje, daje się otworzyć tylko do odczytu i ma którąś ze znanych tabel."""
        try:
            path = self._db_path()
            if not path or not os.path.exists(path):
                return False
            conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
            cur = conn.cursor()
            cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = {row[0] for row in cur.fetchall()}
            conn.close()
            expected = {'Clients', 'Suppliers', 'Offers', 'Wuzetkas'}
            return bool(tables & expected)
        except Exception:
            return False

    # ------------------------------------------------------------------
    # klienci
    # ------------------------------------------------------------------
    def get_clients(self, include_extended: bool = False):
        try:
            # Do not create DB file implicitly when path is invalid
            if not self.is_available():
                return []
            db_path = self._db_path()
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
            if self._ctx.popups_enabled():
                self._ctx.show_error("Database Error", f"Error accessing database: {e}")
            return []

    def get_client_by_nip(self, nip):
        try:
            if not self.is_available():
                return None
            conn = sqlite3.connect(self._db_path())
            cursor = conn.cursor()
            cursor.execute("SELECT Nip, CompanyName, AddressP1, AddressP2, Alias FROM Clients WHERE Nip = ?", (nip,))
            client = cursor.fetchone()
            conn.close()
            return client
        except sqlite3.Error as e:
            self._ctx.show_error("Database Error", f"Error accessing database: {e}")
            return None

    def validate_nip(self, nip):
        """Validate NIP format and uniqueness"""
        # Check if NIP has exactly 10 digits
        if not nip.isdigit() or len(nip) != 10:
            return False, "NIP musi składać się z dokładnie 10 cyfr"

        # Check if NIP already exists in database
        try:
            conn = sqlite3.connect(self._db_path())
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM Clients WHERE Nip = ?", (nip,))
            count = cursor.fetchone()[0]
            conn.close()

            if count > 0:
                return False, "Klient z tym NIP już istnieje w bazie"

            return True, "NIP jest prawidłowy"
        except sqlite3.Error as e:
            return False, f"Błąd sprawdzania NIP: {e}"

    def validate_alias(self, alias):
        """Validate alias format"""
        # Underscore now allowed

        if not alias.strip():
            return False, "Alias nie może być pusty"

        return True, "Alias jest prawidłowy"

    def add_client(self, nip, company_name, address_p1, address_p2, alias):
        try:
            if self._file_missing():
                return False, "Baza danych jest niedostępna lub nie istnieje."
            # Validate NIP
            nip_valid, nip_message = self.validate_nip(nip)
            if not nip_valid:
                return False, nip_message

            # Validate alias
            alias_valid, alias_message = self.validate_alias(alias)
            if not alias_valid:
                return False, alias_message

            # Insert client
            conn = sqlite3.connect(self._db_path())
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

    def update_client(self, nip, company_name, address_p1, address_p2, alias):
        """Update client data (NIP cannot be changed)"""
        try:
            if self._file_missing():
                return False, "Baza danych jest niedostępna lub nie istnieje."
            # Validate alias (but allow current alias to remain the same)
            conn = sqlite3.connect(self._db_path())
            cursor = conn.cursor()

            # Check if alias is used by another client
            cursor.execute("SELECT COUNT(*) FROM Clients WHERE Alias = ? AND Nip != ?", (alias, nip))
            count = cursor.fetchone()[0]

            if count > 0:
                conn.close()
                return False, "Alias już istnieje dla innego klienta"

            # Validate alias format
            alias_valid, alias_message = self.validate_alias(alias)
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

    def set_client_extended_fields(self, nip, termin_realizacji=None, termin_platnosci=None,
                                   warunki_dostawy=None, waznosc_oferty=None,
                                   gwarancja=None, cena=None):
        """Update extended nullable text fields for a client by NIP.
        All parameters are optional; missing values will be set to NULL.
        """
        try:
            if self._file_missing():
                return False, "Baza danych jest niedostępna lub nie istnieje."
            conn = sqlite3.connect(self._db_path())
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

    def delete_client(self, nip):
        try:
            if self._file_missing():
                return False, "Baza danych jest niedostępna lub nie istnieje."
            conn = sqlite3.connect(self._db_path())
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

    # ------------------------------------------------------------------
    # dostawcy
    # ------------------------------------------------------------------
    def get_suppliers(self):
        try:
            # Do not create DB file implicitly when path is invalid
            if not self.is_available():
                return []
            conn = sqlite3.connect(self._db_path())
            cursor = conn.cursor()
            cursor.execute("SELECT Nip, CompanyName, AddressP1, AddressP2, COALESCE(IsDefault, 0) FROM Suppliers ORDER BY CompanyName")
            suppliers = cursor.fetchall()
            conn.close()
            return suppliers
        except sqlite3.Error as e:
            if self._ctx.popups_enabled():
                self._ctx.show_error("Database Error", f"Error accessing database: {e}")
            return []

    def get_supplier_by_nip(self, nip):
        try:
            if not self.is_available():
                return None
            conn = sqlite3.connect(self._db_path())
            cursor = conn.cursor()
            cursor.execute("SELECT Nip, CompanyName, AddressP1, AddressP2, COALESCE(IsDefault, 0) FROM Suppliers WHERE Nip = ?", (nip,))
            supplier = cursor.fetchone()
            conn.close()
            return supplier
        except sqlite3.Error as e:
            self._ctx.show_error("Database Error", f"Error accessing database: {e}")
            return None

    def get_default_supplier(self):
        try:
            if not self.is_available():
                return None
            conn = sqlite3.connect(self._db_path())
            cursor = conn.cursor()
            cursor.execute("SELECT Nip, CompanyName, AddressP1, AddressP2, IsDefault FROM Suppliers WHERE IsDefault = 1")
            supplier = cursor.fetchone()
            conn.close()
            return supplier
        except sqlite3.Error as e:
            self._ctx.show_error("Database Error", f"Error accessing database: {e}")
            return None

    def validate_supplier_nip(self, nip):
        """Validate NIP format and uniqueness for suppliers"""
        # Check if NIP has exactly 10 digits
        if not nip.isdigit() or len(nip) != 10:
            return False, "NIP musi składać się z dokładnie 10 cyfr"

        # Check if NIP already exists in supplier database
        try:
            if not self.is_available():
                return False, "Baza danych jest niedostępna"
            conn = sqlite3.connect(self._db_path())
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM Suppliers WHERE Nip = ?", (nip,))
            count = cursor.fetchone()[0]
            conn.close()

            if count > 0:
                return False, "Dostawca z tym NIP już istnieje w bazie"

            return True, "NIP jest prawidłowy"
        except sqlite3.Error as e:
            return False, f"Błąd sprawdzania NIP: {e}"

    def add_supplier(self, nip, company_name, address_p1, address_p2):
        try:
            if self._file_missing():
                return False, "Baza danych jest niedostępna lub nie istnieje."
            # Validate NIP
            nip_valid, nip_message = self.validate_supplier_nip(nip)
            if not nip_valid:
                return False, nip_message

            # Insert supplier
            conn = sqlite3.connect(self._db_path())
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

    def update_supplier(self, nip, company_name, address_p1, address_p2):
        """Update supplier data (NIP cannot be changed)"""
        try:
            if self._file_missing():
                return False, "Baza danych jest niedostępna lub nie istnieje."
            conn = sqlite3.connect(self._db_path())
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

    def delete_supplier(self, nip):
        try:
            if self._file_missing():
                return False, "Baza danych jest niedostępna lub nie istnieje."
            conn = sqlite3.connect(self._db_path())
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

    def set_default_supplier(self, nip):
        """Set supplier as default (only one can be default at a time)"""
        try:
            if self._file_missing():
                return False, "Baza danych jest niedostępna lub nie istnieje."
            conn = sqlite3.connect(self._db_path())
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

    # ------------------------------------------------------------------
    # oferty
    # ------------------------------------------------------------------
    def get_next_offer_number(self):
        """Get the next offer order number from the database (globalnie, nieużywane przez UI)"""
        try:
            if not self.is_available():
                return 1
            db_path = self._db_path()
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT MAX(OfferOrderNumber) FROM Offers")
            result = cursor.fetchone()[0]
            conn.close()

            # If no offers exist, start with 1, otherwise increment
            return 1 if result is None else result + 1
        except sqlite3.Error as e:
            if self._ctx.popups_enabled():
                self._ctx.show_error("Database Error", f"Error accessing database: {e}")
            return 1

    def get_next_offer_number_for_year(self, year: int):
        """Get next offer sequential number for a given year (requires OfferYearNumber column).
        Błąd lub niedostępna baza przerywa operację (NumberingError) - nie zwraca się numeru domyślnego.
        """
        try:
            if not self.is_available():
                raise RuntimeError("Database unavailable")
            conn = sqlite3.connect(self._db_path())
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
            raise NumberingError(f"Offer yearly numbering error: {e}") from e

    def save_offer(self, offer_order_number, offer_file_path, offer_context=None):
        """Save offer (assumes OfferYearNumber column already exists and composite UNIQUE set)."""
        try:
            # Prevent creating DB when path invalid
            path = self._db_path()
            if not path or not os.path.exists(path):
                raise sqlite3.Error("Database file not found")
            conn = sqlite3.connect(self._db_path())
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
                try:
                    _ctx = dict(offer_context)
                    for k in ('client_name', 'supplier_name'):
                        if k in _ctx and isinstance(_ctx[k], str):
                            if '<w:r>' in _ctx[k] or '<w:t' in _ctx[k]:
                                import re as _re
                                t = _ctx[k]
                                t = _re.sub(r'<w:[^>]+>', '', t)
                                t = t.replace('</w:t>', '').replace('</w:r>', '')
                                _ctx[k] = t
                    offer_context = _ctx
                except Exception:
                    pass
                context_json = json.dumps(offer_context, default=str, ensure_ascii=False)

            # Store relative path in DB
            rel_path = self._norm_offer(offer_file_path)
            cursor.execute(
                "INSERT INTO Offers (OfferYearNumber, OfferOrderNumber, OfferFilePath, OfferContext) VALUES (?, ?, ?, ?)",
                (offer_year, offer_order_number, rel_path, context_json),
            )
            conn.commit()
            conn.close()
            return True
        except sqlite3.IntegrityError as ie:
            self._ctx.show_error("Database Error", f"(OfferYearNumber, OfferOrderNumber) uniqueness violation: {ie}")
            return False
        except sqlite3.Error as e:
            self._ctx.show_error("Database Error", f"Error saving offer to database: {e}")
            return False

    def get_offer_context(self, offer_file_path):
        """Get offer context from database by file path (accepts full or relative)."""
        try:
            if not self.is_available():
                return None
            conn = sqlite3.connect(self._db_path())
            cursor = conn.cursor()
            rel_path = self._norm_offer(offer_file_path)
            cursor.execute("SELECT OfferContext FROM Offers WHERE OfferFilePath = ?", (rel_path,))
            result = cursor.fetchone()
            conn.close()

            if result and result[0]:
                # Parse JSON context
                return json.loads(result[0])
            return None
        except sqlite3.Error as e:
            if self._ctx.popups_enabled():
                self._ctx.show_error("Database Error", f"Error retrieving offer context: {e}")
            return None
        except json.JSONDecodeError as e:
            self._ctx.show_error("Data Error", f"Error parsing offer context: {e}")
            return None

    def update_offer_context(self, offer_file_path, offer_context):
        """Update offer context in database (accepts full or relative path)."""
        try:
            if not self.is_available():
                return False
            conn = sqlite3.connect(self._db_path())
            cursor = conn.cursor()

            # Convert context to JSON
            context_json = json.dumps(offer_context, default=str, ensure_ascii=False)

            rel_path = self._norm_offer(offer_file_path)
            cursor.execute(
                "UPDATE Offers SET OfferContext = ? WHERE OfferFilePath = ?",
                (context_json, rel_path),
            )
            conn.commit()
            conn.close()
            return True
        except sqlite3.Error as e:
            if self._ctx.popups_enabled():
                self._ctx.show_error("Database Error", f"Error updating offer context: {e}")
            return False

    def delete_offer(self, offer_file_path):
        """Delete offer from database based on file path (accepts full or relative)."""
        try:
            if self._file_missing():
                return False, "Baza danych jest niedostępna lub nie istnieje."
            conn = sqlite3.connect(self._db_path())
            cursor = conn.cursor()

            # Delete offer by file path
            rel_path = self._norm_offer(offer_file_path)
            cursor.execute("DELETE FROM Offers WHERE OfferFilePath = ?", (rel_path,))

            if cursor.rowcount == 0:
                conn.close()
                return False, "Oferta nie została znaleziona w bazie danych"

            conn.commit()
            conn.close()

            return True, "Oferta została usunięta z bazy danych"
        except sqlite3.Error as e:
            return False, f"Błąd podczas usuwania oferty z bazy: {e}"

    def find_offer_by_filename(self, filename):
        """Find offer in database by filename (matches end of relative path)."""
        try:
            if not self.is_available():
                return None
            conn = sqlite3.connect(self._db_path())
            cursor = conn.cursor()

            # Search for offer by filename (using LIKE to match the end of the path)
            cursor.execute(
                "SELECT OfferOrderNumber, OfferFilePath FROM Offers WHERE OfferFilePath LIKE ?",
                (f"%{filename}",),
            )
            result = cursor.fetchone()
            conn.close()

            return result
        except sqlite3.Error:
            return None

    def get_all_offer_file_paths(self):
        """Get all offer file paths from database (relative paths)."""
        try:
            if not self.is_available():
                return []
            conn = sqlite3.connect(self._db_path())
            cursor = conn.cursor()

            # Get all offer file paths from database
            cursor.execute("SELECT OfferFilePath FROM Offers ORDER BY OfferOrderNumber DESC")
            results = cursor.fetchall()
            conn.close()

            # Return list of file paths
            return [result[0] for result in results] if results else []
        except sqlite3.Error as e:
            self._ctx.log(f"Database error in get_all_offer_file_paths: {e}")
            return []

    # ------------------------------------------------------------------
    # WZ (wuzetki)
    # ------------------------------------------------------------------
    def get_next_wz_number(self, year: int):
        """Get next WZ sequential number for a given year (requires WzYearNumber column).
        Błąd lub niedostępna baza przerywa operację (NumberingError) - nie zwraca się numeru domyślnego.
        """
        try:
            if not self.is_available():
                raise RuntimeError("Database unavailable")
            conn = sqlite3.connect(self._db_path())
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
            raise NumberingError(f"WZ yearly numbering error: {e}") from e

    def save_wz(self, wz_order_number, wz_file_path, wz_context=None):
        """Save WZ (assumes WzYearNumber column exists after migration)."""
        try:
            if self._file_missing():
                return False, "Baza danych jest niedostępna lub nie istnieje."
            conn = sqlite3.connect(self._db_path())
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
                try:
                    # Make a shallow copy to avoid mutating caller
                    _ctx = dict(wz_context)
                    for k in ('client_name', 'supplier_name'):
                        if k in _ctx and isinstance(_ctx[k], str):
                            if '<w:r>' in _ctx[k] or '<w:t' in _ctx[k]:
                                import re as _re
                                t = _ctx[k]
                                t = _re.sub(r'<w:[^>]+>', '', t)
                                t = t.replace('</w:t>', '').replace('</w:r>', '')
                                _ctx[k] = t
                    wz_context = _ctx
                except Exception:
                    pass
                context_json = json.dumps(wz_context, ensure_ascii=False)

            # Normalize path to relative before saving
            try:
                rel_wz_path = self._norm_wz(wz_file_path)
            except Exception:
                rel_wz_path = wz_file_path

            # Enforce strict 'YYYY/filename.ext' in DB
            try:
                parts = rel_wz_path.strip('/').split('/') if rel_wz_path else []
                if not (len(parts) >= 2 and len(parts[-2]) == 4 and parts[-2].isdigit()):
                    rel_wz_path = f"{wz_year}/{os.path.basename(rel_wz_path)}"
            except Exception:
                rel_wz_path = f"{wz_year}/{os.path.basename(str(rel_wz_path))}"

            if 'WzYearNumber' in cols:
                cursor.execute("INSERT INTO Wuzetkas (WzYearNumber, WzOrderNumber, WzFilePath, WzContext) VALUES (?, ?, ?, ?)",
                               (wz_year, wz_order_number, rel_wz_path, context_json))
            else:
                cursor.execute("INSERT INTO Wuzetkas (WzOrderNumber, WzFilePath, WzContext) VALUES (?, ?, ?)",
                               (wz_order_number, rel_wz_path, context_json))
            conn.commit()
            conn.close()
            return True, "WZ zostało zapisane do bazy danych"
        except sqlite3.Error as e:
            return False, f"Błąd podczas zapisywania WZ do bazy: {e}"

    def get_wz_context(self, wz_file_path):
        """Get WZ context from database by file path (accepts full or relative)."""
        try:
            if not self.is_available():
                return None
            conn = sqlite3.connect(self._db_path())
            cursor = conn.cursor()
            rel_path = self._norm_wz(wz_file_path)
            cursor.execute("SELECT WzContext FROM Wuzetkas WHERE WzFilePath = ?", (rel_path,))
            result = cursor.fetchone()
            conn.close()

            if result and result[0]:
                # Parse JSON context
                return json.loads(result[0])
            return None
        except sqlite3.Error as e:
            self._ctx.show_error("Database Error", f"Error retrieving WZ context: {e}")
            return None
        except json.JSONDecodeError as e:
            self._ctx.show_error("Data Error", f"Error parsing WZ context: {e}")
            return None

    def update_wz_context(self, wz_file_path, wz_context):
        """Update WZ context in database (accepts full or relative path)."""
        try:
            if not self.is_available():
                return False
            conn = sqlite3.connect(self._db_path())
            cursor = conn.cursor()

            # Convert context to JSON
            context_json = json.dumps(wz_context, default=str, ensure_ascii=False)
            rel_path = self._norm_wz(wz_file_path)
            cursor.execute("UPDATE Wuzetkas SET WzContext = ? WHERE WzFilePath = ?",
                           (context_json, rel_path))
            conn.commit()
            conn.close()
            return True
        except sqlite3.Error as e:
            self._ctx.show_error("Database Error", f"Error updating WZ context: {e}")
            return False

    def get_all_wz(self):
        """Get all WZ from database"""
        try:
            if not self.is_available():
                return []
            conn = sqlite3.connect(self._db_path())
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
                rel_wz_path = row[1]
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

                full_path = path_utils.build_full_wz_path(rel_wz_path, self._ctx.wz_folder()) if rel_wz_path else ''
                wz_data.append((wz_id, formatted_wz_number, date, client_name, "Utworzone", full_path))

            conn.close()
            return wz_data

        except sqlite3.Error as e:
            self._ctx.show_error("Database Error", f"Error accessing database: {e}")
            return []

    def delete_wz(self, wz_id):
        """Delete WZ from database (po samym numerze porządkowym - ze wszystkich lat)"""
        try:
            if self._file_missing():
                return False, "Baza danych jest niedostępna lub nie istnieje."
            conn = sqlite3.connect(self._db_path())
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

    def delete_wz_by_file_path(self, wz_file_path: str):
        """Delete a single WZ row using its unique file path (safer with year-based numbering)."""
        try:
            if self._file_missing():
                return False, "Baza danych jest niedostępna lub nie istnieje."
            conn = sqlite3.connect(self._db_path())
            cursor = conn.cursor()
            rel = self._norm_wz(wz_file_path)
            cursor.execute("DELETE FROM Wuzetkas WHERE WzFilePath = ?", (rel,))
            if cursor.rowcount == 0:
                conn.close()
                return False, "WZ nie zostało znalezione w bazie (po ścieżce)"
            conn.commit()
            conn.close()
            return True, "WZ zostało usunięte z bazy danych"
        except sqlite3.Error as e:
            return False, f"Błąd podczas usuwania WZ (po ścieżce): {e}"

    def get_all_wz_file_paths(self):
        """Get all WZ file paths from database"""
        try:
            conn = sqlite3.connect(self._db_path())
            cursor = conn.cursor()

            # Get all WZ file paths from database
            cursor.execute("SELECT WzFilePath FROM Wuzetkas ORDER BY WzOrderNumber DESC")
            results = cursor.fetchall()
            conn.close()

            # Return list of file paths
            return [result[0] for result in results] if results else []
        except sqlite3.Error as e:
            self._ctx.log(f"Database error in get_all_wz_file_paths: {e}")
            return []
