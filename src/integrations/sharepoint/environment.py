"""Aktywne środowisko SharePoint (tylko w pamięci procesu).

Aplikacja zawsze startuje w DEV - wybór środowiska nie jest nigdzie zapisywany,
więc PROD wymaga świadomego przełączenia po każdym uruchomieniu.
"""
import logging
import threading

from .config import DEFAULT_ENV, SharePointEnvironment, get_environment

_log = logging.getLogger("sharepoint.environment")


class EnvironmentManager:
    def __init__(self):
        self._lock = threading.RLock()
        self._active = get_environment(DEFAULT_ENV)
        self._listeners = []

    def get_active(self) -> SharePointEnvironment:
        with self._lock:
            return self._active

    def set_active(self, name: str) -> SharePointEnvironment:
        env = get_environment(name)
        with self._lock:
            changed = env.name != self._active.name
            self._active = env
            listeners = list(self._listeners)
        if changed:
            _log.info("Aktywne środowisko SharePoint: %s", env.name)
            for callback in listeners:
                try:
                    callback(env)
                except Exception:
                    _log.exception("Błąd w nasłuchiwaniu zmiany środowiska")
        return env

    def reset(self) -> SharePointEnvironment:
        return self.set_active(DEFAULT_ENV)

    def subscribe(self, callback):
        with self._lock:
            if callback not in self._listeners:
                self._listeners.append(callback)

    def unsubscribe(self, callback):
        with self._lock:
            if callback in self._listeners:
                self._listeners.remove(callback)


environment_manager = EnvironmentManager()


def get_active_environment() -> SharePointEnvironment:
    return environment_manager.get_active()
