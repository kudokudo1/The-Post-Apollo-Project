"""FaceTime iPhone-only relay: real loopback HTTP exchange, no Apple controls."""
from __future__ import annotations

import importlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "phone"))
RelayModule = importlib.import_module("PhoneFaceTimeShortcutRelay")
Operator = importlib.import_module("PhoneFaceTimeShortcutOperator")
SRC = (ROOT / "services/phone/PhoneFaceTimeShortcutRelay.py").read_text()

ADMIN = "A" * 48
IPHONE = "B" * 48


class TestRelayStateMachine(unittest.TestCase):
    def setUp(self):
        self.now = [100]
        self.relay = RelayModule.Relay(
            ADMIN, IPHONE, clock=lambda: self.now[0],
            new_id=lambda n: "AbCdEfGhIjKlMnOpQrStUvWxYz_01",
        )

    def assert_denials(self, result):
        self.assertEqual(result["schema"], RelayModule.SCHEMA)
        self.assertIn(result["state"], RelayModule.STATES)
        for key in (
            "faceTimeConnected", "incomingCallObserved", "canAnswer",
            "canHangup", "audioVerified", "videoStreamAvailable",
            "authenticatedAppleFaceTimeSession", "personalDataAccess",
        ):
            self.assertIs(result[key], False, key)
        self.assertNotIn("+15551234567", str(result))
        self.assertNotIn("person@example.test", str(result))
        self.assertNotIn("requestId", result)
        self.assertNotIn("faceTimeUri", result)

    def test_audio_lifecycle_claim_ack_no_call_proof(self):
        self.assertTrue(self.relay.prepare({"mode": "audio", "target": "+15551234567"}))
        self.assert_denials(self.relay.status())
        self.assertEqual(self.relay.status()["state"], "QUEUED")
        self.assertFalse(self.relay.prepare({"mode": "video", "target": "other@example.test"}))
        command = self.relay.claim()
        self.assertEqual(command["faceTimeUri"], "facetime-audio:+15551234567")
        self.assertEqual(command["state"], "DELIVERED_TO_SHORTCUT")
        self.assertFalse(command["faceTimeConnected"])
        rid = command["requestId"]
        self.assertEqual(self.relay.claim()["state"], "NONE",
                         "second claim must never redeliver URI")
        self.assertFalse(self.relay.acknowledge({"requestId": rid, "event": "CONNECTED"}))
        self.assertFalse(self.relay.acknowledge({"requestId": "Z" * len(rid),
                                                 "event": "OPEN_URL_REQUESTED"}))
        self.assertTrue(self.relay.acknowledge(
            {"requestId": rid, "event": "OPEN_URL_REQUESTED"}))
        self.assert_denials(self.relay.status())
        self.assertTrue(self.relay.status()["iphoneWorkflowReportedRequest"])
        self.assertEqual(self.relay.status()["state"], "PHONE_REPORTED_OPEN_REQUEST")
        self.assertEqual(self.relay._request.target, "",
                         "recipient erased after terminal phone report")
        self.assertFalse(self.relay.acknowledge(
            {"requestId": rid, "event": "OPEN_URL_REQUESTED"}))
        self.assertEqual(self.relay.claim()["state"], "NONE")
        self.assertTrue(self.relay.prepare({"mode": "video", "target": "person@example.test"}))
        self.assertEqual(self.relay.claim()["faceTimeUri"],
                         "facetime:person@example.test")

    def test_decline_cancel_and_expiry_are_terminal(self):
        self.assertTrue(self.relay.prepare({"mode": "video", "target": "+15551234567"}))
        self.assertTrue(self.relay.cancel())
        self.assertEqual(self.relay._request.target, "")
        self.assertFalse(self.relay.cancel())
        self.assertEqual(self.relay.claim()["state"], "NONE")
        self.assertTrue(self.relay.prepare({"mode": "video", "target": "+15551234567"}))
        rid = self.relay.claim()["requestId"]
        self.assertTrue(self.relay.acknowledge({"requestId": rid, "event": "DECLINED"}))
        self.assertEqual(self.relay.status()["state"], "PHONE_DECLINED")
        self.assertFalse(self.relay.acknowledge({"requestId": rid, "event": "DECLINED"}))
        self.assertTrue(self.relay.prepare({"mode": "audio", "target": "+15551234567"}))
        self.now[0] += RelayModule.REQUEST_TTL_SECONDS
        self.assertEqual(self.relay.status()["state"], "EXPIRED")
        self.assertEqual(self.relay._request.target, "")
        self.assert_denials(self.relay.status())
        self.assertEqual(self.relay.claim()["state"], "NONE")
        self.assertFalse(self.relay.acknowledge(
            {"requestId": "AbCdEfGhIjKlMnOpQrStUvWxYz_01", "event": "DECLINED"}))

    def test_strict_recipient_mode_syntax_no_uri_injection(self):
        for bad in (
            None, True, "15551234567", "+01234567", "+12", "+" + "9" * 16,
            "person@example.test?x=1", "person@example.test#fragment",
            "person@example.test\nother", "javascript:alert(1)",
            "https://facetime.apple.com/join#token",
            "x" * 300, "[::1]", "a@b", "a@b..test",
        ):
            with self.subTest(bad=bad):
                self.assertFalse(self.relay.prepare({"mode": "audio", "target": bad}))
        for bad in (None, [], {}, "AUDIO", "ft audio", "audio\n"):
            with self.subTest(mode=bad):
                self.assertFalse(self.relay.prepare({
                    "mode": bad, "target": "+15551234567"}))
        self.assertFalse(self.relay.prepare({
            "mode": "audio", "target": "+15551234567", "untrusted": True}))

    def test_typed_forged_ack_refused(self):
        self.assertTrue(self.relay.prepare({"mode": "video", "target": "+15551234567"}))
        rid = self.relay.claim()["requestId"]
        for raw in (
            None, {}, {"requestId": rid}, {"requestId": rid, "event": 1},
            {"requestId": rid, "event": "OPEN_URL_REQUESTED", "done": True},
            {"requestId": [], "event": "OPEN_URL_REQUESTED"},
            {"requestId": rid, "event": "answered"},
        ):
            with self.subTest(value=str(raw)[:70]):
                self.assertFalse(self.relay.acknowledge(raw))
        self.assertEqual(self.relay.status()["state"], "DELIVERED_TO_SHORTCUT")

    def test_auth_roles_are_distinct_constant_time_and_not_based_on_iphone_status(self):
        self.assertTrue(self.relay.authorize("admin", "Bearer " + ADMIN))
        self.assertTrue(self.relay.authorize("phone", "Bearer " + IPHONE))
        for role, credential in (
            ("admin", IPHONE), ("phone", ADMIN), ("phone", "x" * 48),
            ("admin", ADMIN[:-1]), ("phone", IPHONE + "\n"),
            ("other", ADMIN), ("phone", None), ("admin", b"Bearer " + ADMIN.encode()),
        ):
            with self.subTest(role=role):
                self.assertFalse(self.relay.authorize(role, (
                    "Bearer " + credential if isinstance(credential, str) else credential)))
        for invalid in (("", IPHONE), (ADMIN, ADMIN), ("tiny", IPHONE)):
            with self.assertRaises(ValueError):
                RelayModule.Relay(*invalid)


