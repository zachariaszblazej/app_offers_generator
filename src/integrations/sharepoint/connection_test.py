"""Test połączenia z SharePoint przez Microsoft Graph - wyłącznie odczyt (GET).

Sprawdza: logowanie MSAL, token, dostęp do witryny wybranego środowiska oraz metadane
i kolumny czterech list. Niczego nie dodaje, nie modyfikuje i nie usuwa.
"""
from dataclasses import dataclass, field

from .config import SCOPES, SharePointEnvironment
from .graph_client import (
    AuthError,
    EnvironmentMismatchError,
    GraphClient,
    GraphError,
    acquire_token,
)

COLUMN_FACETS = (
    "text", "number", "choice", "dateTime", "boolean", "lookup", "currency",
    "personOrGroup", "calculated", "hyperlinkOrPicture", "geolocation",
    "term", "thumbnail", "contentApprovalStatus", "defaultValue",
)
COLUMN_TYPE_FACETS = tuple(f for f in COLUMN_FACETS if f != "defaultValue")


@dataclass
class ConnectionReport:

    environment: str
    lines: list = field(default_factory=list)
    ok: bool = False
    lists_ok: int = 0
    lists_total: int = 0


def column_type(column):
    for facet in COLUMN_TYPE_FACETS:
        if facet in column:
            return facet
    return "inny"


def _norm_url(url):
    return (url or "").strip().rstrip("/").lower()


def _flag(value):
    return "tak" if value else "nie"


def run_readonly_test(env: SharePointEnvironment, log=None, token_provider=acquire_token) -> ConnectionReport:
    """Wykonuje test odczytowy dla podanego środowiska. `log(line)` wywoływane na bieżąco."""
    report = ConnectionReport(environment=env.name, lists_total=len(env.lists))

    def out(line=""):
        report.lines.append(line)
        if log:
            log(line)

    out(f"=== Test połączenia SharePoint ({env.name}) - tylko odczyt ===")
    out(f"Środowisko: {env.name}")
    out(f"Witryna:    {env.site_url}")
    out(f"Site ID:    {env.site_id}")
    for name, list_id in env.lists.items():
        out(f"  lista {name:<10} {list_id}")
    out()

    try:
        result = token_provider(interactive_log=out)
        out("[OK]    Uzyskano token dostępowy (MSAL).")
        out(f"        Zakresy: {result.get('scope', ', '.join(SCOPES))}")

        client = GraphClient(env, result["access_token"])

        me = client.get("/me", params={"$select": "displayName,userPrincipalName"})
        out(f"[OK]    Użytkownik: {me.get('displayName')} <{me.get('userPrincipalName')}>")

        site = client.get(f"/sites/{env.site_id}", params={"$select": "id,displayName,webUrl"})
        site_problems = []
        if _norm_url(site.get("webUrl")) != _norm_url(env.site_url):
            site_problems.append(f"adres witryny z Graph ({site.get('webUrl')}) różni się od konfiguracji")
        if (site.get("id") or "").lower() != env.site_id.lower():
            site_problems.append(f"Site ID z Graph ({site.get('id')}) różni się od konfiguracji")
        if site_problems:
            for problem in site_problems:
                out(f"[BŁĄD]  Witryna: {problem}")
            out("\nWYNIK: TEST NIEUDANY - dane witryny niezgodne z konfiguracją, przerwano.")
            return report
        out(f"[OK]    Witryna: {site.get('displayName')} ({site.get('webUrl')}) - adres i Site ID zgodne")
        out()

        for list_name, list_id in env.lists.items():
            out(f"--- Lista: {list_name} ---")
            try:
                meta = client.get(
                    f"/sites/{env.site_id}/lists/{list_id}",
                    params={"$select": "id,name,displayName,webUrl,createdDateTime,lastModifiedDateTime,list"},
                )
                columns = client.get_all(f"/sites/{env.site_id}/lists/{list_id}/columns")
            except GraphError as e:
                out(f"[BŁĄD]  {e}")
                out()
                continue

            problems = []
            if (meta.get("id") or "").lower() != list_id.lower():
                problems.append(f"ID z Graph ({meta.get('id')}) różni się od konfiguracji")
            if not _norm_url(meta.get("webUrl")).startswith(_norm_url(env.site_url) + "/"):
                problems.append(f"adres listy ({meta.get('webUrl')}) nie należy do witryny {env.name}")
            names = {(meta.get("name") or "").lower(), (meta.get("displayName") or "").lower()}
            if list_name.lower() not in names:
                problems.append(f"nazwa listy ({meta.get('displayName')}) różni się od oczekiwanej '{list_name}'")

            out(f"  id:               {meta.get('id')}")
            out(f"  name/displayName: {meta.get('name')} / {meta.get('displayName')}")
            out(f"  webUrl:           {meta.get('webUrl')}")
            out(f"  szablon:          {(meta.get('list') or {}).get('template')}")
            out(f"  utworzono:        {meta.get('createdDateTime')}")
            out(f"  zmodyfikowano:    {meta.get('lastModifiedDateTime')}")
            out(f"  kolumny:          {len(columns)}")
            out(f"  {'name':<28} {'displayName':<30} {'typ':<14} {'wymag.':<7} {'readOnly':<9} indexed")
            for col in sorted(columns, key=lambda c: (c.get("name") or "").lower()):
                out(
                    f"  {str(col.get('name')):<28} {str(col.get('displayName')):<30} "
                    f"{column_type(col):<14} {_flag(col.get('required')):<7} "
                    f"{_flag(col.get('readOnly')):<9} {_flag(col.get('indexed'))}"
                )
            if problems:
                for problem in problems:
                    out(f"[BŁĄD]  {problem}")
            else:
                report.lists_ok += 1
                out(f"[OK]    Lista {list_name}: metadane i {len(columns)} kolumn odczytane, ID i adres zgodne")
            out()

        report.ok = report.lists_ok == report.lists_total
        out("=== Podsumowanie ===")
        out(f"Środowisko: {env.name}   Poprawnie odczytane listy: {report.lists_ok}/{report.lists_total}")
        out("Operacje: wyłącznie GET (żadne dane nie zostały zmodyfikowane).")
        out("WYNIK: TEST UDANY" if report.ok else "WYNIK: TEST NIEUDANY")
    except (AuthError, GraphError, EnvironmentMismatchError) as e:
        out(f"[BŁĄD]  {e}")
        out("WYNIK: TEST NIEUDANY")
    except Exception as e:
        out(f"[BŁĄD]  Nieoczekiwany błąd: {type(e).__name__}: {e}")
        out("WYNIK: TEST NIEUDANY")
    return report
