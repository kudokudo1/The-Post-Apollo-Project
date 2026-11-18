"""Actual TLS 1.3 iPhone-only ingress and separate loopback operator HTTP tests.

All sockets and certs are CI/temp-local, with no host deployment, iPhone
credential, network listener installation, Apple app or production connection.
"""
from __future__ import annotations

from http.client import RemoteDisconnected
import importlib
import json
from pathlib import Path
import shutil
import ssl
import subprocess
import sys
import tempfile
import threading
import unittest
from urllib.error import HTTPError, URLError
from urllib.request import HTTPSHandler, Request, build_opener, urlopen

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "phone"))
Gate = importlib.import_module("PhoneFaceTimeShortcutHttps")
RelayMod = importlib.import_module("PhoneFaceTimeShortcutRelay")
ADMIN = "A" * 48
PHONE = "B" * 48


def test_certificate(tmp: Path):
    if shutil.which("openssl") is None:
        raise RuntimeError("openssl required for HTTPS test certificate")
    cert, key = tmp / "cert.pem", tmp / "key.pem"
    subprocess.run([
        "openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes",
        "-keyout", str(key), "-out", str(cert), "-days", "1",
        "-subj", "/CN=localhost",
        "-addext", "subjectAltName=IP:127.0.0.1",
    ], capture_output=True, check=True, timeout=12)
    key.chmod(0o600)
    return cert, key


class TestHttpsIsolation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.cert, cls.key = test_certificate(Path(cls.tmp.name))
        cls.context = Gate._tls_context(str(cls.cert), str(cls.key))

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def setUp(self):
        self.relay = RelayMod.Relay(ADMIN, PHONE)
        self.operator = RelayMod._LoopbackOnly(("127.0.0.1", 0), self.relay)
        self.iphone = Gate._PrivateIphoneHTTPSServer(
            "127.0.0.1", 0, self.relay, self.context, "127.0.0.1",
            allow_test_loopback=True)
        self.threads = [
            threading.Thread(target=server.serve_forever, daemon=True)
            for server in (self.operator, self.iphone)
        ]
        for th in self.threads:
            th.start()
        self.http_base = "http://127.0.0.1:" + str(self.operator.server_port)
        self.https_base = "https://127.0.0.1:" + str(self.iphone.server_port)
        # CI tests exercise exact SAN validation with their ephemeral CA.
        ca = ssl.create_default_context(cafile=str(self.cert))
        self.opener = build_opener(HTTPSHandler(context=ca))

    def tearDown(self):
        for server in (self.operator, self.iphone):
            server.shutdown()
        for th in self.threads:
            th.join(timeout=3)
        for server in (self.operator, self.iphone):
            server.server_close()

    def req(self, *, phone: bool, method: str, path: str,
            token: str | None, value: dict | bytes | None = None):
        headers = {"Accept": "application/json"}
        if token:
            headers["Authorization"] = "Bearer " + token
        body = None
        if value is not None:
            if isinstance(value, dict):
                body = json.dumps(value).encode()
                headers["Content-Type"] = "application/json"
            else:
                body = value
                headers["Content-Type"] = "application/json"
        elif method == "POST":
            body = b""
        address = (self.https_base if phone else self.http_base) + path
        request = Request(address, headers=headers, method=method, data=body)
        handler = self.opener if phone else None
        try:
            res = handler.open(request, timeout=3) if phone else urlopen(request, timeout=3)
            with res:
                return res.status, json.load(res), dict(res.headers)
        except HTTPError as e:
            return e.code, json.load(e), dict(e.headers)

    def test_real_https_phone_and_http_operator_end_to_end(self):
        status, body, headers = self.req(
            phone=False, method="POST", path="/v1/operator/request",
            token=ADMIN,
            value={"mode": "audio", "target": "+15551234567"})
        self.assertEqual((status, body["state"]), (200, "QUEUED"))
        self.assertEqual(headers["Cache-Control"], "no-store")
        self.assertNotIn("+15551234567", str(body))
        status, item, headers = self.req(
            phone=True, method="GET", path="/v1/iphone/next", token=PHONE)
        self.assertEqual(status, 200)
        self.assertEqual(item["faceTimeUri"], "facetime-audio:+15551234567")
        self.assertFalse(item["faceTimeConnected"])
        self.assertEqual(headers["Cache-Control"], "no-store")
        rid = item["requestId"]
        self.assertEqual(self.req(
            phone=True, method="GET", path="/v1/iphone/next",
            token=PHONE)[1]["state"], "NONE")
        status, result, _ = self.req(
            phone=True, method="POST", path="/v1/iphone/ack", token=PHONE,
            value={"requestId": rid, "event": "OPEN_URL_REQUESTED"})
        self.assertEqual((status, result["state"]),
                         (200, "PHONE_REPORTED_OPEN_REQUEST"))
        self.assertFalse(result["faceTimeConnected"])
        self.assertTrue(result["iphoneWorkflowReportedRequest"])
        operator = self.req(
            phone=False, method="GET", path="/v1/operator/status",
            token=ADMIN)[1]
        self.assertEqual(operator["state"], "PHONE_REPORTED_OPEN_REQUEST")
        self.assertNotIn("faceTimeUri", str(operator))
        self.assertNotIn(rid, str(operator))
        self.assertNotIn("+15551234567", str(operator))

    def test_admin_routes_cannot_be_reached_on_iphone_https(self):
        for method, path, payload in (
            ("GET", "/v1/operator/status", None),
            ("POST", "/v1/operator/request",
             {"mode": "audio", "target": "+15551234567"}),
            ("POST", "/v1/operator/cancel", None),
            ("GET", "/v1/operator/status?secret=x", None),
            ("GET", "/v1/iphone/next?force=yes", None),
            ("POST", "/v1/iphone/ack?extra=yes", {}),
        ):
            for token in (ADMIN, PHONE, None):
                with self.subTest(method=method, path=path, token=token):
                    code, result, _ = self.req(
                        phone=True, method=method,
                        path=path, token=token, value=payload)
                    self.assertEqual(code, 404)
                    self.assertEqual(result["state"], "REFUSED")
        self.assertEqual(self.relay.status()["state"], "EMPTY")
        self.assertEqual(self.req(
            phone=True, method="OPTIONS", path="/v1/iphone/next",
            token=PHONE)[0], 405)

    def test_phone_routes_need_iphone_not_operator_token(self):
        for role in (None, ADMIN, "bad" * 22):
            code, body, _ = self.req(
                phone=True, method="GET", path="/v1/iphone/next",
                token=role)
            self.assertEqual(code, 403)
            self.assertNotIn("faceTimeUri", body)
        status, body, _ = self.req(
            phone=True, method="POST", path="/v1/iphone/ack",
            token=PHONE, value={"requestId": "A" * 24, "event": "CONNECTED"})
        self.assertEqual((status, body["state"]), (409, "REFUSED"))

    def test_default_tls_client_refuses_untrusted_certificate(self):
        with self.assertRaises((ssl.SSLError, URLError, OSError)):
            urlopen(self.https_base + "/v1/iphone/next", timeout=2)

    def test_plain_http_is_not_accepted_on_https_port(self):
        with self.assertRaises((RemoteDisconnected, ConnectionError,
                                URLError, OSError)):
            urlopen("http://127.0.0.1:" + str(self.iphone.server_port)
                    + "/v1/iphone/next", timeout=2)


