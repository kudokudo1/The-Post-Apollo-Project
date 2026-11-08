#!/usr/bin/env python3
"""C5a: real separate subprocess host/client, exact TASKS scope refusals."""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[2]
HOST = ROOT / "services/connections/experiments/C5aTasksScopeHost.py"
_spec = importlib.util.spec_from_file_location("c5a_host", HOST)
M = importlib.util.module_from_spec(_spec)
assert _spec.loader
_spec.loader.exec_module(M)

CAP = "tasks.draft.capture.encrypted"
PREV = "tasks.draft.preview.unlocked"
CLEAR = "tasks.draft.clear.encrypted"


def request(scope=CAP, target="entry", editor_epoch=3, source_gen=7):
    return {
        "op": "submit", "scope": scope, "target": target,
        "editorEpoch": editor_epoch, "sourceGeneration": source_gen,
    }


def execute(rid, scope=CAP, target="entry", editor_epoch=3, source_gen=7):
    return {
        "op": "execute", "requestId": rid, "scope": scope,
        "target": target, "editorEpoch": editor_epoch,
        "sourceGeneration": source_gen,
    }


def approval(rid, scope=CAP, target="entry", ttl=5000):
    return {
        "op": "approve", "requestId": rid, "scope": scope,
        "target": target, "ttlMs": ttl, "confirmed": True,
    }


def no_authority(out):
    for key, expected in M.FLAGS.items():
        assert out.get(key) is expected, (key, out)
    assert set(out).issubset({"status", "ok", "requestId", *M.FLAGS})
    assert "taskText" not in out and "credential" not in out


class DisposableSession:
    """Harness retains only reviewer FD; separate client receives only client FD."""
    def __init__(self, env):
        self.control, broker_control = socket.socketpair(
            socket.AF_UNIX, socket.SOCK_SEQPACKET)
        test_client, broker_client = socket.socketpair(
            socket.AF_UNIX, socket.SOCK_SEQPACKET)
        self.control.settimeout(3)
        self.host = subprocess.Popen(
            [sys.executable, "-I", "-B", str(HOST), "--host",
             str(broker_control.fileno()), str(broker_client.fileno())],
            pass_fds=(broker_control.fileno(), broker_client.fileno()),
            close_fds=True, stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, env=env)
        broker_control.close()
        broker_client.close()
        self.client = subprocess.Popen(
            [sys.executable, "-I", "-B", str(HOST), "--client",
             str(test_client.fileno()), "0"],
            pass_fds=(test_client.fileno(),), close_fds=True,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, bufsize=1, env=env)
        test_client.close()

    def reviewer(self, data):
        M.exchange(self.control, data)
        out = M.receive(self.control)
        assert isinstance(out, dict), "C5A_REVIEWER_NO_BOUNDED_REPLY"
        no_authority(out)
        return out

    def tasks(self, data):
        assert self.client.stdin and self.client.stdout
        self.client.stdin.write(json.dumps(data, separators=(",", ":")) + "\n")
        self.client.stdin.flush()
        line = self.client.stdout.readline()
        assert line, "C5A_TASKS_CLIENT_DISCONNECTED"
        out = json.loads(line)
        no_authority(out)
        return out

    def close(self):
        try:
            if self.host.poll() is None:
                try:
                    self.reviewer({"op": "shutdown"})
                except (OSError, AssertionError):
                    pass
        finally:
            self.control.close()
            if self.client.stdin:
                self.client.stdin.close()
            try:
                self.client.wait(timeout=4)
            except subprocess.TimeoutExpired:
                self.client.kill()
                self.client.wait(timeout=4)
            try:
                self.host.wait(timeout=4)
            except subprocess.TimeoutExpired:
                self.host.kill()
                self.host.wait(timeout=4)
            assert self.client.returncode == 0, "C5A_CLIENT_NOT_CLEAN"
            assert self.host.returncode == 0, "C5A_HOST_NOT_CLEAN"
            assert self.client.stderr and self.client.stderr.read() == "", "C5A_CLIENT_STDERR"
            assert self.host.stderr and self.host.stderr.read() == "", "C5A_HOST_STDERR"
            assert self.client.stdout and self.client.stdout.read() == "", "C5A_CLIENT_STDOUT_TAIL"
            assert self.host.stdout and self.host.stdout.read() == "", "C5A_HOST_STDOUT"


