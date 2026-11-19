"""Test zapisu na DEV: jeden syntetyczny rekord w liście Clients (utwórz -> odczytaj -> usuń -> zweryfikuj).

Zakres jest celowo wąski: wyłącznie DEV, wyłącznie lista Clients, wyłącznie element o Title z prefiksem
ZZTEST-, usuwany po otrzymanym Item ID. Przy błędzie nie są wykonywane żadne dalsze zapisy
(poza usunięciem właśnie utworzonego elementu testowego).
"""
import json
import os
import uuid
from datetime import datetime

from src.integrations.sharepoint.environment import get_active_environment
from src.integrations.sharepoint.graph_client import GraphError

from .datadir import assert_outside_repo, resolve_data_dir
from .guard import assert_dev_only
from .runner import MigrationReader, _default_token_provider, fetch_remote
from .mapping import Record
from .validate import differing_fields, validate_record
from .writer import SYNTHETIC_LIST, SYNTHETIC_PREFIX, DevWriter, WriteError

CONFIRM_SYNTHETIC = "SYNTHETIC-TEST-DEV"


def build_payload(test_id):
    return {
        "Title": f"{SYNTHETIC_PREFIX}{test_id}",
        "CompanyName": "ZZTEST firma syntetyczna - do usunięcia",
        "AddressP1": "ul. Testowa 0",
        "AddressP2": "00-000 Testowo",
        "Alias": f"{SYNTHETIC_PREFIX}ALIAS-{test_id}",
        "WarunkiDostawy": "ZZTEST linia 1\nZZTEST linia 2 - zażółć gęślą jaźń",
    }


def execute_synthetic(env, reader, writer, columns, existing_items, test_id, log=print):
    """Wykonuje cały scenariusz na podanych zależnościach i zwraca raport (dict)."""
    payload = build_payload(test_id)
    report = {
        "tryb": "synthetic-test", "czas": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "srodowisko": {"nazwa": env.name, "site_url": env.site_url, "site_id": env.site_id,
                       "lista": SYNTHETIC_LIST, "list_id": env.lists[SYNTHETIC_LIST]},
        "test_id": test_id, "payload": payload, "kroki": [], "item_id": None,
        "odpowiedz_graph_utworzenie": None, "odczyt_zwrotny": None, "usuwanie": None,
        "weryfikacja_koncowa": None, "wynik": "NIEUDANY",
    }
    steps = report["kroki"]

    def step(name, ok, detail=""):
        steps.append({"krok": name, "ok": ok, "szczegoly": detail})
        log(f"[{'OK' if ok else 'BŁĄD'}] {name}" + (f" - {detail}" if detail else ""))
        return ok

    item_id = None
    try:
        if not step("Warunek wstępny: lista Clients jest pusta", not existing_items,
                    f"elementów: {len(existing_items)}"):
            return report

        rec = Record(SYNTHETIC_LIST, payload["Title"], payload["Title"], payload, "synthetic")
        validate_record(rec, columns)
        if not step("Payload zgodny ze schematem listy (wymagane pola, typy, długości)", not rec.errors,
                    "; ".join(rec.errors)):
            return report

        try:
            item_id = writer.create_item(SYNTHETIC_LIST, payload)
        except (WriteError, GraphError) as e:
            step("Utworzenie elementu (POST)", False, str(e))
            return report
        report["item_id"] = item_id
        report["odpowiedz_graph_utworzenie"] = writer.last_response
        step("Utworzenie elementu (POST)", True, f"Item ID = {item_id}")

        item_path = f"/sites/{env.site_id}/lists/{env.lists[SYNTHETIC_LIST]}/items/{item_id}"
        back = reader.get(item_path, params={"$expand": "fields"})
        fields = back.get("fields", {})
        diff = differing_fields(payload, fields)
        report["odczyt_zwrotny"] = {
            "pola": {k: fields.get(k) for k in payload}, "zgodne": not diff, "roznice": diff,
        }
        step("Odczyt zwrotny i porównanie z wysłanym payloadem", not diff,
             f"różnice w polach: {diff}" if diff else f"{len(payload)} pól zgodnych")
    except (GraphError, WriteError) as e:
        step("Odczyt zwrotny", False, str(e))
    finally:
        if item_id is not None:
            try:
                gone = not writer.delete_synthetic_item(SYNTHETIC_LIST, item_id, payload["Title"])
                report["usuwanie"] = {"item_id": item_id, "usuniety": True, "juz_nie_istnial": gone}
                step("Usunięcie elementu testowego po Item ID (DELETE)", True, f"Item ID = {item_id}")
            except (WriteError, GraphError) as e:
                report["usuwanie"] = {"item_id": item_id, "usuniety": False, "blad": str(e)}
                step("Usunięcie elementu testowego po Item ID (DELETE)", False,
                     f"{e} - ELEMENT TESTOWY (ID {item_id}) MOŻE POZOSTAWAĆ NA LIŚCIE")

    if item_id is not None:
        verification = {"element_istnieje": None, "http_status_odczytu": None, "clients_elementow": None}
        try:
            reader.get(f"/sites/{env.site_id}/lists/{env.lists[SYNTHETIC_LIST]}/items/{item_id}")
            verification["element_istnieje"], verification["http_status_odczytu"] = True, 200
        except GraphError as e:
            verification["http_status_odczytu"] = e.status
            verification["element_istnieje"] = False if e.status == 404 else None
        try:
            items = reader.get_all(f"/sites/{env.site_id}/lists/{env.lists[SYNTHETIC_LIST]}/items",
                                   params={"$top": "200"})
            verification["clients_elementow"] = len(items)
        except GraphError as e:
            verification["blad_listy"] = str(e)
        report["weryfikacja_koncowa"] = verification
        step("Po usunięciu GET elementu zwraca 404 (rekordu nie ma)", verification["element_istnieje"] is False,
             f"HTTP {verification['http_status_odczytu']}")
        step("Lista Clients jest ponownie pusta", verification["clients_elementow"] == 0,
             f"elementów: {verification['clients_elementow']}")

    report["wynik"] = "UDANY" if steps and all(s["ok"] for s in steps) and item_id is not None else "NIEUDANY"
    return report


