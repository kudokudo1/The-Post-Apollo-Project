"""CI-only real loopback + host-session + private IPC lifecycle integration.

All OIDC exchange, JWT verification and API fetch dependencies below are
explicit disposable test fakes. No real IdP, token file, company membership,
local desktop host, browser or production service is created.
"""
from __future__ import annotations

import http.client
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
import unittest
from urllib.parse import parse_qs, urlencode, urlsplit

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "identity"))

from desktop_context_projection_v0 import HostContextReply
from desktop_host_lifecycle_v0 import DesktopHostLifecycle, HostLifecycleConfig
from desktop_session_host_v0 import VerifiedCodeExchange
from private_context_ipc_v0 import SOCKET_NAME, read_private_display


ISSUER = "https://issuer.example.test/realms/demo"
NOW = 1_800_000_000


class HostLifecycleIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="post-apollo-host-lifecycle-")
        self.addCleanup(self.tmp.cleanup)
        self.directory = Path(self.tmp.name)
        os.chmod(self.directory, 0o700)
        self.time = NOW
        self.secret = "CI-HOST-ONLY-TEST-BEARER"
        self.calls = []
        self.urls = []
        self.api_status = 200
        self.api_bogus = False
        self.host = self._host()
        self.addCleanup(self.host.close)

    def _clock(self) -> int:
        return self.time

    def _config(self) -> HostLifecycleConfig:
        return HostLifecycleConfig(
            issuer=ISSUER,
            authorization_endpoint=ISSUER + "/protocol/openid-connect/auth",
            client_id="ci-native",
            api_audience="ci-api",
            runtime_directory=self.directory,
        )

    def _exchange(self, code, verifier, nonce, redirect) -> VerifiedCodeExchange:
        self.calls.append((code, redirect, len(verifier)))
        if code != "ci-one-use-code" or redirect != self.host.redirect_uri:
            raise ValueError("Invalid CI verification")
        return VerifiedCodeExchange(
            access_token=self.secret, issuer=ISSUER, client_id="ci-native",
            nonce=nonce, subject="hidden-ci-test-person",
            expires_at=self.time + 180, token_type="Bearer",
            signed_id_token_verified=True,
        )

    def _get(self, bearer) -> HostContextReply:
        self.assertEqual(bearer, self.secret)
        if self.api_status != 200:
            return HostContextReply(self.api_status, "application/json",
                                    b'{"status":"DENIED"}')
        body = {
            "schema": "post-apollo.identity.context-summary.v0",
            "status": "OK",
            "organizations": [{
                "organizationId": "llc_example", "kind": "llc",
                "scopeGrants": [{
                    "action": "records.read", "divisionId": "health",
                    "unitId": "east", "expiresAt": self.time + 120,
                }],
            }],
            "portfolios": [{
                "portfolioId": "portfolio_example",
                "organizationIds": ["llc_example"],
            }],
        }
        if self.api_bogus:
            body["role"] = "admin"
        return HostContextReply(200, "application/json",
                                json.dumps(body).encode("utf-8"))

    def _host(self):
        return DesktopHostLifecycle(
            config=self._config(), browser_open=lambda url: self.urls.append(url),
            exchange_and_verify=self._exchange, api_get=self._get,
            clock=self._clock,
        )

    def _callback_request(self, *, code="ci-one-use-code", state=None,
                          issuer=ISSUER):
        parsed = urlsplit(self.urls[-1])
        if state is None:
            state = parse_qs(parsed.query)["state"][0]
        uri = urlsplit(self.host.redirect_uri)
        conn = http.client.HTTPConnection("127.0.0.1", uri.port, timeout=3.0)
        conn.request("GET", uri.path + "?" + urlencode({
            "code": code, "state": state, "iss": issuer,
        }), headers={"Host": f"127.0.0.1:{uri.port}"})
        response = conn.getresponse()
        status, body = response.status, response.read()
        conn.close()
        return status, body

    def _read(self):
        return read_private_display(
            self.host.display_socket_path, clock=self._clock,
        )

    def _signed_in(self):
        self.host.start()
        self.assertEqual(self.host.begin_login(), {"status": "LOGIN_PENDING"})
        status, body = self._callback_request()
        self.assertEqual(status, 200)
        self.assertNotIn(self.secret.encode(), body)

    def test_construct_has_no_ports_browser_files_or_credentials(self):
        self.assertFalse(self.host.started)
        self.assertEqual(self.urls, [])
        self.assertFalse((self.directory / SOCKET_NAME).exists())
        with self.assertRaises(RuntimeError):
            _ = self.host.redirect_uri
        with self.assertRaises(RuntimeError):
            _ = self.host.display_socket_path
        self.assertEqual(self.host.begin_login(), {"status": "UNAVAILABLE"})

    def test_explicit_start_binds_only_test_transports_not_browser(self):
        self.host.start()
        self.assertTrue(self.host.started)
        self.assertEqual(self.urls, [])
        uri = urlsplit(self.host.redirect_uri)
        self.assertEqual(uri.hostname, "127.0.0.1")
        self.assertEqual(uri.scheme, "http")
        self.assertEqual(uri.path, "/callback")
        self.assertTrue(1024 <= uri.port <= 65535)
        sock = self.host.display_socket_path
        self.assertEqual(sock, self.directory / SOCKET_NAME)
        info = sock.lstat()
        self.assertTrue(stat.S_ISSOCK(info.st_mode))
        self.assertEqual(stat.S_IMODE(info.st_mode), 0o600)
        self.assertEqual(self._read()["status"], "NOT_CONNECTED")
        with self.assertRaises(RuntimeError):
            self.host.start()

    def test_one_use_loopback_login_scoped_api_to_tokenless_socket(self):
        self._signed_in()
        parsed = urlsplit(self.urls[0])
        self.assertEqual(parsed.scheme, "https")
        self.assertEqual(parsed.netloc, "issuer.example.test")
        query = parse_qs(parsed.query)
        self.assertEqual(query["code_challenge_method"], ["S256"])
        self.assertEqual(query["redirect_uri"], [self.host.redirect_uri])
        self.assertEqual(self.calls[0][0], "ci-one-use-code")
        self.assertGreaterEqual(self.calls[0][2], 43)
        display = self._read()
        self.assertEqual(display["status"], "READY")
        self.assertEqual(display["organizations"][0]["organizationId"],
                         "llc_example")
        self.assertEqual(display["organizations"][0]["scopeGrants"][0]["action"],
                         "records.read")
        self.assertEqual(display["portfolios"][0]["organizationIds"],
                         ["llc_example"])
        self.assertFalse(display["canSwitchOrganization"])
        for leak in (self.secret, "hidden-ci-test-person", "code_challenge",
                     "ci-one-use-code", "client_secret", "refreshToken",
                     "identity-1"):
            self.assertNotIn(leak, json.dumps(display))
        again, _ = self._callback_request()
        self.assertEqual(again, 410, "One-use callback unexpectedly reusable")
        self.assertEqual(self.host.begin_login(), {"status": "UNAVAILABLE"})
        self.assertEqual(self._read()["status"], "READY")

    def test_logout_clears_context_and_blocks_late_callback(self):
        self.host.start()
        self.assertEqual(self.host.begin_login(), {"status": "LOGIN_PENDING"})
        self.assertEqual(self.host.logout(), {"status": "SIGNED_OUT"})
        status, _ = self._callback_request()
        self.assertEqual(status, 400)
        self.assertEqual(self._read()["status"], "SIGNED_OUT")
        self.assertEqual(self._read()["organizations"], [])
        self.assertEqual(self.calls, [])

    def test_logout_after_ready_never_restores_old_membership(self):
        self._signed_in()
        self.assertEqual(self._read()["status"], "READY")
        self.assertEqual(self.host.logout(), {"status": "SIGNED_OUT"})
        self.assertEqual(self._read()["organizations"], [])
        self.assertEqual(self._read()["status"], "SIGNED_OUT")
        self.assertEqual(self.host.begin_login(), {"status": "UNAVAILABLE"})

    def test_invalid_state_consumes_one_use_receiver(self):
        self.host.start()
        self.assertEqual(self.host.begin_login(), {"status": "LOGIN_PENDING"})
        code, _ = self._callback_request(state="wrong-state")
        self.assertEqual(code, 400)
        code2, _ = self._callback_request()
        self.assertEqual(code2, 410)
        self.assertEqual(self._read()["organizations"], [])
        self.assertEqual(self._read()["status"], "SIGNED_OUT")
        self.assertEqual(self.calls, [])

    def test_api_rejection_and_malformed_claim_revokes_local_session(self):
        for mode in ("denied", "bogus"):
            with self.subTest(mode=mode):
                # One-shot host is recreated for each disposable attempt.
                self.host.close()
                self.host = self._host()
                self._signed_in()
                if mode == "denied":
                    self.api_status = 401
                else:
                    self.api_status = 200
                    self.api_bogus = True
                first = self._read()
                self.assertIn(first["status"], ("SIGNED_OUT", "UNAVAILABLE"))
                self.assertEqual(first["organizations"], [])
                self.api_status = 200
                self.api_bogus = False
                self.assertEqual(self._read()["organizations"], [])
                self.assertEqual(self._read()["status"], "SIGNED_OUT")

    def test_clock_rollback_revokes_and_does_not_recover_session(self):
        self._signed_in()
        self.assertEqual(self._read()["status"], "READY")
        self.time -= 5
        self.assertEqual(self._read()["organizations"], [])
        self.time = NOW
        self.assertEqual(self._read()["status"], "SIGNED_OUT")

    def test_expired_token_denies_and_never_restores_old_view(self):
        self._signed_in()
        self.assertEqual(self._read()["status"], "READY")
        self.time += 181
        self.assertEqual(self._read()["organizations"], [])
        self.assertEqual(self._read()["status"], "SIGNED_OUT")

    def test_close_removes_socket_and_rejects_session_resurrection(self):
        self._signed_in()
        path = self.host.display_socket_path
        self.assertTrue(path.exists())
        self.assertEqual(self._read()["status"], "READY")
        self.host.close()
        self.host.close()
        self.assertFalse(path.exists())
        self.assertFalse(self.host.started)
        self.assertEqual(self.host.begin_login(), {"status": "UNAVAILABLE"})
        self.assertEqual(
            read_private_display(path, clock=self._clock)["organizations"], []
        )

    def test_refuse_untrusted_config_and_nonprivate_directory(self):
        with self.assertRaises(ValueError):
            HostLifecycleConfig(
                issuer="http://issuer.example.test/realms/demo",
                authorization_endpoint=ISSUER + "/protocol/openid-connect/auth",
                client_id="ci-native", api_audience="ci-api",
                runtime_directory=self.directory,
            )
        with self.assertRaises(ValueError):
            HostLifecycleConfig(
                issuer=ISSUER, authorization_endpoint=ISSUER + "/protocol/openid-connect/auth",
                client_id="ci-native", api_audience="ci-api",
                runtime_directory=Path("relative"),
            )
        os.chmod(self.directory, 0o755)
        with self.assertRaises(ValueError):
            self.host.start()
        self.assertFalse((self.directory / SOCKET_NAME).exists())
        self.assertFalse(self.host.started)
        os.chmod(self.directory, 0o700)
        with self.assertRaises(RuntimeError):
            self.host.start()


if __name__ == "__main__":
    unittest.main()
