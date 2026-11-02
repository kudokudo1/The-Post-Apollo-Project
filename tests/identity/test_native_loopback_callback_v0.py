"""Isolated loopback GET + native host PKCE transport contracts.

No real IdP, real browser, existing desktop process, Social QML credentials,
or production port. Tests explicitly start localhost on an ephemeral port and
close it. A fake cryptographic verifier is injected by the trusted test host.
"""
from __future__ import annotations

import contextlib
from dataclasses import replace
from io import StringIO
import http.client
import json
from pathlib import Path
import sys
import unittest
from urllib.parse import parse_qs, urlencode, urlsplit

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "identity"))

from native_loopback_callback_v0 import LoopbackCallbackReceiver
from desktop_session_host_v0 import (
    DesktopSessionHost, TrustedHostConfig, VerifiedCodeExchange,
)
from desktop_context_projection_v0 import HostContextReply

ISSUER = "https://trusted-idp.invalid/realms/desktop"
AUTH = ISSUER + "/protocol/openid-connect/auth"
TOKEN = "THIS_TEST_BEARER_MUST_NOT_ENTER_BROWSER_OR_UI"
SUMMARY = {
    "status": "OK", "schema": "post-apollo.identity.context-summary.v0",
    "organizations": [{"organizationId": "llc_a", "kind": "llc",
                       "scopeGrants": []}],
    "portfolios": [],
}


