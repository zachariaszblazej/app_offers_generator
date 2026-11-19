"""Wyjątki warstwy danych."""


class DataAccessError(Exception):
    """Ogólny błąd dostępu do danych (zgłaszany tam, gdzie nie wolno ukryć niepowodzenia)."""


class NumberingError(DataAccessError):
    """Nie można wyznaczyć kolejnego numeru oferty lub WZ (np. błąd lub niedostępność bazy).

    Operacja tworzenia dokumentu musi zostać przerwana - nie wolno użyć „domyślnego” numeru.
    """
