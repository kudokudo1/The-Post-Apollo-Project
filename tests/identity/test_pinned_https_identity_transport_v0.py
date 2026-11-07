"""Real loopback TLS test of host-only pinned Identity Center HTTPS reads.

This test generates a disposable self-signed localhost TLS certificate using
OpenSSL in the CI temporary directory. It does NOT contact an IdP, save real
tokens, trust insecure TLS, bind a public interface, or start a desktop host.
"""
from __future__ import annotations

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

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "identity"))

from desktop_context_projection_v0 import (
    DesktopContextProjection, HostContextReply,
)
from pinned_https_identity_transport_v0 import (
    HostPinnedHttpsTransport, PinnedIdentityHttpsConfig,
)

NOW = 1_800_000_000
TOKEN = "CI-ONLY-BEARER-DO-NOT-LOG"
RESPONSE = {
    "schema": "post-apollo.identity.context-summary.v0",
    "status": "OK",
    "organizations": [
        {"organizationId": "llc_test", "kind": "llc",
         "scopeGrants": [
             {"action": "records.read", "divisionId": "health",
              "unitId": "east", "expiresAt": NOW + 200}
         ]}
    ],
    "portfolios": [
        {"portfolioId": "test_portfolio", "organizationIds": ["llc_test"]}
    ],
}


class _Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        # Do not log bearer tokens, requested URLs, or response bodies.
        return

    def do_GET(self):
        self.server.calls.append({
            "path": self.path, "authorization": self.headers.get("Authorization"),
            "accept_encoding": self.headers.get("Accept-Encoding"),
        })
        status, data, mimetype, extra = self.server.routes.get(
            self.path, (404, b"missing", "text/plain", {})
        )
        self.send_response(status)
        self.send_header("Content-Type", mimetype)
        self.send_header("Content-Length", str(len(data)))
        for key, value in extra.items():
            self.send_header(key, value)
        self.send_header("Connection", "close")
        self.end_headers()
        try:
            self.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError):
            pass


