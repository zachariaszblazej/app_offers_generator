"""Raport migracji: dane bez ujawniania treści wrażliwych (maskowanie) oraz tekstowy rendering."""
import json
from collections import Counter

SENSITIVE_LISTS = ("Suppliers", "Clients")
CONTEXT_FIELDS = ("OfferContext", "WzContext")
MAX_LISTED = 40


def mask(value):
    text = str(value)
    return f"{text[:2]}***{text[-1:]}" if len(text) > 4 else "***"


def display_key(list_name, key):
    return mask(key) if list_name in SENSITIVE_LISTS else key


def sample_payload(list_name, fields):
    """Przykładowy payload: dane firm maskowane, kontekst JSON tylko jako opis (przenoszony bez zmian)."""
    out = {}
    for name, value in fields.items():
        if name in CONTEXT_FIELDS:
            try:
                n_keys = len(json.loads(value))
            except (ValueError, TypeError):
                n_keys = "?"
            out[name] = f"<JSON {len(value)} znaków, {n_keys} kluczy - bez zmian>"
        elif list_name in SENSITIVE_LISTS and isinstance(value, str):
            out[name] = mask(value)
        else:
            out[name] = value
    return out


def summarize_list(list_name, plan, existing_count, missing_files, file_check_possible):
    actions = Counter(e.action for e in plan)
    errors, infos, warnings = [], Counter(), Counter()
    for e in plan:
        for msg in e.record.errors:
            errors.append({"klucz": display_key(list_name, e.record.key), "zrodlo": e.record.source_ref, "blad": msg})
        for msg in e.record.infos:
            infos[msg] += 1
        for msg in e.record.warnings:
            warnings[msg] += 1
    sample = next((e.record for e in plan if e.record.fields), None)
    return {
        "zrodlo_rekordow": len(plan),
        "poprawne": actions["create"] + actions["exists"],
        "bledne": actions["error"],
        "do_utworzenia": actions["create"],
        "juz_istnieje_identyczne": actions["exists"],
        "elementow_w_sharepoint_przed": existing_count,
        "bledy": errors,
        "ostrzezenia": dict(warnings),
        "informacje": dict(infos),
        "brakujace_pliki": [{"klucz": display_key(list_name, k), "sciezka": p} for k, p in missing_files],
        "sprawdzono_pliki": file_check_possible,
        "przykladowy_payload": sample_payload(list_name, sample.fields) if sample else None,
    }


