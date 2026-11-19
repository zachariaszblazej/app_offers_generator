"""Trwały cache tokenów MSAL szyfrowany przez Windows DPAPI.

* Szyfrowanie: CryptProtectData w zakresie bieżącego użytkownika Windows (bez flagi LOCAL_MACHINE), z dodatkowym
  "entropy" specyficznym dla aplikacji. Na dysku nie ma jawnej zawartości cache (ani tokenów).
* Lokalizacja: %LOCALAPPDATA%\\HantechDokumenty\\auth (poza repozytorium; DPAPI i tak wiąże dane z użytkownikiem i komputerem).
* Odporność: uszkodzony, nieczytelny albo zaszyfrowany przez innego użytkownika/komputer plik jest odrzucany,
  a aplikacja startuje z pustym cache (użytkownik loguje się ponownie). Błąd zapisu nie przerywa pracy.
* Logi zawierają wyłącznie stałe komunikaty i nazwy typów wyjątków - nigdy zawartość cache ani tokeny.
Na systemach innych niż Windows trwały cache jest niedostępny (cache pozostaje tylko w pamięci).
"""
import ctypes
import json
import logging
import os
import sys
import threading
from ctypes import wintypes

from .migration.datadir import assert_outside_repo

_log = logging.getLogger("sharepoint.token_cache")

FILE_MAGIC = b"HTKC1\n"
APP_ENTROPY = b"Hantech.SharePoint.MsalTokenCache.v1"
CACHE_FILE_NAME = "msal_token_cache.bin"
CRYPTPROTECT_UI_FORBIDDEN = 0x1


class ProtectionError(Exception):
    """Nie udało się zaszyfrować/odszyfrować danych (komunikat nie zawiera danych)."""


class _DataBlob(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]


class DpapiProtector:
    """Szyfrowanie Windows DPAPI w zakresie bieżącego użytkownika."""

    def __init__(self, entropy: bytes = APP_ENTROPY):
        if sys.platform != "win32":
            raise ProtectionError("DPAPI jest dostępne tylko w systemie Windows.")
        self._entropy = entropy
        self._crypt32 = ctypes.WinDLL("crypt32", use_last_error=True)
        self._kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        blob_p = ctypes.POINTER(_DataBlob)
        for func in (self._crypt32.CryptProtectData, self._crypt32.CryptUnprotectData):
            func.argtypes = [blob_p, wintypes.LPCWSTR if func is self._crypt32.CryptProtectData else ctypes.c_void_p,
                             blob_p, ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, blob_p]
            func.restype = wintypes.BOOL
        self._kernel32.LocalFree.argtypes = [ctypes.c_void_p]
        self._kernel32.LocalFree.restype = ctypes.c_void_p

    @staticmethod
    def _blob(data: bytes):
        buffer = ctypes.create_string_buffer(data, len(data))
        return _DataBlob(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_char))), buffer

    def _call(self, func, data: bytes, description) -> bytes:
        data_in, keep_data = self._blob(data)
        entropy, keep_entropy = self._blob(self._entropy)
        data_out = _DataBlob()
        ok = func(ctypes.byref(data_in), description, ctypes.byref(entropy), None, None,
                  CRYPTPROTECT_UI_FORBIDDEN, ctypes.byref(data_out))
        del keep_data, keep_entropy
        if not ok:
            raise ProtectionError(f"Operacja DPAPI nie powiodła się (kod {ctypes.get_last_error()}).")
        try:
            return ctypes.string_at(data_out.pbData, data_out.cbData)
        finally:
            ctypes.memset(data_out.pbData, 0, data_out.cbData)
            self._kernel32.LocalFree(data_out.pbData)

    def protect(self, data: bytes) -> bytes:
        return self._call(self._crypt32.CryptProtectData, data, "Hantech MSAL token cache")

    def unprotect(self, data: bytes) -> bytes:
        return self._call(self._crypt32.CryptUnprotectData, data, None)


def default_cache_path() -> str:
    """%LOCALAPPDATA%\\HantechDokumenty\\auth\\msal_token_cache.bin (poza repozytorium)."""
    base = os.environ.get("LOCALAPPDATA") or os.path.join(os.path.expanduser("~"), "AppData", "Local")
    return os.path.join(base, "HantechDokumenty", "auth", CACHE_FILE_NAME)


