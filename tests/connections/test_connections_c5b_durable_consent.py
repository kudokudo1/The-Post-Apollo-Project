#!/usr/bin/env python3
"""C5b: real Linux per-message credentials, durable consent and denial."""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[2]
HOST = ROOT / "services/connections/experiments/C5bTasksDurableConsentHost.py"
sys.path.insert(0, str(HOST.parent))
import C5aTasksScopeHost as A
import C5bTasksDurableConsentHost as B

CAP = "tasks.draft.capture.encrypted"
PREV = "tasks.draft.preview.unlocked"
CLEAR = "tasks.draft.clear.encrypted"


def submit(scope=CAP, target="entry", epoch=3, gen=7):
    return {"op": "submit", "scope": scope, "target": target,
            "editorEpoch": epoch, "sourceGeneration": gen}


def execute(rid, scope=CAP, target="entry", epoch=3, gen=7):
    return {"op": "execute", "requestId": rid, "scope": scope,
            "target": target, "editorEpoch": epoch, "sourceGeneration": gen}


def approve(rid, scope=CAP, target="entry", ttl=10000):
    return {"op": "approve", "requestId": rid, "scope": scope,
            "target": target, "ttlMs": ttl, "confirmed": True}


def check(result):
    assert type(result) is dict and type(result.get("ok")) is bool, result
    for name in A.FLAGS:
        assert result.get(name) is False, (name, result)
    assert set(result).issubset({"status", "ok", "requestId", *A.FLAGS})
    for secret in ("PRIVATE_UNSAVED_NOTE", "KEY_MATERIAL", "rawDraft"):
        assert secret not in json.dumps(result)


class Session:
    """Test harness holds reviewer FD. Client receives only its client FD."""
    def __init__(self, env):
        self.review, broker_review = socket.socketpair(
            socket.AF_UNIX, socket.SOCK_SEQPACKET)
        client_fd, broker_client = socket.socketpair(
            socket.AF_UNIX, socket.SOCK_SEQPACKET)
        self.attack_review = os.dup(self.review.fileno())
        self.attack_client = os.dup(client_fd.fileno())
        self.review.settimeout(4)
        self.host = subprocess.Popen(
            [sys.executable, "-I", "-B", str(HOST), "--host",
             str(broker_review.fileno()), str(broker_client.fileno())],
            pass_fds=(broker_review.fileno(), broker_client.fileno()),
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, env=env)
        broker_review.close()
        broker_client.close()
        self.client = subprocess.Popen(
            [sys.executable, "-I", "-B", str(HOST), "--client",
             str(client_fd.fileno()), "0"],
            pass_fds=(client_fd.fileno(),), close_fds=True,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, bufsize=1, env=env)
        client_fd.close()

    def reviewer(self, data):
        A.exchange(self.review, data)
        result = A.receive(self.review)
        check(result)
        return result

    def tasks(self, data):
        assert self.client.stdin and self.client.stdout
        self.client.stdin.write(json.dumps(data, separators=(",", ":")) + "\n")
        self.client.stdin.flush()
        reply = self.client.stdout.readline()
        assert reply, "C5B_CLIENT_EOF"
        result = json.loads(reply)
        check(result)
        return result

    def bind(self):
        return self.reviewer({"op": "bindClient", "pid": self.client.pid,
                              "uid": os.getuid(), "gid": os.getgid()})

    def forwarded(self, role, data):
        fd = self.attack_client if role == "client" else self.attack_review
        script = ("import socket,sys,json\n"
                  "s=socket.socket(fileno=int(sys.argv[1]));"
                  "s.settimeout(4);"
                  "s.send(json.dumps(json.loads(sys.argv[2])).encode());"
                  "print(s.recv(2048).decode())")
        proc = subprocess.run(
            [sys.executable, "-I", "-B", "-c", script, str(fd),
             json.dumps(data)], pass_fds=(fd,), capture_output=True,
            text=True, timeout=8)
        assert proc.returncode == 0, (proc.stdout, proc.stderr)
        result = json.loads(proc.stdout.strip())
        check(result)
        return result

    def close(self, crash=False):
        if not crash and self.host.poll() is None:
            try:
                self.reviewer({"op": "shutdown"})
            except (AssertionError, OSError, TimeoutError, ValueError):
                pass
        if crash and self.host.poll() is None:
            self.host.kill()
        self.review.close()
        os.close(self.attack_review)
        os.close(self.attack_client)
        if self.client.stdin:
            self.client.stdin.close()
        try:
            self.client.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.client.kill()
            self.client.wait(timeout=5)
        try:
            self.host.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.host.kill()
            self.host.wait(timeout=5)
        assert self.client.returncode == 0, "C5B_CLIENT_NOT_CLEAN"
        if not crash:
            assert self.host.returncode == 0, "C5B_HOST_NOT_CLEAN"
        assert self.client.stdout and self.client.stdout.read() == ""
        assert self.client.stderr and self.client.stderr.read() == ""
        if not crash:
            assert self.host.stdout and self.host.stdout.read() == ""
            assert self.host.stderr and self.host.stderr.read() == ""


