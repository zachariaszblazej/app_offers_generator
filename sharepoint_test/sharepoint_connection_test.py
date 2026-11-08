#!/usr/bin/env python3
"""Niezależny test połączenia z SharePoint DEV przez Microsoft Graph API (tylko odczyt).

Uruchomienie (z katalogu głównego projektu):
    python sharepoint_test\\sharepoint_connection_test.py

Skrypt nie korzysta z SQLite, nie zapisuje tokenów na dysku (cache MSAL tylko w pamięci)
i wykonuje wyłącznie zapytania GET.
"""
import sys

import requests

import sharepoint_config as cfg

try:
    import msal
except ImportError:
    print("[BŁĄD] Brak biblioteki 'msal'. Zainstaluj: pip install -r sharepoint_test\\requirements.txt")
    sys.exit(2)

REQUEST_TIMEOUT = 30


class StepFailed(Exception):
    """Błąd kroku testu z czytelnym komunikatem dla użytkownika."""


def ok(msg):
    print(f"[OK]    {msg}")


def fail(msg):
    print(f"[BŁĄD]  {msg}")


def acquire_token(env):
    authority = f"https://login.microsoftonline.com/{env['tenant_id']}"
    app = msal.PublicClientApplication(env["client_id"], authority=authority)

    # MSAL uruchamia lokalny listener i używa przekierowania http://localhost:<port>;
    # w rejestracji Entra ID musi być dodane http://localhost (Mobile and desktop applications).
    print("Logowanie interaktywne w przeglądarce (redirect URI: http://localhost)...")
    try:
        result = app.acquire_token_interactive(scopes=cfg.SCOPES, prompt="select_account")
    except Exception as e:
        raise StepFailed(f"Błąd logowania MSAL: {e}")

    if not result or "access_token" not in result:
        details = ""
        if result:
            details = f"{result.get('error')}: {result.get('error_description')}"
        raise StepFailed(f"Logowanie nie zwróciło tokenu dostępowego. {details}".strip())
    return result


def graph_get(token, path_or_url, params=None):
    url = path_or_url if path_or_url.startswith("http") else f"{cfg.GRAPH_BASE_URL}{path_or_url}"
    try:
        resp = requests.get(
            url,
            headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
            params=params,
            timeout=REQUEST_TIMEOUT,
        )
    except requests.RequestException as e:
        raise StepFailed(f"Błąd połączenia z Graph API ({url}): {e}")

    if resp.status_code == 200:
        return resp.json()

    try:
        details = resp.json()
    except ValueError:
        details = resp.text
    hint = {
        401: "HTTP 401 - token nieprawidłowy lub wygasł (zaloguj się ponownie).",
        403: "HTTP 403 - brak uprawnień. Nie zmieniam uprawnień automatycznie; poniżej szczegóły z Graph API.",
        404: "HTTP 404 - nie znaleziono zasobu lub brak dostępu do witryny (Sites.Selected bez grantu dla tej witryny).",
    }.get(resp.status_code, f"HTTP {resp.status_code}")
    raise StepFailed(f"{hint}\n        URL: {url}\n        Szczegóły: {details}")


def get_all_lists(token, site_id):
    items = []
    data = graph_get(token, f"/sites/{site_id}/lists", params={"$select": "id,name,displayName"})
    items.extend(data.get("value", []))
    while "@odata.nextLink" in data:
        data = graph_get(token, data["@odata.nextLink"])
        items.extend(data.get("value", []))
    return items


def run(env):
    print(f"=== Test połączenia SharePoint ({env['name']}) ===")
    print(f"Witryna: {env['site_url']}\n")

    if not env["client_id"] or not env["tenant_id"]:
        raise StepFailed(
            "Brak Client ID / Tenant ID. Uzupełnij je w sharepoint_test\\sharepoint_config.py "
            "(ENVIRONMENTS['DEV']) albo w zmiennych HANTECH_SP_CLIENT_ID i HANTECH_SP_TENANT_ID."
        )

    result = acquire_token(env)
    token = result["access_token"]
    ok("Uzyskano token dostępowy (MSAL).")
    print(f"        Przyznane zakresy: {result.get('scope', 'brak informacji')}")

    me = graph_get(token, "/me", params={"$select": "displayName,userPrincipalName,mail"})
    ok(f"Zalogowany użytkownik: {me.get('displayName')} <{me.get('userPrincipalName')}>")

    site = graph_get(token, f"/sites/{env['site_id']}", params={"$select": "id,displayName,webUrl"})
    ok(f"Dostęp do witryny: {site.get('displayName')} ({site.get('webUrl')})")

    lists = get_all_lists(token, env["site_id"])
    ok(f"Pobrano listy z witryny: {len(lists)}")
    for item in sorted(lists, key=lambda x: (x.get("name") or "").lower()):
        print(f"        - {item.get('name')} (displayName: {item.get('displayName')})  id={item.get('id')}")

    by_id = {(item.get("id") or "").lower(): item for item in lists}
    print("\nWeryfikacja oczekiwanych list:")
    problems = []
    for expected_name, expected_id in env["lists"].items():
        found = by_id.get(expected_id.lower())
        if found is None:
            problems.append(f"Brak listy '{expected_name}' o id {expected_id}")
            fail(f"{expected_name}: NIE ZNALEZIONO (id {expected_id})")
            continue
        names = {(found.get("name") or "").lower(), (found.get("displayName") or "").lower()}
        if expected_name.lower() not in names:
            problems.append(
                f"Lista o id {expected_id} ma nazwę '{found.get('displayName')}', oczekiwano '{expected_name}'"
            )
            fail(f"{expected_name}: id zgodne, ale nazwa różni się ('{found.get('displayName')}')")
        else:
            ok(f"{expected_name}: {found.get('id')}")

    if problems:
        raise StepFailed("Weryfikacja list nieudana:\n        - " + "\n        - ".join(problems))


def main():
    try:
        run(cfg.get_environment())
    except StepFailed as e:
        print()
        fail(str(e))
        print("\nWYNIK: TEST NIEUDANY")
        return 1
    except Exception as e:
        print()
        fail(f"Nieoczekiwany błąd: {type(e).__name__}: {e}")
        print("\nWYNIK: TEST NIEUDANY")
        return 1

    print("\nWYNIK: TEST UDANY - logowanie, token, Graph API i wszystkie 4 listy działają.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