class TestNoUnapprovedDeployment(unittest.TestCase):
    def test_explicit_private_addresses_only(self):
        for good in ("10.10.0.2", "172.16.10.2", "172.31.255.254",
                     "192.168.10.23"):
            self.assertEqual(Gate._safe_address(good), good)
        for bad in ("0.0.0.0", "127.0.0.1", "8.8.8.8",
                    "169.254.1.2", "100.64.0.1", "::1",
                    "example.com", "192.168.1.1/24", None, 123):
            with self.subTest(ip=bad), self.assertRaises(ValueError):
                Gate._safe_address(bad)
        self.assertEqual(Gate._safe_address(
            "127.0.0.1", allow_loopback=True), "127.0.0.1")

    def test_key_permissions_and_symlink(self):
        with tempfile.TemporaryDirectory() as folder:
            cert, key = test_certificate(Path(folder))
            self.assertIsInstance(Gate._tls_context(
                str(cert), str(key)), ssl.SSLContext)
            key.chmod(0o644)
            with self.assertRaises(ValueError):
                Gate._tls_context(str(cert), str(key))
            key.chmod(0o600)
            bad = Path(folder) / "key-link.pem"
            bad.symlink_to(key)
            with self.assertRaises(ValueError):
                Gate._tls_context(str(cert), str(bad))
            with self.assertRaises(ValueError):
                Gate._tls_context(str(Path(folder) / "missing"), str(key))

    def test_no_entrypoint_auto_starts_network(self):
        self.assertEqual(Gate.main([]), 2)
        self.assertEqual(Gate.main(["--serve-iphone-https"]), 2)
        self.assertEqual(Gate.main([
            "--serve-iphone-https", "--acknowledge-private-lan-exposure",
            "--phone-bind", "0.0.0.0", "--phone-port", "8124",
            "--operator-port", "8123", "--iphone-client-ip", "192.168.1.20",
        ]), 2)

    def test_operator_credential_unusable_on_phone_route(self):
        src = (ROOT / "services/phone/PhoneFaceTimeShortcutHttps.py").read_text()
        for needed in (
            "ssl.TLSVersion.TLSv1_3", '"127.0.0.1"',
            '"/v1/iphone/next"', '"/v1/iphone/ack"',
            "class _PhoneOnlyHandler", "class _PrivateIphoneHTTPSServer",
            "--acknowledge-private-lan-exposure",
            "_load_token", "OSError", "self._permitted_client",
        ):
            self.assertIn(needed, src)
        for forbidden in (
            "Calls1.Dial", "FaceTimeCallControl", "ListNotifications",
            "systemctl", "pactl", "bluetoothctl", "subprocess",
            "0.0.0.0/0", "wss://", "allow_origin", "SecretService",
            "Qt.openUrlExternally",
        ):
            self.assertNotIn(forbidden, src)


if __name__ == "__main__":
    unittest.main()
