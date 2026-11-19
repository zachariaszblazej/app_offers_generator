"""Zapis do list SharePoint przez Graph API (listy Clients i Suppliers, wyłącznie środowisko DEV).

To jedyne miejsce w warstwie danych, które wysyła żądania POST, PATCH i DELETE do Graph. Zabezpieczenia:
* każde żądanie przechodzi przez `assert_dev_only` (aktywne środowisko aplikacji, Site ID i adres muszą być DEV)
  oraz przez strażnika `GraphClient._guard` (witryna klienta, brak identyfikatorów innego środowiska),
* zapis jest dozwolony tylko dla list z `WRITABLE_LISTS` (Clients i Suppliers; Offers, Wuzetkas i każda inna lista
  są odrzucane przed wysłaniem żądania),
* adres jest budowany wyłącznie z konfiguracji środowiska i cyfrowego ID elementu,
* aktualizacja i usuwanie wymagają konkretnego ETagu w nagłówku If-Match (gwiazdka i brak ETagu są odrzucane),
* ponawiany jest wyłącznie HTTP 429 (żądanie nie zostało przetworzone), z limitem prób i Retry-After;
  zapisu nie ponawia się po 412, 5xx ani po błędzie połączenia (wynik mógłby być niejednoznaczny).
Komunikaty błędów nie zawierają tokenów ani nagłówków.
"""
import logging
import re
import time
from collections import namedtuple

import requests

from .config import GRAPH_BASE_URL
from .graph_client import REQUEST_TIMEOUT, GraphClient, GraphError
from .migration.guard import assert_dev_only
from .reader import retry_delay

_log = logging.getLogger("sharepoint.writer")

WRITABLE_LISTS = frozenset({"Clients", "Suppliers"})
MAX_ATTEMPTS = 3
_FIELD_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_ALLOWED_VALUE_TYPES = (str, int, float, bool, type(None))

WriteResult = namedtuple("WriteResult", "item_id etag fields")


class GraphWriteError(GraphError):
    """Błąd żądania zapisu. `ambiguous=True`: nie wiadomo, czy SharePoint przetworzył żądanie (brak odpowiedzi, 5xx)."""

    def __init__(self, message, status=None, code=None, retry_after=None, ambiguous=False):
        super().__init__(message, status=status, retry_after=retry_after)
        self.code = code
        self.ambiguous = ambiguous