@unittest.skipIf(os.geteuid() == 0 or not sys.platform.startswith("linux"),
                 "C5b real processes require a nonroot Linux CI runner")
class C5bDurableHostTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory(
            prefix="postapollo-c5b-durable-", dir="/tmp")
        self.root = Path(self.folder.name)
        (self.root / ".c5b-test-only").write_text(B.MARKER + "\n")
        (self.root / ".c5b-test-only").chmod(0o600)
        self.env = {**os.environ, "GITHUB_ACTIONS": "true",
                    "POST_APOLLO_C5B_DISPOSABLE": "1",
                    "POST_APOLLO_C5B_FIXTURE_ROOT": str(self.root),
                    "HOME": str(self.root)}

    def tearDown(self):
        self.folder.cleanup()

    def session(self):
        return Session(self.env)

    def test_three_independent_scopes_and_one_use_committed_before_reply(self):
        s = self.session()
        try:
            self.assertEqual(s.tasks(submit())["status"],
                             "CALLER_NOT_BOUND_OR_SENDER_CHANGED")
            self.assertTrue(s.bind()["ok"])
            for scope, target, epoch in ((CAP, "entry", 3),
                                          (CAP, "details", 5),
                                          (PREV, "checkpoint", 0),
                                          (CLEAR, "checkpoint", 0)):
                pending = s.tasks(submit(scope, target, epoch))
                rid = pending["requestId"]
                self.assertFalse(s.tasks(execute(rid, scope, target, epoch))["ok"])
                self.assertFalse(s.tasks(approve(rid, scope, target))["ok"])
                self.assertFalse(s.reviewer(approve(rid, CAP if scope != CAP else CLEAR,
                                                    target))["ok"])
                self.assertFalse(s.reviewer(approve(rid, scope,
                                                    "details" if target != "details"
                                                    else "entry"))["ok"])
                self.assertTrue(s.reviewer(approve(rid, scope, target))["ok"])
                self.assertFalse(s.tasks(execute(rid, scope, target, epoch,
                                                 gen=8))["ok"])
                self.assertTrue(s.tasks(execute(rid, scope, target, epoch))["ok"])
                self.assertFalse(s.tasks(execute(rid, scope, target, epoch))["ok"])
        finally:
            s.close()
        with sqlite3.connect(str(self.root / "consent.sqlite3")) as db:
            rows = db.execute("SELECT DISTINCT state FROM requests").fetchall()
        self.assertEqual(rows, [("CONSUMED",)])
        self.assertEqual((self.root / "consent.sqlite3").stat().st_mode & 0o777,
                         0o600)

    def test_crash_restart_invalidates_approved_and_replay_is_persistently_denied(self):
        first = self.session()
        try:
            first.bind()
            pending = first.tasks(submit())
            approved = first.tasks(submit(PREV, "checkpoint", 0))
            self.assertTrue(first.reviewer(approve(approved["requestId"],
                                                   PREV, "checkpoint"))["ok"])
            spent = first.tasks(submit(CLEAR, "checkpoint", 0))
            first.reviewer(approve(spent["requestId"], CLEAR, "checkpoint"))
            first.tasks(execute(spent["requestId"], CLEAR, "checkpoint", 0))
        finally:
            first.close(crash=True)
        second = self.session()
        try:
            self.assertTrue(second.bind()["ok"])
            for rid, scope, target, epoch in (
                (pending["requestId"], CAP, "entry", 3),
                (approved["requestId"], PREV, "checkpoint", 0),
                (spent["requestId"], CLEAR, "checkpoint", 0),
            ):
                denied = second.tasks(execute(rid, scope, target, epoch))
                self.assertFalse(denied["ok"])
            self.assertFalse(second.reviewer(approve(approved["requestId"],
                                                    PREV, "checkpoint"))["ok"])
            self.assertTrue(second.tasks(submit())["ok"])
        finally:
            second.close()
        with sqlite3.connect(str(self.root / "consent.sqlite3")) as db:
            self.assertEqual(db.execute(
                "SELECT state FROM requests WHERE id=?",
                (approved["requestId"],)).fetchone()[0], "INTERRUPTED")
            self.assertEqual(db.execute(
                "SELECT state FROM requests WHERE id=?",
                (spent["requestId"],)).fetchone()[0], "CONSUMED")

    def test_sender_credential_change_and_forwarded_reviewer_fd_denied(self):
        s = self.session()
        try:
            s.bind()
            pending = s.tasks(submit())
            # Same file descriptor forwarded to another process: the kernel
            # reports that process as the sender on recvmsg.
            forged_request = s.forwarded("client", submit())
            self.assertEqual(forged_request["status"],
                             "CALLER_NOT_BOUND_OR_SENDER_CHANGED")
            forged_review = s.forwarded("reviewer", approve(pending["requestId"]))
            self.assertEqual(forged_review["status"], "REVIEWER_ORIGIN_MISMATCH")
            self.assertFalse(s.tasks(execute(pending["requestId"]))["ok"])
            self.assertTrue(s.reviewer(approve(pending["requestId"]))["ok"])
            self.assertTrue(s.tasks(execute(pending["requestId"]))["ok"])
            self.assertFalse(s.tasks({"op": "bindClient",
                                      "pid": s.client.pid, "uid": os.getuid(),
                                      "gid": os.getgid()})["ok"])
        finally:
            s.close()

    def test_durable_revocation_wrong_scope_expiry_and_malformed_payload(self):
        s = self.session()
        try:
            s.bind()
            first = s.tasks(submit())
            s.reviewer(approve(first["requestId"]))
            self.assertTrue(s.reviewer({"op": "revoke"})["ok"])
            self.assertFalse(s.tasks(execute(first["requestId"]))["ok"])
            second = s.tasks(submit(PREV, "checkpoint", 0))
            s.reviewer(approve(second["requestId"], PREV, "checkpoint", 1))
            time.sleep(.03)
            expired = s.tasks(execute(second["requestId"],
                                      PREV, "checkpoint", 0))
            self.assertEqual(expired["status"], "REVOKED_OR_EXPIRED")
            self.assertFalse(s.tasks(execute(second["requestId"],
                                             PREV, "checkpoint", 0))["ok"])
            for malformed in ({"op": "submit", **{**submit(), "taskText":
                                                   "PRIVATE_UNSAVED_NOTE"}},
                              {**submit(), "editorEpoch": True},
                              {**submit(), "approved": True},
                              {**submit(), "scope": "tasks.draft.keys.read"},
                              {**submit(), "target": "checkpoint"},
                              {"op": "clear", "path": "/home/user"},
                              {"op": "unlock", "key": "KEY_MATERIAL"}):
                self.assertFalse(s.tasks(malformed)["ok"])
        finally:
            s.close()
        with sqlite3.connect(str(self.root / "consent.sqlite3")) as db:
            states = [x[0] for x in db.execute(
                "SELECT state FROM requests ORDER BY rowid").fetchall()]
        self.assertEqual(states, ["REVOKED", "CONSUMED"])

    def test_double_host_lock_and_untrusted_private_paths_refused(self):
        s = self.session()
        try:
            s.bind()
            # A second server cannot silently share the same authority DB.
            other = self.session()
            try:
                out = other.bind()
                self.fail("Second host unexpectedly accepted: " + str(out))
            except (AssertionError, ValueError, TimeoutError, BrokenPipeError,
                    ConnectionResetError, OSError):
                pass
            finally:
                other.close(crash=True)
        finally:
            s.close()
        (self.root / "consent.sqlite3").chmod(0o644)
        bad = self.session()
        try:
            with self.assertRaises((AssertionError, ValueError, TimeoutError,
                                    BrokenPipeError, ConnectionResetError,
                                    OSError)):
                bad.bind()
        finally:
            bad.close(crash=True)