class LoopbackReceiverTests(unittest.TestCase):
    def setUp(self):
        self.clock = 1_700_000_000
        self.browser_urls: list[str] = []
        self.exchanges = []
        self.api_bearers = []
        self.host = None

        def callback(uri):
            return self.host.complete_callback(uri)

        self.receiver = LoopbackCallbackReceiver(callback=callback)
        self.receiver.start()
        self.addCleanup(self.receiver.close)
        self.redirect = self.receiver.redirect_uri
        self.port = urlsplit(self.redirect).port
        assert self.port is not None

        self.config = TrustedHostConfig(
            issuer=ISSUER, authorization_endpoint=AUTH,
            client_id="native-ci", redirect_uri=self.redirect,
            api_audience="ci-api",
        )

        def open_browser(url):
            self.browser_urls.append(url)

        def verified_exchange(code, verifier, nonce, redirect):
            self.exchanges.append((code, verifier, nonce, redirect))
            return VerifiedCodeExchange(
                access_token=TOKEN,
                issuer=ISSUER,
                client_id="native-ci",
                nonce=nonce,
                subject="synthetic-person",
                expires_at=self.clock + 120,
                token_type="Bearer",
                signed_id_token_verified=True,
            )

        def host_api(bearer):
            self.api_bearers.append(bearer)
            return HostContextReply(
                200, "application/json",
                json.dumps(SUMMARY).encode("utf-8"),
            )

        self.host = DesktopSessionHost(
            config=self.config, browser_open=open_browser,
            exchange_and_verify=verified_exchange,
            api_get=host_api, clock=lambda: self.clock,
        )

    def request(self, *, method="GET", path=None, headers=None):
        if path is None:
            path = "/callback"
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        try:
            conn.request(method, path, headers=headers or {})
            resp = conn.getresponse()
            return resp.status, dict(resp.getheaders()), resp.read()
        finally:
            conn.close()

    def callback_path(self, **fields):
        params = parse_qs(urlsplit(self.browser_urls[-1]).query)
        pairs = {
            "code": "synthetic-code",
            "state": params["state"][0],
            "iss": ISSUER,
        }
        pairs.update(fields)
        return "/callback?" + urlencode(pairs)

    def login(self):
        self.assertEqual(self.host.start_login(), {"status": "LOGIN_PENDING"})
        status, headers, body = self.request(path=self.callback_path())
        return status, headers, body

    def test_no_listener_created_until_explicit_start(self):
        candidate = LoopbackCallbackReceiver(callback=lambda _: {})
        with self.assertRaises(RuntimeError):
            _ = candidate.redirect_uri
        candidate.close()
        with self.assertRaises(RuntimeError):
            candidate.start()

    def test_exclusive_numeric_ipv4_loopback_and_host_config_alignment(self):
        self.assertEqual(self.receiver._server.server_address[0], "127.0.0.1")
        self.assertEqual(self.redirect, self.config.redirect_uri)
        self.assertEqual(urlsplit(self.redirect).hostname, "127.0.0.1")
        self.assertEqual(urlsplit(self.redirect).path, "/callback")
        self.assertTrue(1024 <= self.port <= 65535)

    def test_actual_http_callback_completes_host_signed_in(self):
        status, headers, body = self.login()
        self.assertEqual(status, 200)
        self.assertEqual(headers["Cache-Control"], "no-store")
        self.assertEqual(headers["Referrer-Policy"], "no-referrer")
        self.assertEqual(headers["Content-Type"], "text/plain; charset=utf-8")
        self.assertEqual(headers["X-Content-Type-Options"], "nosniff")
        self.assertNotIn("state=", body.decode())
        self.assertNotIn("code=", body.decode())
        self.assertNotIn(TOKEN, repr((headers, body)))
        self.assertEqual(len(self.exchanges), 1)
        self.assertEqual(self.exchanges[0][3], self.redirect)
        view = self.host.refresh_context()
        self.assertEqual(view["status"], "READY")
        self.assertEqual(view["organizations"][0]["organizationId"], "llc_a")
        self.assertFalse(view["canSwitchOrganization"])
        self.assertEqual(self.api_bearers, [TOKEN])
        self.assertNotIn(TOKEN, repr(view))
        self.assertNotIn(TOKEN, self.browser_urls[0])

    def test_valid_callback_is_one_shot_even_with_identical_state(self):
        self.host.start_login()
        path = self.callback_path()
        self.assertEqual(self.request(path=path)[0], 200)
        self.assertEqual(self.request(path=path)[0], 410)
        self.assertEqual(len(self.exchanges), 1)

    def test_wrong_state_is_denied_and_consumes_callback(self):
        self.host.start_login()
        self.assertEqual(self.request(path=self.callback_path(state="wrong"))[0], 400)
        self.assertEqual(self.request(path=self.callback_path())[0], 410)
        self.assertEqual(len(self.exchanges), 0)
        self.assertEqual(self.host.snapshot()["status"], "NOT_CONNECTED")

    def test_wrong_issuer_denied_before_exchange(self):
        self.host.start_login()
        self.assertEqual(self.request(path=self.callback_path(
            iss="https://evil.invalid/realm"))[0], 400)
        self.assertEqual(self.exchanges, [])

    def test_duplicated_parameter_is_denied_by_host(self):
        self.host.start_login()
        self.assertEqual(self.request(
            path=self.callback_path()+"&state=evil")[0], 400)
        self.assertEqual(self.exchanges, [])

    def test_error_response_never_echoes_request_token_or_code(self):
        self.host.start_login()
        path = self.callback_path(code="SENSITIVE_TEST_CODE_NEVER_ECHO")
        status, headers, body = self.request(path=path+"&unexpected=admin")
        self.assertEqual(status, 400)
        for source in (repr(headers), body.decode()):
            self.assertNotIn("SENSITIVE_TEST_CODE", source)
            self.assertNotIn("state=", source)
            self.assertNotIn(TOKEN, source)
            self.assertNotIn(ISSUER, source)

    def test_non_callback_url_does_not_consume_valid_attempt(self):
        self.host.start_login()
        for path in ("/", "/favicon.ico", "/callback", "/callback/extra"):
            self.assertEqual(self.request(path=path)[0], 404)
        self.assertEqual(self.request(path=self.callback_path())[0], 200)

    def test_reject_host_header_mismatch_before_consuming(self):
        self.host.start_login()
        status, _, _ = self.request(
            path=self.callback_path(), headers={"Host": "evil.invalid"})
        self.assertEqual(status, 400)
        self.assertEqual(self.request(path=self.callback_path())[0], 200)

    def test_reject_origin_header_before_consuming(self):
        self.host.start_login()
        status, _, _ = self.request(
            path=self.callback_path(), headers={"Origin": "https://evil.invalid"})
        self.assertEqual(status, 400)
        self.assertEqual(self.request(path=self.callback_path())[0], 200)

    def test_reject_post_put_delete_and_head(self):
        self.host.start_login()
        for method in ("POST", "PUT", "DELETE", "HEAD"):
            self.assertEqual(self.request(method=method,
                                          path=self.callback_path())[0], 405)
        self.assertEqual(self.request(path=self.callback_path())[0], 200)

    def test_reject_request_body_without_consuming(self):
        self.host.start_login()
        status, _, _ = self.request(
            path=self.callback_path(), headers={"Content-Length": "10"})
        self.assertEqual(status, 400)
        self.assertEqual(self.request(path=self.callback_path())[0], 200)

    def test_expired_login_does_not_complete(self):
        self.host.start_login()
        self.clock += 301
        self.assertEqual(self.request(path=self.callback_path())[0], 400)
        self.assertEqual(self.exchanges, [])

    def test_receiver_cannot_be_restarted(self):
        self.receiver.close()
        with self.assertRaises(RuntimeError):
            self.receiver.start()
        with self.assertRaises(RuntimeError):
            _ = self.receiver.redirect_uri

    def test_success_http_does_not_authorize_organization_switch(self):
        self.login()
        display = self.host.refresh_context()
        self.assertFalse(display["canSwitchOrganization"])
        self.assertNotIn("selectOrganization", repr(display))

    def test_request_logging_suppressed_including_token_url(self):
        stream = StringIO()
        with contextlib.redirect_stderr(stream):
            self.login()
            self.request(path="/not-found?code=SENSITIVE_TEST_CODE")
            self.request(path="/callback?code=SENSITIVE_TEST_CODE")
        self.assertNotIn("SENSITIVE_TEST_CODE", stream.getvalue())
        self.assertNotIn("state=", stream.getvalue())

    def test_host_returns_generic_response_for_verifier_failure(self):
        self.host.start_login()
        def bad_verifier(*args):
            raise RuntimeError("private subject and token info")
        self.host._exchange = bad_verifier
        status, _, body = self.request(path=self.callback_path())
        self.assertEqual(status, 400)
        self.assertNotIn("private", body.decode())
        self.assertEqual(self.host.snapshot()["organizations"], [])

    def test_existing_view_stays_disconnected_without_completing_callback(self):
        self.host.start_login()
        self.assertEqual(self.host.snapshot()["status"], "NOT_CONNECTED")
        self.assertEqual(self.api_bearers, [])
        self.assertEqual(self.receiver._server.server_address[0], "127.0.0.1")


if __name__ == "__main__":
    unittest.main()