class GraphWriter(GraphClient):
    def __init__(self, environment, access_token, http=requests.request, sleep=time.sleep,
                 writable_lists=WRITABLE_LISTS, max_attempts=MAX_ATTEMPTS):
        super().__init__(environment, access_token)
        self._http = http
        self._sleep = sleep
        self._writable = frozenset(writable_lists)
        self._max_attempts = max_attempts
        self.requests_made = 0
        self.retries = 0

    # ------------------------------------------------------------------
    def _collection_path(self, list_name):
        if list_name not in self._writable:
            raise GraphWriteError(f"Zapis do listy {list_name} nie jest dozwolony.")
        list_id = self.environment.lists.get(list_name)
        if not list_id:
            raise GraphWriteError(f"Nieznana lista: {list_name}")
        return f"/sites/{self.environment.site_id}/lists/{list_id}/items"

    def _item_path(self, list_name, item_id, suffix=""):
        """Ścieżka elementu: ID musi być niepustym ciągiem cyfr ASCII (brak ID nigdy nie oznacza całej kolekcji)."""
        path = self._collection_path(list_name)
        text = item_id if isinstance(item_id, str) else (str(item_id) if isinstance(item_id, int) and not isinstance(item_id, bool) else "")
        if not (text.isascii() and text.isdigit()):
            raise GraphWriteError(f"Nieprawidłowe ID elementu: {str(item_id)[:20]!r}")
        return f"{path}/{text}{suffix}"

    @staticmethod
    def _check_fields(fields):
        if not isinstance(fields, dict) or not fields:
            raise GraphWriteError("Brak pól do zapisu.")
        for name, value in fields.items():
            if not _FIELD_NAME.match(str(name)):
                raise GraphWriteError(f"Nieprawidłowa nazwa pola: {str(name)[:30]!r}")
            if not isinstance(value, _ALLOWED_VALUE_TYPES):
                raise GraphWriteError(f"Nieprawidłowy typ wartości pola {name}.")

    @staticmethod
    def _error_details(resp):
        try:
            error = (resp.json() or {}).get("error") or {}
            return error.get("code"), error.get("message") or ""
        except (ValueError, AttributeError):
            return None, ""

    def _send(self, method, path, expected, json_body=None, extra_headers=None):
        headers = {"Authorization": f"Bearer {self._access_token}", "Accept": "application/json"}
        headers.update(extra_headers or {})
        url = f"{GRAPH_BASE_URL}{path}"
        for attempt in range(1, self._max_attempts + 1):
            assert_dev_only(self.environment)
            self._guard(path)
            self.requests_made += 1
            _log.info("[%s] %s %s", self.environment.name, method, url)
            try:
                resp = self._http(method, url, headers=headers, json=json_body, timeout=REQUEST_TIMEOUT)
            except requests.RequestException as e:
                raise GraphWriteError(f"Błąd połączenia z Graph API ({type(e).__name__}); wynik operacji jest nieznany.",
                                      ambiguous=True) from None
            if resp.status_code in expected:
                return resp
            code, message = self._error_details(resp)
            retry_after = resp.headers.get("Retry-After")
            if resp.status_code == 429 and attempt < self._max_attempts:
                self.retries += 1
                self._sleep(retry_delay(attempt, retry_after))
                continue
            raise GraphWriteError(
                f"HTTP {resp.status_code}" + (f" {code}" if code else "") + (f": {message}" if message else ""),
                status=resp.status_code, code=code, retry_after=retry_after,
                ambiguous=resp.status_code >= 500)
        raise GraphWriteError("Wyczerpano liczbę prób.")  # niedostępne: pętla zawsze zwraca lub zgłasza wyjątek

    @staticmethod
    def _etag(resp, body):
        return resp.headers.get("ETag") or body.get("@odata.etag") or body.get("eTag")

    @staticmethod
    def _require_etag(etag, operation):
        """If-Match musi zawierać konkretny ETag: brak, pusty, `*` oraz znaki nowej linii (nagłówek HTTP) są odrzucane."""
        if (not isinstance(etag, str) or not etag.strip() or etag.strip() == "*"
                or "\r" in etag or "\n" in etag):
            raise GraphWriteError(f"{operation} wymaga konkretnego ETagu elementu (If-Match).")
        return etag

    # ------------------------------------------------------------------
    def create_item(self, list_name, fields) -> WriteResult:
        """POST: tworzy element i zwraca jego ID oraz ETag."""
        self._check_fields(fields)
        resp = self._send("POST", self._collection_path(list_name), (200, 201), json_body={"fields": fields})
        body = resp.json()
        return WriteResult(str(body["id"]), self._etag(resp, body), body.get("fields") or {})

    def update_item_fields(self, list_name, item_id, fields, etag) -> WriteResult:
        """PATCH pól elementu z If-Match: wymaga konkretnego ETagu (nie '*'). 412 => GraphWriteError(status=412)."""
        self._check_fields(fields)
        self._require_etag(etag, "Aktualizacja")
        path = self._item_path(list_name, item_id, "/fields")
        resp = self._send("PATCH", path, (200,), json_body=fields, extra_headers={"If-Match": etag})
        body = resp.json()
        return WriteResult(str(item_id), self._etag(resp, body), body)

    def delete_item(self, list_name, item_id, etag):
        """DELETE elementu o dokładnym ID z If-Match (element trafia do kosza witryny).

        Wymaga konkretnego ETagu (brak, pusty i `*` są odrzucane), bez wariantu zapasowego bez If-Match.
        204 => sukces; 404 => GraphWriteError(status=404); 412 => GraphWriteError(status=412), bez ponowienia."""
        self._require_etag(etag, "Usuwanie")
        self._send("DELETE", self._item_path(list_name, item_id), (200, 204), extra_headers={"If-Match": etag})
