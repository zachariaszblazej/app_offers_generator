"""Backend SharePoint - WYŁĄCZNIE ODCZYT (etap 3).

Zwraca dane z czterech list SharePoint DEV w dokładnie takich samych kształtach i z takimi samymi konwencjami
błędów jak `SqliteBackend` (krotki pozycyjne, NIP jako int, sortowanie, formatowanie). Granica konwersji:
SharePoint przechowuje NIP jako 10-znakowy tekst (Title), a publiczny wynik ma NIP jako int.

Zapis, aktualizacja, usuwanie i numerowanie NIE są obsługiwane: metody zgłaszają `ReadOnlyBackendError`,
nie wykonują żadnych żądań i nigdy nie przekierowują operacji do SQLite. Backend używa wyłącznie metody GET.
Na tym etapie działa wyłącznie dla środowiska DEV.
"""
import json
import re
import time
from collections import namedtuple

from src.data import path_utils
from src.data.backends.base import BackendContext, DataBackend
from src.data.errors import DataAccessError, ReadOnlyBackendError, SharePointError
from src.integrations.sharepoint.config import DEV
from src.integrations.sharepoint.environment import get_active_environment
from src.integrations.sharepoint.graph_client import AuthError, GraphError
from src.integrations.sharepoint.reader import RetryingGraphClient
from src.integrations.sharepoint.session import NotSignedInError, SharePointSession

DEFAULT_PAGE_SIZE = 999
MAX_PAGES = 500
FAILURE_COOLDOWN_SECONDS = 15

CLIENT_FIELDS = ("Title", "CompanyName", "AddressP1", "AddressP2", "Alias")
CLIENT_EXTENDED_FIELDS = ("TerminRealizacji", "TerminPlatnosci", "WarunkiDostawy", "WaznoscOferty", "Gwarancja", "Cena")
SUPPLIER_FIELDS = ("Title", "CompanyName", "AddressP1", "AddressP2", "IsDefault")

_Item = namedtuple("_Item", "id fields")


def sqlite_like(pattern: str, text: str) -> bool:
    """Semantyka operatora LIKE z SQLite: `%` i `_` jako wzorce, wielkość liter ignorowana tylko dla ASCII."""
    regex = []
    for ch in pattern:
        if ch == "%":
            regex.append(".*")
        elif ch == "_":
            regex.append(".")
        elif ch.isascii() and ch.isalpha():
            regex.append(f"[{ch.lower()}{ch.upper()}]")
        else:
            regex.append(re.escape(ch))
    return re.fullmatch("".join(regex), text, re.DOTALL) is not None


def _odata_quote(value: str) -> str:
    return value.replace("'", "''")


def _int(value):
    return None if value is None else int(value)


def _text(value):
    return "" if value is None else value


