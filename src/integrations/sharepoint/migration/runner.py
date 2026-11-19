"""Orkiestracja migracji: dry-run (domyślnie) oraz zapis do DEV (wyłącznie po jawnym potwierdzeniu)."""
import glob
import json
import os
import time
from collections import Counter
from datetime import datetime

from src.integrations.sharepoint.environment import get_active_environment
from src.integrations.sharepoint.graph_client import GraphClient, GraphError, acquire_token

from .datadir import assert_outside_repo, migration_dir, resolve_data_dir  # noqa: F401  (migration_dir: re-eksport)
from .guard import MigrationGuardError, assert_dev_only, assert_site_matches_dev
from .idmap import IdMap
from .mapping import map_all
from .report import render_text, summarize_list
from .source import file_fingerprint, read_source_tables
from .validate import CREATE, ERROR, EXISTS, plan_list
from .writer import MAX_RETRIES, DevWriter, WriteError, retry_delay

LIST_ORDER = ("Suppliers", "Clients", "Offers", "Wuzetkas")
CONFIRM_PHRASE = "MIGRATE-DEV"
FILE_KINDS = {"Offers": "offers_folder", "Wuzetkas": "wz_folder"}


class MigrationRefused(Exception):
    """Migrator odmawia wykonania (brak potwierdzenia, brak dry-runu, błędy w planie itd.)."""


class MigrationReader(GraphClient):
    """Klient tylko do odczytu: liczy żądania i ponawia 429/503 (Retry-After lub backoff)."""

    def __init__(self, env, token, sleep=time.sleep):
        super().__init__(env, token)
        self.calls = Counter()
        self._sleep = sleep

    def get(self, path_or_url, params=None):
        for attempt in range(MAX_RETRIES + 1):
            self.calls["GET"] += 1
            try:
                return super().get(path_or_url, params=params)
            except GraphError as e:
                if e.status in (429, 503) and attempt < MAX_RETRIES:
                    self._sleep(retry_delay(attempt, e.retry_after))
                    continue
                raise


class Remote:
    def __init__(self):
        self.site = None
        self.lists_info = {}
        self.columns = {}
        self.items = {}


def default_db_path():
    from src.utils.settings import settings_manager
    path = settings_manager.get_database_path()
    if path and not os.path.isabs(path):
        root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
        path = os.path.abspath(os.path.join(root, path))
    return path


def _document_roots():
    from src.utils.settings import settings_manager
    return {name: (settings_manager.get_app_setting(key) or "") for name, key in FILE_KINDS.items()}


def fetch_remote(reader, env) -> Remote:
    """Tylko odczyt: witryna, metadane list, kolumny i istniejące elementy."""
    remote = Remote()
    remote.site = reader.get(f"/sites/{env.site_id}", params={"$select": "id,displayName,webUrl"})
    assert_site_matches_dev(remote.site)
    for name in LIST_ORDER:
        list_id = env.lists[name]
        base = f"/sites/{env.site_id}/lists/{list_id}"
        meta = reader.get(base, params={"$select": "id,name,displayName,webUrl"})
        same_id = (meta.get("id") or "").lower() == list_id.lower()
        in_site = (meta.get("webUrl") or "").lower().startswith(env.site_url.lower() + "/")
        same_name = name.lower() in {(meta.get("name") or "").lower(), (meta.get("displayName") or "").lower()}
        if not (same_id and in_site and same_name):
            raise MigrationGuardError(f"Lista {name}: metadane z Graph nie zgadzają się z konfiguracją DEV - przerwano.")
        remote.lists_info[name] = f"{list_id}  ({meta.get('displayName')}) - ID, adres i nazwa zgodne"
        remote.columns[name] = {c["name"]: c for c in reader.get_all(f"{base}/columns")}
        remote.items[name] = reader.get_all(f"{base}/items", params={"$expand": "fields", "$top": "200"})
    return remote


def build_plans(tables, remote):
    mapped = map_all(tables)
    return {name: plan_list(mapped[name], remote.columns[name], remote.items[name]) for name in LIST_ORDER}


def find_missing_files(plans):
    roots = _document_roots()
    result = {}
    for name in plans:
        if name not in FILE_KINDS:
            result[name] = (None, [])
            continue
        root = roots[name]
        possible = bool(root) and os.path.isdir(root)
        missing = []
        if possible:
            for e in plans[name]:
                if e.record.file_check and e.record.file_check[1]:
                    if not os.path.isfile(os.path.join(root, e.record.file_check[1])):
                        missing.append((e.record.key, e.record.file_check[1]))
        result[name] = (possible, missing)
    return result


