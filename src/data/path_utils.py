"""Czyste funkcje do ścieżek dokumentów (niezależne od backendu danych).

Folder bazowy jest przekazywany jawnie jako argument; odczyt ustawień pozostaje w fasadzie.
"""
import os
import re


def normalize_offer_path(path: str, base: str) -> str:
    """Zamienia ścieżkę bezwzględną/mieszaną na względną 'YYYY/plik.docx' (zapisywaną w bazie).
    Gdy podano samą nazwę pliku, zwraca nazwę (tolerancja dla starych danych).
    """
    if not path:
        return ''
    p = path.replace('\\', '/')
    base = (base or '').replace('\\', '/')
    if base and p.startswith(base.rstrip('/') + '/'):
        p = p[len(base.rstrip('/') + '/'):]
    p = p.lstrip('/')
    return p


def build_full_offer_path(rel_path: str, base: str) -> str:
    base = base or ''
    return os.path.join(base, rel_path) if rel_path else base


def normalize_wz_path(path: str, base: str) -> str:
    """Zamienia ścieżkę WZ na format względny 'YYYY/plik.ext' (lustro normalizacji ofert)."""
    if not path:
        return ''
    p = path.replace('\\', '/')
    base = (base or '').replace('\\', '/')
    if base and p.startswith(base.rstrip('/') + '/'):
        p = p[len(base.rstrip('/') + '/'):]
    m = re.search(r'(?:^|/)((?:19|20)\d{2})/([^/]+\.[A-Za-z0-9]+)$', p)
    if m:
        year, fname = m.group(1), m.group(2)
        return f"{year}/{fname}"
    if '/' in p:
        parts = p.strip('/').split('/')
        if len(parts) >= 2 and len(parts[-2]) == 4 and parts[-2].isdigit():
            return f"{parts[-2]}/{parts[-1]}"
        return p.strip('/')
    return os.path.basename(p)


def build_full_wz_path(rel_path: str, base: str) -> str:
    """Składa pełną ścieżkę z względnego WzFilePath i folderu WZ (tolerancja dla błędnych ścieżek bezwzględnych)."""
    base = base or ''
    if not rel_path:
        return base
    if os.path.isabs(rel_path):
        return rel_path
    p_norm = rel_path.replace('\\', '/')
    base_norm = base.replace('\\', '/').strip('/')
    if p_norm.startswith(base_norm + '/'):
        return '/' + p_norm
    return os.path.join(base, rel_path)
