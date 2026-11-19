"""Backend SharePoint (DEV): odczyt czterech list oraz - od etapu 4A - zapis, aktualizacja i usuwanie klientów.

Zwraca dane z list SharePoint DEV w dokładnie takich samych kształtach i z takimi samymi konwencjami
błędów jak `SqliteBackend` (krotki pozycyjne, NIP jako int, sortowanie, formatowanie). Granica konwersji:
SharePoint przechowuje NIP jako 10-znakowy tekst (Title), a publiczny wynik ma NIP jako int.

Zapis klientów idzie wyłącznie przez `GraphWriter` (osobny moduł z zabezpieczeniami DEV-only i listą dozwolonych
list). Pozostałe operacje zapisu (dostawcy, oferty, WZ, numeracja) nadal zgłaszają `ReadOnlyBackendError`:
nie wykonują żadnych żądań i nigdy nie są przekierowywane do SQLite. Na tym etapie backend działa wyłącznie dla DEV.

Współbieżność: backend zapamiętuje ETag każdego klienta odczytanego przez `get_clients` / `get_client_by_nip`
oraz zapisanego przez siebie. Aktualizacja używa tego ETagu w nagłówku If-Match (a gdy klient nie był wcześniej
odczytany - ETagu z odczytu wykonanego tuż przed zapisem). Przy konflikcie (412) zapis nie jest ponawiany, a wynik
to (False, ConflictMessage).
"""
import json
import re
import time
from collections import namedtuple

from src.data import path_utils
from src.data.backends.base import BackendContext, DataBackend
from src.data.errors import (
    ConcurrencyConflictError, ConflictMessage, DataAccessError, ItemNotFoundError, ReadOnlyBackendError,
    SharePointError, UniqueConstraintError)
from src.integrations.sharepoint.config import DEV
from src.integrations.sharepoint.environment import get_active_environment
from src.integrations.sharepoint.graph_client import AuthError, GraphError
from src.integrations.sharepoint.migration.mapping import newline_to_comma
from src.integrations.sharepoint.reader import RetryingGraphClient
from src.integrations.sharepoint.session import NotSignedInError, SharePointSession
from src.integrations.sharepoint.writer import GraphWriteError, GraphWriter, WriteResult

DEFAULT_PAGE_SIZE = 999
MAX_PAGES = 500
FAILURE_COOLDOWN_SECONDS = 15

CLIENT_FIELDS = ("Title", "CompanyName", "AddressP1", "AddressP2", "Alias")
CLIENT_EXTENDED_FIELDS = ("TerminRealizacji", "TerminPlatnosci", "WarunkiDostawy", "WaznoscOferty", "Gwarancja", "Cena")
SUPPLIER_FIELDS = ("Title", "CompanyName", "AddressP1", "AddressP2", "IsDefault")

UNAVAILABLE_MESSAGE = "Baza danych jest niedostępna lub nie istnieje."
NIP_FORMAT_MESSAGE = "NIP musi składać się z dokładnie 10 cyfr"
ALIAS_TAKEN_MESSAGE = "Alias już istnieje dla innego klienta"
CLIENT_NOT_FOUND_MESSAGE = "Klient nie został znaleziony"
CONFLICT_MESSAGE = ("Dane klienta zostały zmienione przez innego użytkownika od czasu ich odczytu. "
                    "Zapis nie został wykonany - odśwież listę klientów i spróbuj ponownie.")

