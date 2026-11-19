"""Testy trwałego cache MSAL szyfrowanego przez Windows DPAPI - offline, na syntetycznych tokenach.

Uruchomienie: python -m unittest tests.sharepoint_token_cache_test -v
Testy używają tymczasowych katalogów (poza repozytorium), nie wykonują żądań sieciowych (gniazda zablokowane),
nie dotykają prawdziwego cache użytkownika ani SharePoint.
"""
import base64
import json
import logging
import os
import socket
import sys
import tempfile
import unittest
from contextlib import contextmanager
from unittest import mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import msal  # noqa: E402

from src.integrations.sharepoint import graph_client, token_cache  # noqa: E402
from src.integrations.sharepoint.config import SCOPES, get_client_id, get_tenant_id  # noqa: E402
from src.integrations.sharepoint.migration.datadir import DataDirError, assert_outside_repo, project_root  # noqa: E402
from src.integrations.sharepoint.session import NotSignedInError, SharePointSession  # noqa: E402
from src.integrations.sharepoint.token_cache import (  # noqa: E402
    FILE_MAGIC, DpapiProtector, PersistentTokenCache, ProtectionError, default_cache_path)

ACCESS = "AT-SYNTH-ACCESS-TOKEN-9f3a1c"
REFRESH = "RT-SYNTH-REFRESH-TOKEN-77b2e4"
USER = "zztest.user@example.invalid"
WINDOWS = sys.platform == "win32"


def _b64(data):
    return base64.urlsafe_b64encode(json.dumps(data).encode()).rstrip(b"=").decode()


def add_synthetic_login(cache, client_id=None, tenant=None):
    """Dodaje do cache MSAL syntetyczne konto i tokeny (tak jak po udanym logowaniu)."""
    client_id, tenant = client_id or get_client_id(), tenant or get_tenant_id()
    id_token = ".".join([_b64({"alg": "none"}), _b64({
        "aud": client_id, "iss": f"https://login.microsoftonline.com/{tenant}/v2.0", "tid": tenant,
        "oid": "zz-user", "preferred_username": USER, "name": "ZZ Test"}), "sig"])
    cache.add({
        "client_id": client_id, "scope": list(SCOPES),
        "token_endpoint": f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token",
        "response": {"access_token": ACCESS, "refresh_token": REFRESH, "id_token": id_token, "expires_in": 3600,
                     "token_type": "Bearer", "scope": " ".join(SCOPES),
                     "client_info": _b64({"uid": "zz-user", "utid": tenant})}})


def _discovery_patches():
    tenant = get_tenant_id()
    base = f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0"
    discovery = {"authorization_endpoint": base + "/authorize", "token_endpoint": base + "/token",
                 "issuer": f"https://login.microsoftonline.com/{tenant}/v2.0"}
    return (mock.patch("msal.authority._instance_discovery",
                       return_value={"tenant_discovery_endpoint": f"https://login.microsoftonline.com/{tenant}/v2.0/.well-known/openid-configuration",
                                     "metadata": []}),
            mock.patch("msal.authority.tenant_discovery", return_value=discovery))


@contextmanager
def msal_offline():
    """Wykrywanie endpointów MSAL (instancji i tenanta) jest podmienione, a sieć zablokowana - żadnych żądań HTTP."""
    entra, tenant = _discovery_patches()
    with entra, tenant, network_blocked():
        yield


def make_app(cache):
    """Prawdziwa aplikacja MSAL z podanym cache, bez żadnych żądań sieciowych."""
    with msal_offline():
        app = msal.PublicClientApplication(
            get_client_id(), authority=f"https://login.microsoftonline.com/{get_tenant_id()}", token_cache=cache)
    return offline(app)


def offline(app):
    """MSAL pobiera metadane instancji (aliasy hosta) przy get_accounts(); hak przewidziany przez MSAL do mockowania."""
    app._get_instance_metadata = lambda instance: [{"aliases": [instance]}]
    return app


