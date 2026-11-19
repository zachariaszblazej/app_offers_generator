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
    ConcurrencyConflictError, ConflictMessage, DataAccessError, ItemNotFoundError, PartialFailureMessage,
    ReadOnlyBackendError, SharePointError, UniqueConstraintError)
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
ETAG_LISTS = ("Clients", "Suppliers")
DELETABLE_LISTS = ("Clients", "Suppliers")

UNAVAILABLE_MESSAGE = "Baza danych jest niedostępna lub nie istnieje."
NIP_FORMAT_MESSAGE = "NIP musi składać się z dokładnie 10 cyfr"
ALIAS_TAKEN_MESSAGE = "Alias już istnieje dla innego klienta"
CLIENT_NOT_FOUND_MESSAGE = "Klient nie został znaleziony"
CONFLICT_MESSAGE = ("Dane klienta zostały zmienione przez innego użytkownika od czasu ich odczytu. "
                    "Zapis nie został wykonany - odśwież listę klientów i spróbuj ponownie.")
SUPPLIER_NOT_FOUND_MESSAGE = "Dostawca nie został znaleziony"
SUPPLIER_NIP_TAKEN_MESSAGE = "Dostawca z tym NIP już istnieje w bazie"
SUPPLIER_DEFAULT_REMOVAL_MESSAGE = "Nie można usunąć domyślnego dostawcy. Najpierw ustaw innego dostawcę jako domyślny."
SUPPLIER_UPDATE_CONFLICT_MESSAGE = ("Dane dostawcy zostały zmienione przez innego użytkownika od czasu ich odczytu. "
                                    "Zapis nie został wykonany - odśwież listę dostawców i spróbuj ponownie.")
SUPPLIER_REMOVAL_CONFLICT_MESSAGE = ("Dane dostawcy zostały zmienione przez innego użytkownika od czasu ich odczytu. "
                                    "Dostawca nie został usunięty - odśwież listę dostawców i spróbuj ponownie.")
SUPPLIER_DEFAULT_SET_MESSAGE = "Dostawca został ustawiony jako domyślny"
SUPPLIER_DEFAULT_CONFLICT_MESSAGE = ("Dane dostawców zostały zmienione przez innego użytkownika od czasu ich odczytu. "
                                    "Zmiana domyślnego dostawcy nie została wykonana - odśwież listę dostawców i spróbuj ponownie.")
SUPPLIER_DEFAULT_CHANGED_MESSAGE = ("Inny użytkownik zmienił domyślnego dostawcę w trakcie operacji. Odśwież listę dostawców "
                                    "i ponownie ustaw wybranego dostawcę jako domyślnego.")
DEFAULT_SUPPLIER_FIELDS = ("Title", "CompanyName", "IsDefault")

# Pola, które wolno zmieniać przy aktualizacji elementu. Dla dostawców celowo nie ma tu IsDefault (to zadanie set_default_supplier).
UPDATABLE_FIELDS = {
    "Clients": frozenset(CLIENT_FIELDS[1:] + CLIENT_EXTENDED_FIELDS),
    "Suppliers": frozenset({"CompanyName", "AddressP1", "AddressP2"}),
}

_Item = namedtuple("_Item", "id fields etag", defaults=(None,))


