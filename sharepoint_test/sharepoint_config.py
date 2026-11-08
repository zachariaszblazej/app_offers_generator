"""Jedyne miejsce konfiguracji integracji z SharePoint (test połączenia).

Client ID i Tenant ID to identyfikatory publiczne (nie sekrety) - można je wpisać
poniżej albo podać przez zmienne środowiskowe HANTECH_SP_CLIENT_ID / HANTECH_SP_TENANT_ID.
Nie dodawaj tu Client Secret ani tokenów.
"""
import os

# Aktywne środowisko. Na tym etapie wyłącznie DEV.
ACTIVE_ENV = "DEV"

GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"

# Delegated permissions zgodne z rejestracją aplikacji w Entra ID.
SCOPES = ["User.Read", "Sites.Selected"]

ENVIRONMENTS = {
    "DEV": {
        "client_id": "95640770-2a93-482f-8e4b-a26936fbdcdb",  # Application ID: "Hantech - Aplikacja Ofertowa"
        "tenant_id": "c919f5e4-d4fb-408b-ae92-b899899770f1",  # Directory ID
        "site_url": "https://hantechwalbrzych.sharepoint.com/sites/AplikacjaOfertowa-DEV",
        "site_id": (
            "hantechwalbrzych.sharepoint.com,"
            "52c89624-fff1-4250-9199-d1bc6bd37aab,"
            "da3d322b-8b05-46ad-b480-0287bcf8c44b"
        ),
        "lists": {
            "Clients": "72258472-1ccb-4b8d-8cdb-57465b2fdd12",
            "Offers": "41f4fff7-a749-422d-88b0-0402d5895d50",
            "Suppliers": "a951449a-5d41-4c9a-b454-42e091a39c11",
            "Wuzetkas": "32c71643-1cdd-4e64-a676-aabd1007a38c",
        },
    },
    # Miejsce na przyszłe środowisko produkcyjne - celowo nieaktywne.
    "PROD": {
        "client_id": "",
        "tenant_id": "",
        "site_url": "",
        "site_id": "",
        "lists": {},
    },
}


def get_environment(name=None):
    """Zwraca konfigurację wybranego środowiska (z nadpisaniem przez zmienne środowiskowe)."""
    name = (name or ACTIVE_ENV).upper()
    if name != "DEV":
        raise ValueError(f"Środowisko '{name}' nie jest jeszcze aktywne - dozwolone tylko DEV.")

    env = dict(ENVIRONMENTS[name])
    env["name"] = name
    env["client_id"] = os.environ.get("HANTECH_SP_CLIENT_ID", env["client_id"]).strip()
    env["tenant_id"] = os.environ.get("HANTECH_SP_TENANT_ID", env["tenant_id"]).strip()
    return env