def silent_token(app):
    accounts = app.get_accounts()
    if not accounts:
        return None
    result = app.acquire_token_silent(list(SCOPES), account=accounts[0])
    return result.get("access_token") if result else None


@contextmanager
def network_blocked():
    def blocked(*args, **kwargs):
        raise RuntimeError("SIEĆ ZABLOKOWANA W TESTACH")
    with mock.patch.object(socket.socket, "connect", blocked), mock.patch.object(socket, "create_connection", blocked):
        yield


class ReversingProtector:
    """Prosty, deterministyczny 'szyfr' do testów logiki cache niezależnych od DPAPI."""

    def protect(self, data):
        return bytes(b ^ 0x5A for b in data)[::-1]

    def unprotect(self, data):
        return bytes(b ^ 0x5A for b in data[::-1])


class CacheTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = os.path.join(self.tmp.name, "auth", "msal_token_cache.bin")
        self.logger_records = []
        handler = logging.Handler()
        handler.emit = lambda record: self.logger_records.append(record.getMessage())
        root = logging.getLogger()
        self._old_level = root.level
        root.setLevel(logging.DEBUG)
        root.addHandler(handler)
        self.addCleanup(lambda: (root.removeHandler(handler), root.setLevel(self._old_level)))

    def new_cache(self, protector=None):
        return PersistentTokenCache(self.path, protector or ReversingProtector())

    def saved_cache_with_login(self, protector=None):
        pc = self.new_cache(protector)
        add_synthetic_login(pc.cache)
        self.assertTrue(pc.save())
        return pc

    def disk_bytes(self):
        with open(self.path, "rb") as f:
            return f.read()

    def assert_logs_clean(self):
        joined = "\n".join(self.logger_records)
        for secret in (ACCESS, REFRESH, USER):
            self.assertNotIn(secret, joined)


@unittest.skipUnless(WINDOWS, "DPAPI działa tylko w systemie Windows")
class DpapiProtectorTests(unittest.TestCase):
    def test_round_trip_returns_original_and_ciphertext_differs(self):
        p = DpapiProtector()
        plain = ("tajne-" + ACCESS).encode()
        blob = p.protect(plain)
        self.assertNotEqual(blob, plain)
        self.assertNotIn(ACCESS.encode(), blob)
        self.assertEqual(p.unprotect(blob), plain)

    def test_empty_and_large_payloads_round_trip(self):
        p = DpapiProtector()
        for plain in (b"", b"x", os.urandom(300_000)):
            self.assertEqual(p.unprotect(p.protect(plain)), plain)

    def test_same_plaintext_gives_different_ciphertext_each_time(self):
        p = DpapiProtector()
        self.assertNotEqual(p.protect(b"abc"), p.protect(b"abc"))

    def test_tampered_or_foreign_data_is_rejected(self):
        p = DpapiProtector()
        blob = bytearray(p.protect(b"dane"))
        blob[-3] ^= 0xFF
        with self.assertRaises(ProtectionError):
            p.unprotect(bytes(blob))
        with self.assertRaises(ProtectionError):
            p.unprotect(b"to nie jest blob DPAPI")

    def test_blob_protected_with_other_entropy_cannot_be_read(self):
        other = DpapiProtector(entropy=b"inna-aplikacja")
        with self.assertRaises(ProtectionError):
            DpapiProtector().unprotect(other.protect(b"dane"))


