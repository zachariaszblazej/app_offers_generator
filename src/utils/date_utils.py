"""Date formatting utilities for Polish and English (genitive month names)."""
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

# English month names
_ENGLISH_MONTHS = {
    1: "January",
    2: "February",
    3: "March",
    4: "April",
    5: "May",
    6: "June",
    7: "July",
    8: "August",
    9: "September",
    10: "October",
    11: "November",
    12: "December",
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

def format_english_date(date: _dt.datetime | _dt.date) -> str:
    """Return date formatted as 'Month D, YYYY' (e.g., 'November 13, 2025').
    Accepts datetime or date.
    """
    if isinstance(date, _dt.datetime):
        d = date
    else:
        # date object (no time)
        d = _dt.datetime(date.year, date.month, date.day)
    month = _ENGLISH_MONTHS.get(d.month, "")
    return f"{month} {d.day}, {d.year}".strip()

def format_date(date: _dt.datetime | _dt.date, language: str = "PL") -> str:
    """Format date based on language selection.
    
    Args:
        date: Date or datetime object to format
        language: Language code - "PL" for Polish, "EN" for English
        
    Returns:
        Formatted date string:
        - PL: "13 listopada 2025"
        - EN: "November 13, 2025"
    """
    if language == "EN":
        return format_english_date(date)
    else:
        return format_polish_date(date)

__all__ = ["format_polish_date", "format_english_date", "format_date"]
