"""Mapowanie wierszy SQLite na elementy list SharePoint (bez zapisów, czyste funkcje).

Zasady (uzgodnione):
* Title w SharePoint to techniczny, unikalny tytuł elementu - dla ofert "{numer}/OF/{rok}",
  dla WZ "WZ_{numer}_{rok}", dla klientów i dostawców 10-znakowy NIP z zerami wiodącymi.
* OfferFilePath/WzFilePath oraz OfferContext/WzContext są przenoszone bez zmian.
* Jedyna zmiana wartości: Clients.AddressP2 - znak nowej linii zastępowany przez ", ".
* Dane historyczne (pozostałości XML, wielkość liter aliasów itd.) nie są poprawiane.
"""
import json
import re
from dataclasses import dataclass, field

CLIENT_OPTIONAL_TEXT = (
    "TerminRealizacji", "TerminPlatnosci", "WarunkiDostawy",
    "WaznoscOferty", "Gwarancja", "Cena",
)

_OFFER_PATH_RE = re.compile(r"_OF_\d{4}_(.+)\.docx$")
_WZ_PATH_RE = re.compile(r"_\d{4}_(.+)\.docx$")


@dataclass
class Record:
    list_name: str
    key: str
    title: str
    fields: dict
    source_ref: str
    file_check: tuple = None  # (rodzaj, ścieżka względna) - do sprawdzenia istnienia pliku
    errors: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    infos: list = field(default_factory=list)


def format_nip(value) -> str:
    if value is None or isinstance(value, bool):
        raise ValueError("pusty NIP")
    text = str(value).strip()
    if not text.isdigit():
        raise ValueError("NIP zawiera znaki inne niż cyfry")
    if len(text) > 10:
        raise ValueError(f"NIP ma {len(text)} cyfr (maks. 10)")
    return text.zfill(10)


def newline_to_comma(value):
    if value is None:
        return value
    return str(value).replace("\r\n", ", ").replace("\n", ", ").replace("\r", ", ")


def _to_int(value, name):
    if isinstance(value, bool):
        raise ValueError(f"{name}: wartość logiczna zamiast liczby")
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip().lstrip("-").isdigit():
        return int(value.strip())
    raise ValueError(f"{name}: oczekiwano liczby całkowitej, jest {value!r}")


def _base(list_name, key, title, fields, row):
    return Record(list_name, key, title, fields, f"rowid={row.get('_rowid_')}")


def map_suppliers(rows):
    records = []
    for row in rows:
        try:
            nip = format_nip(row.get("Nip"))
        except ValueError as e:
            records.append(Record("Suppliers", f"?rowid={row.get('_rowid_')}", "", {},
                                  f"rowid={row.get('_rowid_')}", errors=[str(e)]))
            continue
        fields = {
            "Title": nip,
            "CompanyName": row.get("CompanyName"),
            "AddressP1": row.get("AddressP1"),
            "AddressP2": row.get("AddressP2"),
            "IsDefault": bool(row.get("IsDefault") or 0),
        }
        records.append(_base("Suppliers", nip, nip, fields, row))
    return records


def map_clients(rows):
    records = []
    for row in rows:
        try:
            nip = format_nip(row.get("Nip"))
        except ValueError as e:
            records.append(Record("Clients", f"?rowid={row.get('_rowid_')}", "", {},
                                  f"rowid={row.get('_rowid_')}", errors=[str(e)]))
            continue
        address2 = row.get("AddressP2")
        fields = {
            "Title": nip,
            "CompanyName": row.get("CompanyName"),
            "AddressP1": row.get("AddressP1"),
            "AddressP2": newline_to_comma(address2),
            "Alias": row.get("Alias"),
        }
        for name in CLIENT_OPTIONAL_TEXT:
            if row.get(name) is not None:
                fields[name] = row[name]
        rec = _base("Clients", nip, nip, fields, row)
        if address2 is not None and fields["AddressP2"] != address2:
            rec.infos.append("AddressP2: nowa linia zastąpiona przez ', '")
        records.append(rec)
    return records


def _context_infos(rec, context_text, number_key, expected_prefix):
    if not context_text:
        return
    try:
        data = json.loads(context_text)
    except ValueError:
        rec.warnings.append("kontekst nie jest poprawnym JSON (przenoszony bez zmian)")
        return
    if "<w:" in context_text:
        rec.infos.append("kontekst zawiera pozostałości XML (przenoszone bez zmian)")
    number = data.get(number_key) if isinstance(data, dict) else None
    if number is not None and not str(number).startswith(expected_prefix):
        rec.warnings.append(f"{number_key} w kontekście nie zaczyna się od '{expected_prefix}'")


def _file_alias_info(rec, path, regex, client_aliases):
    m = regex.search(path or "")
    if m and client_aliases is not None and m.group(1) not in client_aliases:
        rec.infos.append("alias z nazwy pliku nie występuje dokładnie w Clients.Alias (np. inna wielkość liter)")


def map_offers(rows, client_aliases=None):
    records = []
    for row in rows:
        ref = f"rowid={row.get('_rowid_')}"
        try:
            year = _to_int(row.get("OfferYearNumber"), "OfferYearNumber")
            order = _to_int(row.get("OfferOrderNumber"), "OfferOrderNumber")
        except ValueError as e:
            records.append(Record("Offers", f"?{ref}", "", {}, ref, errors=[str(e)]))
            continue
        title = f"{order}/OF/{year}"
        fields = {
            "Title": title,
            "OfferYearNumber": year,
            "OfferOrderNumber": order,
            "OfferFilePath": row.get("OfferFilePath"),
        }
        if row.get("OfferContext") is not None:
            fields["OfferContext"] = row["OfferContext"]
        rec = Record("Offers", f"{year}/{order}", title, fields, ref,
                     file_check=("offers", row.get("OfferFilePath")))
        _context_infos(rec, row.get("OfferContext"), "offer_number", title)
        _file_alias_info(rec, row.get("OfferFilePath"), _OFFER_PATH_RE, client_aliases)
        records.append(rec)
    return records


def map_wuzetkas(rows, client_aliases=None):
    records = []
    for row in rows:
        ref = f"rowid={row.get('_rowid_')}"
        try:
            year = _to_int(row.get("WzYearNumber"), "WzYearNumber")
            order = _to_int(row.get("WzOrderNumber"), "WzOrderNumber")
        except ValueError as e:
            records.append(Record("Wuzetkas", f"?{ref}", "", {}, ref, errors=[str(e)]))
            continue
        title = f"WZ_{order}_{year}"
        fields = {
            "Title": title,
            "WzYearNumber": year,
            "WzOrderNumber": order,
            "WzFilePath": row.get("WzFilePath"),
        }
        if row.get("WzContext") is not None:
            fields["WzContext"] = row["WzContext"]
        rec = Record("Wuzetkas", f"{year}/{order}", title, fields, ref,
                     file_check=("wz", row.get("WzFilePath")))
        _context_infos(rec, row.get("WzContext"), "wz_number", title)
        _file_alias_info(rec, row.get("WzFilePath"), _WZ_PATH_RE, client_aliases)
        records.append(rec)
    return records


def map_all(tables):
    """Zwraca rekordy w kolejności importu: Suppliers -> Clients -> Offers -> Wuzetkas."""
    clients = map_clients(tables["Clients"])
    aliases = {r.get("Alias") for r in tables["Clients"]}
    return {
        "Suppliers": map_suppliers(tables["Suppliers"]),
        "Clients": clients,
        "Offers": map_offers(tables["Offers"], aliases),
        "Wuzetkas": map_wuzetkas(tables["Wuzetkas"], aliases),
    }
