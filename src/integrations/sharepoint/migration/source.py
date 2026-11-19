"""Źródło danych migracji: baza SQLite otwierana wyłącznie do odczytu."""
import hashlib
import os
import sqlite3
from dataclasses import dataclass
from pathlib import Path

SOURCE_TABLES = ("Suppliers", "Clients", "Offers", "Wuzetkas")
SIDECAR_SUFFIXES = ("-journal", "-wal", "-shm")


class SourceError(Exception):
    pass


@dataclass(frozen=True)
class Fingerprint:
    sha256: str
    size: int
    mtime_ns: int
    sidecars: tuple

    def same_as(self, other: "Fingerprint") -> bool:
        return (self.sha256, self.size, self.mtime_ns, self.sidecars) == (
            other.sha256, other.size, other.mtime_ns, other.sidecars)


def file_fingerprint(path) -> Fingerprint:
    p = Path(path)
    if not p.is_file():
        raise SourceError(f"Brak pliku bazy SQLite: {p}")
    digest = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    st = p.stat()
    sidecars = tuple(s for s in SIDECAR_SUFFIXES if os.path.exists(str(p) + s))
    return Fingerprint(digest.hexdigest(), st.st_size, st.st_mtime_ns, sidecars)


def read_source_tables(path) -> dict:
    """Czyta wszystkie wiersze czterech tabel. Połączenie: mode=ro + PRAGMA query_only."""
    uri = Path(path).resolve().as_uri() + "?mode=ro"
    try:
        conn = sqlite3.connect(uri, uri=True)
    except sqlite3.Error as e:
        raise SourceError(f"Nie można otworzyć bazy w trybie tylko do odczytu: {e}")
    try:
        conn.execute("PRAGMA query_only = ON")
        conn.row_factory = sqlite3.Row
        existing = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        missing = [t for t in SOURCE_TABLES if t not in existing]
        if missing:
            raise SourceError(f"W bazie brakuje tabel: {', '.join(missing)}")
        tables = {}
        for table in SOURCE_TABLES:
            rows = conn.execute(f'SELECT rowid AS _rowid_, * FROM "{table}"').fetchall()
            tables[table] = [dict(r) for r in rows]
        return tables
    except sqlite3.Error as e:
        raise SourceError(f"Błąd odczytu bazy SQLite: {e}")
    finally:
        conn.close()