@unittest.skipUnless(shutil.which("openssl"), "Disposable OpenSSL fixture required")
class PinnedHttpsIdentityTransportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="identity-test-https-")
        cls.ca_file = Path(cls.temp.name) / "localhost-cert.pem"
        cls.key_file = Path(cls.temp.name) / "localhost-key.pem"
        subprocess.run([
            "openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes",
            "-keyout", str(cls.key_file), "-out", str(cls.ca_file),
            "-days", "1", "-subj", "/CN=localhost",
            "-addext", "subjectAltName=DNS:localhost",
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
           check=True, timeout=20)
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
        tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        tls.minimum_version = ssl.TLSVersion.TLSv1_2
        tls.load_cert_chain(certfile=str(cls.ca_file), keyfile=str(cls.key_file))
        cls.server.socket = tls.wrap_socket(cls.server.socket, server_side=True)
        cls.thread = threading.Thread(
            target=cls.server.serve_forever, daemon=True,
            name="identity-disposable-https-fixture",
        )
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)
        cls.temp.cleanup()

    def setUp(self):
        self.origin = f"https://localhost:{self.server.server_port}"
        self.issuer = self.origin + "/realms/ci"
        self.jwks = self.issuer + "/protocol/openid-connect/certs"
        self.api = self.origin + "/v0/me/contexts"
        self.metadata = self.issuer + "/.well-known/openid-configuration"
        self.server.calls = []
        self.metadata_data = {
            "issuer": self.issuer,
            "jwks_uri": self.jwks,
            "authorization_endpoint": self.issuer + "/protocol/openid-connect/auth",
            "token_endpoint": self.issuer + "/protocol/openid-connect/token",
            "response_types_supported": ["code"],
            "code_challenge_methods_supported": ["S256"],
        }
        self.server.routes = {
            "/v0/me/contexts": (200, json.dumps(RESPONSE).encode("utf-8"),
                                "application/json", {}),
            "/realms/ci/.well-known/openid-configuration":
                (200, json.dumps(self.metadata_data).encode("utf-8"),
                 "application/json", {}),
            "/realms/ci/protocol/openid-connect/certs":
                (200, b'{"keys":[]}', "application/json", {}),
        }

    def client(self, **overrides):
        settings = {
            "issuer": self.issuer, "jwks_url": self.jwks,
            "context_url": self.api, "timeout_seconds": 2,
            "ca_bundle": self.ca_file,
        }
        settings.update(overrides)
        return HostPinnedHttpsTransport(PinnedIdentityHttpsConfig(**settings))

    def test_constructor_is_inert_and_ca_is_private_to_trusted_host(self):
        client = self.client()
        self.assertEqual(self.server.calls, [])
        self.assertEqual(client._config.metadata_url, self.metadata)
        self.assertEqual(self.server.calls, [])
        self.assertNotIn("authorization", vars(client))

    def test_real_tls_context_response_becomes_only_display_preview(self):
        client = self.client()
        reply = client.get_contexts(TOKEN)
        self.assertEqual(type(reply), HostContextReply)
        self.assertEqual(reply.status_code, 200)
        self.assertEqual(reply.content_type, "application/json")
        self.assertEqual(self.server.calls[0]["path"], "/v0/me/contexts")
        self.assertEqual(self.server.calls[0]["authorization"], "Bearer " + TOKEN)
        self.assertEqual(self.server.calls[0]["accept_encoding"], "identity")
        projection = DesktopContextProjection(
            host_fetch=lambda: client.get_contexts(TOKEN), clock=lambda: NOW,
        )
        view = projection.refresh()
        self.assertEqual(view["status"], "READY")
        self.assertEqual(view["organizations"][0]["organizationId"], "llc_test")
        self.assertEqual(view["organizations"][0]["scopeGrants"][0]["action"],
                         "records.read")
        self.assertFalse(view["canSwitchOrganization"])
        for needle in (TOKEN, "Authorization", "sessionId", "subject", "role"):
            self.assertNotIn(needle, json.dumps(view))

    def test_host_only_metadata_and_jwks_fetch_have_no_bearer(self):
        client = self.client()
        self.assertEqual(client.fetch_json(self.metadata), self.metadata_data)
        self.assertEqual(client.fetch_json(self.jwks), {"keys": []})
        self.assertEqual(len(self.server.calls), 2)
        self.assertTrue(all(x["authorization"] is None for x in self.server.calls))
        for untrusted in (
            self.origin + "/anything",
            self.api, self.origin + "/admin",
            self.metadata + "?tenant=other",
            self.jwks.replace("localhost", "127.0.0.1"),
        ):
            with self.subTest(url=untrusted):
                with self.assertRaises(ValueError):
                    client.fetch_json(untrusted)
        self.assertEqual(len(self.server.calls), 2)

    def test_redirect_is_never_followed_and_server_body_never_returns(self):
        self.server.routes["/v0/me/contexts"] = (
            302, b"PRIVATE-REDIRECT", "text/plain",
            {"Location": self.origin + "/admin"},
        )
        result = self.client().get_contexts(TOKEN)
        self.assertEqual(result.status_code, 503)
        self.assertNotIn(b"PRIVATE", result.body)
        self.assertEqual([x["path"] for x in self.server.calls], ["/v0/me/contexts"])

    def test_denied_status_is_sanitized_and_cannot_restore_context(self):
        for code in (401, 403):
            self.server.calls = []
            self.server.routes["/v0/me/contexts"] = (
                code, b'{"accessToken":"BAD_SECRET"}', "application/json", {},
            )
            res = self.client().get_contexts(TOKEN)
            self.assertEqual(res.status_code, code)
            self.assertEqual(res.body, b'{"status":"DENIED"}')

    def test_invalid_bearer_cannot_trigger_network(self):
        client = self.client()
        for value in (None, "", "bad token", "abc\nHeader:", "\x00", "x" * 8193):
            with self.subTest(value=repr(value)[:35]):
                self.assertEqual(client.get_contexts(value).status_code, 401)
        self.assertEqual(self.server.calls, [])

    def test_wrong_tls_root_or_hostname_cannot_succeed(self):
        self.assertEqual(
            self.client(ca_bundle=None).get_contexts(TOKEN).status_code, 503
        )
        other = self.origin.replace("localhost", "127.0.0.1")
        result = self.client(
            issuer=self.issuer.replace("localhost", "127.0.0.1"),
            jwks_url=self.jwks.replace("localhost", "127.0.0.1"),
            context_url=other + "/v0/me/contexts",
        ).get_contexts(TOKEN)
        self.assertEqual(result.status_code, 503)

    def test_content_type_encoding_empty_and_size_are_rejected(self):
        for body, typ, headers in (
            (b"{}", "text/plain", {}),
            (b"{}", "application/json", {"Content-Encoding": "gzip"}),
            (b"", "application/json", {}),
            (b"x" * 65537, "application/json", {}),
        ):
            with self.subTest(kind=(len(body), typ, headers)):
                self.server.routes["/v0/me/contexts"] = (200, body, typ, headers)
                result = self.client().get_contexts(TOKEN)
                self.assertEqual(result.status_code, 503)
                self.assertEqual(result.body, b'{"status":"DENIED"}')

    def test_json_duplicate_keys_nonfinite_and_invalid_utf8_are_rejected(self):
        client = self.client()
        metadata_path = "/realms/ci/.well-known/openid-configuration"
        for content in (
            b'{"issuer":"x","issuer":"y"}',
            b'{"value":NaN}', b"\xff", b"[]", b"",
        ):
            with self.subTest(data=repr(content)[:30]):
                self.server.routes[metadata_path] = (
                    200, content, "application/json", {}
                )
                with self.assertRaises(ValueError):
                    client.fetch_json(self.metadata)

    def test_endpoint_validation_rejects_unsafe_host_and_protocol(self):
        candidates = [
            {"issuer": self.issuer.replace("https://", "http://")},
            {"context_url": self.api.replace("https://", "http://")},
            {"context_url": self.origin + "/v0/me/contexts?person=other"},
            {"context_url": self.origin + "/v0/me/contexts#trace"},
            {"context_url": self.origin + "/v0/me/contexts/"},
            {"context_url": self.origin + "/v0/me/context"},
            {"context_url": self.origin + "/../../v0/me/contexts"},
            {"context_url": "https://user:password@localhost/v0/me/contexts"},
            {"jwks_url": self.jwks.replace("localhost", "other.example")},
            {"issuer": self.issuer + "/"},
            {"context_url": self.origin + "/v0/me/%63ontexts"},
            {"timeout_seconds": 0},
            {"timeout_seconds": 11},
            {"ca_bundle": Path("relative-ca-file.pem")},
        ]
        for override in candidates:
            with self.subTest(config=override):
                with self.assertRaises(ValueError):
                    self.client(**override)
        self.assertEqual(self.server.calls, [])

    def test_host_only_caller_must_explicitly_approve_ca_and_network(self):
        self.assertEqual(self.server.calls, [])
        config = PinnedIdentityHttpsConfig(
            issuer=self.issuer, jwks_url=self.jwks,
            context_url=self.api, ca_bundle=self.ca_file,
        )
        HostPinnedHttpsTransport(config)
        self.assertEqual(self.server.calls, [])
        bad_config = self.ca_file.parent / "link.pem"
        bad_config.symlink_to(self.ca_file)
        try:
            with self.assertRaises(ValueError):
                PinnedIdentityHttpsConfig(
                    issuer=self.issuer, jwks_url=self.jwks,
                    context_url=self.api, ca_bundle=bad_config,
                )
        finally:
            bad_config.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
