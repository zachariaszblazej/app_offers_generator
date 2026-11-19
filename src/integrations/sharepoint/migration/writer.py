"""Zapis elementów do list SharePoint DEV (jedyna operacja: utworzenie elementu).

Nie jest używany w dry-run. Każde żądanie przechodzi przez assert_dev_only, a adres
jest budowany wyłącznie z konfiguracji DEV (witryna i lista z config.py).
"""
import logging
import time

import requests

from src.integrations.sharepoint.config import GRAPH_BASE_URL
from src.integrations.sharepoint.graph_client import GraphError

from .guard import assert_dev_only

_log = logging.getLogger("sharepoint.migration.writer")

MAX_RETRIES = 6
MAX_BACKOFF = 60
RETRYABLE = (429, 503)
AMBIGUOUS = (504,)
SYNTHETIC_PREFIX = "ZZTEST-"
SYNTHETIC_LIST = "Clients"


class WriteError(Exception):
    def __init__(self, message, status=None):
        super().__init__(message)
        self.status = status


def retry_delay(attempt, retry_after=None):
    if retry_after is not None:
        try:
            return min(max(float(retry_after), 0), 300)
        except (TypeError, ValueError):
            pass
    return min(2 ** attempt, MAX_BACKOFF)


class DevWriter:
    def __init__(self, env, token_provider, reader, sleep=time.sleep, http_post=requests.post,
                 http_delete=requests.delete):
        self.env = assert_dev_only(env)
        self._token_provider = token_provider
        self._reader = reader
        self._sleep = sleep
        self._post = http_post
        self._delete = http_delete
        self._token = token_provider()
        self.created = 0
        self.deleted = 0
        self.attempts = 0
        self.delete_attempts = 0
        self.retries = 0
        self.last_response = None

    def _url(self, list_name):
        if list_name not in self.env.lists:
            raise WriteError(f"Nieznana lista: {list_name}")
        return f"{GRAPH_BASE_URL}/sites/{self.env.site_id}/lists/{self.env.lists[list_name]}/items"

    def find_id_by_title(self, list_name, title):
        """Odczyt (GET): ID elementu o danym Title albo None. Używane po niejednoznacznych błędach."""
        safe = title.replace("'", "''")
        data = self._reader.get(
            f"/sites/{self.env.site_id}/lists/{self.env.lists[list_name]}/items",
            params={"$filter": f"fields/Title eq '{safe}'", "$expand": "fields($select=Title)", "$top": "2"},
        )
        items = data.get("value", [])
        return str(items[0]["id"]) if items else None

    def create_item(self, list_name, fields):
        """Tworzy element i zwraca jego ID. 429/503: ponawianie z Retry-After lub backoffem."""
        url = self._url(list_name)
        title = fields.get("Title")
        refreshed = False
        last = "brak odpowiedzi"
        for attempt in range(MAX_RETRIES + 1):
            assert_dev_only(self.env)
            ambiguous = False
            self.attempts += 1
            try:
                resp = self._post(
                    url, json={"fields": fields}, timeout=60,
                    headers={"Authorization": f"Bearer {self._token}", "Accept": "application/json"},
                )
            except requests.RequestException as e:
                last, ambiguous, resp = f"błąd połączenia: {type(e).__name__}", True, None

            if resp is not None:
                if resp.status_code in (200, 201):
                    self.created += 1
                    self.last_response = resp.json()
                    return str(self.last_response["id"])
                if resp.status_code == 401 and not refreshed:
                    refreshed = True
                    self._token = self._token_provider()
                    continue
                if resp.status_code in RETRYABLE or resp.status_code in AMBIGUOUS:
                    ambiguous = resp.status_code in AMBIGUOUS
                    last = f"HTTP {resp.status_code}"
                else:
                    try:
                        details = resp.json().get("error", {}).get("message", "")
                    except ValueError:
                        details = resp.text[:200]
                    raise WriteError(f"HTTP {resp.status_code}: {details}", status=resp.status_code)

            if ambiguous and title:
                try:
                    existing = self.find_id_by_title(list_name, title)
                except GraphError:
                    existing = None
                if existing:
                    return existing
            if attempt == MAX_RETRIES:
                break
            self.retries += 1
            delay = retry_delay(attempt, resp.headers.get("Retry-After") if resp is not None else None)
            _log.warning("[DEV] %s: %s - ponowienie za %.0f s", list_name, last, delay)
            self._sleep(delay)
        raise WriteError(f"Wyczerpano liczbę ponowień ({last})")

    def delete_synthetic_item(self, list_name, item_id, expected_title):
        """Usuwa WYŁĄCZNIE syntetyczny element testowy (lista Clients, Item ID, Title z prefiksem ZZTEST-).

        To nie jest ogólna operacja usuwania: przed DELETE element jest pobierany po ID, a jego Title
        musi być identyczny z oczekiwanym i zaczynać się od prefiksu testowego.
        Zwraca True po usunięciu, False gdy elementu już nie było (404).
        """
        if list_name != SYNTHETIC_LIST:
            raise WriteError(f"Usuwanie dozwolone wyłącznie na liście {SYNTHETIC_LIST}")
        item_id = str(item_id)
        if not item_id.isdigit():
            raise WriteError(f"Nieprawidłowe Item ID: {item_id!r}")
        if not expected_title or not expected_title.startswith(SYNTHETIC_PREFIX):
            raise WriteError("Usuwać można wyłącznie element o Title z prefiksem testowym")

        assert_dev_only(self.env)
        item_path = f"/sites/{self.env.site_id}/lists/{self.env.lists[list_name]}/items/{item_id}"
        item = self._reader.get(item_path, params={"$expand": "fields($select=Title)"})
        title = (item.get("fields") or {}).get("Title")
        if str(item.get("id")) != item_id or title != expected_title:
            raise WriteError("Element o podanym ID nie jest oczekiwanym elementem testowym - nie usunięto")

        url = f"{self._url(list_name)}/{item_id}"
        refreshed = False
        for attempt in range(MAX_RETRIES + 1):
            assert_dev_only(self.env)
            self.delete_attempts += 1
            try:
                resp = self._delete(url, timeout=60, headers={"Authorization": f"Bearer {self._token}"})
            except requests.RequestException as e:
                raise WriteError(f"Błąd połączenia przy usuwaniu: {type(e).__name__}")
            if resp.status_code in (200, 204):
                self.deleted += 1
                return True
            if resp.status_code == 404:
                return False
            if resp.status_code == 401 and not refreshed:
                refreshed = True
                self._token = self._token_provider()
                continue
            if resp.status_code in RETRYABLE and attempt < MAX_RETRIES:
                self.retries += 1
                self._sleep(retry_delay(attempt, resp.headers.get("Retry-After")))
                continue
            try:
                details = resp.json().get("error", {}).get("message", "")
            except ValueError:
                details = ""
            raise WriteError(f"HTTP {resp.status_code} przy usuwaniu: {details}", status=resp.status_code)
        raise WriteError("Wyczerpano liczbę ponowień przy usuwaniu")
