"""Walidacja rekordów względem rzeczywistego schematu listy SharePoint oraz plan (create / już istnieje)."""
from dataclasses import dataclass

MULTILINE_DEFAULT_LIMIT = 63999
SINGLE_LINE_DEFAULT_LIMIT = 255

CREATE = "create"
EXISTS = "exists"
ERROR = "error"


@dataclass
class PlanEntry:
    record: object
    action: str
    existing_id: str = None


def _facet(col):
    for name in ("text", "number", "boolean"):
        if name in col:
            return name
    return None


def validate_record(rec, columns):
    """Dopisuje błędy do rec.errors: nieznane pola, typy, długości, wymagane pola."""
    for name, value in rec.fields.items():
        col = columns.get(name)
        if col is None:
            rec.errors.append(f"{name}: kolumna nie istnieje na liście")
            continue
        if col.get("readOnly") or col.get("hidden"):
            rec.errors.append(f"{name}: kolumna tylko do odczytu/ukryta")
            continue
        _validate_value(rec, name, value, col)

    for name, col in columns.items():
        if not col.get("required") or col.get("readOnly") or col.get("hidden"):
            continue
        value = rec.fields.get(name)
        if value is None or (isinstance(value, str) and value.strip() == ""):
            rec.errors.append(f"{name}: brak wartości w polu wymaganym")


def _validate_value(rec, name, value, col):
    facet = _facet(col)
    if value is None:
        return
    if facet == "text":
        if not isinstance(value, str):
            rec.errors.append(f"{name}: oczekiwano tekstu, jest {type(value).__name__}")
            return
        spec = col["text"]
        if spec.get("allowMultipleLines"):
            limit = spec.get("maxLength") or MULTILINE_DEFAULT_LIMIT
        else:
            limit = spec.get("maxLength") or SINGLE_LINE_DEFAULT_LIMIT
            if "\n" in value or "\r" in value:
                rec.errors.append(f"{name}: nowa linia w kolumnie jednoliniowej")
        if len(value) > limit:
            rec.errors.append(f"{name}: długość {len(value)} przekracza limit {limit}")
    elif facet == "number":
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            rec.errors.append(f"{name}: oczekiwano liczby, jest {type(value).__name__}")
            return
        spec = col["number"]
        if spec.get("decimalPlaces") == "none" and float(value) != int(value):
            rec.errors.append(f"{name}: wartość {value} nie jest liczbą całkowitą")
        lo, hi = spec.get("minimum"), spec.get("maximum")
        if lo is not None and value < lo or hi is not None and value > hi:
            rec.errors.append(f"{name}: wartość {value} poza zakresem")
    elif facet == "boolean":
        if not isinstance(value, bool):
            rec.errors.append(f"{name}: oczekiwano wartości logicznej, jest {type(value).__name__}")
    else:
        rec.errors.append(f"{name}: nieobsługiwany typ kolumny")


def _norm(value):
    if isinstance(value, str):
        return value.replace("\r\n", "\n")
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return float(value)
    return value


def differing_fields(fields, existing_fields):
    return [k for k, v in fields.items() if _norm(v) != _norm(existing_fields.get(k))]


def _unique_columns(columns, fields):
    return [n for n, c in columns.items() if c.get("enforceUniqueValues") and n in fields]


def plan_list(records, columns, existing_items):
    """Zwraca listę PlanEntry. existing_items: elementy z Graph ({'id', 'fields'})."""
    for rec in records:
        validate_record(rec, columns)

    unique_names = set()
    for rec in records:
        unique_names.update(_unique_columns(columns, rec.fields))

    by_title = {}
    existing_unique = {n: {} for n in unique_names}
    for item in existing_items:
        f = item.get("fields", {})
        if f.get("Title") is not None:
            by_title[str(f["Title"]).lower()] = item
        for n in unique_names:
            if f.get(n) is not None:
                existing_unique[n].setdefault(str(f[n]).lower(), item)

    seen = {n: {} for n in unique_names}
    plan = []
    for rec in records:
        entry = PlanEntry(rec, CREATE)
        if not rec.errors:
            item = by_title.get(rec.title.lower())
            if item is not None:
                diff = differing_fields(rec.fields, item.get("fields", {}))
                if diff:
                    rec.errors.append(
                        f"element o tym samym Title już istnieje w SharePoint (ID {item['id']}) "
                        f"i różni się polami: {', '.join(diff)}")
                else:
                    entry.action, entry.existing_id = EXISTS, str(item["id"])
            else:
                for n in _unique_columns(columns, rec.fields):
                    clash = existing_unique[n].get(str(rec.fields[n]).lower())
                    if clash is not None:
                        rec.errors.append(f"{n}: wartość unikalna już zajęta w SharePoint (element ID {clash['id']})")
        for n in _unique_columns(columns, rec.fields):
            value = rec.fields[n]
            if value is None:
                continue
            first = seen[n].get(str(value).lower())
            if first is None:
                seen[n][str(value).lower()] = rec.key
            else:
                rec.errors.append(f"{n}: duplikat wartości unikalnej w źródle (pierwszy: {first})")
        if rec.errors:
            entry.action = ERROR
        plan.append(entry)
    return plan