class _DeleteRefused(SharePointError):
    """Usunięcie odrzucone na podstawie świeżo odczytanych danych (np. dostawca stał się domyślny)."""


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
        self._etags = {}  # (lista, Title) -> (ID elementu, ETag z ostatniego odczytu lub własnego zapisu)
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

    def _remember_etag(self, list_name, title, item_id, etag):
        if title and etag:
            self._etags[self._etag_key(list_name, title)] = (str(item_id), etag)

    def _forget_etag(self, list_name, title):
        self._etags.pop(self._etag_key(list_name, title), None)

    def _cached_etag(self, list_name, title, item_id):
        """ETag zapamiętany dla elementu tej listy i tego ID (po zmianie ID, np. usunięcie i ponowne dodanie, brak)."""
        cached = self._etags.get(self._etag_key(list_name, title))
        return cached[1] if cached and cached[0] == str(item_id) else None

    def _replace_etags(self, list_name, items):
        """Pełny odczyt listy: ETagi tej listy odpowiadają dokładnie temu, co zobaczył użytkownik; inne listy bez zmian."""
        for key in [k for k in self._etags if k[0] == list_name]:
            del self._etags[key]
        for item in items:
            self._remember_etag(list_name, item.fields.get("Title"), item.id, item.etag)

    @staticmethod
    def _etag_key(list_name, title):
        """Klucz pamięci ETagów: (lista, Title). Ten sam NIP może istnieć jednocześnie jako klient i dostawca."""
        if list_name not in ETAG_LISTS:
            raise ValueError(f"Pamięć ETagów nie obsługuje listy {list_name!r}.")
        return (list_name, title)

    def get_clients(self, include_extended: bool = False):
        try:
            if not self.is_available():
                return []
            fields = CLIENT_FIELDS + (CLIENT_EXTENDED_FIELDS if include_extended else ())
            items = self._items("Clients", fields)
            self._replace_etags("Clients", items)
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
                self._remember_etag("Clients", title, item.id, item.etag)
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
            self._remember_etag("Clients", title, created.item_id, created.etag)
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
        """Zapis zmian klienta (patrz `_patch_item`); zachowanie bez zmian względem etapu 4A."""
        return self._patch_item("Clients", item, desired, success_message, conflict_message=CONFLICT_MESSAGE,
                                not_found_message=CLIENT_NOT_FOUND_MESSAGE, unique_message=ALIAS_TAKEN_MESSAGE)

    def _patch_item(self, list_name, item, desired, success_message, *, conflict_message, not_found_message,
                    unique_message=None, verify_ambiguous=False):
        """Zapisuje różnice między `desired` a stanem elementu z If-Match; bez różnic nie wysyła nic (brak nowej wersji).

        Wysyłane są wyłącznie pola z UPDATABLE_FIELDS tej listy (dla dostawców nigdy IsDefault). 412 => ConflictMessage,
        404 => `not_found_message`; żaden z nich nie jest ponawiany. Po niejednoznacznym błędzie (5xx, brak odpowiedzi)
        zapamiętany ETag jest odrzucany, a przy `verify_ambiguous` odczyt weryfikujący ustala, czy zmiana została zapisana
        (zapis nigdy nie jest ponawiany w ciemno)."""
        forbidden = set(desired) - UPDATABLE_FIELDS[list_name]
        if forbidden:
            raise DataAccessError(f"Pola niedozwolone przy aktualizacji listy {list_name}: {sorted(forbidden)}")
        title = item.fields.get("Title")
        changed = {k: v for k, v in desired.items() if _text(item.fields.get(k)) != _text(v)}
        if not changed:
            return True, success_message
        body = {k: (None if v in (None, "") else v) for k, v in changed.items()}
        etag = self._cached_etag(list_name, title, item.id) or item.etag
        if not etag:
            raise SharePointError("Brak ETagu elementu - nie można bezpiecznie zapisać zmian.")
        try:
            result = self._write(lambda w: w.update_item_fields(list_name, item.id, body, etag), item_scope=True)
        except ConcurrencyConflictError:
            self._forget_etag(list_name, title)
            return False, ConflictMessage(conflict_message)
        except ItemNotFoundError:
            self._forget_etag(list_name, title)
            return False, not_found_message
        except UniqueConstraintError:
            if unique_message is None:
                raise
            return False, unique_message
        except SharePointError as e:
            if getattr(e, "ambiguous", False):  # zapis mógł się udać - zapamiętany ETag jest już nieaktualny
                self._forget_etag(list_name, title)
                if verify_ambiguous:
                    verdict = self._verify_patch(list_name, title, item, changed)
                    if verdict is not None:
                        kind, current = verdict
                        if kind == "applied":
                            self._remember_etag(list_name, title, current.id, current.etag)
                            return True, success_message
                        if kind == "missing":
                            return False, not_found_message
                        if kind == "foreign":
                            return False, ConflictMessage(conflict_message)
                        raise SharePointError(f"{e} Odczyt weryfikujący potwierdził, że zmiana nie została zapisana.") from e
            raise
        self._remember_etag(list_name, title, item.id, result.etag)
        return True, success_message

    def _verify_patch(self, list_name, title, previous, changed):
        """Po niejednoznacznym zapisie pól: odczyt ustala, czy zmiana jest zapisana ('applied'), nie jest ('not_applied'),
        element zmienił ktoś inny ('foreign') albo zniknął ('missing'). None, gdy odczyt się nie powiódł."""
        try:
            found = self._items_by_value(list_name, ("Title",) + tuple(changed), "Title", title)
        except SharePointError:
            return None
        if not found:
            return "missing", None
        current = found[0]
        if current.id != previous.id:
            return "foreign", current
        if all(_text(current.fields.get(k)) == _text(v) for k, v in changed.items()):
            return "applied", current
        if all(_text(current.fields.get(k)) == _text(previous.fields.get(k)) for k in changed):
            return "not_applied", current
        return "foreign", current

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

    def _delete_verified(self, list_name, item_id, expected_title, select=("Title",), refuse=None):
        """Usuwa element o dokładnym ID, ale dopiero po ponownym odczycie i sprawdzeniu, że jego Title to oczekiwany NIP.

        Odczyt dostarcza aktualny ETag, który trafia do If-Match: jeśli element zmienił się po odczycie (412),
        nie jest usuwany. Bez ETagu usunięcie jest odmawiane (brak wariantu zapasowego bez If-Match).
        `refuse(fields)` (opcjonalne) ocenia pola z TEGO SAMEGO odczytu, z którego pochodzi ETag, i może zwrócić
        komunikat odmowy - dzięki temu późniejsza zmiana elementu kończy się 412, a nie usunięciem."""
        text = str(item_id)
        if list_name not in DELETABLE_LISTS or not (text.isascii() and text.isdigit()):
            raise SharePointError("Odmowa usunięcia: nieprawidłowa lista lub ID elementu.")
        path = f"/sites/{self._env.site_id}/lists/{self._env.lists[list_name]}/items/{text}"
        expand = f"fields($select={','.join(select)})"
        current = self._request(lambda c: c.get(path, {"$expand": expand}), item_scope=True)
        fields = current.get("fields") or {}
        if fields.get("Title") != expected_title:
            raise SharePointError(f"Odmowa usunięcia: element {text} nie odpowiada oczekiwanemu NIP-owi.")
        if refuse is not None:
            message = refuse(fields)
            if message:
                raise _DeleteRefused(message)
        etag = current.get("@odata.etag") or current.get("eTag")
        if not etag:
            raise SharePointError("Odmowa usunięcia: brak ETagu elementu (wymagany konkretny If-Match).")
        self._write(lambda w: w.delete_item(list_name, text, etag), item_scope=True)

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
                self._forget_etag("Clients", title)
                return False, CLIENT_NOT_FOUND_MESSAGE
            except ConcurrencyConflictError:
                self._forget_etag("Clients", title)
                return False, ConflictMessage(CONFLICT_MESSAGE)
            except SharePointError:
                self._forget_etag("Clients", title)  # po błędzie wynik usunięcia może być nieznany
                raise
            self._forget_etag("Clients", title)
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
        # pusty tekst zwracamy jak SQLite: "" (SharePoint pomija pola puste); IsDefault jako int 0/1
        return (nip, _text(f.get("CompanyName")), _text(f.get("AddressP1")), _text(f.get("AddressP2")),
                1 if f.get("IsDefault") else 0)

    def get_suppliers(self):
        try:
            if not self.is_available():
                return []
            items = self._items("Suppliers", SUPPLIER_FIELDS)
            self._replace_etags("Suppliers", items)
            rows = [r for r in (self._supplier_row(i) for i in items) if r]
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
                self._remember_etag("Suppliers", title, item.id, item.etag)
                return self._supplier_row(item)
            return None
        except SharePointError as e:
            self._ctx.show_error("Database Error", f"Error accessing database: {e}")
            return None

    def get_default_supplier(self):
        try:
            if not self.is_available():
                return None
            defaults = [i for i in self._items("Suppliers", SUPPLIER_FIELDS)  # IsDefault nie jest zindeksowane - filtr po stronie klienta
                        if i.fields.get("IsDefault")]
            if len(defaults) > 1:  # odczyt niczego nie naprawia; w logu tylko ID elementów (bez NIP i nazw)
                self._ctx.log(f"Wykryto {len(defaults)} domyślnych dostawców (ID elementów: "
                              f"{', '.join(str(i.id) for i in defaults)}); zwrócono pierwszego wg ID. "
                              "Ponowne ustawienie domyślnego dostawcy naprawi stan.")
            return self._supplier_row(defaults[0]) if defaults else None
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
    # dostawcy (zapis, aktualizacja, usuwanie) - IsDefault zmienia wyłącznie set_default_supplier (etap 4B-3)
    # ------------------------------------------------------------------
    def _find_supplier(self, title, fields=("Title", "CompanyName", "AddressP1", "AddressP2")):
        """Dokładne dopasowanie po Title (NIP); None, gdy NIP jest nieprawidłowy lub dostawcy nie ma."""
        if title is None:
            return None
        found = self._items_by_value("Suppliers", fields, "Title", title)
        return found[0] if found else None

    def add_supplier(self, nip, company_name, address_p1, address_p2):
        try:
            if not self.is_available():
                return False, UNAVAILABLE_MESSAGE
            nip_valid, nip_message = self.validate_supplier_nip(nip)  # format i zajętość NIP - przed jakimkolwiek POST
            if not nip_valid:
                return False, nip_message
            title = self._nip_title(nip)
            values = {"Title": title, "CompanyName": company_name, "AddressP1": address_p1, "AddressP2": address_p2}
            fields = {k: v for k, v in values.items() if v not in (None, "")}  # nigdy null dla pól tekstowych
            fields["IsDefault"] = False  # nowy dostawca nigdy nie jest domyślny
            try:
                created = self._write(lambda w: w.create_item("Suppliers", fields))
            except UniqueConstraintError:
                return False, self._explain_supplier_conflict(title)
            except SharePointError as e:
                if not getattr(e, "ambiguous", False):
                    raise
                created = self._confirm_supplier_created(title, fields)  # POST nigdy nie jest ponawiany
                if created == "foreign":
                    return False, SUPPLIER_NIP_TAKEN_MESSAGE
                if created is None:
                    raise
            self._remember_etag("Suppliers", title, created.item_id, created.etag)
            return True, "Dostawca został pomyślnie dodany do bazy"
        except SharePointError as e:
            return False, f"Błąd podczas dodawania dostawcy: {e}"

    def _explain_supplier_conflict(self, title):
        """POST zwrócił 400 bez wskazania pola - odczyt weryfikacyjny sprawdza, czy NIP rzeczywiście jest zajęty."""
        if self._items_by_value("Suppliers", ("Title",), "Title", title):
            return SUPPLIER_NIP_TAKEN_MESSAGE
        return "Dostawca nie został dodany: SharePoint zgłosił naruszenie unikalności (NIP)."

    def _confirm_supplier_created(self, title, fields):
        """Po niejednoznacznym błędzie POST: odczyt po NIP. WriteResult - to nasz rekord (nazwa i adresy zgodne),
        "foreign" - NIP zajmuje rekord z innymi danymi (utworzony przez kogoś innego), None - brak rekordu lub odczyt się nie udał."""
        try:
            found = self._items_by_value("Suppliers", ("Title", "CompanyName", "AddressP1", "AddressP2", "IsDefault"), "Title", title)
        except SharePointError:
            return None
        if not found:
            return None
        item = found[0]
        same = all(_text(item.fields.get(k)) == _text(fields.get(k)) for k in ("CompanyName", "AddressP1", "AddressP2"))
        if same and not item.fields.get("IsDefault"):
            return WriteResult(str(item.id), item.etag, item.fields)
        return "foreign"

    def update_supplier(self, nip, company_name, address_p1, address_p2):
        """Update supplier data (NIP cannot be changed); nigdy nie dotyka IsDefault."""
        try:
            if not self.is_available():
                return False, UNAVAILABLE_MESSAGE
            item = self._find_supplier(self._nip_title(nip))
            if item is None:
                return False, SUPPLIER_NOT_FOUND_MESSAGE
            desired = {"CompanyName": company_name, "AddressP1": address_p1, "AddressP2": address_p2}
            return self._patch_item("Suppliers", item, desired, "Dane dostawcy zostały zaktualizowane",
                                    conflict_message=SUPPLIER_UPDATE_CONFLICT_MESSAGE,
                                    not_found_message=SUPPLIER_NOT_FOUND_MESSAGE, verify_ambiguous=True)
        except SharePointError as e:
            return False, f"Błąd podczas aktualizacji dostawcy: {e}"

    @staticmethod
    def _refuse_default_supplier(fields):
        return SUPPLIER_DEFAULT_REMOVAL_MESSAGE if fields.get("IsDefault") else None

    def delete_supplier(self, nip):
        try:
            if not self.is_available():
                return False, UNAVAILABLE_MESSAGE
            title = self._nip_title(nip)
            item = self._find_supplier(title, ("Title", "IsDefault"))
            if item is None:
                return False, SUPPLIER_NOT_FOUND_MESSAGE
            if item.fields.get("IsDefault"):
                return False, SUPPLIER_DEFAULT_REMOVAL_MESSAGE
            try:
                # ponowna weryfikacja ID, Title i IsDefault w odczycie, z którego pochodzi ETag dla If-Match
                self._delete_verified("Suppliers", item.id, title, select=("Title", "IsDefault"),
                                      refuse=self._refuse_default_supplier)
            except _DeleteRefused as e:
                return False, str(e)
            except ItemNotFoundError:
                self._forget_etag("Suppliers", title)
                return False, SUPPLIER_NOT_FOUND_MESSAGE
            except ConcurrencyConflictError:
                self._forget_etag("Suppliers", title)
                return False, ConflictMessage(SUPPLIER_REMOVAL_CONFLICT_MESSAGE)
            except SharePointError:
                self._forget_etag("Suppliers", title)  # po błędzie wynik usunięcia może być nieznany
                raise
            self._forget_etag("Suppliers", title)
            return True, "Dostawca został usunięty z bazy"
        except SharePointError as e:
            return False, f"Błąd podczas usuwania dostawcy: {e}"

    # --- set_default_supplier: kilka niezależnych zapisów bez transakcji, więc kolejność i weryfikacja są kluczowe ---
    @staticmethod
    def _display_name(fields):
        return _text(fields.get("CompanyName")).replace("\\n", " ").strip() or "(bez nazwy)"

    def _read_default_flag(self, item_id):
        """Odczyt flagi jednego dostawcy po ID: ('ok', bool), ('missing', None) lub ('unknown', None) przy błędzie odczytu."""
        path = f"/sites/{self._env.site_id}/lists/{self._env.lists['Suppliers']}/items/{item_id}"
        try:
            current = self._request(lambda c: c.get(path, {"$expand": "fields($select=Title,IsDefault)"}), item_scope=True)
        except ItemNotFoundError:
            return "missing", None
        except SharePointError:
            return "unknown", None
        return "ok", bool((current.get("fields") or {}).get("IsDefault"))

    def _write_default_flag(self, item, value):
        """Jedyne miejsce zapisu IsDefault: konkretny ETag z odczytu (nigdy `*`), wartość true/false (nigdy null)."""
        etag = item.etag
        if not etag:
            raise SharePointError("Brak ETagu elementu - nie można bezpiecznie zapisać zmian.")
        result = self._write(lambda w: w.update_item_fields("Suppliers", item.id, {"IsDefault": value}, etag), item_scope=True)
        self._remember_etag("Suppliers", item.fields.get("Title"), item.id, result.etag)

    def _enable_default(self, target):
        """Krok B: ustawia target jako domyślnego. None = target jest domyślny (zapisany lub potwierdzony odczytem);
        w przeciwnym razie gotowy wynik (False, komunikat). Niepowodzenie bez zmiany stanu zgłasza SharePointError."""
        title = target.fields.get("Title")
        try:
            self._write_default_flag(target, True)
            return None
        except ConcurrencyConflictError:
            self._forget_etag("Suppliers", title)
            return False, ConflictMessage(SUPPLIER_DEFAULT_CONFLICT_MESSAGE)
        except ItemNotFoundError:
            self._forget_etag("Suppliers", title)
            return False, SUPPLIER_NOT_FOUND_MESSAGE
        except SharePointError as e:
            if not getattr(e, "ambiguous", False):
                raise  # żądanie odrzucone: nic się nie zmieniło
            self._forget_etag("Suppliers", title)
            kind, flag = self._read_default_flag(target.id)  # zapis mógł się udać - ustalamy odczytem, bez ponawiania
            if kind == "ok" and flag:
                return None
            if kind == "missing":
                return False, SUPPLIER_NOT_FOUND_MESSAGE
            if kind == "ok":
                raise SharePointError(f"{e} Odczyt weryfikujący potwierdził, że zmiana nie została zapisana.") from e
            return False, PartialFailureMessage(
                f"Nie udało się potwierdzić wyniku ustawienia dostawcy „{self._display_name(target.fields)}” jako domyślnego "
                f"({e}). Stan w SharePoint jest nieznany - odśwież listę dostawców i ponownie ustaw wybranego dostawcę "
                "jako domyślnego.")

    def _disable_default(self, other):
        """Krok C: odznacza jednego dotychczasowego domyślnego. None = nie jest już domyślny (odznaczony, usunięty lub
        potwierdzony odczytem); w przeciwnym razie tekst przyczyny. Nigdy nie ponawia zapisu i nie zgłasza wyjątku."""
        title = other.fields.get("Title")
        try:
            self._write_default_flag(other, False)
            return None
        except ItemNotFoundError:
            self._forget_etag("Suppliers", title)
            return None  # element zniknął, więc nie jest już domyślny
        except ConcurrencyConflictError:
            self._forget_etag("Suppliers", title)
            return self._still_default_cause(other, "element został zmieniony przez innego użytkownika (konflikt wersji)")
        except SharePointError as e:
            if getattr(e, "ambiguous", False):
                self._forget_etag("Suppliers", title)
                return self._still_default_cause(other, str(e))
            return str(e)

    def _still_default_cause(self, other, cause):
        kind, flag = self._read_default_flag(other.id)
        if kind == "missing" or (kind == "ok" and not flag):
            return None  # odczyt potwierdził, że flaga jest już zdjęta
        return cause if kind == "ok" else f"{cause}; nie udało się potwierdzić stanu odczytem"

    def _partial_default_message(self, target, other, cause, remaining):
        more = f" oraz {remaining} kolejnych" if remaining else ""
        return PartialFailureMessage(
            f"Dostawca „{self._display_name(target.fields)}” jest ustawiony jako domyślny, ale nie udało się odznaczyć "
            f"dotychczasowego domyślnego dostawcy („{self._display_name(other.fields)}”{more}): {cause.rstrip('.')}. "
            "W SharePoint jest teraz więcej niż jeden domyślny dostawca. Odśwież listę dostawców i ponownie ustaw wybranego "
            "dostawcę jako domyślnego - operacja naprawi stan.")

    def _verify_single_default(self, target):
        """Krok D: sukces dopiero po świeżym odczycie potwierdzającym dokładnie jednego domyślnego - target."""
        try:
            items = self._items("Suppliers", ("Title", "CompanyName", "IsDefault"))
        except SharePointError as e:
            return False, PartialFailureMessage(
                f"Zmiany zostały wysłane, ale nie udało się potwierdzić końcowego stanu domyślnego dostawcy ({e}). "
                "Odśwież listę dostawców i ponownie ustaw wybranego dostawcę jako domyślnego.")
        defaults = [i for i in items if i.fields.get("IsDefault")]
        current = next((i for i in items if i.id == target.id), None)
        if current is None:
            return False, PartialFailureMessage(
                "Dostawca został usunięty w trakcie zmiany domyślnego dostawcy. Odśwież listę dostawców i ustaw domyślnego "
                "dostawcę ponownie.")
        if not current.fields.get("IsDefault"):
            return False, ConflictMessage(SUPPLIER_DEFAULT_CHANGED_MESSAGE)
        if len(defaults) > 1:
            return False, PartialFailureMessage(
                f"Dostawca „{self._display_name(current.fields)}” jest ustawiony jako domyślny, ale w SharePoint jest teraz "
                f"{len(defaults)} domyślnych dostawców (zmiana wykonana równolegle przez innego użytkownika). Odśwież listę "
                "dostawców i ponownie ustaw wybranego dostawcę jako domyślnego - operacja naprawi stan.")
        return True, SUPPLIER_DEFAULT_SET_MESSAGE

    def set_default_supplier(self, nip):
        """Set supplier as default (only one can be default at a time).

        Brak transakcji Graph obejmującej wiele elementów, więc: (A) świeży odczyt listy z ETagami, (B) najpierw ustawienie
        wskazanego dostawcy (nigdy stan „brak domyślnego”), (C) odznaczenie pozostałych po kolei, (D) odczyt weryfikujący.
        Operacja jest idempotentna i samonaprawiająca; po częściowej awarii wynik to (False, PartialFailureMessage)."""
        try:
            if not self.is_available():
                return False, UNAVAILABLE_MESSAGE
            title = self._nip_title(nip)
            items = self._items("Suppliers", DEFAULT_SUPPLIER_FIELDS)  # krok A: zawsze świeży odczyt, nie pamięć ETagów
            target = next((i for i in items if title is not None and i.fields.get("Title") == title), None)
            if target is None:
                return False, SUPPLIER_NOT_FOUND_MESSAGE
            others = [i for i in items if i.id != target.id and i.fields.get("IsDefault")]
            target_is_default = bool(target.fields.get("IsDefault"))
            if target_is_default and not others:
                return True, SUPPLIER_DEFAULT_SET_MESSAGE  # już jedyny domyślny: bez zbędnych zapisów
            if not target_is_default:
                failure = self._enable_default(target)  # krok B
                if failure is not None:
                    return failure
            for index, other in enumerate(others):  # krok C
                cause = self._disable_default(other)
                if cause:
                    return False, self._partial_default_message(target, other, cause, len(others) - index - 1)
            return self._verify_single_default(target)  # krok D
        except SharePointError as e:
            return False, f"Błąd podczas ustawiania domyślnego dostawcy: {e}"

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
