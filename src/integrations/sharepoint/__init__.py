"""Integracja z SharePoint (Microsoft Graph, MSAL) - konfiguracja DEV/PROD i test połączenia."""
from .config import DEV, PROD, SharePointEnvironment, get_environment
from .environment import environment_manager, get_active_environment

__all__ = [
    "DEV",
    "PROD",
    "SharePointEnvironment",
    "get_environment",
    "environment_manager",
    "get_active_environment",
]