def render_text(report):
    L = [f"=== RAPORT TESTU ZAPISU (syntetyczny rekord, DEV) - WYNIK: {report['wynik']} ===",
         f"Czas: {report['czas']}",
         f"Środowisko: {report['srodowisko']['nazwa']}   Witryna: {report['srodowisko']['site_url']}",
         f"Site ID: {report['srodowisko']['site_id']}",
         f"Lista: {report['srodowisko']['lista']} ({report['srodowisko']['list_id']})",
         f"Identyfikator testowy: {report['test_id']}   Item ID: {report['item_id']}", "",
         "--- Wysłany payload (fields) ---", json.dumps(report["payload"], ensure_ascii=False, indent=1), "",
         "--- Odpowiedź Graph na utworzenie ---",
         json.dumps(report["odpowiedz_graph_utworzenie"], ensure_ascii=False, indent=1), "",
         "--- Odczyt zwrotny ---", json.dumps(report["odczyt_zwrotny"], ensure_ascii=False, indent=1), "",
         "--- Usuwanie ---", json.dumps(report["usuwanie"], ensure_ascii=False, indent=1), "",
         "--- Weryfikacja końcowa ---", json.dumps(report["weryfikacja_koncowa"], ensure_ascii=False, indent=1), "",
         "--- Kroki ---"]
    L += [f"[{'OK' if s['ok'] else 'BŁĄD'}] {s['krok']}" + (f" - {s['szczegoly']}" if s["szczegoly"] else "")
          for s in report["kroki"]]
    http = report.get("http", {})
    L += ["", f"Żądania HTTP: {http}", f"Operacje na PROD: NIE   Migracja właściwych danych: NIE"]
    return "\n".join(L)


def run_synthetic_test(confirm, token_provider=None, report_dir=None, log=print):
    if confirm != CONFIRM_SYNTHETIC:
        raise ValueError(f"Brak potwierdzenia. Użyj --confirm {CONFIRM_SYNTHETIC}.")
    directory = resolve_data_dir(report_dir)
    env = assert_dev_only(get_active_environment())
    token_provider = token_provider or _default_token_provider(log)
    reader = MigrationReader(env, token_provider())
    remote = fetch_remote(reader, env)  # tylko odczyty + weryfikacja witryny i list DEV
    writer = DevWriter(env, token_provider, reader)
    test_id = f"{datetime.now():%Y%m%d%H%M%S}-{uuid.uuid4().hex[:8]}"
    report = execute_synthetic(env, reader, writer, remote.columns[SYNTHETIC_LIST],
                               remote.items[SYNTHETIC_LIST], test_id, log=log)
    http = dict(reader.calls)
    http["POST"], http["DELETE"] = writer.attempts, writer.delete_attempts
    report["http"] = http
    directory = assert_outside_repo(directory)
    os.makedirs(directory, exist_ok=True)
    base = os.path.join(directory, f"synthetic_test_{datetime.now():%Y%m%d_%H%M%S}")
    with open(base + ".json", "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=1)
    with open(base + ".txt", "w", encoding="utf-8") as f:
        f.write(render_text(report))
    report["_plik"] = base
    return report
