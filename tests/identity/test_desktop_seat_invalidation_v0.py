"""Host-owned seat lifecycle: real loopback, private socket, concurrent revoke.

All account, token and seat values here are disposable synthetic fixtures.
No system bus, logind subscription, actual seat lock, browser, production
identity session or desktop changes occur during these tests.
"""
from __future__ import annotations

import http.client
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from urllib.parse import parse_qs, urlencode, urlsplit

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "identity"))
from desktop_context_projection_v0 import HostContextReply
from desktop_host_lifecycle_v0 import DesktopHostLifecycle, HostLifecycleConfig
from desktop_session_host_v0 import VerifiedCodeExchange
from private_context_ipc_v0 import read_private_display

NOW = 1_800_000_000
ISSUER = "https://ci-idp.invalid/realms/session"
TOKEN = "synthetic-private-bearer"
REPLY = {
    "schema": "post-apollo.identity.context-summary.v0",
    "status": "OK",
    "organizations": [{
        "organizationId": "example_llc",
        "kind": "llc",
        "scopeGrants": [{
            "action": "records.read", "divisionId": "test",
            "unitId": "east", "expiresAt": NOW + 90,
        }],
    }],
    "portfolios": [],
}


class DesktopSeatInvalidationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="identity-seat-invalidation-")
        self.addCleanup(self.tmp.cleanup)
        self.directory = Path(self.tmp.name)
        self.directory.chmod(0o700)
        self.active = True
        self.probe_error = False
        self.login_drops_seat = False
        self.exchange_drops_seat = False
        self.api_drops_seat = False
        self.block_api = False
        self.entered = threading.Event()
        self.release = threading.Event()
        self.urls = []
        self.api_calls = 0
        self.host = self._new_host()
        self.addCleanup(lambda: self.host.close())

    def _probe(self):
        if self.probe_error:
            raise OSError("No host-owned seat state available")
        return self.active

    def _browser(self, url):
        self.urls.append(url)
        if self.login_drops_seat:
            self.active = False

    def _exchange(self, code, verifier, nonce, redirect):
        if self.exchange_drops_seat:
            self.active = False
        if code != "test-code":
            raise ValueError("Unknown disposable code")
        return VerifiedCodeExchange(
            access_token=TOKEN, issuer=ISSUER, client_id="ci-app",
            nonce=nonce, subject="synthetic-person",
            expires_at=NOW + 150, token_type="Bearer",
            signed_id_token_verified=True,
        )

    def _api(self, bearer):
        self.api_calls += 1
        if self.block_api:
            self.entered.set()
            if not self.release.wait(timeout=4):
                raise TimeoutError("Test API gate failed")
        if self.api_drops_seat:
            self.active = False
        if bearer != TOKEN:
            return HostContextReply(401, "application/json", b'{"status":"DENIED"}')
        return HostContextReply(
            200, "application/json", json.dumps(REPLY).encode("ascii"),
        )

    def _new_host(self):
        return DesktopHostLifecycle(
            config=HostLifecycleConfig(
                issuer=ISSUER,
                authorization_endpoint=ISSUER + "/protocol/openid-connect/auth",
                client_id="ci-app", api_audience="ci-api",
                runtime_directory=self.directory,
            ),
            browser_open=self._browser, exchange_and_verify=self._exchange,
            api_get=self._api, clock=lambda: NOW,
            session_is_active=self._probe,
        )

    def _snapshot(self, path=None):
        return read_private_display(
            path if path is not None else self.host.display_socket_path,
            clock=lambda: NOW,
        )

    def _sign_in(self):
        self.host.start()
        self.assertEqual(self.host.begin_login(), {"status": "LOGIN_PENDING"})
        parameters = parse_qs(urlsplit(self.urls[-1]).query)
        loopback = urlsplit(self.host.redirect_uri)
        conn = http.client.HTTPConnection(
            "127.0.0.1", loopback.port, timeout=5,
        )
        conn.request(
            "GET", "/callback?" + urlencode({
                "code": "test-code", "state": parameters["state"][0],
                "iss": ISSUER,
            }),
            headers={"Host": "127.0.0.1:" + str(loopback.port)},
        )
        response = conn.getresponse()
        status, payload = response.status, response.read()
        conn.close()
        return status, payload

    def test_inactive_seat_prevents_start_without_binding_socket_or_browser(self):
        self.active = False
        with self.assertRaises(RuntimeError):
            self.host.start()
        self.assertFalse(self.host.started)
        self.assertEqual(self.urls, [])
        self.assertFalse(any(self.directory.iterdir()))
        self.assertEqual(self.host.begin_login(), {"status": "UNAVAILABLE"})

    def test_lock_after_start_prevents_browser_opening(self):
        self.host.start()
        self.active = False
        self.assertEqual(self.host.begin_login(), {"status": "UNAVAILABLE"})
        self.assertEqual(self.urls, [])
        self.assertEqual(self._snapshot()["status"], "SIGNED_OUT")
        self.assertEqual(self._snapshot()["organizations"], [])

    def test_probe_failure_is_fail_closed_even_after_valid_login(self):
        self.assertEqual(self._sign_in()[0], 200)
        self.assertEqual(self._snapshot()["status"], "READY")
        self.probe_error = True
        refused = self._snapshot()
        self.assertEqual(refused["status"], "SIGNED_OUT")
        self.assertEqual(refused["organizations"], [])
        self.probe_error = False
        self.assertEqual(self._snapshot()["organizations"], [])
        self.assertEqual(self.host.begin_login(), {"status": "UNAVAILABLE"})

    def test_seat_drops_during_browser_open(self):
        self.host.start()
        self.login_drops_seat = True
        self.assertEqual(self.host.begin_login(), {"status": "UNAVAILABLE"})
        self.assertEqual(self._snapshot()["organizations"], [])
        self.assertEqual(self.host.begin_login(), {"status": "UNAVAILABLE"})

    def test_seat_drops_during_code_exchange_and_callback_fails(self):
        self.exchange_drops_seat = True
        code, body = self._sign_in()
        self.assertEqual(code, 400)
        self.assertNotIn(TOKEN.encode(), body)
        self.assertEqual(self._snapshot()["status"], "SIGNED_OUT")
        self.assertEqual(self._snapshot()["organizations"], [])

    def test_seat_drops_during_api_read_and_cannot_publish_company(self):
        self.assertEqual(self._sign_in()[0], 200)
        self.api_drops_seat = True
        display = self._snapshot()
        self.assertEqual(display["status"], "SIGNED_OUT")
        self.assertEqual(display["organizations"], [])
        self.assertEqual(self._snapshot()["organizations"], [])
        self.assertEqual(self.api_calls, 1)

    def test_lock_suspend_user_switch_and_session_end_teardown(self):
        for kind in ("lock", "suspend", "user-switch", "session-end"):
            with self.subTest(kind=kind):
                self.host.close()
                self.active = True
                self.host = self._new_host()
                self.assertEqual(self._sign_in()[0], 200)
                old_path = self.host.display_socket_path
                self.assertEqual(self._snapshot()["status"], "READY")
                self.host.session_event(kind)
                self.assertFalse(self.host.started)
                self.assertFalse(old_path.exists())
                self.assertEqual(self.host.begin_login(), {"status": "UNAVAILABLE"})
                self.assertEqual(self._snapshot(old_path)["organizations"], [])
                self.assertEqual(self._snapshot(old_path)["status"], "UNAVAILABLE")
                self.host.close()

    def test_unknown_events_do_not_bypass_host_only_contract(self):
        self.assertEqual(self._sign_in()[0], 200)
        for kind in ("unlock", "grant", "role", "LOGIN", "", None):
            with self.subTest(kind=kind):
                with self.assertRaises(ValueError):
                    self.host.session_event(kind)
        self.assertEqual(self._snapshot()["status"], "READY")

    def test_concurrent_session_end_invalidates_inflight_api_read(self):
        self.assertEqual(self._sign_in()[0], 200)
        self.block_api = True
        result = {}
        path = self.host.display_socket_path
        read_thread = threading.Thread(
            target=lambda: result.update(view=self._snapshot(path)),
            name="ci-blocked-identity-display-read",
        )
        read_thread.start()
        try:
            self.assertTrue(self.entered.wait(3))
            done = threading.Event()
            def invalidate():
                try:
                    self.host.session_event("lock")
                finally:
                    done.set()
            stop_thread = threading.Thread(target=invalidate, name="ci-seat-lock")
            stop_thread.start()
            try:
                # The event is set synchronously before the owner lock is
                # acquired. The read may still be awaiting its HTTPS fixture.
                self.assertTrue(self.host._revoked.wait(3))
            finally:
                self.release.set()
            self.assertTrue(done.wait(6))
            stop_thread.join(timeout=2)
            read_thread.join(timeout=6)
            self.assertFalse(read_thread.is_alive())
            self.assertNotEqual(result.get("view", {}).get("status"), "READY")
            self.assertEqual(result.get("view", {}).get("organizations"), [])
            self.assertFalse(path.exists())
        finally:
            self.release.set()
            read_thread.join(timeout=6)

    def test_logout_invalidates_inflight_display_before_lock_acquired(self):
        self.assertEqual(self._sign_in()[0], 200)
        self.block_api = True
        path = self.host.display_socket_path
        data = {}
        worker = threading.Thread(
            target=lambda: data.update(view=self._snapshot(path)),
            name="ci-pending-display",
        )
        worker.start()
        try:
            self.assertTrue(self.entered.wait(3))
            done = threading.Event()
            def logout():
                try:
                    self.host.logout()
                finally:
                    done.set()
            t = threading.Thread(target=logout, name="ci-host-logout")
            t.start()
            try:
                self.assertTrue(self.host._revoked.wait(3))
            finally:
                self.release.set()
            self.assertTrue(done.wait(6))
            t.join(timeout=2)
            worker.join(timeout=6)
            self.assertEqual(data["view"]["organizations"], [])
            self.assertEqual(self._snapshot()["status"], "SIGNED_OUT")
        finally:
            self.release.set()
            worker.join(timeout=6)


if __name__ == "__main__":
    unittest.main()
