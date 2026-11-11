"""Klient Microsoft Graph (wyłącznie odczyt) powiązany z konkretnym środowiskiem SharePoint.

Zabezpieczenia przed pomyłką środowiska:
* klient jest na stałe związany z jednym środowiskiem,
* przed każdym zapytaniem sprawdzane jest, że aktywne środowisko aplikacji (to, które widzi
  użytkownik w interfejsie) jest tym samym środowiskiem co środowisko klienta,
* ścieżki zapytań muszą dotyczyć Site ID klienta i nie mogą zawierać żadnego identyfikatora
  witryny ani listy z innego środowiska.

Klient udostępnia tylko metodę GET. Tokeny nie są logowane ani zapisywane na dysku.
"""
import logging
import threading
from urllib.parse import unquote

import requests

from .config import (
    ENVIRONMENTS,
    GRAPH_BASE_URL,
    SCOPES,
    SharePointEnvironment,
    get_client_id,
    get_tenant_id,
)
from .environment import get_active_environment

_log = logging.getLogger("sharepoint.graph")

REQUEST_TIMEOUT = 30


class GraphError(Exception):
    """Błąd komunikacji z Graph API (komunikat nie zawiera tokenu)."""

    def __init__(self, message, status=None):
        super().__init__(message)
        self.status = status


class AuthError(Exception):
    """Błąd logowania MSAL."""


class EnvironmentMismatchError(Exception):
    """Zapytanie dotyczyłoby innego środowiska niż aktywne w aplikacji."""


_msal_app = None
_msal_lock = threading.Lock()


def _get_msal_app():
    """Jedna aplikacja MSAL z cache tylko w pamięci (ta sama rejestracja dla DEV i PROD)."""
    global _msal_app
    with _msal_lock:
        if _msal_app is None:
            import msal

            _msal_app = msal.PublicClientApplication(
                get_client_id(),
                authority=f"https://login.microsoftonline.com/{get_tenant_id()}",
            )
        return _msal_app


def acquire_token(interactive_log=None):
    """Zwraca wynik MSAL z tokenem dostępu. Najpierw próbuje po cichu, potem logowanie w przeglądarce."""
    try:
        app = _get_msal_app()
    except ImportError:
        raise AuthError("Brak biblioteki 'msal'. Zainstaluj: pip install -r requirements.txt")

    result = None
    try:
        accounts = app.get_accounts()
        if accounts:
            result = app.acquire_token_silent(list(SCOPES), account=accounts[0])
        if not result or "access_token" not in result:
            if interactive_log:
                interactive_log("Logowanie interaktywne w przeglądarce (redirect URI: http://localhost)...")
            result = app.acquire_token_interactive(scopes=list(SCOPES), prompt="select_account")
    except Exception as e:
        raise AuthError(f"Błąd logowania MSAL: {e}")

    if not result or "access_token" not in result:
        details = ""
        if result:
            details = f"{result.get('error')}: {result.get('error_description')}"
        raise AuthError(f"Logowanie nie zwróciło tokenu dostępowego. {details}".strip())
    return result


class GraphClient:
    """Klient tylko do odczytu, związany z jednym środowiskiem."""

    def __init__(self, environment: SharePointEnvironment, access_token: str):
        self.environment = environment
        self._access_token = access_token
        self._forbidden = self._foreign_identifiers(environment)

    @staticmethod
    def _foreign_identifiers(environment):
        forbidden = set()
        for other in ENVIRONMENTS.values():
            if other.name == environment.name:
                continue
            forbidden.add(other.site_id.lower())
            forbidden.update(part.lower() for part in other.site_id.split(",")[1:2])
            forbidden.update(list_id.lower() for list_id in other.lists.values())
        return forbidden

    def _guard(self, path_or_url):
        active = get_active_environment()
        if active.name != self.environment.name:
            raise EnvironmentMismatchError(
                f"Klient Graph jest przypisany do {self.environment.name}, "
                f"a aktywne środowisko aplikacji to {active.name}. Zapytanie zablokowane."
            )

        if path_or_url.startswith("http"):
            if not path_or_url.startswith(GRAPH_BASE_URL + "/"):
                raise GraphError(f"Zablokowano zapytanie spoza Microsoft Graph: {path_or_url}")
            path = path_or_url[len(GRAPH_BASE_URL):]
        else:
            path = path_or_url
        path = unquote(path)
        lowered = path.lower()

        own_site = f"/sites/{self.environment.site_id}".lower()
        if not (lowered == "/me" or lowered == own_site or lowered.startswith(own_site + "/")):
            raise EnvironmentMismatchError(
                f"Zapytanie nie dotyczy witryny {self.environment.name}: {path}"
            )
        for foreign in self._forbidden:
            if foreign in lowered:
                raise EnvironmentMismatchError(
                    f"Zapytanie dla {self.environment.name} zawiera identyfikator z innego środowiska."
                )

    def get(self, path_or_url, params=None):
        """GET /v1.0{path}. Zwraca sparsowany JSON."""
        self._guard(path_or_url)
        url = path_or_url if path_or_url.startswith("http") else f"{GRAPH_BASE_URL}{path_or_url}"
        _log.info("[%s] GET %s", self.environment.name, url)
        try:
            resp = requests.get(
                url,
                headers={"Authorization": f"Bearer {self._access_token}", "Accept": "application/json"},
                params=params,
                timeout=REQUEST_TIMEOUT,
            )
        except requests.RequestException as e:
            raise GraphError(f"Błąd połączenia z Graph API ({url}): {e}")

        if resp.status_code == 200:
            return resp.json()

        try:
            details = resp.json()
        except ValueError:
            details = resp.text
        hint = {
            401: "HTTP 401 - token nieprawidłowy lub wygasł (zaloguj się ponownie).",
            403: "HTTP 403 - brak uprawnień do zasobu (uprawnień nie zmieniam automatycznie).",
            404: "HTTP 404 - nie znaleziono zasobu lub brak dostępu do witryny (Sites.Selected bez grantu).",
        }.get(resp.status_code, f"HTTP {resp.status_code}")
        raise GraphError(f"{hint} URL: {url} Szczegóły: {details}", status=resp.status_code)

    def get_all(self, path, params=None):
        """Zbiera wszystkie strony kolekcji (@odata.nextLink)."""
        data = self.get(path, params=params)
        items = list(data.get("value", []))
        while "@odata.nextLink" in data:
            data = self.get(data["@odata.nextLink"])
            items.extend(data.get("value", []))
        return items