class SerializationTests(CacheTestCase):
    def test_save_then_load_restores_accounts_and_tokens(self):
        first = self.saved_cache_with_login()
        second = self.new_cache()
        self.assertFalse(second.recovered_from_error)
        self.assertEqual(json.loads(second.cache.serialize()), json.loads(first.cache.serialize()))
        self.assertEqual(len(make_app(second.cache).get_accounts()), 1)

    def test_nothing_is_written_when_cache_did_not_change(self):
        pc = self.new_cache()
        self.assertFalse(pc.save())
        self.assertFalse(os.path.exists(self.path))
        add_synthetic_login(pc.cache)
        self.assertTrue(pc.save())
        mtime = os.stat(self.path).st_mtime_ns
        self.assertFalse(pc.save())
        self.assertEqual(os.stat(self.path).st_mtime_ns, mtime)

    def test_directory_is_created_and_no_temporary_file_remains(self):
        self.saved_cache_with_login()
        self.assertEqual(os.listdir(os.path.dirname(self.path)), [os.path.basename(self.path)])

    def test_file_has_format_marker_and_is_replaced_atomically_on_update(self):
        pc = self.saved_cache_with_login()
        self.assertTrue(self.disk_bytes().startswith(FILE_MAGIC))
        before = self.disk_bytes()
        pc.cache.add({"client_id": "other-client", "scope": ["User.Read"],
                      "token_endpoint": "https://login.microsoftonline.com/t/oauth2/v2.0/token",
                      "response": {"access_token": "AT2", "expires_in": 60, "token_type": "Bearer"}})
        self.assertTrue(pc.save())
        self.assertNotEqual(self.disk_bytes(), before)
        self.assertEqual(json.loads(self.new_cache().cache.serialize()), json.loads(pc.cache.serialize()))

    def test_clear_removes_file_and_memory(self):
        pc = self.saved_cache_with_login()
        pc.clear()
        self.assertFalse(os.path.exists(self.path))
        self.assertEqual(make_app(pc.cache).get_accounts(), [])
        self.assertFalse(self.new_cache().cache.has_state_changed)


class RestartTests(CacheTestCase):
    def test_new_process_recovers_session_silently_without_network(self):
        first = self.new_cache()
        add_synthetic_login(first.cache)
        self.assertTrue(first.save())
        del first  # "zamknięcie aplikacji"

        with network_blocked():
            restarted = self.new_cache()
            self.assertEqual(silent_token(make_app(restarted.cache)), ACCESS)
        self.assert_logs_clean()


