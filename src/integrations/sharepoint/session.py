"""Sesja logowania do SharePoint (MSAL) dla warstwy danych.

Token dostępu jest przechowywany w pamięci procesu i nigdy nie jest logowany; na dysk trafia wyłącznie cache MSAL
szyfrowany przez DPAPI (graph_client/token_cache). Logowanie interaktywne jest jawną akcją (`sign_in`); po restarcie
aplikacji sesję można po cichu odzyskać z cache (`resume`), a w trakcie pracy token jest tylko po cichu odświeżany.
"""
import time

from . import graph_client

REFRESH_MARGIN_SECONDS = 120


class NotSignedInError(Exception):
    """Brak aktywnej sesji logowania do SharePoint (a odświeżenie po cichu nie jest możliwe)."""


class SharePointSession:
    def __init__(self, acquire=None, acquire_silent=None, clock=time.time, forget=None):
        self._acquire = acquire or graph_client.acquire_token
        self._acquire_silent = acquire_silent or graph_client.acquire_token_silent
        self._forget = forget or graph_client.forget_account
        self._clock = clock
        self._token = None
        self._expires_at = 0.0

    def _store(self, result):
        self._token = result["access_token"]
        self._expires_at = self._clock() + float(result.get("expires_in", 3000))

    def sign_in(self, interactive_log=None):
        """Jawne logowanie (może otworzyć przeglądarkę; najpierw próbuje cache MSAL)."""
        self._store(self._acquire(interactive_log=interactive_log))

    def resume(self) -> bool:
        """Ciche odzyskanie sesji z trwałego cache (np. po restarcie), bez okna logowania. True, gdy się udało."""
        result = self._acquire_silent()
        if not result:
            return False
        self._store(result)
        return True

    def sign_out(self, forget=False):
        """Kończy sesję w pamięci; z `forget=True` usuwa też konto z cache MSAL i zaszyfrowany plik z dysku."""
        self._token, self._expires_at = None, 0.0
        if forget:
            self._forget()

    def is_active(self) -> bool:
        """Tanie sprawdzenie (bez sieci): użytkownik się zalogował i sesja nie została unieważniona."""
        return self._token is not None

    def is_token_fresh(self) -> bool:
        return self._token is not None and self._clock() < self._expires_at - REFRESH_MARGIN_SECONDS

    def get_token(self) -> str:
        if self.is_token_fresh():
            return self._token
        result = self._acquire_silent() if self._token is not None else None
        if not result:
            self.sign_out()
            raise NotSignedInError("Sesja SharePoint wygasła - zaloguj się ponownie.")
        self._store(result)
        return self._token

    def invalidate_token(self):
        """Po odpowiedzi 401: następne użycie wymusi ciche odświeżenie."""
        self._expires_at = 0.0