class C5bNoProductionTests(unittest.TestCase):
    def test_no_mount_or_credential_writes_and_default_deny(self):
        source = HOST.read_text()
        store = (ROOT / "services/hub/ApolloHubTodoStore.qml").read_text()
        broker = (ROOT / "services/connections/ConnectionsBroker.qml").read_text()
        access = (ROOT / "widgets/tasks/TaskEncryptedDraftAccessPaneM15c.qml").read_text()
        shell = (ROOT / "shell.qml").read_text()
        self.assertIn("readonly property bool credentialActionsEnabled: false", broker)
        self.assertIn("readonly property bool encryptedRecoveryEnabled: false", store)
        self.assertEqual(store.count("FileView {"), 1)
        self.assertEqual(store.count("todoFile.setText("), 1)
        self.assertIn("readonly property bool canCaptureDraft: false", access)
        for production in (store, broker, access, shell):
            self.assertNotIn("C5bTasksDurableConsentHost", production)
        for forbidden in ("secret-tool", "gnome-keyring", "entryInput.text",
                          "descriptionInput.text", "ApolloHubTodoStore",
                          "systemctl", "keyring.get", "QProcess",
                          "credentialActionsEnabled = true"):
            self.assertNotIn(forbidden, source)
        self.assertIn("SO_PASSCRED", source)
        self.assertIn("recvmsg", source)
        self.assertIn("PRAGMA synchronous=FULL", source)

    def test_binary_is_inert_outside_CI_fixture(self):
        run = subprocess.run(
            [sys.executable, "-I", "-B", str(HOST), "--host", "9", "10"],
            env={**os.environ, "POST_APOLLO_C5B_DISPOSABLE": "0"},
            text=True, capture_output=True, timeout=5)
        self.assertEqual(run.returncode, 2)
        self.assertIn("C5B_REFUSED_OUTSIDE_DISPOSABLE_HOST", run.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