class PersistentTokenCache:
    """Opakowanie `msal.SerializableTokenCache`: wczytanie przy starcie, zapis po zmianie, szyfrowanie DPAPI."""

    def __init__(self, path, protector=None):
        import msal

        self.path = assert_outside_repo(path)
        self._protector = protector if protector is not None else DpapiProtector()
        self._lock = threading.Lock()
        self.cache = msal.SerializableTokenCache()
        self.recovered_from_error = False
        self.load()

    # ------------------------------------------------------------------
    def load(self) -> bool:
        """Wczytuje cache z dysku. Zwraca True, gdy odczytano zawartość; błąd => pusty cache (nowe logowanie)."""
        with self._lock:
            self.recovered_from_error = False
            try:
                with open(self.path, "rb") as f:
                    raw = f.read()
            except FileNotFoundError:
                return False
            except OSError as e:
                _log.warning("Nie można odczytać pliku cache tokenów (%s) - wymagane ponowne logowanie.", type(e).__name__)
                self.recovered_from_error = True
                return False
            try:
                if not raw.startswith(FILE_MAGIC):
                    raise ProtectionError("nieznany format pliku")
                plain = self._protector.unprotect(raw[len(FILE_MAGIC):])
                text = plain.decode("utf-8")
                self._validate_structure(json.loads(text))
                self.cache.deserialize(text)
                self.cache.has_state_changed = False
                return True
            except Exception as e:  # uszkodzony, obcy lub niedeszyfrowalny plik - zawartość nigdy nie jest logowana
                _log.warning("Cache tokenów jest nieczytelny (%s) - zostanie odrzucony, wymagane ponowne logowanie.",
                             type(e).__name__)
                self._reset_memory()
                self.recovered_from_error = True
                self._discard_file()
                return False

    def save(self) -> bool:
        """Zapisuje cache, jeśli się zmienił. Błąd zapisu nie przerywa pracy (cache zostaje w pamięci)."""
        with self._lock:
            if not self.cache.has_state_changed:
                return False
            try:
                blob = FILE_MAGIC + self._protector.protect(self.cache.serialize().encode("utf-8"))
                os.makedirs(os.path.dirname(self.path), exist_ok=True)
                tmp = self.path + ".tmp"
                with open(tmp, "wb") as f:
                    f.write(blob)
                os.replace(tmp, self.path)
            except Exception as e:
                _log.warning("Nie udało się zapisać cache tokenów (%s).", type(e).__name__)
                self.cache.has_state_changed = True  # serialize() zerowało flagę - kolejna próba ma znów zapisać
                return False
            self.cache.has_state_changed = False
            return True

    def clear(self):
        """Usuwa cache z pamięci i z dysku (np. przy wylogowaniu z zapomnieniem konta)."""
        with self._lock:
            self._reset_memory()
            self._discard_file()

    # ------------------------------------------------------------------
    def _reset_memory(self):
        self.cache.deserialize("{}")
        self.cache.has_state_changed = False

    @staticmethod
    def _validate_structure(data):
        """Cache MSAL to słownik: rodzaj wpisu -> {klucz -> słownik wpisu}. Inna struktura = cache uszkodzony."""
        if not isinstance(data, dict):
            raise ValueError("nieprawidłowa struktura cache")
        for entries in data.values():
            if not isinstance(entries, dict) or not all(isinstance(e, dict) for e in entries.values()):
                raise ValueError("nieprawidłowa struktura cache")

    def _discard_file(self):
        for path in (self.path, self.path + ".tmp"):
            try:
                os.remove(path)
            except FileNotFoundError:
                pass
            except OSError as e:
                _log.warning("Nie udało się usunąć pliku cache tokenów (%s).", type(e).__name__)


def create_default_cache():
    """Trwały cache w domyślnej lokalizacji albo None (poza Windows / DPAPI niedostępne => tylko pamięć)."""
    if sys.platform != "win32":
        return None
    try:
        return PersistentTokenCache(default_cache_path())
    except Exception as e:
        _log.warning("Trwały cache tokenów jest niedostępny (%s) - cache tylko w pamięci.", type(e).__name__)
        return None