class CorruptedCacheTests(CacheTestCase):
    def write_raw(self, data):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, "wb") as f:
            f.write(data)

    def assert_recovers(self):
        pc = self.new_cache()
        self.assertTrue(pc.recovered_from_error)
        self.assertEqual(make_app(pc.cache).get_accounts(), [])
        self.assertFalse(os.path.exists(self.path))  # bezużyteczny plik został odrzucony
        add_synthetic_login(pc.cache)  # ponowne logowanie i zapis działają
        self.assertTrue(pc.save())
        again = self.new_cache()
        self.assertFalse(again.recovered_from_error)
        self.assertEqual(len(make_app(again.cache).get_accounts()), 1)
        self.assert_logs_clean()

    def test_garbage_bytes(self):
        self.write_raw(os.urandom(512))
        self.assert_recovers()

    def test_empty_file(self):
        self.write_raw(b"")
        self.assert_recovers()

    def test_valid_marker_but_garbage_payload(self):
        self.write_raw(FILE_MAGIC + os.urandom(128))
        self.assert_recovers()

    def test_truncated_file(self):
        self.saved_cache_with_login()
        self.write_raw(self.disk_bytes()[:-9])
        self.assert_recovers()

    def test_plaintext_json_file_is_never_trusted(self):
        self.write_raw(json.dumps({"AccessToken": {"x": {"secret": ACCESS}}}).encode())
        self.assert_recovers()

    def test_valid_encryption_but_payload_is_not_a_cache(self):
        self.write_raw(FILE_MAGIC + ReversingProtector().protect(b"to nie jest JSON"))
        self.assert_recovers()

    def test_payload_json_of_wrong_type(self):
        for payload in (b"[1, 2, 3]", b'{"AccessToken": 5}', b'{"AccessToken": {"k": 5}}', b'{"Account": [1]}', b'"x"', b"null"):
            with self.subTest(payload=payload):
                self.write_raw(FILE_MAGIC + ReversingProtector().protect(payload))
                pc = self.new_cache()
                self.assertTrue(pc.recovered_from_error)
                self.assertEqual(make_app(pc.cache).get_accounts(), [])
                self.assertFalse(os.path.exists(self.path))

    @unittest.skipUnless(WINDOWS, "DPAPI działa tylko w systemie Windows")
    def test_data_protected_for_another_context_with_real_dpapi(self):
        other = DpapiProtector(entropy=b"inny-uzytkownik-lub-komputer")
        self.write_raw(FILE_MAGIC + other.protect(b"{}"))
        pc = PersistentTokenCache(self.path, DpapiProtector())
        self.assertTrue(pc.recovered_from_error)
        self.assertFalse(os.path.exists(self.path))

    def test_unreadable_file_is_not_deleted_and_does_not_crash(self):
        self.saved_cache_with_login()
        real_open = open

        def deny(path, mode="r", *a, **k):
            if os.fspath(path) == self.path and "r" in mode:
                raise PermissionError("odmowa dostępu")
            return real_open(path, mode, *a, **k)

        with mock.patch("builtins.open", deny):
            pc = self.new_cache()
        self.assertTrue(pc.recovered_from_error)
        self.assertEqual(make_app(pc.cache).get_accounts(), [])
        self.assertTrue(os.path.exists(self.path))

    def test_save_failure_does_not_raise_and_keeps_memory_cache(self):
        pc = self.new_cache()
        add_synthetic_login(pc.cache)
        with mock.patch.object(os, "replace", side_effect=PermissionError("zablokowany")):
            self.assertFalse(pc.save())
        self.assertEqual(len(make_app(pc.cache).get_accounts()), 1)
        self.assertTrue(pc.cache.has_state_changed)
        self.assertTrue(pc.save())  # kolejna próba po ustąpieniu błędu

    def test_protector_failure_on_save_does_not_raise(self):
        class Failing(ReversingProtector):
            def protect(self, data):
                raise ProtectionError("błąd DPAPI")
        pc = self.new_cache(Failing())
        add_synthetic_login(pc.cache)
        self.assertFalse(pc.save())
        self.assertFalse(os.path.exists(self.path))
        self.assert_logs_clean()

    def test_log_messages_name_only_exception_types(self):
        self.write_raw(FILE_MAGIC + ReversingProtector().protect(f'{{"secret": "{ACCESS}"'.encode()))
        self.new_cache()
        self.assertTrue(any("nieczytelny" in m for m in self.logger_records))
        self.assert_logs_clean()


class NoPlaintextOnDiskTests(CacheTestCase):
    def assert_no_plaintext(self, data):
        for secret in (ACCESS, REFRESH, USER, get_client_id(), "refresh_token", "access_token", "AccessToken",
                       "RefreshToken", "home_account_id", "secret"):
            for encoding in ("utf-8", "utf-16-le"):
                self.assertNotIn(secret.encode(encoding), data, f"jawna zawartość: {secret!r} ({encoding})")

    def test_test_cipher_hides_tokens(self):
        self.saved_cache_with_login()
        self.assert_no_plaintext(self.disk_bytes())

    @unittest.skipUnless(WINDOWS, "DPAPI działa tylko w systemie Windows")
    def test_real_dpapi_file_contains_no_token_or_account_data(self):
        pc = PersistentTokenCache(self.path)  # domyślny protektor = DPAPI
        add_synthetic_login(pc.cache)
        self.assertTrue(pc.save())
        data = self.disk_bytes()
        self.assertTrue(data.startswith(FILE_MAGIC))
        self.assert_no_plaintext(data)
        for name in os.listdir(os.path.dirname(self.path)):
            with open(os.path.join(os.path.dirname(self.path), name), "rb") as f:
                self.assert_no_plaintext(f.read())
        restarted = PersistentTokenCache(self.path)
        with network_blocked():
            self.assertEqual(silent_token(make_app(restarted.cache)), ACCESS)


