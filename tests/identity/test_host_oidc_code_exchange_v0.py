"""Real disposable HTTPS OIDC code POST + signed ID-token host lifecycle test.

This is NOT a real identity provider. The test signs genuine RS256 JWTs with
an ephemeral RSA test key while a TLS fixture enforces PKCE at the code
endpoint. No real accounts, browser, host deployment or credentials are used.
"""
from __future__ import annotations

import base64
import hashlib
import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import shutil
import ssl
import subprocess
import sys
import tempfile
import threading
import unittest
from urllib.parse import parse_qs, urlsplit, urlencode

from cryptography.hazmat.primitives.asymmetric import rsa
import jwt

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "identity"))
from desktop_host_lifecycle_v0 import DesktopHostLifecycle, HostLifecycleConfig
from host_oidc_code_exchange_v0 import HostOidcCodeExchange, HostOidcExchangeConfig
from pinned_https_identity_transport_v0 import (
    HostPinnedHttpsTransport, PinnedIdentityHttpsConfig,
)
from private_context_ipc_v0 import read_private_display

NOW = 1_800_000_000
CODE = "ci-authorized-oidc-code"
ACCESS = "ci-opaque-disposable-access-token"


def _b64(value):
    raw = value.to_bytes((value.bit_length() + 7) // 8, "big")
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


class _Idp(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *args):
        # NEVER log code, verifier, nonce, bearer or returned ID JWT.
        return

    def _json(self, value, status=200, mime="application/json"):
        data = value if isinstance(value, bytes) else json.dumps(value).encode("ascii")
        self.send_response(status)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(data)
        self.close_connection = True

    def do_GET(self):
        server = self.server
        if self.path == "/realms/ci/.well-known/openid-configuration":
            self._json(server.metadata)
        elif self.path == "/realms/ci/protocol/openid-connect/certs":
            self._json(server.jwks)
        elif self.path == "/v0/me/contexts":
            server.api_calls += 1
            if self.headers.get("Authorization") != "Bearer " + ACCESS:
                self._json({"status": "DENIED"}, status=401)
            else:
                self._json({
                    "schema": "post-apollo.identity.context-summary.v0",
                    "status": "OK",
                    "organizations": [{
                        "organizationId": "llc_ci", "kind": "llc",
                        "scopeGrants": [{
                            "action": "records.read", "divisionId": "health",
                            "unitId": "east", "expiresAt": NOW + 120,
                        }],
                    }],
                    "portfolios": [],
                })
        else:
            self._json(b"missing", status=404, mime="text/plain")

    def do_POST(self):
        server = self.server
        server.token_calls += 1
        if self.path != "/realms/ci/protocol/openid-connect/token":
            self._json({"error": "denied"}, status=404)
            return
        if server.mode == "redirect":
            self.send_response(302)
            self.send_header("Location", server.origin + "/unauthorized")
            self.send_header("Content-Length", "0")
            self.send_header("Connection", "close")
            self.end_headers()
            return
        raw = self.rfile.read(min(int(self.headers.get("Content-Length", "0")), 4096))
        form = parse_qs(raw.decode("ascii"), keep_blank_values=True)
        server.form_keys = sorted(form)
        if (self.headers.get("Content-Type") != "application/x-www-form-urlencoded"
                or set(form) != {"grant_type", "code", "redirect_uri",
                                "client_id", "code_verifier"}
                or form["grant_type"] != ["authorization_code"]
                or form["code"] != [CODE]
                or form["client_id"] != ["ci-native"]
                or form["redirect_uri"] != [server.redirect_uri]
                or base64.urlsafe_b64encode(
                    hashlib.sha256(form["code_verifier"][0].encode("ascii")).digest()
                ).rstrip(b"=").decode("ascii") != server.challenge):
            self._json({"error": "invalid_grant"}, status=400)
            return
        claims = {
            "iss": server.issuer, "aud": "ci-native", "sub": "ci-person",
            "iat": NOW, "exp": NOW + 180, "nonce": server.nonce,
        }
        if server.mode == "wrong-issuer":
            claims["iss"] = "https://attacker.invalid/realms/x"
        if server.mode == "wrong-audience":
            claims["aud"] = "other-client"
        if server.mode == "wrong-nonce":
            claims["nonce"] = "invalid-nonce-long-enough"
        if server.mode == "expired":
            claims["exp"] = NOW - 1
        if server.mode == "future":
            claims["iat"] = NOW + 120
        if server.mode == "at-hash":
            claims["at_hash"] = "wrong-hash"
        if server.mode == "good-at-hash":
            claims["at_hash"] = base64.urlsafe_b64encode(
                hashlib.sha256(ACCESS.encode("ascii")).digest()[:16]
            ).rstrip(b"=").decode("ascii")
        if server.mode == "admin-claim":
            claims["role"] = "administrator"  # Must never authorize UI.
        signing_key = server.other_key if server.mode == "wrong-key" else server.key
        id_token = jwt.encode(
            claims, signing_key, algorithm="RS256",
            headers={"kid": "ci-rsa", "typ": "JWT"},
        )
        response = {
            "access_token": ACCESS, "id_token": id_token,
            "token_type": "Bearer", "expires_in": 180,
            # Deliberately supplied; client must not retain/forward it.
            "refresh_token": "ci-test-refresh-token-must-be-discarded",
        }
        if server.mode == "wrong-type":
            response["token_type"] = "Basic"
        if server.mode == "too-long":
            response["expires_in"] = 36000
        if server.mode == "bad-json":
            self._json(b'{"access_token":"a","access_token":"b"}')
            return
        if server.mode == "bad-content-type":
            self._json(response, mime="text/html")
            return
        self._json(response)


@unittest.skipUnless(shutil.which("openssl"), "OpenSSL disposable TLS fixture required")
class HostOidcCodeExchangeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="post-apollo-oidc-code-")
        cls.cert = Path(cls.temp.name) / "localhost.pem"
        cls.keyfile = Path(cls.temp.name) / "private.pem"
        subprocess.run([
            "openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes",
            "-keyout", str(cls.keyfile), "-out", str(cls.cert), "-days", "1",
            "-subj", "/CN=localhost", "-addext", "subjectAltName=DNS:localhost",
        ], check=True, timeout=20, stdout=subprocess.DEVNULL,
           stderr=subprocess.DEVNULL)
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), _Idp)
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ssl_context.minimum_version = ssl.TLSVersion.TLSv1_2
        ssl_context.load_cert_chain(certfile=str(cls.cert), keyfile=str(cls.keyfile))
        cls.server.socket = ssl_context.wrap_socket(
            cls.server.socket, server_side=True
        )
        cls.server.origin = f"https://localhost:{cls.server.server_port}"
        cls.server.issuer = cls.server.origin + "/realms/ci"
        cls.server.key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        cls.server.other_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        pub = cls.server.key.public_key().public_numbers()
        cls.server.jwks = {"keys": [{
            "kid": "ci-rsa", "kty": "RSA", "alg": "RS256", "use": "sig",
            "n": _b64(pub.n), "e": _b64(pub.e),
        }]}
        cls.server.metadata = {
            "issuer": cls.server.issuer,
            "jwks_uri": cls.server.issuer + "/protocol/openid-connect/certs",
            "authorization_endpoint": cls.server.issuer
                                      + "/protocol/openid-connect/auth",
            "token_endpoint": cls.server.issuer
                              + "/protocol/openid-connect/token",
            "response_types_supported": ["code"],
            "code_challenge_methods_supported": ["S256"],
        }
        cls.thread = threading.Thread(
            target=cls.server.serve_forever, daemon=True,
            name="disposable-oidc-test-issuer",
        )
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)
        cls.temp.cleanup()

    def setUp(self):
        self.now = NOW
        self.tmp = tempfile.TemporaryDirectory(prefix="identity-runtime-")
        self.addCleanup(self.tmp.cleanup)
        self.runtime = Path(self.tmp.name)
        os.chmod(self.runtime, 0o700)
        self.urls = []
        self.server.mode = "good"
        self.server.token_calls = 0
        self.server.api_calls = 0
        self.server.form_keys = []
        self.server.nonce = ""
        self.server.challenge = ""
        self.server.redirect_uri = ""
        self.transport = HostPinnedHttpsTransport(PinnedIdentityHttpsConfig(
            issuer=self.server.issuer,
            jwks_url=self.server.metadata["jwks_uri"],
            context_url=self.server.origin + "/v0/me/contexts",
            ca_bundle=self.cert,
        ))
        self.config = HostOidcExchangeConfig(
            issuer=self.server.issuer,
            authorization_endpoint=self.server.metadata["authorization_endpoint"],
            token_endpoint=self.server.metadata["token_endpoint"],
            client_id="ci-native", ca_bundle=self.cert,
        )
        self.exchange = HostOidcCodeExchange.from_pinned_transport(
            config=self.config, transport=self.transport,
            clock=lambda: self.now,
        )
        self.host = self._host()
        self.addCleanup(lambda: self.host.close())

    def _browser(self, url):
        self.urls.append(url)
        query = parse_qs(urlsplit(url).query)
        self.server.nonce = query["nonce"][0]
        self.server.challenge = query["code_challenge"][0]
        self.server.redirect_uri = query["redirect_uri"][0]

    def _host(self):
        return DesktopHostLifecycle(
            config=HostLifecycleConfig(
                issuer=self.server.issuer,
                authorization_endpoint=self.config.authorization_endpoint,
                client_id=self.config.client_id, api_audience="ci-api",
                runtime_directory=self.runtime,
            ),
            browser_open=self._browser,
            exchange_and_verify=self.exchange.exchange_and_verify,
            api_get=self.transport.get_contexts,
            clock=lambda: self.now,
        )

    def _start_and_callback(self):
        self.host.start()
        self.assertEqual(self.host.begin_login(), {"status": "LOGIN_PENDING"})
        query = parse_qs(urlsplit(self.urls[-1]).query)
        port = urlsplit(self.host.redirect_uri).port
        uri = "/callback?" + urlencode({
            "code": CODE, "state": query["state"][0],
            "iss": self.server.issuer,
        })
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        conn.request("GET", uri, headers={"Host": f"127.0.0.1:{port}"})
        res = conn.getresponse()
        status, body = res.status, res.read()
        conn.close()
        return status, body

    def _display(self):
        return read_private_display(
            self.host.display_socket_path, clock=lambda: self.now,
        )

    def test_real_https_code_and_signed_id_token_to_tokenless_display(self):
        status, body = self._start_and_callback()
        self.assertEqual(status, 200)
        self.assertEqual(self.server.token_calls, 1)
        self.assertEqual(sorted(self.server.form_keys), sorted([
            "grant_type", "code", "redirect_uri", "client_id", "code_verifier",
        ]))
        display = self._display()
        self.assertEqual(display["status"], "READY")
        self.assertEqual(display["organizations"][0]["organizationId"], "llc_ci")
        self.assertEqual(display["organizations"][0]["scopeGrants"][0]["action"],
                         "records.read")
        self.assertFalse(display["canSwitchOrganization"])
        for secret in (ACCESS, "ci-test-refresh-token-must-be-discarded",
                       "ci-person", "code_verifier", "nonce", "id_token"):
            self.assertNotIn(secret, json.dumps(display))
            self.assertNotIn(secret.encode("ascii"), body)
        self.assertEqual(self.server.api_calls, 1)
        self.assertEqual(self.host.begin_login(), {"status": "UNAVAILABLE"})

    def test_signed_jwt_failures_reject_callback_and_keep_company_empty(self):
        for mode in (
            "wrong-issuer", "wrong-audience", "wrong-nonce", "expired",
            "future", "wrong-key", "at-hash", "wrong-type", "too-long",
            "bad-json", "bad-content-type", "redirect",
        ):
            with self.subTest(mode=mode):
                self.host.close()
                self.server.mode = mode
                self.server.token_calls = 0
                self.host = self._host()
                status, body = self._start_and_callback()
                self.assertEqual(status, 400)
                self.assertEqual(self.server.token_calls, 1)
                self.assertEqual(self._display()["organizations"], [])
                self.assertEqual(self._display()["status"], "SIGNED_OUT")
                self.assertNotIn(ACCESS.encode(), body)

    def test_valid_at_hash_and_extra_identity_claim_never_grant_permissions(self):
        for mode in ("good-at-hash", "admin-claim"):
            with self.subTest(mode=mode):
                self.host.close()
                self.server.mode = mode
                self.host = self._host()
                status, _ = self._start_and_callback()
                self.assertEqual(status, 200)
                displayed = self._display()
                self.assertEqual(displayed["status"], "READY")
                self.assertNotIn("administrator", json.dumps(displayed))
                self.assertFalse(displayed["canSwitchOrganization"])

    def test_logout_and_host_stop_clear_verified_company_data(self):
        status, _ = self._start_and_callback()
        self.assertEqual(status, 200)
        path = self.host.display_socket_path
        self.assertEqual(self._display()["status"], "READY")
        self.host.logout()
        self.assertEqual(self._display()["organizations"], [])
        self.assertEqual(self._display()["status"], "SIGNED_OUT")
        self.host.close()
        self.assertFalse(path.exists())
        self.assertEqual(
            read_private_display(path, clock=lambda: self.now)["organizations"], []
        )

    def test_discovery_must_match_preapproved_issuer_and_endpoints(self):
        metadata = self.server.metadata.copy()
        try:
            for name, value in (
                ("issuer", "https://attacker.invalid/realm"),
                ("jwks_uri", "https://attacker.invalid/keys"),
                ("token_endpoint", "https://attacker.invalid/token"),
                ("response_types_supported", ["token"]),
                ("code_challenge_methods_supported", ["plain"]),
            ):
                with self.subTest(name=name):
                    self.server.metadata = {**metadata, name: value}
                    with self.assertRaises(ValueError):
                        HostOidcCodeExchange.from_pinned_transport(
                            config=self.config, transport=self.transport,
                            clock=lambda: self.now,
                        )
        finally:
            self.server.metadata = metadata

    def test_invalid_host_code_args_cannot_reach_token_server(self):
        calls = self.server.token_calls
        for code, verifier, nonce, redirect in (
            ("", "A" * 64, "N" * 32, "http://127.0.0.1:5555/callback"),
            (CODE, "short", "N" * 32, "http://127.0.0.1:5555/callback"),
            (CODE, "A" * 64, "N" * 32, "https://localhost/callback"),
            (CODE, "A" * 64, "N" * 32, "http://127.0.0.1:5555/other"),
            (CODE, "A" * 64, "N" * 32, "http://127.0.0.1:5555/callback?admin=1"),
        ):
            with self.subTest(code=code, redirect=redirect):
                with self.assertRaises(ValueError):
                    self.exchange.exchange_and_verify(code, verifier, nonce, redirect)
        self.assertEqual(self.server.token_calls, calls)

    def test_wrong_certificate_hostname_and_invalid_token_endpoint_fail(self):
        config = HostOidcExchangeConfig(
            issuer=self.server.issuer,
            authorization_endpoint=self.config.authorization_endpoint,
            token_endpoint=self.config.token_endpoint,
            client_id="ci-native", ca_bundle=None,
        )
        other = HostOidcCodeExchange(
            config=config, trusted_jwks=self.server.jwks,
            clock=lambda: self.now,
        )
        with self.assertRaises(ValueError):
            other.exchange_and_verify(
                CODE, "A" * 64, "N" * 32, "http://127.0.0.1:5555/callback",
            )
        with self.assertRaises(ValueError):
            HostOidcExchangeConfig(
                issuer=self.server.issuer,
                authorization_endpoint=self.config.authorization_endpoint,
                token_endpoint=self.server.origin + "/other/token",
                client_id="ci-native", ca_bundle=self.cert,
            )
        with self.assertRaises(ValueError):
            HostOidcExchangeConfig(
                issuer=self.server.issuer,
                authorization_endpoint=self.config.authorization_endpoint,
                token_endpoint="https://attacker.invalid/token",
                client_id="ci-native", ca_bundle=self.cert,
            )

    def test_jwks_refuses_weak_private_duplicate_and_untrusted_keys(self):
        entry = self.server.jwks["keys"][0]
        bad_sets = (
            {"keys": []},
            {"keys": [entry, entry]},
            {"keys": [{**entry, "d": "private-exponent"}]},
            {"keys": [{**entry, "alg": "none"}]},
            {"keys": [{**entry, "use": "enc"}]},
            {"keys": [{**entry, "kid": "other", "kty": "EC"}]},
        )
        for jwks in bad_sets:
            with self.subTest(jwks=repr(jwks)[:80]):
                with self.assertRaises(ValueError):
                    HostOidcCodeExchange(
                        config=self.config, trusted_jwks=jwks,
                        clock=lambda: self.now,
                    )


if __name__ == "__main__":
    unittest.main()