_Item = namedtuple("_Item", "id fields etag", defaults=(None,))


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
                 page_size: int = DEFAULT_PAGE_SIZE, client_factory=None, clock=time.monotonic,
                 writer_factory=None):
        self._ctx = context
        self._session = session
        self._env = environment or get_active_environment()
        if self._env.name != DEV or self._env.is_prod:
            raise DataAccessError("SharePointBackend działa na tym etapie wyłącznie dla środowiska DEV.")
        self._page_size = page_size
        self._client_factory = client_factory
        self._writer_factory = writer_factory
        self._clock = clock
        self._down_until = 0.0
        self._etags = {}  # Title klienta -> (ID elementu, ETag z ostatniego odczytu lub własnego zapisu)
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

    def _writer(self):
        if self._writer_factory is not None:
            return self._writer_factory()
        return GraphWriter(self._env, self._session.get_token())

    def _request(self, call, item_scope=False):
        """Odczyt: call(client). Zapis: patrz `_write`. Błędy Graph/uwierzytelniania => SharePointError (lub podtyp)."""
        return self._guarded(self._client, call, item_scope)

    def _write(self, call, item_scope=False):
        """Zapis: call(writer). `item_scope=True`: HTTP 404 oznacza brak elementu o podanym ID (ItemNotFoundError)."""
        return self._guarded(self._writer, call, item_scope)

    @staticmethod
    def _friendly(e):
        """Czytelny komunikat dla błędów zapisu; błędy odczytu zachowują dotychczasowe brzmienie."""
        if not isinstance(e, GraphWriteError):
            return f"Graph API: {e}"
        if e.status == 429:
            return "SharePoint tymczasowo ogranicza liczbę żądań (HTTP 429). Spróbuj ponownie za chwilę."
        if e.status is not None and e.status >= 500:
            return f"SharePoint jest chwilowo niedostępny (HTTP {e.status}). Spróbuj ponownie za chwilę."
        if e.status is None and e.ambiguous:
            return "Brak połączenia z SharePoint - wynik operacji jest nieznany. Sprawdź listę i spróbuj ponownie."
        return f"Graph API: {e}"

    def _guarded(self, factory, call, item_scope):
        try:
            result = call(factory())
        except NotSignedInError as e:
            raise SharePointError(str(e)) from e
        except AuthError as e:
            raise SharePointError(f"Błąd uwierzytelniania: {e}") from e
        except GraphError as e:
            if e.status == 401:
                self._session.invalidate_token()
            elif e.status is None or e.status >= 500 or e.status == 429:
                self._down_until = self._clock() + FAILURE_COOLDOWN_SECONDS
            if e.status == 412:
                raise ConcurrencyConflictError(f"Graph API: {e}") from e
            if item_scope and e.status == 404:
                raise ItemNotFoundError(f"Graph API: {e}") from e
            if isinstance(e, GraphWriteError) and e.status == 400 and "unique constraints" in str(e):
                raise UniqueConstraintError(f"Graph API: {e}") from e
            error = SharePointError(self._friendly(e))
            error.ambiguous = bool(getattr(e, "ambiguous", False))
            raise error from e
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
                    collected[int(raw["id"])] = (raw.get("fields") or {}, raw.get("@odata.etag") or raw.get("eTag"))
                next_link = data.get("@odata.nextLink")
                if not next_link:
                    return collected
                if pages >= MAX_PAGES:
                    raise SharePointError(f"Przekroczono limit stron ({MAX_PAGES}) przy odczycie listy {list_name}.")
                data = client.get(next_link)

        collected = self._request(run)
        return [_Item(i, *collected[i]) for i in sorted(collected)]

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
        # SharePoint nie odróżnia NULL od "" (pole puste jest pomijane), więc pusty tekst zwracamy jak SQLite: ""
        row = (nip, _text(f.get("CompanyName")), _text(f.get("AddressP1")), _text(f.get("AddressP2")),
               _text(f.get("Alias")))
        if extended:
            row += tuple(_text(f.get(k)) for k in CLIENT_EXTENDED_FIELDS)
        return row

    def _remember_etag(self, title, item_id, etag):
        if title and etag:
            self._etags[title] = (str(item_id), etag)

    def _forget_etag(self, title):
        self._etags.pop(title, None)

    def get_clients(self, include_extended: bool = False):
        try:
            if not self.is_available():
                return []
            fields = CLIENT_FIELDS + (CLIENT_EXTENDED_FIELDS if include_extended else ())
            items = self._items("Clients", fields)
            self._etags = {}  # pełny odczyt: ETagi odpowiadają dokładnie temu, co zobaczył użytkownik
            for item in items:
                self._remember_etag(item.fields.get("Title"), item.id, item.etag)
            rows = [r for r in (self._client_row(i, include_extended) for i in items) if r]
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
                self._remember_etag(title, item.id, item.etag)
                return self._client_row(item, False)
            return None
        except SharePointError as e:
            self._ctx.show_error("Database Error", f"Error accessing database: {e}")
            return None

    def validate_nip(self, nip):
        """Validate NIP format and uniqueness"""
        if not nip.isdigit() or len(nip) != 10:
            return False, NIP_FORMAT_MESSAGE
        title = self._nip_title(nip)
        if title is None:  # cyfry spoza ASCII - nie mogą być NIP-em
            return False, NIP_FORMAT_MESSAGE
        try:
            exists = bool(self._items_by_value("Clients", ("Title",), "Title", title))
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
    # klienci (zapis, aktualizacja, usuwanie)
    # ------------------------------------------------------------------
    @staticmethod
    def _same_alias(a, b):
        """SharePoint porównuje unikalne wartości bez rozróżniania wielkości liter."""
        return _text(a).casefold() == _text(b).casefold()

    def _alias_in_use(self, alias, ignore_title=None):
        for item in self._items("Clients", ("Title", "Alias")):
            if ignore_title is not None and item.fields.get("Title") == ignore_title:
                continue
            if self._same_alias(item.fields.get("Alias"), alias):
                return True
        return False

    def _find_client(self, title, fields=CLIENT_FIELDS + CLIENT_EXTENDED_FIELDS):
        """Dokładne dopasowanie po Title (NIP); None, gdy NIP jest nieprawidłowy lub klienta nie ma."""
        if title is None:
            return None
        found = self._items_by_value("Clients", fields, "Title", title)
        return found[0] if found else None

    def add_client(self, nip, company_name, address_p1, address_p2, alias):
        try:
            if not self.is_available():
                return False, UNAVAILABLE_MESSAGE
            nip_valid, nip_message = self.validate_nip(nip)
            if not nip_valid:
                return False, nip_message
            alias_valid, alias_message = self.validate_alias(alias)
            if not alias_valid:
                return False, alias_message
            if self._alias_in_use(alias):
                return False, ALIAS_TAKEN_MESSAGE

            title = self._nip_title(nip)
            values = {"Title": title, "CompanyName": company_name, "AddressP1": address_p1,
                      "AddressP2": newline_to_comma(address_p2), "Alias": alias}
            fields = {k: v for k, v in values.items() if v not in (None, "")}  # SharePoint nie przechowuje pustych pól
            try:
                created = self._write(lambda w: w.create_item("Clients", fields))
            except UniqueConstraintError:
                return False, self._explain_unique_conflict(title, alias)
            except SharePointError as e:
                created = self._confirm_created(title, fields) if getattr(e, "ambiguous", False) else None
                if created is None:
                    raise
            self._remember_etag(title, created.item_id, created.etag)
            return True, "Klient został pomyślnie dodany do bazy"
        except SharePointError as e:
            return False, f"Błąd podczas dodawania klienta: {e}"

    def _explain_unique_conflict(self, title, alias):
        """POST zwrócił 400 bez wskazania pola - odczyt weryfikacyjny ustala, która wartość jest zajęta."""
        items = self._items("Clients", ("Title", "Alias"))
        if any(item.fields.get("Title") == title for item in items):
            return "Klient z tym NIP już istnieje w bazie"
        if any(self._same_alias(item.fields.get("Alias"), alias) for item in items):
            return ALIAS_TAKEN_MESSAGE
        return "Klient nie został dodany: SharePoint zgłosił naruszenie unikalności (NIP lub alias)."

    def _confirm_created(self, title, fields):
        """Po niejednoznacznym błędzie POST (brak odpowiedzi, 5xx): czy element o tym NIP, nazwie i aliasie już istnieje?"""
        try:
            for item in self._items_by_value("Clients", ("Title", "CompanyName", "Alias"), "Title", title):
                if (item.fields.get("CompanyName") == fields.get("CompanyName")
                        and item.fields.get("Alias") == fields.get("Alias")):
                    return WriteResult(str(item.id), item.etag, item.fields)
        except SharePointError:
            return None
        return None

    def _patch_client(self, item, desired, success_message):
        """Zapisuje różnice między `desired` a stanem elementu z If-Match; bez różnic nie wysyła nic (brak nowej wersji)."""
        title = item.fields.get("Title")
        changed = {k: v for k, v in desired.items() if _text(item.fields.get(k)) != _text(v)}
        if not changed:
            return True, success_message
        body = {k: (None if v in (None, "") else v) for k, v in changed.items()}
        cached = self._etags.get(title)
        etag = cached[1] if cached and cached[0] == str(item.id) else item.etag
        if not etag:
            raise SharePointError("Brak ETagu elementu - nie można bezpiecznie zapisać zmian.")
        try:
            result = self._write(lambda w: w.update_item_fields("Clients", item.id, body, etag), item_scope=True)
        except ConcurrencyConflictError:
            self._forget_etag(title)
            return False, ConflictMessage(CONFLICT_MESSAGE)
        except ItemNotFoundError:
            self._forget_etag(title)
            return False, CLIENT_NOT_FOUND_MESSAGE
        except UniqueConstraintError:
            return False, ALIAS_TAKEN_MESSAGE
        except SharePointError as e:
            if getattr(e, "ambiguous", False):  # zapis mógł się udać - zapamiętany ETag jest już nieaktualny
                self._forget_etag(title)
            raise
        self._remember_etag(title, item.id, result.etag)
        return True, success_message

    def update_client(self, nip, company_name, address_p1, address_p2, alias):
        """Update client data (NIP cannot be changed)"""
        try:
            if not self.is_available():
                return False, UNAVAILABLE_MESSAGE
            title = self._nip_title(nip)
            if self._alias_in_use(alias, ignore_title=title):
                return False, ALIAS_TAKEN_MESSAGE
            alias_valid, alias_message = self.validate_alias(alias)
            if not alias_valid:
                return False, alias_message
            item = self._find_client(title)
            if item is None:  # świadoma różnica względem SQLite (tam: cichy sukces) - w SharePoint to realny błąd
                return False, CLIENT_NOT_FOUND_MESSAGE
            desired = {"CompanyName": company_name, "AddressP1": address_p1,
                       "AddressP2": newline_to_comma(address_p2), "Alias": alias}
            return self._patch_client(item, desired, "Dane klienta zostały zaktualizowane")
        except SharePointError as e:
            return False, f"Błąd podczas aktualizacji klienta: {e}"

    def set_client_extended_fields(self, nip, termin_realizacji=None, termin_platnosci=None,
                                   warunki_dostawy=None, waznosc_oferty=None,
                                   gwarancja=None, cena=None):
        """Update extended nullable text fields for a client by NIP.
        All parameters are optional; missing values will be set to NULL.
        """
        try:
            if not self.is_available():
                return False, UNAVAILABLE_MESSAGE
            item = self._find_client(self._nip_title(nip))
            if item is None:  # świadoma różnica względem SQLite (tam: cichy sukces) - w SharePoint to realny błąd
                return False, CLIENT_NOT_FOUND_MESSAGE
            values = dict(zip(CLIENT_EXTENDED_FIELDS, (termin_realizacji, termin_platnosci, warunki_dostawy,
                                                      waznosc_oferty, gwarancja, cena)))
            return self._patch_client(item, values, "Zapisano dodatkowe pola klienta")
        except SharePointError as e:
            return False, f"Błąd zapisu dodatkowych pól klienta: {e}"

    def _offers_for_alias(self, alias):
        """Liczba ofert, których ścieżka kończy się na `_{alias}.docx` (semantyka LIKE jak w SQLite)."""
        pattern = f"%_{alias}.docx"
        paths = (i.fields.get("OfferFilePath") for i in self._items("Offers", ("OfferFilePath",)))
        return sum(1 for path in paths if path is not None and sqlite_like(pattern, path))

    def _delete_verified(self, list_name, item_id, expected_title):
        """Usuwa element o dokładnym ID, ale dopiero po ponownym odczycie i sprawdzeniu, że jego Title to oczekiwany NIP."""
        text = str(item_id)
        if list_name != "Clients" or not (text.isascii() and text.isdigit()):
            raise SharePointError("Odmowa usunięcia: nieprawidłowa lista lub ID elementu.")
        path = f"/sites/{self._env.site_id}/lists/{self._env.lists[list_name]}/items/{text}"
        current = self._request(lambda c: c.get(path, {"$expand": "fields($select=Title)"}), item_scope=True)
        if (current.get("fields") or {}).get("Title") != expected_title:
            raise SharePointError(f"Odmowa usunięcia: element {text} nie odpowiada oczekiwanemu NIP-owi.")
        self._write(lambda w: w.delete_item(list_name, text), item_scope=True)

    def delete_client(self, nip):
        try:
            if not self.is_available():
                return False, UNAVAILABLE_MESSAGE
            title = self._nip_title(nip)
            item = self._find_client(title, ("Title", "Alias"))
            if item is None:
                return False, CLIENT_NOT_FOUND_MESSAGE
            offer_count = self._offers_for_alias(_text(item.fields.get("Alias")))
            if offer_count > 0:
                return False, f"Nie można usunąć klienta - istnieją {offer_count} ofert(y) dla tego klienta"
            try:
                self._delete_verified("Clients", item.id, title)
            except ItemNotFoundError:
                self._forget_etag(title)
                return False, CLIENT_NOT_FOUND_MESSAGE
            except SharePointError:
                self._forget_etag(title)  # po błędzie wynik usunięcia może być nieznany - nie ufamy starym danym
                raise
            self._forget_etag(title)
            return True, "Klient został usunięty z bazy"
        except SharePointError as e:
            return False, f"Błąd podczas usuwania klienta: {e}"

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
        title = self._nip_title(nip)
        if title is None:  # cyfry spoza ASCII - nie mogą być NIP-em
            return False, "NIP musi składać się z dokładnie 10 cyfr"
        try:
            if not self.is_available():
                return False, "Baza danych jest niedostępna"
            exists = bool(self._items_by_value("Suppliers", ("Title",), "Title", title))
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
    # operacje NIEOBSŁUGIWANE (dostawcy, oferty, WZ, numeracja) - bez żadnych żądań i bez przekierowania do SQLite
    # ------------------------------------------------------------------
    @staticmethod
    def _read_only(operation):
        raise ReadOnlyBackendError(
            f"Operacja '{operation}' nie jest jeszcze obsługiwana przez backend SharePoint (tryb tylko do odczytu).")

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
