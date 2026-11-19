"""Wyjątki warstwy danych."""


class DataAccessError(Exception):
    """Ogólny błąd dostępu do danych (zgłaszany tam, gdzie nie wolno ukryć niepowodzenia)."""


class NumberingError(DataAccessError):
    """Nie można wyznaczyć kolejnego numeru oferty lub WZ (np. błąd lub niedostępność bazy).

    Operacja tworzenia dokumentu musi zostać przerwana - nie wolno użyć „domyślnego” numeru.
    """


class ReadOnlyBackendError(DataAccessError):
    """Operacja zapisu, aktualizacji, usuwania lub numerowania nie jest obsługiwana przez backend w trybie tylko do odczytu.

    Backend nie przekierowuje takich operacji po cichu do innej bazy.
    """


class SharePointError(DataAccessError):
    """Błąd odczytu z SharePoint (Graph API, uwierzytelnianie, nieoczekiwana odpowiedź)."""
