"""Backendy danych aplikacji."""
from .base import BackendContext, DataBackend
from .sharepoint_backend import SharePointBackend
from .sqlite_backend import SqliteBackend

__all__ = ["BackendContext", "DataBackend", "SharePointBackend", "SqliteBackend"]
