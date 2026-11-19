"""Lokalna mapa kluczy SQLite -> ID elementów SharePoint (poza repozytorium).

Plik leży w katalogu danych aplikacji (%APPDATA%\\HantechDokumenty\\migration). Źródłem prawdy
dla idempotencji jest zawsze aktualna zawartość list w SharePoint; mapa służy do raportowania
i wznawiania, a nigdy nie jest używana dla środowiska innego niż to, dla którego powstała.
"""
import json
import os
from datetime import datetime, timezone

from .datadir import assert_outside_repo


class IdMapError(Exception):
    pass


class IdMap:
    def __init__(self, path, environment, site_id):
        self.path = path
        self.environment = environment
        self.site_id = site_id
        self.lists = {}

    @classmethod
    def load(cls, path, environment, site_id):
        m = cls(path, environment, site_id)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if data.get("environment") != environment or data.get("site_id") != site_id:
                raise IdMapError(
                    f"Plik mapy {path} dotyczy innego środowiska/witryny "
                    f"({data.get('environment')}) - nie wolno go użyć dla {environment}.")
            m.lists = data.get("lists", {})
        return m

    def get(self, list_name, key):
        return self.lists.get(list_name, {}).get(key)

    def set(self, list_name, key, item_id, title):
        self.lists.setdefault(list_name, {})[key] = {
            "item_id": str(item_id),
            "title": title,
            "migrated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }

    def count(self, list_name=None):
        if list_name:
            return len(self.lists.get(list_name, {}))
        return sum(len(v) for v in self.lists.values())

    def save(self):
        directory = assert_outside_repo(os.path.dirname(self.path))
        os.makedirs(directory, exist_ok=True)
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"version": 1, "environment": self.environment, "site_id": self.site_id,
                       "lists": self.lists}, f, ensure_ascii=False, indent=1)
        os.replace(tmp, self.path)
