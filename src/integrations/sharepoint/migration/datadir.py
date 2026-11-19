"""Katalog danych migracji (raporty, mapa ID) - zawsze poza repozytorium projektu.

Raporty, mapa ID i inne dane migracyjne zawierają informacje o firmie, dlatego nie wolno ich zapisywać
w katalogu projektu ani w jego podkatalogach. Ścieżki są normalizowane (ścieżki względne, `..`,
symlinki/junctiony, wielkość liter na Windows), więc nie da się tego obejść zapisem ścieżki w inny sposób.
Reguła dotyczy tylko repozytorium tego projektu: inne repozytoria git (np. założone w katalogu domowym)
nie wpływają na domyślną lokalizację w %APPDATA%.
"""
import os


class DataDirError(Exception):
    """Katalog danych migracji wskazuje na repozytorium projektu lub jego podkatalog."""


def project_root() -> str:
    # .../<root>/src/integrations/sharepoint/migration/datadir.py
    path = os.path.abspath(__file__)
    for _ in range(5):
        path = os.path.dirname(path)
    return path


def _canonical(path) -> str:
    return os.path.normcase(os.path.realpath(os.path.abspath(os.fspath(path))))


def _is_within(path, root) -> bool:
    try:
        return os.path.commonpath([path, root]) == root
    except ValueError:  # inne dyski
        return False


def assert_outside_repo(path, root=None) -> str:
    """Zwraca znormalizowaną ścieżkę albo zgłasza DataDirError, gdy leży w repozytorium projektu."""
    if _is_within(_canonical(path), _canonical(root or project_root())):
        raise DataDirError(
            f"Katalog danych migracji nie może leżeć w repozytorium projektu: {path} "
            "(wskaż katalog poza projektem lub użyj domyślnego %APPDATA%\\HantechDokumenty\\migration).")
    return os.path.realpath(os.path.abspath(os.fspath(path)))


def migration_dir() -> str:
    from src.utils.config import get_data_dir
    return os.path.join(get_data_dir(), "migration")


def resolve_data_dir(path=None) -> str:
    """Domyślnie %APPDATA%\\HantechDokumenty\\migration; wskazana ścieżka jest walidowana."""
    return assert_outside_repo(path or migration_dir())
