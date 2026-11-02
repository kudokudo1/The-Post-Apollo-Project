"""Offline security contract for host-owned OAuth code+S256 PKCE state machine.

All browser/API/ID-token verification dependencies are INJECTED disposable
test doubles. This is NOT a running OAuth callback listener or real IdP host.
"""
from __future__ import annotations

from dataclasses import replace
import hashlib
import base64
import json
import sys
from pathlib import Path
import unittest
from urllib.parse import urlencode, parse_qs, urlsplit

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "identity"))
from desktop_context_projection_v0 import HostContextReply
from desktop_session_host_v0 import (
    DesktopSessionHost, TrustedHostConfig, VerifiedCodeExchange,
)

ISSUER = "https://idp.synthetic.invalid/realms/test"
AUTH = ISSUER + "/protocol/openid-connect/auth"
REDIRECT = "http://127.0.0.1:8765/callback"
CLIENT = "test-public"
AUDIENCE = "test-api"
SECRET = "TEST_ONLY_BEARER_NOT_FOR_UI"

BODY = {
    "status": "OK", "schema": "post-apollo.identity.context-summary.v0",
    "organizations": [
        {"organizationId": "llc_a", "kind": "llc", "scopeGrants": []}
    ],
    "portfolios": [],
}


class HostTests(unittest.TestCase):
    def setUp(self):
        self.now = 1000
        self.opened = []
        self.exchanges = []
        self.api_received = []
        self.break_browser = False
        self.break_exchange = False
        self.break_api = False
        self.override = {}
        self.api_code = 200

        def open_browser(url):
            if self.break_browser:
                raise RuntimeError("fake browser failed; secrets never logged")
            self.opened.append(url)

        def exchange(code, verifier, nonce, redirect):
            self.exchanges.append((code, verifier, nonce, redirect))
            if self.break_exchange:
                raise RuntimeError("synthetic ID token verifier denied")
            return replace(VerifiedCodeExchange(
                access_token=SECRET,
                issuer=ISSUER,
                client_id=CLIENT,
                nonce=nonce,
                subject="synthetic-subject",
                expires_at=self.now + 180,
                token_type="Bearer",
                signed_id_token_verified=True,
            ), **self.override)

        def api_get(bearer):
            self.api_received.append(bearer)
            if self.break_api:
                raise RuntimeError("synthetic protected API failed")
            if self.api_code == 200:
                return HostContextReply(
                    200, "application/json", json.dumps(BODY).encode()
                )
            return HostContextReply(
                self.api_code, "application/json", b'{"status":"DENIED"}'
            )

        self.config = TrustedHostConfig(
            issuer=ISSUER, authorization_endpoint=AUTH,
            client_id=CLIENT, redirect_uri=REDIRECT, api_audience=AUDIENCE,
        )
        self.host = DesktopSessionHost(
            config=self.config, browser_open=open_browser,
            exchange_and_verify=exchange, api_get=api_get,
            clock=lambda: self.now,
        )

    def callback_url(self, *, state=None, issuer=ISSUER, code="test-authorization-code",
                     redirect=REDIRECT, extra=None):
        state = (parse_qs(urlsplit(self.opened[-1]).query)["state"][0]
                 if state is None else state)
        fields = [("code", code), ("state", state), ("iss", issuer)]
        if extra:
            fields.extend(extra)
        return redirect + "?" + urlencode(fields)

    def login(self):
        self.assertEqual(self.host.start_login(), {"status": "LOGIN_PENDING"})
        return self.host.complete_callback(self.callback_url())

    def test_no_access_before_real_host_login(self):
        self.assertEqual(self.host.snapshot()["status"], "NOT_CONNECTED")
        self.assertEqual(self.host.refresh_context()["status"], "SIGNED_OUT")
        self.assertFalse(self.host.snapshot()["canSwitchOrganization"])
        self.assertEqual(self.api_received, [])

    def test_browser_pkce_s256_state_nonce_and_loopback_callback(self):
        self.assertEqual(self.host.start_login(), {"status": "LOGIN_PENDING"})
        params = parse_qs(urlsplit(self.opened[0]).query)
        self.assertEqual(urlsplit(self.opened[0]).scheme, "https")
        self.assertEqual(params["response_type"], ["code"])
        self.assertEqual(params["code_challenge_method"], ["S256"])
        self.assertEqual(params["redirect_uri"], [REDIRECT])
        self.assertEqual(params["client_id"], [CLIENT])
        self.assertEqual(params["scope"], ["openid"])
        self.assertEqual(len(params["code_challenge"][0]), 43)
        self.assertGreaterEqual(len(params["state"][0]), 40)
        self.assertGreaterEqual(len(params["nonce"][0]), 40)
        self.assertNotIn(SECRET, self.opened[0])
        self.assertNotIn("code_verifier", params)

    def test_valid_signin_has_no_token_in_status_or_UI(self):
        self.assertEqual(self.login(), {"status": "SIGNED_IN"})
        view = self.host.refresh_context()
        self.assertEqual(view["status"], "READY")
        self.assertEqual([x["organizationId"] for x in view["organizations"]],
                         ["llc_a"])
        self.assertFalse(view["canSwitchOrganization"])
        self.assertEqual(self.api_received, [SECRET])
        for forbidden in (SECRET, "synthetic-subject", "test-authorization-code",
                          self.exchanges[0][1], self.exchanges[0][2]):
            self.assertNotIn(forbidden, repr(view))
            self.assertNotIn(forbidden, repr(self.host.snapshot()))

    def test_host_passes_original_pkce_verifier_only_to_trusted_exchange(self):
        self.assertEqual(self.login(), {"status": "SIGNED_IN"})
        code, verifier, nonce, redirect = self.exchanges[0]
        params = parse_qs(urlsplit(self.opened[0]).query)
        challenge = base64.urlsafe_b64encode(
            hashlib.sha256(verifier.encode()).digest()
        ).rstrip(b"=").decode()
        self.assertEqual(params["code_challenge"], [challenge])
        self.assertEqual(params["nonce"], [nonce])
        self.assertEqual(redirect, REDIRECT)
        self.assertEqual(code, "test-authorization-code")

    def test_callback_consumed_once_no_code_replay(self):
        self.host.start_login()
        callback = self.callback_url()
        self.assertEqual(self.host.complete_callback(callback)["status"], "SIGNED_IN")
        self.assertEqual(self.host.complete_callback(callback)["status"], "SIGNED_OUT")
        self.assertEqual(len(self.exchanges), 1)

    def test_wrong_state_cancels_pending_login(self):
        self.host.start_login()
        self.assertEqual(self.host.complete_callback(
            self.callback_url(state="wrong-state"))["status"], "SIGNED_OUT")
        self.assertEqual(self.exchanges, [])
        self.assertEqual(self.host.complete_callback(
            self.callback_url())["status"], "SIGNED_OUT")

    def test_wrong_issuer_rejected_before_exchange(self):
        self.host.start_login()
        self.assertEqual(self.host.complete_callback(
            self.callback_url(issuer="https://evil.example"))["status"],
            "SIGNED_OUT")
        self.assertEqual(self.exchanges, [])

    def test_duplicate_callback_fields_and_extra_authority_denied(self):
        for extra in ([("state", "duplicate")], [("role", "admin")],
                      [("organizationId", "llc_b")], [("access_token", SECRET)]):
            with self.subTest(extra=extra):
                self.host.start_login()
                self.assertEqual(self.host.complete_callback(
                    self.callback_url(extra=extra))["status"], "SIGNED_OUT")
        self.assertEqual(self.exchanges, [])

    def test_wrong_callback_path_host_scheme_fragment_denied(self):
        for redirect in ("http://localhost:8765/callback",
                         "http://127.0.0.1:8766/callback",
                         "http://127.0.0.1:8765/other",
                         "https://127.0.0.1:8765/callback",
                         "http://127.0.0.1:8765/callback#fake"):
            with self.subTest(redirect=redirect):
                self.host.start_login()
                self.assertEqual(self.host.complete_callback(
                    self.callback_url(redirect=redirect))["status"],
                    "SIGNED_OUT")
        self.assertEqual(self.exchanges, [])

    def test_invalid_code_denied(self):
        for code in ("", "a b", "x"*2049, "x\nx"):
            with self.subTest(code=code[:16]):
                self.host.start_login()
                self.assertEqual(self.host.complete_callback(
                    self.callback_url(code=code))["status"], "SIGNED_OUT")
        self.assertEqual(self.exchanges, [])

    def test_expired_login_denied_before_exchange(self):
        self.host.start_login()
        callback = self.callback_url()
        self.now += 301
        self.assertEqual(self.host.complete_callback(callback)["status"],
                         "SIGNED_OUT")
        self.assertEqual(self.exchanges, [])

    def test_new_login_replaces_pending_state(self):
        self.host.start_login()
        stale = self.callback_url()
        self.host.start_login()
        self.assertEqual(self.host.complete_callback(stale)["status"],
                         "SIGNED_OUT")
        self.assertEqual(self.exchanges, [])

    def test_browser_launch_failure_clears_pending(self):
        self.break_browser = True
        self.assertEqual(self.host.start_login()["status"], "UNAVAILABLE")
        self.assertEqual(self.host.complete_callback(
            REDIRECT+"?code=x&state=y&iss="+ISSUER)["status"], "SIGNED_OUT")

    def test_trusted_exchange_failure_leaks_nothing(self):
        self.break_exchange = True
        self.host.start_login()
        self.assertEqual(self.host.complete_callback(
            self.callback_url())["status"], "SIGNED_OUT")
        self.assertEqual(self.host.refresh_context()["status"], "SIGNED_OUT")

    def test_signed_id_attestation_required(self):
        self.override = {"signed_id_token_verified": False}
        self.assertEqual(self.login()["status"], "SIGNED_OUT")

    def test_issuer_client_nonce_restrictions(self):
        for override in ({"issuer": "https://evil.example"},
                         {"client_id": "another-client"},
                         {"nonce": "wrong-nonce"},
                         {"subject": ""}):
            with self.subTest(override=override):
                self.override = override
                self.assertEqual(self.login()["status"], "SIGNED_OUT")

    def test_token_type_expiry_size_and_blank_rejected(self):
        for overrides in ({"token_type": "Basic"},
                          {"expires_at": 1000},
                          {"expires_at": 1901},
                          {"expires_at": True},
                          {"access_token": ""},
                          {"access_token": "bad bearer"},
                          {"access_token": "x" * 8193}):
            with self.subTest(overrides=repr(overrides)[:40]):
                self.override = overrides
                self.assertEqual(self.login()["status"], "SIGNED_OUT")

    def test_signout_erases_active_context_and_secret(self):
        self.login()
        self.host.refresh_context()
        out = self.host.logout()
        self.assertEqual(out["status"], "NOT_CONNECTED")
        self.assertEqual(out["organizations"], [])
        self.assertEqual(self.host.refresh_context()["status"], "SIGNED_OUT")
        self.assertEqual(len(self.api_received), 1)

    def test_local_token_expiry_clears_company_info(self):
        self.login()
        self.host.refresh_context()
        self.now = 1180
        self.assertEqual(self.host.snapshot()["status"], "NOT_CONNECTED")
        self.assertEqual(self.host.refresh_context()["status"], "SIGNED_OUT")

    def test_clock_rollback_invalidates_session_and_pending(self):
        self.login()
        self.host.refresh_context()
        self.now = 999
        self.assertEqual(self.host.snapshot()["status"], "NOT_CONNECTED")
        self.assertEqual(self.host.refresh_context()["organizations"], [])

    def test_api_401_clears_display_and_does_not_authorize_switch(self):
        self.login()
        self.host.refresh_context()
        self.api_code = 401
        view = self.host.refresh_context()
        self.assertEqual(view["status"], "SIGNED_OUT")
        self.assertEqual(view["organizations"], [])
        self.assertFalse(view["canSwitchOrganization"])

    def test_api_failure_leaks_no_exception_to_UI(self):
        self.login()
        self.host.refresh_context()
        self.break_api = True
        self.assertEqual(self.host.refresh_context()["status"], "UNAVAILABLE")
        self.assertEqual(self.host.snapshot()["organizations"], [])

    def test_session_status_does_not_return_login_url_or_code(self):
        self.host.start_login()
        self.assertEqual(self.host.snapshot()["organizations"], [])
        self.assertNotIn("nonce", repr(self.host.snapshot()))
        self.assertNotIn("state", repr(self.host.snapshot()))
        self.assertNotIn("authorization", repr(self.host.snapshot()))

    def test_https_issuer_and_exact_loopback_redirect_required(self):
        invalid_config = [
            {"issuer": "http://idp.synthetic.invalid/realms/test"},
            {"authorization_endpoint": "https://evil.invalid/auth"},
            {"redirect_uri": "http://0.0.0.0:8765/callback"},
            {"redirect_uri": "http://127.0.0.1:80/callback"},
            {"redirect_uri": "http://127.0.0.1:8765/callback?x=y"},
            {"redirect_uri": "http://127.0.0.1:8765/evil"},
            {"client_id": "evil client"},
        ]
        for change in invalid_config:
            with self.subTest(change=change):
                with self.assertRaises(ValueError):
                    replace(self.config, **change)

    def test_host_is_not_a_production_listener_or_token_file(self):
        source = (ROOT / "services/identity/desktop_session_host_v0.py").read_text()
        for text in ("socket.bind", "HTTPServer(", "ThreadingHTTPServer(",
                     "Path.home(", "FileView", "subprocess.", "requests.",
                     "os.environ", "start_dev", "Qt.openUrlExternally",
                     "print(", "access_token.json", "pickle.dump"):
            with self.subTest(text=text):
                self.assertNotIn(text, source)


if __name__ == "__main__":
    unittest.main()
