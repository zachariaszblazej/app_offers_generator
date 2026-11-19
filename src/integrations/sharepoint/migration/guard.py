"""Twarde zabezpieczenia migratora: wyłącznie SharePoint DEV.

Identyfikator witryny DEV jest tu celowo zapisany niezależnie od config.py - zmiana
konfiguracji nie może przypadkiem skierować migratora na inną witrynę.
"""
from src.integrations.sharepoint.config import DEV, ENVIRONMENTS, PROD
from src.integrations.sharepoint.environment import get_active_environment

DEV_SITE_ID = (
    "hantechwalbrzych.sharepoint.com,"
    "52c89624-fff1-4250-9199-d1bc6bd37aab,"
    "da3d322b-8b05-46ad-b480-0287bcf8c44b"
)
DEV_SITE_URL = "https://hantechwalbrzych.sharepoint.com/sites/AplikacjaOfertowa-DEV"


class MigrationGuardError(Exception):
    """Migrator odmawia pracy - cel nie jest środowiskiem DEV."""


def assert_dev_only(env=None):
    """Przerywa, gdy aktywne środowisko to nie DEV albo cel nie jest witryną DEV."""
    active = get_active_environment()
    if active.name != DEV:
        raise MigrationGuardError(
            f"Aktywne środowisko to {active.name}. Migrator działa wyłącznie w DEV - przerwano.")
    env = env or active
    if env.name != DEV or env.is_prod:
        raise MigrationGuardError(f"Środowisko docelowe {env.name} nie jest dozwolone (tylko DEV).")
    if env.site_id.lower() != DEV_SITE_ID.lower():
        raise MigrationGuardError("Site ID nie odpowiada witrynie DEV - przerwano.")
    if env.site_url.rstrip("/").lower() != DEV_SITE_URL.lower():
        raise MigrationGuardError("Adres witryny nie odpowiada witrynie DEV - przerwano.")
    prod = ENVIRONMENTS[PROD]
    prod_ids = {prod.site_id.lower()} | {v.lower() for v in prod.lists.values()}
    if env.site_id.lower() in prod_ids or any(v.lower() in prod_ids for v in env.lists.values()):
        raise MigrationGuardError("Konfiguracja DEV zawiera identyfikatory PROD - przerwano.")
    return env


def assert_site_matches_dev(site_json):
    """Weryfikacja odpowiedzi Graph dla witryny (id i adres muszą być witryną DEV)."""
    sid = (site_json.get("id") or "").lower()
    url = (site_json.get("webUrl") or "").rstrip("/").lower()
    if sid != DEV_SITE_ID.lower() or url != DEV_SITE_URL.lower():
        raise MigrationGuardError(
            f"Graph zwrócił witrynę {site_json.get('webUrl')} ({site_json.get('id')}), "
            "która nie jest witryną DEV - przerwano.")