def _build_report(mode, env, db_path, before, after, remote, reader, plans, idmap, writer=None, execution=None):
    files = find_missing_files(plans)
    http = dict(reader.calls)
    if writer is not None:
        http["POST"] = writer.attempts
    return {
        "tryb": mode,
        "czas": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "srodowisko": {
            "nazwa": env.name,
            "tylko_dev": env.name == "DEV" and not env.is_prod,
            "site_url": env.site_url,
            "site_id": env.site_id,
            "weryfikacja_graph": f"witryna '{remote.site.get('displayName')}' - adres i Site ID zgodne z DEV",
            "listy": remote.lists_info,
        },
        "zrodlo": {
            "sciezka": str(db_path),
            "sha256_przed": before.sha256,
            "sha256_po": after.sha256,
            "niezmienione": before.same_as(after),
            "rozmiar": before.size,
            "pliki_pomocnicze": list(before.sidecars),
        },
        "http": http,
        "zapisy_wykonane": writer.created if writer is not None else 0,
        "mapa_id": {"sciezka": idmap.path, "wpisow": idmap.count(), "istnieje": os.path.exists(idmap.path)},
        "listy": {
            name: summarize_list(name, plans[name], len(remote.items[name]), files[name][1], files[name][0])
            for name in plans
        },
        "wykonanie": execution,
    }


