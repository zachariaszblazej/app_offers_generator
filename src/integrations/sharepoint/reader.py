"""Klient Graph tylko do odczytu z ograniczonymi ponowieniami (429/503/504 i błędy połączenia).

Nie wykonuje żądań zapisu: dziedziczy wyłącznie GET z `GraphClient`. Liczba prób jest ograniczona,
a czas oczekiwania wynika z nagłówka Retry-After (z górnym limitem) albo z krótkiego backoffu.
"""
import time

from .graph_client import GraphClient, GraphError

RETRY_STATUSES = (429, 503, 504)
MAX_ATTEMPTS = 4
MAX_RETRY_AFTER_SECONDS = 30
MAX_BACKOFF_SECONDS = 8


def retry_delay(attempt: int, retry_after=None) -> float:
    """attempt = numer właśnie nieudanej próby (1, 2, ...)."""
    if retry_after is not None:
        try:
            return min(max(float(retry_after), 0.0), MAX_RETRY_AFTER_SECONDS)
        except (TypeError, ValueError):
            pass
    return min(2 ** (attempt - 1), MAX_BACKOFF_SECONDS)


class RetryingGraphClient(GraphClient):
    def __init__(self, environment, access_token, max_attempts=MAX_ATTEMPTS, sleep=time.sleep):
        super().__init__(environment, access_token)
        self._max_attempts = max_attempts
        self._sleep = sleep
        self.requests_made = 0
        self.retries = 0

    def get(self, path_or_url, params=None):
        for attempt in range(1, self._max_attempts + 1):
            self.requests_made += 1
            try:
                return super().get(path_or_url, params=params)
            except GraphError as e:
                retryable = e.status in RETRY_STATUSES or e.status is None
                if not retryable or attempt == self._max_attempts:
                    raise
                self.retries += 1
                self._sleep(retry_delay(attempt, e.retry_after))
