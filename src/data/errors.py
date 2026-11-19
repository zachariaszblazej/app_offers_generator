"""Wyjątki warstwy danych."""


class DataAccessError(Exception):
    """Ogólny błąd dostępu do danych (zgłaszany tam, gdzie nie wolno ukryć niepowodzenia)."""


class NumberingError(DataAccessError):
    """Nie można wyznaczyć kolejnego numeru oferty lub WZ (np. błąd lub niedostępność bazy).

    Operacja tworzenia dokumentu musi zostać przerwana - nie wolno użyć „domyślnego” numeru.
    """


class ReadOnlyBackendError(DataAccessError):
    """Operacja zapisu, aktualizacji, usuwania lub numerowania nie jest jeszcze obsługiwana przez backend.

    Backend nie przekierowuje takich operacji po cichu do innej bazy.
    """


class SharePointError(DataAccessError):
    """Błąd operacji w SharePoint (Graph API, uwierzytelnianie, nieoczekiwana odpowiedź)."""


class ConcurrencyConflictError(SharePointError):
    """Element zmienił się w SharePoint od czasu odczytu (HTTP 412) - zapis nie został wykonany i nie jest ponawiany."""


class ItemNotFoundError(SharePointError):
    """Element o podanym ID nie istnieje w SharePoint (HTTP 404)."""


class UniqueConstraintError(SharePointError):
    """SharePoint odrzucił zapis z powodu naruszenia unikalności (HTTP 400, bez wskazania pola)."""


class ConflictMessage(str):
    """Komunikat (False, komunikat) zwracany przy konflikcie współbieżności.

    Zachowuje się jak zwykły tekst, a `isinstance(msg, ConflictMessage)` pozwala interfejsowi odróżnić
    „dane zmieniły się od czasu odczytu” od innych błędów bez zmiany publicznego API (krotki (bool, str)).
    """
    conflict = True


class PartialFailureMessage(str):
    """Komunikat (False, komunikat) zwracany, gdy operacja obejmująca kilka zapisów została wykonana tylko częściowo.

    Stan w SharePoint może być niespójny (np. dwóch domyślnych dostawców), więc operacja NIE jest zgłaszana jako
    sukces. Zachowuje się jak zwykły tekst; `isinstance(msg, PartialFailureMessage)` lub `msg.partial` pozwala
    interfejsowi odróżnić częściowe niepowodzenie od zwykłego błędu i konfliktu współbieżności.
    """
    partial = True
