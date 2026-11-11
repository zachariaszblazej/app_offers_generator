"""Centralna konfiguracja środowisk SharePoint (DEV / PROD).

To jedyne miejsce w aplikacji, w którym występują identyfikatory witryn i list.
Client ID i Tenant ID są publiczne (nie są sekretami) i dotyczą jednej rejestracji
Entra ID dla obu środowisk. Nie dodawaj tu Client Secret ani tokenów.
"""
import os
from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping

GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"

# Delegowane uprawnienia zgodne z istniejącą rejestracją Entra ID.
SCOPES = ("User.Read", "Sites.Selected")

# Jedna rejestracja aplikacji "Hantech - Aplikacja Ofertowa" dla DEV i PROD.
DEFAULT_CLIENT_ID = "95640770-2a93-482f-8e4b-a26936fbdcdb"
DEFAULT_TENANT_ID = "c919f5e4-d4fb-408b-ae92-b899899770f1"

DEV = "DEV"
PROD = "PROD"
DEFAULT_ENV = DEV

LIST_NAMES = ("Clients", "Offers", "Suppliers", "Wuzetkas")


@dataclass(frozen=True)
class SharePointEnvironment:
    name: str
    site_url: str
    site_id: str
    lists: Mapping[str, str]

    @property
    def is_prod(self) -> bool:
        return self.name == PROD


def _env(name, site_url, site_id, lists):
    return SharePointEnvironment(name, site_url, site_id, MappingProxyType(dict(lists)))


ENVIRONMENTS = MappingProxyType({
    DEV: _env(
        DEV,
        "https://hantechwalbrzych.sharepoint.com/sites/AplikacjaOfertowa-DEV",
        "hantechwalbrzych.sharepoint.com,"
        "52c89624-fff1-4250-9199-d1bc6bd37aab,"
        "da3d322b-8b05-46ad-b480-0287bcf8c44b",
        {
            "Clients": "72258472-1ccb-4b8d-8cdb-57465b2fdd12",
            "Offers": "41f4fff7-a749-422d-88b0-0402d5895d50",
            "Suppliers": "a951449a-5d41-4c9a-b454-42e091a39c11",
            "Wuzetkas": "32c71643-1cdd-4e64-a676-aabd1007a38c",
        },
    ),
    PROD: _env(
        PROD,
        "https://hantechwalbrzych.sharepoint.com/sites/AplikacjaOfertowa",
        "hantechwalbrzych.sharepoint.com,"
        "b139d869-4e27-4212-8d74-0f90a353ba2b,"
        "da3d322b-8b05-46ad-b480-0287bcf8c44b",
        {
            "Clients": "b45b3740-cf5e-4e32-982e-f7a4146669c7",
            "Offers": "cee6797a-1d87-4f11-a11f-0ae338d52f34",
            "Suppliers": "113b0d81-2272-408f-a2a0-4e3e45aad712",
            "Wuzetkas": "94e21363-10cc-4add-b8a8-a59f8c30b21d",
        },
    ),
})


class EnvironmentConfigError(ValueError):
    """Nieprawidłowa lub niespójna konfiguracja środowiska."""


def get_client_id() -> str:
    return os.environ.get("HANTECH_SP_CLIENT_ID", DEFAULT_CLIENT_ID).strip()


def get_tenant_id() -> str:
    return os.environ.get("HANTECH_SP_TENANT_ID", DEFAULT_TENANT_ID).strip()


def validate_configuration():
    """Sprawdza spójność DEV/PROD, aby identyfikatory nie mogły się pomieszać."""
    site_ids = [e.site_id.lower() for e in ENVIRONMENTS.values()]
    if len(set(site_ids)) != len(site_ids):
        raise EnvironmentConfigError("Site ID środowisk DEV i PROD nie mogą być takie same.")

    seen_lists = {}
    for env in ENVIRONMENTS.values():
        if not env.site_url.lower().startswith("https://"):
            raise EnvironmentConfigError(f"{env.name}: nieprawidłowy adres witryny.")
        if len(env.site_id.split(",")) != 3:
            raise EnvironmentConfigError(f"{env.name}: Site ID musi mieć postać host,siteGuid,webGuid.")
        if tuple(env.lists) != LIST_NAMES:
            raise EnvironmentConfigError(f"{env.name}: oczekiwane listy {LIST_NAMES}, jest {tuple(env.lists)}.")
        for list_name, list_id in env.lists.items():
            key = list_id.lower()
            if key in seen_lists:
                raise EnvironmentConfigError(
                    f"Lista {env.name}/{list_name} ma to samo ID co {seen_lists[key]}."
                )
            seen_lists[key] = f"{env.name}/{list_name}"


def get_environment(name=None) -> SharePointEnvironment:
    """Zwraca konfigurację środowiska; nieznana nazwa to błąd (bez cichego fallbacku)."""
    key = (name or DEFAULT_ENV).strip().upper()
    if key not in ENVIRONMENTS:
        raise EnvironmentConfigError(
            f"Nieznane środowisko '{name}'. Dozwolone: {', '.join(ENVIRONMENTS)}."
        )
    validate_configuration()
    return ENVIRONMENTS[key]
