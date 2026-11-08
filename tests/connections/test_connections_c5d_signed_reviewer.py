#!/usr/bin/env python3
"""C5d: independent signed reviewer program; no real operator consent."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services/connections/experiments"))
sys.path.insert(0, str(ROOT / "tests/connections"))
import test_connections_c5c_signed_executable as T
import C5aTasksScopeHost as A
import C5bTasksDurableConsentHost as B
import C5cSignedCallerHost as C
import C5dSignedReviewerHost as D

HOST = ROOT / "services/connections/experiments/C5dSignedReviewerHost.py"
FIXTURE = ROOT / "tests/connections/fixtures/C5dSignedReviewerDummy.c"


class Session:
    """Real reviewer ELF and client ELF are different Unix sender processes."""
    def __init__(self, env, client_binary, reviewer_binary):
        review_fd, host_review = socket.socketpair(
            socket.AF_UNIX, socket.SOCK_SEQPACKET)
        client_fd, host_client = socket.socketpair(
            socket.AF_UNIX, socket.SOCK_SEQPACKET)
        self.attack_fd = os.dup(review_fd.fileno())
        self.reviewer_process = subprocess.Popen(
            [str(reviewer_binary), str(review_fd.fileno())],
            pass_fds=(review_fd.fileno(),), close_fds=True,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, bufsize=1)
        review_fd.close()
        self.client_process = subprocess.Popen(
            [str(client_binary), str(client_fd.fileno())],
            pass_fds=(client_fd.fileno(),), close_fds=True,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, bufsize=1)
        client_fd.close()
        env = {**env,
               "POST_APOLLO_C5D_REVIEWER_PID": str(self.reviewer_process.pid),
               "POST_APOLLO_C5D_REVIEWER_UID": str(os.getuid()),
               "POST_APOLLO_C5D_REVIEWER_GID": str(os.getgid())}
        self.host = subprocess.Popen(
            [sys.executable, "-I", "-B", str(HOST), "--host",
             str(host_review.fileno()), str(host_client.fileno())],
            pass_fds=(host_review.fileno(), host_client.fileno()), close_fds=True,
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, env=env)
        host_review.close()
        host_client.close()

    def request(self, process, data):
        assert process.stdin and process.stdout
        process.stdin.write(json.dumps(data, separators=(",", ":")) + "\n")
        process.stdin.flush()
        raw = process.stdout.readline()
        assert raw, "C5D_PROCESS_EOF"
        result = json.loads(raw)
        T.no_real_grants(result)
        return result

    def tasks(self, data):
        return self.request(self.client_process, data)

    def review(self, data):
        return self.request(self.reviewer_process, data)

    def bind(self):
        # Synchronize sender credential collection before reviewer message.
        probe = self.tasks(T.submit())
        assert probe["status"] == "CALLER_NOT_BOUND_OR_SENDER_CHANGED", probe
        return self.review({"op": "bindClient", "pid": self.client_process.pid,
                            "uid": os.getuid(), "gid": os.getgid()})

    def attack_reviewer(self, data):
        # The harness itself has a duplicate reviewer FD, but its kernel PID
        # differs from the signed reviewer. No child needs to be created or
        # destroyed, avoiding a closing-handle race with the genuine peer.
        with socket.socket(fileno=os.dup(self.attack_fd)) as forged:
            forged.settimeout(6)
            A.exchange(forged, data)
            result = A.receive(forged)
        T.no_real_grants(result)
        return result

    def close(self, *, expected_clean=True):
        if self.host.poll() is None:
            try:
                self.review({"op": "shutdown"})
            except (AssertionError, OSError, BrokenPipeError,
                    ConnectionResetError, ValueError):
                pass
        for proc in (self.client_process, self.reviewer_process):
            if proc.stdin:
                try:
                    proc.stdin.close()
                except BrokenPipeError:
                    pass
        os.close(self.attack_fd)
        for proc in (self.client_process, self.reviewer_process, self.host):
            try:
                proc.wait(timeout=7)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=7)
        if expected_clean:
            assert self.host.returncode == 0, "C5D_HOST_EXIT"
        for proc in (self.client_process, self.reviewer_process, self.host):
            for name in ("stdout", "stderr"):
                stream = getattr(proc, name)
                if stream:
                    tail = stream.read()
                    stream.close()
                    assert not tail, (name, proc.args, tail[-200:])


@unittest.skipIf(os.geteuid() == 0 or not sys.platform.startswith("linux"),
                 "Only nonroot isolated Linux CI with real kernel sender credentials")
class C5dSignedReviewerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Reuse the exact compiled signed C5c caller, its synthetic signing
        # identities and release policy, without changing production code.
        cls.c5c_fixture = T.C5cSignedProcessTests
        cls.c5c_fixture.setUpClass()
        cls.root_signer = cls.c5c_fixture.root_key
        cls.root_public = cls.c5c_fixture.root_public
        cls.root_pin = cls.c5c_fixture.root_pin
        cls.reviewer_signer, cls.reviewer_public, cls.reviewer_pin = T.key(
            cls.c5c_fixture.home, "c5d-reviewer")
        cls.review_binary = cls.c5c_fixture.home / "signed-c5d-reviewer"
        T.command(["gcc", "-O2", "-Wall", "-Wextra", "-Werror",
                   "-o", str(cls.review_binary), str(FIXTURE)])
        cls.other_reviewer = cls.c5c_fixture.home / "different-c5d-reviewer"
        T.command(["gcc", "-O0", "-Wall", "-Wextra", "-Werror",
                   "-o", str(cls.other_reviewer), str(FIXTURE)])
        assert cls.other_reviewer.read_bytes() != cls.review_binary.read_bytes()
        cls.policy = cls.c5c_fixture.home / "c5d-reviewer-policy.json"
        cls.policy_sig = cls.c5c_fixture.home / "c5d-reviewer-policy.sig"
        cls.manifest = cls.c5c_fixture.home / "c5d-reviewer-manifest.json"
        cls.manifest_sig = cls.c5c_fixture.home / "c5d-reviewer-manifest.sig"
        cls.policy_doc = {
            "schema": C.POLICY_SCHEMA, "role": D.REVIEW_ROLE, "epoch": 2,
            "min_sequence": 4, "delegated_fingerprint": cls.reviewer_pin,
        }
        cls.manifest_doc = {
            "schema": C.MANIFEST_SCHEMA, "role": D.REVIEW_ROLE,
            "epoch": 2, "sequence": 4,
            "sha256": hashlib.sha256(cls.review_binary.read_bytes()).hexdigest(),
            "size": cls.review_binary.stat().st_size,
        }
        T.json_file(cls.policy, cls.policy_doc)
        T.json_file(cls.manifest, cls.manifest_doc)
        T.gpg(cls.root_signer, "--output", str(cls.policy_sig),
              "--detach-sign", str(cls.policy))
        T.gpg(cls.reviewer_signer, "--output", str(cls.manifest_sig),
              "--detach-sign", str(cls.manifest))

    @classmethod
    def tearDownClass(cls):
        cls.c5c_fixture.tearDownClass()

    def setUp(self):
        self.folder = tempfile.TemporaryDirectory(
            prefix="postapollo-c5b-durable-", dir="/tmp")
        self.root = Path(self.folder.name)
        for name, text in ((".c5b-test-only", B.MARKER),
                           (".c5c-test-only", C.GATE_MARKER),
                           (".c5d-test-only", D.MARKER)):
            path = self.root / name
            path.write_text(text + "\n")
            path.chmod(0o600)
        fx = self.c5c_fixture
        self.env = {
            **os.environ, "GITHUB_ACTIONS": "true",
            "POST_APOLLO_C5B_DISPOSABLE": "1",
            "POST_APOLLO_C5B_FIXTURE_ROOT": str(self.root),
            "POST_APOLLO_C5C_DISPOSABLE": "1",
            "POST_APOLLO_C5C_ROOT_PUBLIC": str(fx.root_public),
            "POST_APOLLO_C5C_ROOT_PIN": fx.root_pin,
            "POST_APOLLO_C5C_POLICY": str(fx.policy),
            "POST_APOLLO_C5C_POLICY_SIGNATURE": str(fx.policy_sig),
            "POST_APOLLO_C5C_DELEGATE_PUBLIC": str(fx.delegate_public),
            "POST_APOLLO_C5C_MANIFEST": str(fx.manifest),
            "POST_APOLLO_C5C_MANIFEST_SIGNATURE": str(fx.manifest_sig),
            "POST_APOLLO_C5C_MIN_EPOCH": "2",
            "POST_APOLLO_C5C_MIN_SEQUENCE": "4",
            "POST_APOLLO_C5D_DISPOSABLE": "1",
            "POST_APOLLO_C5D_ROOT_PUBLIC": str(self.root_public),
            "POST_APOLLO_C5D_ROOT_PIN": self.root_pin,
            "POST_APOLLO_C5D_POLICY": str(self.policy),
            "POST_APOLLO_C5D_POLICY_SIGNATURE": str(self.policy_sig),
            "POST_APOLLO_C5D_DELEGATE_PUBLIC": str(self.reviewer_public),
            "POST_APOLLO_C5D_MANIFEST": str(self.manifest),
            "POST_APOLLO_C5D_MANIFEST_SIGNATURE": str(self.manifest_sig),
            "POST_APOLLO_C5D_MIN_EPOCH": "2",
            "POST_APOLLO_C5D_MIN_SEQUENCE": "4",
            "HOME": str(self.root),
        }

    def tearDown(self):
        self.folder.cleanup()

    def session(self, reviewer=None, client=None):
        return Session(self.env, client or self.c5c_fixture.binary,
                       reviewer or self.review_binary)

    def test_separate_signed_reviewer_client_and_all_three_scopes(self):
        s = self.session()
        try:
            binding = s.bind()
            self.assertEqual(binding["status"],
                             "C5C_SIGNED_TEST_EXECUTABLE_BOUND_NO_REAL_GRANT")
            for scope, target, epoch in (
                (T.CAP, "entry", 3), (T.CAP, "details", 5),
                (T.PREV, "checkpoint", 0), (T.CLEAR, "checkpoint", 0),
            ):
                pending = s.tasks(T.submit(scope, target, epoch))
                self.assertTrue(pending["ok"])
                rid = pending["requestId"]
                self.assertFalse(s.tasks(T.execute(rid, scope, target, epoch))["ok"])
                self.assertTrue(s.review(T.approval(rid, scope, target))["ok"])
                self.assertTrue(s.tasks(T.execute(rid, scope, target, epoch))["ok"])
                self.assertFalse(s.tasks(T.execute(rid, scope, target, epoch))["ok"])
            # Reviewer must never have authority to write user TASKS source.
            self.assertFalse(s.tasks({"op": "approve"})["ok"])
            self.assertTrue(s.review({"op": "revoke"})["ok"])
        finally:
            s.close()

    def test_same_uid_wrong_reviewer_binary_cannot_authorize(self):
        s = self.session(reviewer=self.other_reviewer)
        try:
            self.assertEqual(s.bind()["status"], "REVIEWER_ORIGIN_MISMATCH")
            self.assertFalse(s.tasks(T.submit())["ok"])
        finally:
            s.close(expected_clean=False)

    def test_harness_parent_cannot_replace_reviewer_through_forwarded_fd(self):
        s = self.session()
        try:
            self.assertTrue(s.bind()["ok"])
            pending = s.tasks(T.submit())
            rid = pending["requestId"]
            attacker = s.attack_reviewer(T.approval(rid))
            self.assertEqual(attacker["status"], "REVIEWER_ORIGIN_MISMATCH")
            self.assertFalse(s.tasks(T.execute(rid))["ok"])
            self.assertTrue(s.review(T.approval(rid))["ok"])
            self.assertTrue(s.tasks(T.execute(rid))["ok"])
        finally:
            s.close()

    def test_separately_signed_wrong_role_refused(self):
        role_policy = self.root / "wrong-role-policy.json"
        signature = self.root / "wrong-role-policy.sig"
        T.json_file(role_policy, {**self.policy_doc, "role": C.ROLE})
        T.gpg(self.root_signer, "--output", str(signature),
              "--detach-sign", str(role_policy))
        self.env["POST_APOLLO_C5D_POLICY"] = str(role_policy)
        self.env["POST_APOLLO_C5D_POLICY_SIGNATURE"] = str(signature)
        s = self.session()
        try:
            self.assertEqual(s.bind()["status"], "REVIEWER_ORIGIN_MISMATCH")
        finally:
            s.close(expected_clean=False)

    def test_wrong_reviewer_root_or_delegate_refused(self):
        for label, key, value in (
            ("wrong_root", "POST_APOLLO_C5D_ROOT_PUBLIC",
             str(self.c5c_fixture.attacker_public)),
            ("wrong_delegate", "POST_APOLLO_C5D_DELEGATE_PUBLIC",
             str(self.c5c_fixture.attacker_public)),
            ("revoked_floor", "POST_APOLLO_C5D_MIN_SEQUENCE", "7"),
        ):
            with self.subTest(label=label):
                previous = self.env[key]
                self.env[key] = value
                s = self.session()
                try:
                    self.assertEqual(s.bind()["status"],
                                     "REVIEWER_ORIGIN_MISMATCH")
                finally:
                    s.close(expected_clean=False)
                    self.env[key] = previous

    def test_real_durable_revoke_preserved_with_separate_reviewer(self):
        s = self.session()
        try:
            self.assertTrue(s.bind()["ok"])
            pending = s.tasks(T.submit())
            rid = pending["requestId"]
            self.assertTrue(s.review(T.approval(rid))["ok"])
            self.assertTrue(s.review({"op": "revoke"})["ok"])
            self.assertFalse(s.tasks(T.execute(rid))["ok"])
        finally:
            s.close()
        with B.sqlite3.connect(str(self.root / "consent.sqlite3")) as db:
            self.assertEqual(db.execute(
                "SELECT state FROM requests WHERE id=?", (rid,)).fetchone()[0],
                "REVOKED")

    def test_client_cannot_self_approve_even_with_signed_executable(self):
        s = self.session()
        try:
            self.assertTrue(s.bind()["ok"])
            pending = s.tasks(T.submit())
            self.assertEqual(s.tasks(T.approval(pending["requestId"]))["status"],
                             "CLIENT_CANNOT_AUTHORIZE")
            self.assertFalse(s.tasks(T.execute(pending["requestId"]))["ok"])
        finally:
            s.close()


class ProductionInert(unittest.TestCase):
    def test_no_desktop_or_key_paths(self):
        store = (ROOT / "services/hub/ApolloHubTodoStore.qml").read_text()
        broker = (ROOT / "services/connections/ConnectionsBroker.qml").read_text()
        ui = (ROOT / "widgets/tasks/TaskEncryptedDraftAccessPaneM15c.qml").read_text()
        shell = (ROOT / "shell.qml").read_text()
        for file in (store, broker, ui, shell):
            self.assertNotIn("C5dSignedReviewerHost", file)
        self.assertIn("readonly property bool credentialActionsEnabled: false", broker)
        self.assertIn("readonly property bool encryptedRecoveryEnabled: false", store)
        self.assertEqual(store.count("todoFile.setText("), 1)
        self.assertEqual(store.count("FileView {"), 1)
        self.assertIn("readonly property bool canCaptureDraft: false", ui)
        for forbidden in ("secret-tool", "gnome-keyring", "entryInput.text",
                          "descriptionInput.text", "systemctl"):
            self.assertNotIn(forbidden, HOST.read_text())

    def test_ci_refuses_non_disposable_invocation(self):
        process = subprocess.run(
            [sys.executable, "-I", "-B", str(HOST), "--host", "9", "10"],
            env={**os.environ, "POST_APOLLO_C5D_DISPOSABLE": "0"},
            capture_output=True, text=True, timeout=6)
        self.assertEqual(process.returncode, 2)
        self.assertIn("C5D_REFUSED_OUTSIDE_DISPOSABLE_CI", process.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