class LocationTests(unittest.TestCase):
    def test_default_path_is_under_local_app_data_and_outside_the_repository(self):
        path = default_cache_path()
        self.assertTrue(path.endswith(os.path.join("HantechDokumenty", "auth", "msal_token_cache.bin")))
        self.assertEqual(assert_outside_repo(path), os.path.realpath(path))  # nie zgłasza DataDirError

    def test_path_inside_repository_is_refused_including_via_parent_segments(self):
        inside = os.path.join(project_root(), "tmp_cache", "msal.bin")
        with self.assertRaises(DataDirError):
            PersistentTokenCache(inside, ReversingProtector())
        sneaky = os.path.join(project_root(), "..", os.path.basename(project_root()), "src", "msal.bin")
        with self.assertRaises(DataDirError):
            PersistentTokenCache(sneaky, ReversingProtector())

    def test_default_cache_falls_back_to_memory_only_when_unavailable(self):
        with mock.patch.object(token_cache, "default_cache_path", return_value=os.path.join(project_root(), "x.bin")):
            self.assertIsNone(token_cache.create_default_cache())
        with mock.patch.object(token_cache.sys, "platform", "linux"):
            self.assertIsNone(token_cache.create_default_cache())

    def test_no_cache_file_is_present_in_the_repository_tree(self):
        for folder, _, files in os.walk(project_root()):
            if ".venv" in folder or ".git" in folder:
                continue
            self.assertNotIn(token_cache.CACHE_FILE_NAME, files, folder)


class GraphClientIntegrationTests(CacheTestCase):
    """acquire_token / acquire_token_silent / forget_account z trwałym cache (MSAL z podmienionym wykrywaniem endpointów)."""

    def setUp(self):
        super().setUp()
        self._patches = []

    def tearDown(self):
        for p in reversed(self._patches):
            p.stop()
        super().tearDown()

    def start(self, patcher):
        value = patcher.start()
        self._patches.append(patcher)
        return value

    def boot(self, protector=None, interactive=None):
        """Symuluje start procesu: nowy moduł graph_client bez zapamiętanej aplikacji, cache z pliku."""
        self.start(mock.patch.object(graph_client, "_msal_app", None))
        self.start(mock.patch.object(graph_client, "_persistent_cache", None))
        self.start(mock.patch.object(graph_client, "create_default_cache",
                                     lambda: PersistentTokenCache(self.path, protector or ReversingProtector())))
        with msal_offline():
            app = offline(graph_client._get_msal_app())
        if interactive is not None:
            self.start(mock.patch.object(app, "acquire_token_interactive", side_effect=interactive))
        return app

    def interactive_login(self, **kwargs):
        add_synthetic_login(graph_client._persistent_cache.cache)
        return {"access_token": ACCESS, "expires_in": 3600}

    def test_app_uses_the_persistent_cache_object(self):
        app = self.boot()
        self.assertIs(app.token_cache, graph_client._persistent_cache.cache)

    def test_msal_debug_events_are_not_logged(self):
        self.boot()
        self.addCleanup(logging.getLogger("msal").setLevel, logging.getLogger("msal").level)
        self.assertGreaterEqual(logging.getLogger("msal").getEffectiveLevel(), logging.WARNING)

    def test_login_is_persisted_and_next_start_signs_in_silently(self):
        self.boot(interactive=self.interactive_login)
        self.assertEqual(graph_client.acquire_token()["access_token"], ACCESS)
        self.assertTrue(os.path.exists(self.path))
        for p in reversed(self._patches):
            p.stop()
        self._patches.clear()

        interactive = mock.Mock(side_effect=AssertionError("nie wolno otwierać okna logowania"))
        self.boot(interactive=interactive)
        with network_blocked():
            self.assertEqual(graph_client.acquire_token_silent()["access_token"], ACCESS)
            self.assertEqual(graph_client.acquire_token()["access_token"], ACCESS)
        interactive.assert_not_called()
        self.assert_logs_clean()

    def test_silent_acquire_without_cache_returns_none_and_never_raises(self):
        self.boot()
        self.assertIsNone(graph_client.acquire_token_silent())

    def test_corrupted_cache_file_allows_new_login(self):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, "wb") as f:
            f.write(FILE_MAGIC + os.urandom(64))
        self.boot(interactive=self.interactive_login)
        self.assertTrue(graph_client._persistent_cache.recovered_from_error)
        self.assertIsNone(graph_client.acquire_token_silent())
        self.assertEqual(graph_client.acquire_token()["access_token"], ACCESS)
        self.assertTrue(os.path.exists(self.path))

    def test_forget_account_removes_accounts_and_file(self):
        app = self.boot(interactive=self.interactive_login)
        graph_client.acquire_token()
        self.assertEqual(len(app.get_accounts()), 1)
        graph_client.forget_account()
        self.assertEqual(app.get_accounts(), [])
        self.assertFalse(os.path.exists(self.path))
        self.assertIsNone(graph_client.acquire_token_silent())

    def test_without_persistent_cache_everything_still_works_in_memory(self):
        self.start(mock.patch.object(graph_client, "_msal_app", None))
        self.start(mock.patch.object(graph_client, "_persistent_cache", None))
        self.start(mock.patch.object(graph_client, "create_default_cache", lambda: None))
        with msal_offline():
            offline(graph_client._get_msal_app())
        self.assertIsNone(graph_client.acquire_token_silent())
        graph_client.forget_account()

    def test_scopes_and_registration_are_unchanged(self):
        self.assertEqual(list(SCOPES), ["User.Read", "Sites.Selected"])
        self.assertEqual(get_client_id(), "95640770-2a93-482f-8e4b-a26936fbdcdb")


