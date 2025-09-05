"""Service to restore (re-generate) Offer and WZ Word documents from an existing legacy database file.

Usage workflow (orchestrated by UI window):
- Provide path to .db (SQLite) file (read-only)
- Provide output root folder (created if missing)
- For each record in Offers table having (OfferFilePath, OfferContext JSON) generate a .docx
- For each record in Wuzetkas table having (WzFilePath, WzContext JSON) generate a .docx
- Offers: select the proper template using existing select_template logic
- WZ: use existing wz template selection (simple fixed template?)

The database schema is expected to contain columns:
 Offers(OfferFilePath TEXT, OfferContext TEXT)
 Wuzetkas(WzFilePath TEXT, WzContext TEXT)

We do NOT write back to the DB. Pure export.
"""
from __future__ import annotations
import os, json, sqlite3, datetime
from typing import Optional, Callable
import tkinter.messagebox

# Reuse existing logic
from src.services.offer_generator_service import select_template, convert_date
from docxtpl import DocxTemplate, RichText

TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'templates')

OFFER_TEMPLATES = {
    'offer_template.docx',
    'offer_template_no_gwarancja.docx',
    'offer_template_long_names.docx',
    'offer_template_long_names_no_gwarancja.docx',
}

DEFAULT_WZ_TEMPLATE_CANDIDATES = [
    'wz_template.docx',
    'wz_template_long_names.docx'
]

class RestoreReport:
    def __init__(self):
        self.offers_total = 0
        self.offers_ok = 0
        self.offers_errors: list[str] = []
        self.wz_total = 0
        self.wz_ok = 0
        self.wz_errors: list[str] = []

    def summary_text(self) -> str:
        return ("Przywracanie zakończone.\n"
                f"Oferty: {self.offers_ok}/{self.offers_total} OK\n"
                f"WZ: {self.wz_ok}/{self.wz_total} OK\n"
                + ("\nBłędy ofert:\n" + "\n".join(self.offers_errors) if self.offers_errors else "")
                + ("\nBłędy WZ:\n" + "\n".join(self.wz_errors) if self.wz_errors else "")
               )

def _rich(value: str | None):
    if not value:
        return ""
    if '\\n' not in value:
        return value
    rt = RichText()
    rt.add(value.replace('\\n', '\n'))
    return rt

def _ensure_parent(path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)

