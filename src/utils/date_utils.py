"""Polish date formatting utilities (genitive month names)."""
from __future__ import annotations
import datetime as _dt

# Genitive month names used after day numbers in Polish dates
_POLISH_MONTHS_GENITIVE = {
    1: "stycznia",
    2: "lutego",
    3: "marca",
    4: "kwietnia",
    5: "maja",
    6: "czerwca",
    7: "lipca",
    8: "sierpnia",
    9: "września",
    10: "października",
    11: "listopada",
    12: "grudnia",
}

def format_polish_date(date: _dt.datetime | _dt.date) -> str:
    """Return date formatted as 'D <miesiąca> RRRR' without leading zero in day.
    Accepts datetime or date.
    """
    if isinstance(date, _dt.datetime):
        d = date
    else:
        # date object (no time)
        d = _dt.datetime(date.year, date.month, date.day)
    month = _POLISH_MONTHS_GENITIVE.get(d.month, "")
    return f"{d.day} {month} {d.year}".strip()

__all__ = ["format_polish_date"]