class TestHttpRelay(unittest.TestCase):
    def setUp(self):
        self.relay = RelayModule.Relay(ADMIN, IPHONE)
        self.server = RelayModule._LoopbackOnly(("127.0.0.1", 0), self.relay)
        self.thread = threading.Thread(
            target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = "http://127.0.0.1:" + str(self.server.server_port)

    def tearDown(self):
        self.server.shutdown()
        self.thread.join(timeout=2)
        self.server.server_close()

    def request(self, method, path, token=None, payload=None, mime="application/json"):
        headers = {"Accept": "application/json"}
        if token is not None:
            headers["Authorization"] = "Bearer " + token
        if payload is not None:
            headers["Content-Type"] = mime
            if isinstance(payload, dict):
                data = json.dumps(payload).encode()
            else:
                data = payload
        elif method == "POST":
            data = b""
        else:
            data = None
        req = Request(self.base + path, method=method, headers=headers, data=data)
        try:
            with urlopen(req, timeout=3) as res:
                return res.status, json.load(res)
        except HTTPError as err:
            return err.code, json.load(err)

    def test_real_http_request_claim_ack_and_redacted_status(self):
        res = self.request("POST", "/v1/operator/request", ADMIN,
                           {"mode": "video", "target": "+15551234567"})
        self.assertEqual(res[0], 200)
        self.assertEqual(res[1]["state"], "QUEUED")
        self.assertNotIn("+15551234567", str(res[1]))
        for path in ("/v1/operator/status", "/v1/iphone/next"):
            self.assertEqual(self.request("GET", path)[0], 403)
        self.assertEqual(self.request("GET", "/v1/operator/status", IPHONE)[0], 403)
        self.assertEqual(self.request("GET", "/v1/iphone/next", ADMIN)[0], 403)
        status, cmd = self.request("GET", "/v1/iphone/next", IPHONE)
        self.assertEqual(status, 200)
        self.assertEqual(cmd["faceTimeUri"], "facetime:+15551234567")
        self.assertFalse(cmd["faceTimeConnected"])
        self.assertEqual(self.request("GET", "/v1/iphone/next", IPHONE)[1]["state"], "NONE")
        self.assertEqual(self.request("POST", "/v1/iphone/ack", ADMIN,
            {"requestId": cmd["requestId"], "event": "OPEN_URL_REQUESTED"})[0], 403)
        status, report = self.request("POST", "/v1/iphone/ack", IPHONE,
            {"requestId": cmd["requestId"], "event": "OPEN_URL_REQUESTED"})
        self.assertEqual(status, 200)
        self.assertEqual(report["state"], "PHONE_REPORTED_OPEN_REQUEST")
        self.assertNotIn("+15551234567", str(report))
        self.assertFalse(report["faceTimeConnected"])
        self.assertEqual(self.request("POST", "/v1/iphone/ack", IPHONE,
            {"requestId": cmd["requestId"], "event": "OPEN_URL_REQUESTED"})[0], 409)

    def test_http_methods_bodies_and_unknown_paths_fail_closed(self):
        self.assertEqual(self.request("GET", "/v1/operator/status?leak=1", ADMIN)[0], 404)
        self.assertEqual(self.request("GET", "/v1/iphone/next/../", IPHONE)[0], 404)
        self.assertEqual(self.request("OPTIONS", "/v1/iphone/next", IPHONE)[0], 405)
        self.assertEqual(self.request("POST", "/v1/operator/request", ADMIN,
                         b'{"mode":"audio","target":"+15551234567"}',
                         mime="text/plain")[0], 400)
        self.assertEqual(self.request("POST", "/v1/operator/request", ADMIN,
                         b"{" + b"x" * 600 + b"}")[0], 400)
        self.assertEqual(self.request("POST", "/v1/operator/request", ADMIN,
                         b'{"mode":"audio","target":"javascript:alert(1)"}')[0], 409)
        self.assertEqual(self.request("POST", "/v1/operator/cancel", IPHONE)[0], 403)
        self.assertEqual(self.request("GET", "/v1/operator/status", ADMIN)[1]["state"], "EMPTY")

    def test_actual_local_operator_client_queues_checks_and_cancels(self):
        port = self.server.server_port
        invalid = Operator.request("queue-audio", ADMIN, port,
                                   recipient="+15551234567", approved=False)
        self.assertEqual(invalid["state"], "REFUSED")
        self.assertEqual(self.relay.status()["state"], "EMPTY")
        queued = Operator.request("queue-audio", ADMIN, port,
                                  recipient="+15551234567", approved=True)
        self.assertEqual(queued["state"], "QUEUED")
        self.assertFalse(queued["faceTimeConnected"])
        self.assertNotIn("+15551234567", str(queued))
        self.assertEqual(Operator.request("status", ADMIN, port)["state"], "QUEUED")
        self.assertEqual(Operator.request("status", IPHONE, port)["state"], "UNAVAILABLE")
        self.assertEqual(Operator.request("cancel", ADMIN, port)["state"], "CANCELLED")
        self.assertEqual(Operator.request("status", ADMIN, port)["state"], "CANCELLED")
        self.assertEqual(self.request("GET", "/v1/iphone/next", IPHONE)[1]["state"], "NONE")
        for target in ("15551234567", "javascript:alert(1)", "bad\\nrecipient"):
            self.assertEqual(Operator.request("queue-video", ADMIN, port,
                             recipient=target, approved=True)["state"], "REFUSED")
        self.assertEqual(Operator.request("status", ADMIN, 0)["state"], "REFUSED")

    def test_only_loopback_can_bind(self):
        with self.assertRaises(ValueError):
            RelayModule._LoopbackOnly(("0.0.0.0", 0), self.relay)
        with self.assertRaises(ValueError):
            RelayModule._LoopbackOnly(("192.168.1.2", 0), self.relay)


class TestCredentialSafety(unittest.TestCase):
    def test_permissions_and_symlink_refusal(self):
        with tempfile.TemporaryDirectory() as tmp:
            good = Path(tmp) / "admin"
            good.write_text(ADMIN + "\n")
            good.chmod(0o600)
            self.assertEqual(RelayModule._load_token(str(good)), ADMIN)
            good.chmod(0o644)
            with self.assertRaises(ValueError):
                RelayModule._load_token(str(good))
            good.chmod(0o600)
            link = Path(tmp) / "symbolic"
            link.symlink_to(good)
            with self.assertRaises(ValueError):
                RelayModule._load_token(str(link))
        self.assertEqual(RelayModule.main([]), 2)
        self.assertEqual(RelayModule.main(["--serve", "--port", "8123"]), 2)

    def test_operator_client_never_hands_credentials_to_redirect_or_argv(self):
        code = (ROOT / "services/phone/PhoneFaceTimeShortcutOperator.py").read_text()
        for required in (
            "class _NoRedirect", "redirect_request", "getpass.getpass",
            'Type PREPARE', "http://127.0.0.1:",
            "faceTimeConnected", "PhoneFaceTimeShortcutRelay",
        ):
            if required == 'Type PREPARE':
                self.assertIn('Type PREPARE:', code)
            else:
                self.assertIn(required, code)
        for bad in (
            '("--target"', "'--target'", "print(recipient)",
            "print(token)", "systemctl", "Qt.openUrlExternally",
            "https://facetime.apple.com", "shell=True",
        ):
            self.assertNotIn(bad, code)

    def test_forbidden_operations_absent_from_process(self):
        for bad in (
            "Qt.openUrlExternally", "ListNotifications", "ListCalls",
            "GetContact", "FaceTimeCallControl", "Dial(", "Answer(",
            "Hangup(", "systemctl", "bluetoothctl", "pactl",
            "subprocess", "socket.create_connection",
            "requests.post", "input(", "http://0.0.0.0",
        ):
            self.assertNotIn(bad, SRC)


if __name__ == "__main__":
    unittest.main()