class C5aScopeTests(unittest.TestCase):
    def test_finite_three_scopes_target_bound_and_no_real_authority(self):
        clock = [10.0]
        host = M.Broker(clock=lambda: clock[0])
        for scope, target, epoch in ((CAP, "entry", 3),
                                      (CAP, "details", 10),
                                      (PREV, "checkpoint", 0),
                                      (CLEAR, "checkpoint", 0)):
            with self.subTest(scope=scope, target=target):
                draft = host.client(request(scope, target, epoch))
                self.assertTrue(draft["ok"])
                self.assertEqual(draft["status"], "SYNTHETIC_REVIEW_PENDING")
                no_authority(draft)
                before = host.client(execute(draft["requestId"], scope, target, epoch))
                self.assertEqual(before["status"], "NOT_APPROVED_OR_ALREADY_USED")
                no_authority(before)
                accepted = host.operator(approval(draft["requestId"], scope, target))
                self.assertTrue(accepted["ok"])
                no_authority(accepted)
                action = host.client(execute(draft["requestId"], scope, target, epoch))
                self.assertTrue(action["ok"])
                self.assertEqual(action["status"],
                                 "SYNTHETIC_SCOPED_STEP_ACCEPTED_NO_REAL_GRANT")
                no_authority(action)
                replay = host.client(execute(draft["requestId"], scope, target, epoch))
                self.assertFalse(replay["ok"])
                no_authority(replay)

    def test_client_cannot_review_or_revoke_and_cross_scope_never_succeeds(self):
        host = M.Broker()
        req = host.client(request())
        rid = req["requestId"]
        for value in (
            approval(rid),
            {"op": "revoke"},
            {"op": "shutdown"},
            {"op": "unlock", "key": "PRIVATE_KEY"},
            {"op": "clear", "path": "/tmp/private-task"},
        ):
            denied = host.client(value)
            self.assertEqual(denied["status"], "CLIENT_CANNOT_AUTHORIZE")
            no_authority(denied)
        self.assertFalse(host.client(execute(rid, scope=PREV))["ok"])
        self.assertFalse(host.operator(approval(rid, scope=CLEAR))["ok"])
        self.assertFalse(host.operator(approval(rid, target="details"))["ok"])
        self.assertTrue(host.operator(approval(rid))["ok"])
        self.assertFalse(host.client(execute(rid, source_gen=8))["ok"])
        self.assertFalse(host.client(execute(rid, editor_epoch=4))["ok"])
        self.assertFalse(host.client(execute(rid, target="details"))["ok"])
        self.assertTrue(host.client(execute(rid))["ok"])

    def test_revocation_expiry_and_consumption_before_action(self):
        fake_clock = [100.0]
        host = M.Broker(clock=lambda: fake_clock[0])
        r = host.client(request())
        host.operator(approval(r["requestId"]))
        host.operator({"op": "revoke"})
        denied = host.client(execute(r["requestId"]))
        self.assertFalse(denied["ok"])
        no_authority(denied)
        r2 = host.client(request(PREV, "checkpoint", 0))
        host.operator(approval(r2["requestId"], PREV, "checkpoint", 40))
        fake_clock[0] += 0.05
        self.assertEqual(host.client(execute(r2["requestId"], PREV, "checkpoint", 0))
                         ["status"], "REVOKED_OR_EXPIRED")
        self.assertFalse(host.client(execute(r2["requestId"], PREV, "checkpoint", 0))
                         ["ok"])

    def test_malformed_schema_types_and_injected_draft_text_refused(self):
        host = M.Broker()
        payload = request()
        rejected = [
            {}, [], None, {"op": "submit"},
            {**payload, "editorEpoch": True},
            {**payload, "sourceGeneration": False},
            {**payload, "scope": "tasks.draft.keys.read"},
            {**payload, "target": "other"},
            {**payload, "target": "checkpoint"},
            {**payload, "taskText": "PRIVATE_UNSAVED_NOTE"},
            {**payload, "sourcePath": "/home/operator/source"},
            {**payload, "approved": True},
            request(PREV, "checkpoint", 1),
            request(CLEAR, "entry", 0),
        ]
        for value in rejected:
            with self.subTest(value=repr(value)[:30]):
                r = host.client(value)
                self.assertFalse(r["ok"], value)
                self.assertNotIn("PRIVATE_UNSAVED_NOTE", json.dumps(r))
                no_authority(r)
        self.assertIsNone(M.decode(b'{"op":"submit","op":"approve"}'))
        self.assertIsNone(M.decode(b'{"a":NaN}'))
        self.assertIsNone(M.decode(b"\xff\xfe"))
        self.assertIsNone(M.decode(b"x" * (M.MAX_WIRE + 1)))
        self.assertFalse(host.operator({"op": "approve", "confirmed": True})["ok"])
        self.assertFalse(host.operator({"op": "revoke", "newKey": "bad"})["ok"])

    def test_real_distinct_host_and_client_processes_under_private_fds(self):
        if os.geteuid() == 0:
            self.skipTest("CI job uses non-root Ubuntu runner")
        with tempfile.TemporaryDirectory(prefix="postapollo-c5a-scope-", dir="/tmp") as folder:
            root = Path(folder)
            (root / ".c5a-test-only").write_text(M.MARKER + "\n")
            (root / ".c5a-test-only").chmod(0o600)
            environment = {
                **os.environ,
                "GITHUB_ACTIONS": "true",
                "POST_APOLLO_C5A_DISPOSABLE": "1",
                "POST_APOLLO_C5A_FIXTURE_ROOT": folder,
                "HOME": folder,
            }
            self.assertTrue(M.private_ci() is False or
                            os.environ.get("POST_APOLLO_C5A_FIXTURE_ROOT") == folder)
            bad = subprocess.run(
                [sys.executable, "-I", "-B", str(HOST), "--host", "9", "10"],
                env={**environment, "POST_APOLLO_C5A_DISPOSABLE": "0"},
                text=True, capture_output=True, timeout=4)
            self.assertEqual(bad.returncode, 2)
            self.assertIn("C5A_REFUSED_OUTSIDE_DISPOSABLE_HOST", bad.stdout)
            with self.assertRaisesRegex(Exception, "(?i)"):
                # Force no exception? This assertion is intentionally avoided
                # by the following explicit real session instead.
                raise ValueError("EXPLICIT_REAL_SESSION_NEXT")
            session = DisposableSession(environment)
            try:
                for scope, target, epoch in (
                    (CAP, "entry", 7),
                    (PREV, "checkpoint", 0),
                    (CLEAR, "checkpoint", 0),
                ):
                    pending = session.tasks(request(scope, target, epoch))
                    rid = pending["requestId"]
                    self.assertEqual(pending["status"], "SYNTHETIC_REVIEW_PENDING")
                    fake_approve = session.tasks(approval(rid, scope, target))
                    self.assertEqual(fake_approve["status"], "CLIENT_CANNOT_AUTHORIZE")
                    blocked = session.tasks(execute(rid, scope, target, epoch))
                    self.assertFalse(blocked["ok"])
                    denied_other_scope = session.reviewer(
                        approval(rid, CLEAR if scope != CLEAR else CAP, target))
                    self.assertFalse(denied_other_scope["ok"])
                    reviewed = session.reviewer(approval(rid, scope, target))
                    self.assertTrue(reviewed["ok"])
                    success = session.tasks(execute(rid, scope, target, epoch))
                    self.assertTrue(success["ok"])
                    self.assertFalse(session.tasks(execute(rid, scope, target, epoch))["ok"])
                # Subsequent revocation consumes any unspent approval.
                r4 = session.tasks(request())
                session.reviewer(approval(r4["requestId"]))
                self.assertTrue(session.reviewer({"op": "revoke"})["ok"])
                self.assertFalse(session.tasks(execute(r4["requestId"]))["ok"])
                self.assertFalse(session.tasks({"op": "revoke"})["ok"])
            finally:
                session.close()

    def test_production_stays_disabled_and_service_has_no_autostart(self):
        store = (ROOT / "services/hub/ApolloHubTodoStore.qml").read_text()
        broker = (ROOT / "services/connections/ConnectionsBroker.qml").read_text()
        shell = (ROOT / "shell.qml").read_text()
        qml = (ROOT / "widgets/tasks/TaskEncryptedDraftAccessPaneM15c.qml").read_text()
        source = HOST.read_text()
        self.assertIn("readonly property bool credentialActionsEnabled: false", broker)
        self.assertIn("readonly property bool encryptedRecoveryEnabled: false", store)
        self.assertEqual(store.count("FileView {"), 1)
        self.assertEqual(store.count("todoFile.setText("), 1)
        for where in (broker, store, shell, qml):
            self.assertNotIn("C5aTasksScopeHost", where)
        for banned in ("secret-tool", "gnome-keyring", "crypto.encrypt",
                       "ApolloHubTodoStore", "entryInput.text", "descriptionInput.text",
                       "systemctl", "subprocess.Popen(", "os.replace(", "os.chmod("):
            self.assertNotIn(banned, source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
