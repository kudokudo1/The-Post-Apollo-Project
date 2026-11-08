"""S2: actual separate Linux requester, reviewer and fake-provider host processes.

Uses S1 fake sign-out, C5b SO_PASSCRED/SCM_CREDENTIALS helpers and Unix
SOCK_SEQPACKET. No Telethon, network, account credentials, real session files,
production host install or user consent. Runs only in disposable nonroot CI.
"""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "tests/messaging/fixtures/telegram_session_revocation_s2.py"
def fixed_import(file, name):
    spec = importlib.util.spec_from_file_location(name, file)
    assert spec and spec.loader
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m

S2 = fixed_import(FIXTURE, "telegram_s2_test")
S1 = S2.S1
C5A = S2.C5A


@unittest.skipUnless(sys.platform == "linux" and os.geteuid() != 0,
                     "requires disposable nonroot Linux process credentials")
class TelegramS2Transport(unittest.TestCase):
    def setUp(self):
        self.env = dict(os.environ, GITHUB_ACTIONS="true",
                        POST_APOLLO_TELEGRAM_S2_DISPOSABLE=S2.MARKER)
        self.operator, reviewer_host = socket.socketpair(
            socket.AF_UNIX, socket.SOCK_SEQPACKET)
        self.requester_peer, requester_host = socket.socketpair(
            socket.AF_UNIX, socket.SOCK_SEQPACKET)
        self.operator.settimeout(8)
        self.requester_peer.settimeout(8)
        self.host = subprocess.Popen(
            [sys.executable, str(FIXTURE), "--host",
             str(reviewer_host.fileno()), str(requester_host.fileno()),
             str(os.getpid()), str(os.geteuid()), str(os.getegid()),
             str(S2.C5B.process_start_ticks(os.getpid()))],
            pass_fds=(reviewer_host.fileno(), requester_host.fileno()),
            env=self.env, stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        reviewer_host.close()
        requester_host.close()
        self.client = subprocess.Popen(
            [sys.executable, str(FIXTURE), "--client",
             str(self.requester_peer.fileno())],
            pass_fds=(self.requester_peer.fileno(),), env=self.env,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, bufsize=1)
        self.track = [self.host, self.client]
        self.addCleanup(self.cleanup)
        bound = self.reviewer({
            "op": "bind", "pid": self.client.pid,
            "uid": os.geteuid(), "gid": os.getegid()
        })
        self.assertEqual(bound["status"],
                         "SYNTHETIC_KERNEL_SENDER_BOUND_NO_REAL_GRANT")
        self.assertFalse(bound["callerAuthenticated"])

    def cleanup(self):
        try:
            if self.host.poll() is None:
                self.reviewer({"op": "shutdown"})
        except Exception:
            pass
        for p in reversed(getattr(self, "track", [])):
            if p.poll() is None:
                p.terminate()
            try:
                p.communicate(timeout=3)
            except subprocess.TimeoutExpired:
                p.kill()
                p.communicate(timeout=3)
        for sock in ("operator", "requester_peer"):
            try:
                getattr(self, sock).close()
            except (AttributeError, OSError):
                pass

    def reviewer(self, obj, sock=None):
        sock = sock or self.operator
        S2.credential_frame(sock, obj)
        return C5A.receive(sock)

    def client_request(self, obj):
        self.client.stdin.write(json.dumps(obj) + "\n")
        self.client.stdin.flush()
        raw = self.client.stdout.readline()
        if not raw:
            client_status = self.client.poll()
            host_status = self.host.poll()
            details = {
                "clientStatus": client_status, "hostStatus": host_status,
                "clientError": self.client.stderr.read() if client_status is not None else "still running",
                "hostError": self.host.stderr.read() if host_status is not None else "still running",
            }
            self.fail("EMPTY_CLIENT_RESPONSE " + repr(details))
        return json.loads(raw)

    @staticmethod
    def request(target="shared", identity=""):
        return {"op": "prepare", "scope": S1.OPERATION,
                "operation": "log_out", "target": target, "identity": identity}

    @staticmethod
    def approve(rid, target="shared", identity="", **override):
        return {
            "op": "approve", "requestId": rid, "scope": S1.OPERATION,
            "operation": "log_out", "target": target, "identity": identity,
            "confirmRemoteRevocation": True, "confirmLocalSessionLoss": True,
            **override
        }

    @staticmethod
    def execute(rid, target="shared", identity="", **override):
        return {"op": "execute", "requestId": rid, "scope": S1.OPERATION,
                "operation": "log_out", "target": target, "identity": identity,
                **override}

    def denied_power(self, packet):
        for key in S1.DENY:
            self.assertIs(packet[key], False, key)
        for secret in (".session", "fake-session-", "identity-1", "access_token",
                       "apiHash", "personal.session"):
            self.assertNotIn(secret, json.dumps(packet))

    def test_two_process_review_and_exact_one_use_fake_provider_logout(self):
        req = self.client_request(self.request())
        rid = req["requestId"]
        self.assertEqual(req["status"], "SYNTHETIC_REVIEW_REQUIRED_NO_GRANT")
        self.denied_power(req)
        self.assertEqual(self.client_request(self.execute(rid))["status"],
                         "NOT_APPROVED_OR_REPLAYED")
        # A requesting process cannot self-approve through its own FD.
        self.assertEqual(self.client_request(self.approve(rid))["status"],
                         "CLIENT_CANNOT_REVIEW_OR_ADMINISTER")
        approval = self.reviewer(self.approve(rid))
        self.assertEqual(approval["status"], "SYNTHETIC_REVIEW_ACCEPTED_NO_REAL_GRANT")
        self.denied_power(approval)
        ok = self.client_request(self.execute(rid))
        self.assertEqual(ok["status"], "SYNTHETIC_TELETHON_ACK_AND_LOCAL_STATUS_ONLY")
        self.assertTrue(ok["syntheticStepAccepted"])
        self.denied_power(ok)
        self.assertEqual(self.client_request(self.execute(rid))["status"],
                         "NOT_APPROVED_OR_REPLAYED")

    def test_shared_private_mismatch_and_two_consequence_review(self):
        prepared = self.client_request(self.request("private", "identity-1"))
        rid = prepared["requestId"]
        self.assertEqual(self.reviewer(self.approve(
            rid, "private", "identity-1",
            confirmLocalSessionLoss=False))["status"], "SYNTHETIC_REVIEW_REFUSED")
        self.assertEqual(self.reviewer(self.approve(
            rid, "shared", ""))["status"], "SYNTHETIC_REVIEW_REFUSED")
        self.assertEqual(self.client_request(
            self.execute(rid, "shared", ""))["status"], "REQUEST_BINDING_CHANGED")
        self.assertEqual(self.reviewer(self.approve(
            rid, "private", "identity-1"))["status"],
            "SYNTHETIC_REVIEW_ACCEPTED_NO_REAL_GRANT")
        self.assertEqual(self.client_request(
            self.execute(rid, "private", "identity-1"))["status"],
            "SYNTHETIC_TELETHON_ACK_AND_LOCAL_STATUS_ONLY")

    def test_wrong_sender_forwarded_client_fd_fails_even_same_uid(self):
        # Parent retained a copy of the child's client socket only for this
        # malicious-forwarded-FD test; packet origin must be the bound child.
        unauth = self.reviewer(self.request(), sock=self.requester_peer)
        self.assertEqual(unauth["status"], "CALLER_NOT_BOUND_OR_SENDER_CHANGED")
        self.denied_power(unauth)
        self.assertEqual(self.client_request(self.request())["status"],
                         "SYNTHETIC_REVIEW_REQUIRED_NO_GRANT")

    def test_transferred_reviewer_fd_fails_sender_credential_check(self):
        # A non-reviewer process intentionally receives the reviewer endpoint.
        # SO_PEERCRED alone sees its original creator; SCM_CREDENTIALS must
        # reject the actual new sender at the host on every packet.
        rogue = subprocess.Popen(
            [sys.executable, str(FIXTURE), "--client",
             str(self.operator.fileno())],
            pass_fds=(self.operator.fileno(),), env=self.env,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, bufsize=1)
        self.track.append(rogue)
        rogue.stdin.write(json.dumps({"op": "revoke"})+"\n")
        rogue.stdin.flush()
        result = json.loads(rogue.stdout.readline())
        self.assertEqual(result["status"], "REVIEWER_ORIGIN_MISMATCH")
        self.denied_power(result)
        req = self.client_request(self.request())
        rid = req["requestId"]
        self.assertEqual(self.reviewer(self.approve(rid))["status"],
                         "SYNTHETIC_REVIEW_ACCEPTED_NO_REAL_GRANT")
        self.assertEqual(self.client_request(self.execute(rid))["status"],
                         "SYNTHETIC_TELETHON_ACK_AND_LOCAL_STATUS_ONLY")

    def test_stale_provider_receipt_and_revoked_review_fail_without_logout(self):
        rid = self.client_request(self.request())["requestId"]
        self.assertEqual(self.reviewer({"op": "invalidate", "target": "shared",
                                        "identity": ""})["status"], "SYNTHETIC_SOURCE_CHANGED")
        self.assertEqual(self.reviewer(self.approve(rid))["status"],
                         "SESSION_CHANGED_BEFORE_REVIEW")
        self.assertEqual(self.client_request(self.execute(rid))["status"],
                         "NOT_APPROVED_OR_REPLAYED")
        rid = self.client_request(self.request())["requestId"]
        self.assertEqual(self.reviewer(self.approve(rid))["status"],
                         "SYNTHETIC_REVIEW_ACCEPTED_NO_REAL_GRANT")
        self.reviewer({"op": "revoke"})
        self.assertEqual(self.client_request(self.execute(rid))["status"],
                         "NOT_APPROVED_OR_REPLAYED")

    def test_provider_uncertainty_never_replays(self):
        rid = self.client_request(self.request())["requestId"]
        self.reviewer(self.approve(rid))
        self.reviewer({"op": "failProvider"})
        fail = self.client_request(self.execute(rid))
        self.assertEqual(fail["status"], "PROVIDER_RESULT_UNKNOWN_MANUAL_RECHECK_REQUIRED")
        self.denied_power(fail)
        self.assertEqual(self.client_request(self.execute(rid))["status"],
                         "NOT_APPROVED_OR_REPLAYED")

    def test_unbound_wrong_client_packet_and_production_host_remain_disabled(self):
        self.assertEqual(self.client_request({
            "op": "execute", "scope": S1.OPERATION, "operation": "log_out",
            "target": "shared", "identity": "", "requestId": "unknown",
            "approved": True})["status"], "INVALID_CLIENT_FIELDS")
        self.assertEqual(self.client_request({
            "op": "prepare", "scope": "tasks.draft.clear.encrypted",
            "operation": "log_out", "target": "shared", "identity": ""
        })["status"], "INVALID_OPERATION_OR_SCOPE")
        for path in (
            ROOT / "shell.qml",
            ROOT / "widgets/CpuPlusW.qml",
            ROOT / "widgets/messanger/MessagingW.qml",
            ROOT / "services/messaging/adapters/TelegramAdapter.qml",
            ROOT / "services/messaging/bridges/telegram/bridge.py",
            ROOT / "services/connections/ConnectionsBroker.qml",
        ):
            self.assertNotIn("telegram_session_revocation_s2", path.read_text())
        broker = (ROOT / "services/connections/ConnectionsBroker.qml").read_text()
        self.assertIn("readonly property bool credentialActionsEnabled: false", broker)
        details = (ROOT / "widgets/cpuplus/CpuPlusSettingsConnectionsDetailsPane.qml").read_text()
        self.assertNotIn('label: "DISCONNECT"', details)


if __name__ == "__main__":
    unittest.main()