def restore_from_database(db_path: str, output_root: str, progress_cb: Optional[Callable[[str], None]] = None) -> RestoreReport:
    rep = RestoreReport()
    if progress_cb is None:
        progress_cb = lambda msg: None

    if not os.path.isfile(db_path):
        raise FileNotFoundError(f"Brak pliku bazy: {db_path}")
    os.makedirs(output_root, exist_ok=True)

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Offers
    try:
        cur.execute("SELECT OfferFilePath, OfferContext FROM Offers")
        rows = cur.fetchall()
        rep.offers_total = len(rows)
        for rel_path, ctx_json in rows:
            if not rel_path:
                rep.offers_errors.append("Pusty OfferFilePath")
                continue
            try:
                context = json.loads(ctx_json) if ctx_json else {}
            except Exception as e:  # malformed JSON
                rep.offers_errors.append(f"{rel_path}: JSON error {e}")
                continue
            try:
                # Rebuild template selection context
                supplier_name = context.get('supplier_name', '')
                supplier_address1 = context.get('supplier_address_1', '')
                client_name = context.get('client_name', '')
                client_address1 = context.get('client_address_1', '')
                gwarancja = context.get('gwarancja', '')
                template_name = select_template(supplier_name, supplier_address1, client_name, client_address1, gwarancja)
                template_path = os.path.join(TEMPLATES_DIR, template_name)
                if not os.path.isfile(template_path):
                    raise FileNotFoundError(f"Brak szablonu: {template_name}")

                # Convert date in context
                date_raw = context.get('date')
                if isinstance(date_raw, str):
                    # Try ISO parse else fallback now
                    try:
                        date_dt = datetime.datetime.fromisoformat(date_raw)
                    except Exception:
                        date_dt = datetime.datetime.now()
                elif isinstance(date_raw, (datetime.date, datetime.datetime)):
                    date_dt = datetime.datetime.combine(date_raw, datetime.time()) if isinstance(date_raw, datetime.date) and not isinstance(date_raw, datetime.datetime) else date_raw
                else:
                    date_dt = datetime.datetime.now()
                context['date'] = convert_date(date_dt)

                # Replace newline markers
                context['client_name'] = _rich(context.get('client_name'))
                context['supplier_name'] = _rich(context.get('supplier_name'))

                # Build absolute target path (Offers folder prefix)
                target_path = os.path.join(output_root, 'Oferty', rel_path)
                _ensure_parent(target_path)

                doc = DocxTemplate(template_path)
                doc.render(context)
                doc.save(target_path)
                rep.offers_ok += 1
                progress_cb(f"Oferta: {rel_path}")
            except Exception as e:
                rep.offers_errors.append(f"{rel_path}: {e}")
    except sqlite3.Error as e:
        rep.offers_errors.append(f"DB error (Offers): {e}")

    # WZ
    try:
        cur.execute("SELECT WzFilePath, WzContext FROM Wuzetkas")
        rows = cur.fetchall()
        rep.wz_total = len(rows)
        # Pick first available wz template
        wz_template_path = None
        for cand in DEFAULT_WZ_TEMPLATE_CANDIDATES:
            p = os.path.join(TEMPLATES_DIR, cand)
            if os.path.isfile(p):
                wz_template_path = p
                break
        for rel_path, ctx_json in rows:
            if not rel_path:
                rep.wz_errors.append("Pusty WzFilePath")
                continue
            try:
                context = json.loads(ctx_json) if ctx_json else {}
            except Exception as e:
                rep.wz_errors.append(f"{rel_path}: JSON error {e}")
                continue
            try:
                if not wz_template_path:
                    raise FileNotFoundError("Brak szablonu WZ")
                # Convert date to Polish long form (e.g. '4 sierpnia 2025') similar to offers
                date_raw = context.get('date')
                try:
                    # If already in Polish long form (month name), leave as is
                    if isinstance(date_raw, str) and any(m in date_raw.lower() for m in [
                        'stycznia','lutego','marca','kwietnia','maja','czerwca','lipca','sierpnia','września','października','listopada','grudnia'
                    ]):
                        pass
                    else:
                        date_dt = None
                        if isinstance(date_raw, str):
                            # Try multiple patterns
                            patterns = [
                                '%Y-%m-%d', '%d-%m-%Y', '%d.%m.%Y', '%d/%m/%Y', '%d %m %Y'
                            ]
                            for p in patterns:
                                try:
                                    date_dt = datetime.datetime.strptime(date_raw, p)
                                    break
                                except Exception:
                                    continue
                            if date_dt is None:
                                # last resort ISO attempt
                                try:
                                    date_dt = datetime.datetime.fromisoformat(date_raw)
                                except Exception:
                                    date_dt = datetime.datetime.now()
                        elif isinstance(date_raw, (datetime.date, datetime.datetime)):
                            date_dt = date_raw if isinstance(date_raw, datetime.datetime) else datetime.datetime.combine(date_raw, datetime.time())
                        else:
                            date_dt = datetime.datetime.now()
                        context['date'] = convert_date(date_dt)
                except Exception:
                    # On any failure just force now() formatted
                    context['date'] = convert_date(datetime.datetime.now())
                # Newline conversions
                context['client_name'] = _rich(context.get('client_name'))
                context['supplier_name'] = _rich(context.get('supplier_name'))

                # Build absolute target path (WZki folder prefix)
                target_path = os.path.join(output_root, 'WZki', rel_path)
                _ensure_parent(target_path)
                doc = DocxTemplate(wz_template_path)
                doc.render(context)
                doc.save(target_path)
                rep.wz_ok += 1
                progress_cb(f"WZ: {rel_path}")
            except Exception as e:
                rep.wz_errors.append(f"{rel_path}: {e}")
    except sqlite3.Error as e:
        rep.wz_errors.append(f"DB error (Wuzetkas): {e}")

    conn.close()
    return rep