def render_text(report):
    L = []
    add = L.append
    env = report["srodowisko"]
    add(f"=== RAPORT MIGRACJI SQLite -> SharePoint ({report['tryb'].upper()}) ===")
    add(f"Czas: {report['czas']}")
    add("")
    add("--- Środowisko docelowe ---")
    add(f"Środowisko: {env['nazwa']}   (wyłącznie DEV: {'TAK' if env['tylko_dev'] else 'NIE'})")
    add(f"Witryna:    {env['site_url']}")
    add(f"Site ID:    {env['site_id']}")
    add(f"Weryfikacja przez Graph: {env['weryfikacja_graph']}")
    for name, info in env["listy"].items():
        add(f"  lista {name:<10} {info}")
    add("")
    src = report["zrodlo"]
    add("--- Źródło SQLite ---")
    add(f"Plik: {src['sciezka']}")
    add(f"SHA-256 przed: {src['sha256_przed']}")
    add(f"SHA-256 po:    {src['sha256_po']}")
    add(f"Źródło niezmienione: {'TAK' if src['niezmienione'] else 'NIE !!!'}   "
        f"(rozmiar {src['rozmiar']} B, pliki pomocnicze: {src['pliki_pomocnicze'] or 'brak'})")
    add("Tryb otwarcia: mode=ro + PRAGMA query_only=ON")
    add("")
    add("--- Podsumowanie list (kolejność importu) ---")
    add(f"{'Lista':<11}{'źródło':>8}{'poprawne':>10}{'błędne':>8}{'do utw.':>9}{'już jest':>10}{'w SP przed':>12}{'brak plików':>13}")
    tot = Counter()
    for name, s in report["listy"].items():
        add(f"{name:<11}{s['zrodlo_rekordow']:>8}{s['poprawne']:>10}{s['bledne']:>8}{s['do_utworzenia']:>9}"
            f"{s['juz_istnieje_identyczne']:>10}{s['elementow_w_sharepoint_przed']:>12}{len(s['brakujace_pliki']):>13}")
        for k in ("zrodlo_rekordow", "poprawne", "bledne", "do_utworzenia", "juz_istnieje_identyczne"):
            tot[k] += s[k]
    add(f"{'RAZEM':<11}{tot['zrodlo_rekordow']:>8}{tot['poprawne']:>10}{tot['bledne']:>8}{tot['do_utworzenia']:>9}"
        f"{tot['juz_istnieje_identyczne']:>10}")
    add("")
    for name, s in report["listy"].items():
        add(f"--- {name} ---")
        if s["bledy"]:
            add(f"Błędy ({len(s['bledy'])}):")
            for e in s["bledy"][:MAX_LISTED]:
                add(f"  [{e['klucz']}] ({e['zrodlo']}) {e['blad']}")
            if len(s["bledy"]) > MAX_LISTED:
                add(f"  ... i {len(s['bledy']) - MAX_LISTED} kolejnych")
        else:
            add("Błędy: brak (wymagane pola, długości, typy i unikalność OK)")
        for msg, n in s["ostrzezenia"].items():
            add(f"Ostrzeżenie [{n}]: {msg}")
        for msg, n in s["informacje"].items():
            add(f"Informacja [{n}]: {msg}")
        if s["sprawdzono_pliki"] is None:
            pass
        elif not s["sprawdzono_pliki"]:
            add("Pliki: nie sprawdzono (folder dokumentów nie jest dostępny)")
        elif s["brakujace_pliki"]:
            for m in s["brakujace_pliki"]:
                add(f"BRAK PLIKU: [{m['klucz']}] {m['sciezka']}  (rekord i tak zostanie przeniesiony)")
        else:
            add("Pliki: wszystkie istnieją")
        add("Przykładowy payload (fields; dane firm zamaskowane):")
        add("  " + json.dumps(s["przykladowy_payload"], ensure_ascii=False))
        add("")
    http = report["http"]
    add("--- Operacje na SharePoint ---")
    add(f"Żądania HTTP: GET={http.get('GET', 0)}, POST={http.get('POST', 0)}, "
        f"PATCH={http.get('PATCH', 0)}, DELETE={http.get('DELETE', 0)}")
    add(f"Zapisy do SharePoint wykonane: {'NIE' if report['zapisy_wykonane'] == 0 else report['zapisy_wykonane']}")
    add(f"Mapa ID: {report['mapa_id']['sciezka']} (wpisów: {report['mapa_id']['wpisow']}, "
        f"plik istnieje: {'tak' if report['mapa_id']['istnieje'] else 'nie'})")
    if report.get("wykonanie"):
        w = report["wykonanie"]
        add("")
        add("--- Wykonanie ---")
        add(f"Listy etapu: {', '.join(w['listy_etapu'])}")
        add(f"Utworzono: {w['utworzono']}, pominięto (już istniały): {w['pominieto']}, "
            f"błędy zapisu: {len(w['bledy'])}, ponowienia 429/503: {w['ponowienia']}")
        for n, v in w["listy"].items():
            c = w["kontrola"][n]
            add(f"  {n:<10} utworzono {v['utworzono']:>4}  pominięto {v['pominieto']:>4}  błędy {v['bledy']:>3}  | "
                f"w SharePoint {c['w_sharepoint']}/{c['zrodlo']}, pola zgodne {c['pola_zgodne']}, "
                f"brakujące {c['brakujace']}, różne/błąd {c['rozne_lub_blad']} -> {'OK' if c['ok'] else 'NIEZGODNE'}")
        for e in w["bledy"][:MAX_LISTED]:
            add(f"  BŁĄD ZAPISU [{e['lista']}/{e['klucz']}] {e['blad']}")
        add(f"Weryfikacja po zapisie: {w['weryfikacja']}")
        add(f"WYNIK ETAPU: {'UDANY' if w['ok'] else 'NIEUDANY'}")
    return "\n".join(L)