def save_report(report, directory, prefix):
    directory = assert_outside_repo(directory)
    os.makedirs(directory, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base = os.path.join(directory, f"{prefix}_{stamp}")
    with open(base + ".json", "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=1)
    with open(base + ".txt", "w", encoding="utf-8") as f:
        f.write(render_text(report))
    return base


def _open_context(db_path, token_provider, mapfile_dir, log):
    env = assert_dev_only(get_active_environment())
    before = file_fingerprint(db_path)
    log(f"Źródło: {db_path} (SHA-256 {before.sha256[:16]}...)")
    tables = read_source_tables(db_path)
    token = token_provider()
    reader = MigrationReader(env, token)
    remote = fetch_remote(reader, env)
    idmap = IdMap.load(os.path.join(mapfile_dir, "id_map_DEV.json"), env.name, env.site_id)
    return env, before, tables, reader, remote, idmap


def run_dry_run(db_path=None, report_dir=None, token_provider=None, log=print):
    """Dry-run: tylko odczyty (SQLite mode=ro i GET do Graph). Nie tworzy klienta zapisu."""
    db_path = db_path or default_db_path()
    report_dir = resolve_data_dir(report_dir)
    token_provider = token_provider or _default_token_provider(log)
    env, before, tables, reader, remote, idmap = _open_context(db_path, token_provider, report_dir, log)
    plans = build_plans(tables, remote)
    after = file_fingerprint(db_path)
    report = _build_report("dry-run", env, db_path, before, after, remote, reader, plans, idmap)
    return report


def _latest_dry_run(report_dir):
    files = sorted(glob.glob(os.path.join(report_dir, "dryrun_*.json")))
    if not files:
        return None
    with open(files[-1], "r", encoding="utf-8") as f:
        return json.load(f)


def _default_token_provider(log):
    return lambda: acquire_token(interactive_log=log)["access_token"]


def parse_lists(lists):
    """Zwraca wybrane listy w kolejności importu; wymaga jawnego, poprawnego wyboru."""
    if isinstance(lists, str):
        lists = [x.strip() for x in lists.split(",") if x.strip()]
    if not lists:
        raise MigrationRefused("Podaj listy do migracji (--lists), np. Suppliers,Clients.")
    unknown = [x for x in lists if x not in LIST_ORDER]
    if unknown:
        raise MigrationRefused(f"Nieznane listy: {', '.join(unknown)}. Dozwolone: {', '.join(LIST_ORDER)}.")
    return tuple(n for n in LIST_ORDER if n in lists)


def run_execute(confirm, lists=None, db_path=None, report_dir=None, token_provider=None, allow_errors=False,
                log=print, sleep=time.sleep):
    """Zapis do DEV wskazanych list (etap). Wymaga frazy potwierdzającej i dry-runu dla tego samego pliku bazy."""
    if confirm != CONFIRM_PHRASE:
        raise MigrationRefused(f"Brak potwierdzenia. Użyj --confirm {CONFIRM_PHRASE}.")
    selected = parse_lists(lists)
    db_path = db_path or default_db_path()
    report_dir = resolve_data_dir(report_dir)
    env = assert_dev_only(get_active_environment())

    previous = _latest_dry_run(report_dir)
    current = file_fingerprint(db_path)
    if not previous or previous.get("tryb") != "dry-run":
        raise MigrationRefused("Brak raportu dry-run - najpierw wykonaj dry-run.")
    if previous["zrodlo"]["sha256_przed"] != current.sha256:
        raise MigrationRefused("Baza SQLite zmieniła się od ostatniego dry-runu - powtórz dry-run.")
    prev_errors = sum(previous["listy"][n]["bledne"] for n in selected if n in previous["listy"])
    if prev_errors and not allow_errors:
        raise MigrationRefused(f"Ostatni dry-run zawiera {prev_errors} błędnych rekordów (użyj --allow-errors, aby je pominąć).")

    token_provider = token_provider or _default_token_provider(log)
    env, before, tables, reader, remote, idmap = _open_context(db_path, token_provider, report_dir, log)
    all_plans = build_plans(tables, remote)
    plans = {n: all_plans[n] for n in selected}
    plan_errors = sum(1 for p in plans.values() for e in p if e.action == ERROR)
    if plan_errors and not allow_errors:
        raise MigrationRefused(f"Plan zawiera {plan_errors} błędnych rekordów - przerwano przed zapisem.")

    writer = DevWriter(env, token_provider, reader, sleep=sleep)
    per_list = {n: {"utworzono": 0, "pominieto": 0, "bledy": 0} for n in selected}
    failures = []
    try:
        for name in selected:
            for i, entry in enumerate(plans[name], 1):
                rec = entry.record
                if entry.action == EXISTS:
                    idmap.set(name, rec.key, entry.existing_id, rec.title)
                    per_list[name]["pominieto"] += 1
                elif entry.action == CREATE:
                    try:
                        item_id = writer.create_item(name, rec.fields)
                        idmap.set(name, rec.key, item_id, rec.title)
                        per_list[name]["utworzono"] += 1
                    except (WriteError, GraphError) as e:
                        per_list[name]["bledy"] += 1
                        failures.append({"lista": name, "klucz": rec.key if name not in ("Suppliers", "Clients") else "***",
                                         "blad": str(e)})
                if i % 50 == 0:
                    idmap.save()
                    log(f"  {name}: {i}/{len(plans[name])}")
            idmap.save()
            log(f"Lista {name}: gotowe (utworzono {per_list[name]['utworzono']}, błędy {per_list[name]['bledy']})")
    finally:
        idmap.save()

    # Weryfikacja: ponowny odczyt list i porównanie każdego pola z danymi źródłowymi
    verify_remote = fetch_remote(reader, env)
    verify_plans = build_plans(read_source_tables(db_path), verify_remote)
    checks, all_ok = {}, True
    for n in selected:
        entries = verify_plans[n]
        valid = [e for e in entries if e.action != ERROR]
        identical = sum(1 for e in entries if e.action == EXISTS)
        in_sp = len(verify_remote.items[n])
        no_missing = not any(e.action == CREATE for e in entries)
        ok = (no_missing and identical == len(valid) and in_sp == len(valid)
              and (allow_errors or len(valid) == len(entries)))
        checks[n] = {"zrodlo": len(entries), "w_sharepoint": in_sp, "pola_zgodne": identical,
                     "brakujace": sum(1 for e in entries if e.action == CREATE),
                     "rozne_lub_blad": sum(1 for e in entries if e.action == ERROR), "ok": ok}
        all_ok &= ok
    execution = {
        "listy_etapu": list(selected), "listy": per_list, "kontrola": checks,
        "utworzono": sum(v["utworzono"] for v in per_list.values()),
        "pominieto": sum(v["pominieto"] for v in per_list.values()),
        "bledy": failures, "ponowienia": writer.retries,
        "ok": all_ok and not failures,
        "weryfikacja": ("OK - liczba elementów i wszystkie pola zgodne ze źródłem: "
                        + ", ".join(f"{n} {c['w_sharepoint']}/{c['zrodlo']}" for n, c in checks.items()))
        if all_ok and not failures else f"NIEZGODNOŚCI: {checks}",
    }
    after = file_fingerprint(db_path)
    return _build_report("execute", env, db_path, before, after, remote, reader, plans, idmap,
                         writer=writer, execution=execution)