class SharePointBackend(DataBackend):
    def __init__(self, context: BackendContext, session: SharePointSession, environment=None,
                 page_size: int = DEFAULT_PAGE_SIZE, client_factory=None, clock=time.monotonic):
        self._ctx = context
        self._session = session
        self._env = environment or get_active_environment()
        if self._env.name != DEV or self._env.is_prod:
            raise DataAccessError("SharePointBackend działa na tym etapie wyłącznie dla środowiska DEV.")
        self._page_size = page_size
        self._client_factory = client_factory
        self._clock = clock
        self._down_until = 0.0
        self.page_requests = 0

    @property
    def environment(self):
        return self._env

    # ------------------------------------------------------------------
    # dostępność i dostęp do Graph
    # ------------------------------------------------------------------
    def is_available(self) -> bool:
        """Tanie sprawdzenie bez sieci: aktywna sesja i brak niedawnej awarii połączenia."""
        return self._session.is_active() and self._clock() >= self._down_until

    def _client(self):
        if self._client_factory is not None:
            return self._client_factory()
        return RetryingGraphClient(self._env, self._session.get_token())

    def _request(self, call):
        """Wykonuje call(client); błędy Graph/uwierzytelniania zamienia na SharePointError."""
        try:
            result = call(self._client())
        except NotSignedInError as e:
            raise SharePointError(str(e)) from e
        except AuthError as e:
            raise SharePointError(f"Błąd uwierzytelniania: {e}") from e
        except GraphError as e:
            if e.status == 401:
                self._session.invalidate_token()
            elif e.status is None or e.status >= 500 or e.status == 429:
                self._down_until = self._clock() + FAILURE_COOLDOWN_SECONDS
            raise SharePointError(f"Graph API: {e}") from e
        self._down_until = 0.0
        return result

    def _items(self, list_name, fields, odata_filter=None):
        """Wszystkie elementy listy (z paginacją przez @odata.nextLink), posortowane rosnąco po ID elementu."""
        path = f"/sites/{self._env.site_id}/lists/{self._env.lists[list_name]}/items"
        params = {"$select": "id", "$expand": f"fields($select={','.join(fields)})", "$top": str(self._page_size)}
        if odata_filter:
            params["$filter"] = odata_filter

        def run(client):
            collected, pages = {}, 0
            data = client.get(path, params)
            while True:
                pages += 1
                self.page_requests += 1
                for raw in data.get("value", []):
                    collected[int(raw["id"])] = raw.get("fields") or {}
                next_link = data.get("@odata.nextLink")
                if not next_link:
                    return collected
                if pages >= MAX_PAGES:
                    raise SharePointError(f"Przekroczono limit stron ({MAX_PAGES}) przy odczycie listy {list_name}.")
                data = client.get(next_link)

        collected = self._request(run)
        return [_Item(i, collected[i]) for i in sorted(collected)]

    def _items_by_value(self, list_name, fields, field, value):
        """Elementy z dokładną (wielkość liter) wartością pola; $filter w SharePoint ignoruje wielkość liter."""
        found = self._items(list_name, fields, f"fields/{field} eq '{_odata_quote(value)}'")
        return [i for i in found if i.fields.get(field) == value]

    # ------------------------------------------------------------------
    # pomocnicze: NIP, okienka błędów, ścieżki
    # ------------------------------------------------------------------
    @staticmethod
    def _nip_title(nip):
        """Tytuł SharePoint (10 cyfr) dla NIP-u podanego jako int lub tekst; None gdy nie może istnieć.
        Białe znaki na brzegach są pomijane - tak jak przy porównaniu z kolumną INTEGER w SQLite."""
        text = str(nip).strip()
        if not (text.isascii() and text.isdigit()) or len(text) > 10:
            return None
        return text.zfill(10)

    def _parse_nip(self, title):
        text = "" if title is None else str(title)
        if text.isascii() and text.isdigit():
            return int(text)
        self._ctx.log(f"Pominięto element listy o nieprawidłowym tytule (NIP): {text[:20]!r}")
        return None

    def _popup_if_enabled(self, message):
        if self._ctx.popups_enabled():
            self._ctx.show_error("Database Error", message)

    def _norm_offer(self, path):
        return path_utils.normalize_offer_path(path, self._ctx.offers_folder())

    def _norm_wz(self, path):
        return path_utils.normalize_wz_path(path, self._ctx.wz_folder())

    # ------------------------------------------------------------------
    # klienci (odczyt)
    # ------------------------------------------------------------------
    def _client_row(self, item, extended):
        nip = self._parse_nip(item.fields.get("Title"))
        if nip is None:
            return None
        f = item.fields
        row = (nip, f.get("CompanyName"), f.get("AddressP1"), f.get("AddressP2"), f.get("Alias"))
        if extended:
            row += tuple(_text(f.get(k)) for k in CLIENT_EXTENDED_FIELDS)
        return row

    def get_clients(self, include_extended: bool = False):
        try:
            if not self.is_available():
                return []
            fields = CLIENT_FIELDS + (CLIENT_EXTENDED_FIELDS if include_extended else ())
            rows = [r for r in (self._client_row(i, include_extended) for i in self._items("Clients", fields)) if r]
            rows.sort(key=lambda r: r[1] or "")  # jak ORDER BY CompanyName (porównanie kodów znaków)
            return rows
        except SharePointError as e:
            self._popup_if_enabled(f"Error accessing database: {e}")
            return []

    def get_client_by_nip(self, nip):
        try:
            if not self.is_available():
                return None
            title = self._nip_title(nip)
            if title is None:
                return None
            for item in self._items_by_value("Clients", CLIENT_FIELDS, "Title", title):
                return self._client_row(item, False)
            return None
        except SharePointError as e:
            self._ctx.show_error("Database Error", f"Error accessing database: {e}")
            return None

    def validate_nip(self, nip):
        """Validate NIP format and uniqueness"""
        if not nip.isdigit() or len(nip) != 10:
            return False, "NIP musi składać się z dokładnie 10 cyfr"
        try:
            exists = bool(self._items_by_value("Clients", ("Title",), "Title", self._nip_title(nip)))
            if exists:
                return False, "Klient z tym NIP już istnieje w bazie"
            return True, "NIP jest prawidłowy"
        except SharePointError as e:
            return False, f"Błąd sprawdzania NIP: {e}"

    def validate_alias(self, alias):
        """Validate alias format"""
        if not alias.strip():
            return False, "Alias nie może być pusty"
        return True, "Alias jest prawidłowy"

    # ------------------------------------------------------------------
    # dostawcy (odczyt)
    # ------------------------------------------------------------------
    def _supplier_row(self, item):
        nip = self._parse_nip(item.fields.get("Title"))
        if nip is None:
            return None
        f = item.fields
        return (nip, f.get("CompanyName"), f.get("AddressP1"), f.get("AddressP2"), 1 if f.get("IsDefault") else 0)

    def get_suppliers(self):
        try:
            if not self.is_available():
                return []
            rows = [r for r in (self._supplier_row(i) for i in self._items("Suppliers", SUPPLIER_FIELDS)) if r]
            rows.sort(key=lambda r: r[1] or "")
            return rows
        except SharePointError as e:
            self._popup_if_enabled(f"Error accessing database: {e}")
            return []

    def get_supplier_by_nip(self, nip):
        try:
            if not self.is_available():
                return None
            title = self._nip_title(nip)
            if title is None:
                return None
            for item in self._items_by_value("Suppliers", SUPPLIER_FIELDS, "Title", title):
                return self._supplier_row(item)
            return None
        except SharePointError as e:
            self._ctx.show_error("Database Error", f"Error accessing database: {e}")
            return None

    def get_default_supplier(self):
        try:
            if not self.is_available():
                return None
            for item in self._items("Suppliers", SUPPLIER_FIELDS):  # IsDefault nie jest zindeksowane - filtr po stronie klienta
                if item.fields.get("IsDefault"):
                    return self._supplier_row(item)
            return None
        except SharePointError as e:
            self._ctx.show_error("Database Error", f"Error accessing database: {e}")
            return None

    def validate_supplier_nip(self, nip):
        """Validate NIP format and uniqueness for suppliers"""
        if not nip.isdigit() or len(nip) != 10:
            return False, "NIP musi składać się z dokładnie 10 cyfr"
        try:
            if not self.is_available():
                return False, "Baza danych jest niedostępna"
            exists = bool(self._items_by_value("Suppliers", ("Title",), "Title", self._nip_title(nip)))
            if exists:
                return False, "Dostawca z tym NIP już istnieje w bazie"
            return True, "NIP jest prawidłowy"
        except SharePointError as e:
            return False, f"Błąd sprawdzania NIP: {e}"

    # ------------------------------------------------------------------
    # oferty (odczyt)
    # ------------------------------------------------------------------
    def _context_text(self, list_name, key_field, context_field, key):
        for item in self._items_by_value(list_name, (key_field, context_field), key_field, key):
            return item.fields.get(context_field)
        return None

    def get_offer_context(self, offer_file_path):
        """Get offer context by file path (accepts full or relative); kontekst pobierany na żądanie."""
        try:
            if not self.is_available():
                return None
            text = self._context_text("Offers", "OfferFilePath", "OfferContext", self._norm_offer(offer_file_path))
            if text:
                return json.loads(text)
            return None
        except SharePointError as e:
            self._popup_if_enabled(f"Error retrieving offer context: {e}")
            return None
        except json.JSONDecodeError as e:
            self._ctx.show_error("Data Error", f"Error parsing offer context: {e}")
            return None

    def find_offer_by_filename(self, filename):
        """Find offer by filename (dopasowanie końcówki ścieżki jak LIKE '%nazwa'); pierwszy wiersz wg ID."""
        try:
            if not self.is_available():
                return None
            pattern = f"%{filename}"
            for item in self._items("Offers", ("OfferOrderNumber", "OfferFilePath")):
                path = item.fields.get("OfferFilePath")
                if path is not None and sqlite_like(pattern, path):
                    return (_int(item.fields.get("OfferOrderNumber")), path)
            return None
        except SharePointError:
            return None

    def get_all_offer_file_paths(self):
        """All offer file paths (relative), sorted by OfferOrderNumber desc (bez uwzględnienia roku)."""
        try:
            if not self.is_available():
                return []
            items = self._items("Offers", ("OfferOrderNumber", "OfferFilePath"))
            items.sort(key=lambda i: -(_int(i.fields.get("OfferOrderNumber")) or 0))
            return [i.fields.get("OfferFilePath") for i in items]
        except SharePointError as e:
            self._ctx.log(f"Database error in get_all_offer_file_paths: {e}")
            return []

    # ------------------------------------------------------------------
    # WZ (odczyt)
    # ------------------------------------------------------------------
    def get_wz_context(self, wz_file_path):
        """Get WZ context by file path (accepts full or relative); kontekst pobierany na żądanie."""
        try:
            if not self.is_available():
                return None
            text = self._context_text("Wuzetkas", "WzFilePath", "WzContext", self._norm_wz(wz_file_path))
            if text:
                return json.loads(text)
            return None
        except SharePointError as e:
            self._ctx.show_error("Database Error", f"Error retrieving WZ context: {e}")
            return None
        except json.JSONDecodeError as e:
            self._ctx.show_error("Data Error", f"Error parsing WZ context: {e}")
            return None

    def get_all_wz(self):
        """Get all WZ: (id, numer, data, klient, status, pełna ścieżka); sortowanie po numerze malejąco."""
        try:
            if not self.is_available():
                return []
            items = self._items("Wuzetkas", ("WzOrderNumber", "WzFilePath", "WzContext"))
            items.sort(key=lambda i: -(_int(i.fields.get("WzOrderNumber")) or 0))
            wz_data = []
            for item in items:
                wz_number = _int(item.fields.get("WzOrderNumber"))
                rel_wz_path = item.fields.get("WzFilePath")
                context_json = item.fields.get("WzContext")

                client_name = "N/A"
                date = "N/A"
                if context_json:
                    try:
                        context = json.loads(context_json)
                        client_name = context.get('client_name', 'N/A')
                        date = context.get('date', 'N/A')
                    except Exception:
                        pass

                # (zachowane historyczne zachowanie: numer z bieżącym rokiem)
                if isinstance(wz_number, int):
                    import datetime
                    year = datetime.datetime.now().year
                    formatted_wz_number = f"WZ_{wz_number}_{year}"
                else:
                    formatted_wz_number = str(wz_number)

                full_path = path_utils.build_full_wz_path(rel_wz_path, self._ctx.wz_folder()) if rel_wz_path else ''
                wz_data.append((wz_number, formatted_wz_number, date, client_name, "Utworzone", full_path))
            return wz_data
        except SharePointError as e:
            self._ctx.show_error("Database Error", f"Error accessing database: {e}")
            return []

    def get_all_wz_file_paths(self):
        """All WZ file paths, sorted by WzOrderNumber desc."""
        try:
            items = self._items("Wuzetkas", ("WzOrderNumber", "WzFilePath"))
            items.sort(key=lambda i: -(_int(i.fields.get("WzOrderNumber")) or 0))
            return [i.fields.get("WzFilePath") for i in items]
        except SharePointError as e:
            self._ctx.log(f"Database error in get_all_wz_file_paths: {e}")
            return []

    # ------------------------------------------------------------------
    # operacje NIEOBSŁUGIWANE w trybie tylko do odczytu (bez żadnych żądań i bez przekierowania do SQLite)
    # ------------------------------------------------------------------
    @staticmethod
    def _read_only(operation):
        raise ReadOnlyBackendError(
            f"Operacja '{operation}' nie jest jeszcze obsługiwana przez backend SharePoint (tryb tylko do odczytu).")

    def add_client(self, nip, company_name, address_p1, address_p2, alias):
        self._read_only("add_client")

    def update_client(self, nip, company_name, address_p1, address_p2, alias):
        self._read_only("update_client")

    def set_client_extended_fields(self, nip, termin_realizacji=None, termin_platnosci=None,
                                   warunki_dostawy=None, waznosc_oferty=None, gwarancja=None, cena=None):
        self._read_only("set_client_extended_fields")

    def delete_client(self, nip):
        self._read_only("delete_client")

    def add_supplier(self, nip, company_name, address_p1, address_p2):
        self._read_only("add_supplier")

    def update_supplier(self, nip, company_name, address_p1, address_p2):
        self._read_only("update_supplier")

    def delete_supplier(self, nip):
        self._read_only("delete_supplier")

    def set_default_supplier(self, nip):
        self._read_only("set_default_supplier")

    def get_next_offer_number(self):
        self._read_only("get_next_offer_number")

    def get_next_offer_number_for_year(self, year: int):
        self._read_only("get_next_offer_number_for_year")

    def save_offer(self, offer_order_number, offer_file_path, offer_context=None):
        self._read_only("save_offer")

    def update_offer_context(self, offer_file_path, offer_context):
        self._read_only("update_offer_context")

    def delete_offer(self, offer_file_path):
        self._read_only("delete_offer")

    def get_next_wz_number(self, year: int):
        self._read_only("get_next_wz_number")

    def save_wz(self, wz_order_number, wz_file_path, wz_context=None):
        self._read_only("save_wz")

    def update_wz_context(self, wz_file_path, wz_context):
        self._read_only("update_wz_context")

    def delete_wz(self, wz_id):
        self._read_only("delete_wz")

    def delete_wz_by_file_path(self, wz_file_path: str):
        self._read_only("delete_wz_by_file_path")