class SessionResumeTests(unittest.TestCase):
    def make(self, silent=None, forget=None):
        return SharePointSession(acquire=lambda interactive_log=None: {"access_token": "T-IN", "expires_in": 3600},
                                 acquire_silent=silent or (lambda: None), forget=forget or (lambda: None))

    def test_resume_restores_session_from_cache_without_interactive_login(self):
        s = self.make(silent=lambda: {"access_token": "T-CICHY", "expires_in": 3600})
        self.assertFalse(s.is_active())
        self.assertTrue(s.resume())
        self.assertTrue(s.is_active())
        self.assertEqual(s.get_token(), "T-CICHY")

    def test_resume_without_usable_cache_returns_false_and_stays_signed_out(self):
        s = self.make()
        self.assertFalse(s.resume())
        self.assertFalse(s.is_active())
        with self.assertRaises(NotSignedInError):
            s.get_token()

    def test_sign_out_keeps_the_persistent_cache_unless_forget_is_requested(self):
        forget = mock.Mock()
        s = self.make(forget=forget)
        s.sign_in()
        s.sign_out()
        forget.assert_not_called()
        s.sign_in()
        s.sign_out(forget=True)
        forget.assert_called_once_with()
        self.assertFalse(s.is_active())

    def test_expired_session_end_does_not_forget_the_account(self):
        forget = mock.Mock()
        now = {"t": 1000.0}
        s = SharePointSession(acquire=lambda interactive_log=None: {"access_token": "T", "expires_in": 60},
                              acquire_silent=lambda: None, forget=forget, clock=lambda: now["t"])
        s.sign_in()
        now["t"] += 3600
        with self.assertRaises(NotSignedInError):
            s.get_token()
        forget.assert_not_called()


if __name__ == "__main__":
    unittest.main()
