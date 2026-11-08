#!/usr/bin/env python3
"""C5c real signed ELF process, kernel sender and C5b durable denial."""
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
TEST_CLIENT = ROOT / "tests/connections/fixtures/C5cTasksSignedDummy.c"
HOST = ROOT / "services/connections/experiments/C5cSignedCallerHost.py"
sys.path.insert(0, str(HOST.parent))
import C5aTasksScopeHost as A
import C5bTasksDurableConsentHost as B
import C5cSignedCallerHost as C

CAP = "tasks.draft.capture.encrypted"
PREV = "tasks.draft.preview.unlocked"
CLEAR = "tasks.draft.clear.encrypted"


def command(args, *, timeout=20):
    result = subprocess.run(args, stdin=subprocess.DEVNULL, capture_output=True,
                            text=True, timeout=timeout)
    if result.returncode:
        raise AssertionError("C5C_TEST_TOOL_FAILED: " + repr(args[:2])
                             + " " + result.stderr[-700:])
    return result.stdout


def gpg(home, *args):
    return command(["gpg", "--homedir", str(home), "--batch", "--yes",
                    "--pinentry-mode", "loopback", "--passphrase", "", *args])


def key(root, name):
    home = root / ("gpg-" + name)
    home.mkdir(mode=0o700)
    gpg(home, "--quick-generate-key", "C5c " + name + " <" + name
        + "@example.invalid>", "ed25519", "sign", "0")
    listing = gpg(home, "--with-colons", "--fingerprint", "--list-keys")
    fingerprints = [line.split(":")[9] for line in listing.splitlines()
                    if line.startswith("fpr:")]
    assert len(fingerprints) == 1, "C5C_TEST_SIGNER_FINGERPRINT_AMBIGUOUS"
    pub = root / (name + "-public.asc")
    pub.write_text(gpg(home, "--armor", "--export", fingerprints[0]))
    return home, pub, fingerprints[0]


def json_file(path, doc):
    path.write_text(json.dumps(doc, sort_keys=True, separators=(",", ":")) + "\n")


def submit(scope=CAP, target="entry", epoch=3, generation=7):
    return {"op": "submit", "scope": scope, "target": target,
            "editorEpoch": epoch, "sourceGeneration": generation}


def execute(rid, scope=CAP, target="entry", epoch=3, generation=7):
    return {"op": "execute", "requestId": rid, "scope": scope,
            "target": target, "editorEpoch": epoch, "sourceGeneration": generation}


def approval(rid, scope=CAP, target="entry"):
    return {"op": "approve", "requestId": rid, "scope": scope,
            "target": target, "ttlMs": 10000, "confirmed": True}


def no_real_grants(result):
    assert type(result) is dict and type(result.get("ok")) is bool, result
    for name in A.FLAGS:
        assert result.get(name) is False, (name, result)
    assert set(result).issubset({"status", "ok", "requestId", *A.FLAGS})


class ProcessSession:
    def __init__(self, env, binary):
        self.reviewer_sock, host_reviewer = socket.socketpair(
            socket.AF_UNIX, socket.SOCK_SEQPACKET)
        client_fd, host_client = socket.socketpair(
            socket.AF_UNIX, socket.SOCK_SEQPACKET)
        self.reviewer_sock.settimeout(8)
        self.host = subprocess.Popen(
            [sys.executable, "-I", "-B", str(HOST), "--host",
             str(host_reviewer.fileno()), str(host_client.fileno())],
            pass_fds=(host_reviewer.fileno(), host_client.fileno()),
            close_fds=True, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, env=env)
        host_reviewer.close()
        host_client.close()
        self.client = subprocess.Popen(
            [str(binary), str(client_fd.fileno())],
            pass_fds=(client_fd.fileno(),), close_fds=True,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, bufsize=1)
        client_fd.close()

    def tasks(self, request):
        assert self.client.stdin and self.client.stdout
        self.client.stdin.write(json.dumps(request, separators=(",", ":")) + "\n")
        self.client.stdin.flush()
        raw = self.client.stdout.readline()
        assert raw, "C5C_TEST_CLIENT_EOF"
        result = json.loads(raw)
        no_real_grants(result)
        return result

    def reviewer(self, request):
        A.exchange(self.reviewer_sock, request)
        result = A.receive(self.reviewer_sock)
        no_real_grants(result)
        return result

    def bind(self):
        # First packet also synchronizes with host's SO_PASSCRED setup.
        preflight = self.tasks(submit())
        assert preflight["status"] == "CALLER_NOT_BOUND_OR_SENDER_CHANGED", preflight
        return self.reviewer({"op": "bindClient", "pid": self.client.pid,
                              "uid": os.getuid(), "gid": os.getgid()})

    def close(self):
        if self.host.poll() is None:
            try:
                self.reviewer({"op": "shutdown"})
            except (AssertionError, OSError, ValueError, TimeoutError,
                    ConnectionResetError, BrokenPipeError):
                pass
        self.reviewer_sock.close()
        if self.client.stdin:
            self.client.stdin.close()
        for proc in (self.client, self.host):
            try:
                proc.wait(timeout=6)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=6)
        assert self.client.returncode == 0, "C5C_TEST_CLIENT_NOT_CLEAN"
        assert self.host.returncode == 0, "C5C_HOST_NOT_CLEAN"
        for proc in (self.client, self.host):
            for name in ("stdout", "stderr"):
                stream = getattr(proc, name)
                if stream:
                    tail = stream.read()
                    stream.close()
                    if proc is self.host:
                        assert tail == "", "C5C_HOST_OUTPUT_LEAK: " + tail[:80]
                    elif name == "stderr":
                        assert tail == "", "C5C_CLIENT_STDERR: " + tail[:80]
                    else:
                        assert tail == "", "C5C_CLIENT_STDOUT_TAIL"


@unittest.skipIf(os.geteuid() == 0 or not sys.platform.startswith("linux"),
                 "CI requires Linux non-root, no host-keyring access")
class C5cSignedProcessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory(prefix="c5c-signing-")
        cls.home = Path(cls.directory.name)
        cls.root_key, cls.root_public, cls.root_pin = key(cls.home, "root")
        cls.delegate_key, cls.delegate_public, cls.delegate_pin = key(
            cls.home, "delegate")
        cls.attacker_key, cls.attacker_public, cls.attacker_pin = key(
            cls.home, "attacker")
        cls.binary = cls.home / "signed-test-client"
        command(["gcc", "-O2", "-Wall", "-Wextra", "-Werror", "-o",
                 str(cls.binary), str(TEST_CLIENT)])
        cls.stray_binary = cls.home / "other-test-client"
        command(["gcc", "-O0", "-Wall", "-Wextra", "-Werror", "-o",
                 str(cls.stray_binary), str(TEST_CLIENT)])
        assert cls.stray_binary.read_bytes() != cls.binary.read_bytes()
        cls.policy = cls.home / "policy.json"
        cls.policy_sig = cls.home / "policy.sig"
        cls.manifest = cls.home / "manifest.json"
        cls.manifest_sig = cls.home / "manifest.sig"
        cls.policy_data = {
            "schema": C.POLICY_SCHEMA, "role": C.ROLE, "epoch": 2,
            "min_sequence": 4, "delegated_fingerprint": cls.delegate_pin,
        }
        cls.manifest_data = {
            "schema": C.MANIFEST_SCHEMA, "role": C.ROLE, "epoch": 2,
            "sequence": 4, "sha256": hashlib.sha256(cls.binary.read_bytes()).hexdigest(),
            "size": cls.binary.stat().st_size,
        }
        json_file(cls.policy, cls.policy_data)
        json_file(cls.manifest, cls.manifest_data)
        gpg(cls.root_key, "--output", str(cls.policy_sig), "--detach-sign",
            str(cls.policy))
        gpg(cls.delegate_key, "--output", str(cls.manifest_sig),
            "--detach-sign", str(cls.manifest))

    @classmethod
    def tearDownClass(cls):
        cls.directory.cleanup()

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(
            prefix="postapollo-c5b-durable-", dir="/tmp")
        self.root = Path(self.directory.name)
        (self.root / ".c5b-test-only").write_text(B.MARKER + "\n")
        (self.root / ".c5b-test-only").chmod(0o600)
        (self.root / ".c5c-test-only").write_text(C.GATE_MARKER + "\n")
        (self.root / ".c5c-test-only").chmod(0o600)
        self.env = {
            **os.environ, "GITHUB_ACTIONS": "true",
            "POST_APOLLO_C5B_DISPOSABLE": "1",
            "POST_APOLLO_C5B_FIXTURE_ROOT": str(self.root),
            "POST_APOLLO_C5C_DISPOSABLE": "1",
            "POST_APOLLO_C5C_ROOT_PUBLIC": str(self.root_public),
            "POST_APOLLO_C5C_ROOT_PIN": self.root_pin,
            "POST_APOLLO_C5C_POLICY": str(self.policy),
            "POST_APOLLO_C5C_POLICY_SIGNATURE": str(self.policy_sig),
            "POST_APOLLO_C5C_DELEGATE_PUBLIC": str(self.delegate_public),
            "POST_APOLLO_C5C_MANIFEST": str(self.manifest),
            "POST_APOLLO_C5C_MANIFEST_SIGNATURE": str(self.manifest_sig),
            "POST_APOLLO_C5C_MIN_EPOCH": "2",
            "POST_APOLLO_C5C_MIN_SEQUENCE": "4",
            "HOME": str(self.root),
        }

    def tearDown(self):
        self.directory.cleanup()

    def session(self, executable=None):
        return ProcessSession(self.env, executable or self.binary)

    def test_signed_running_elf_admitted_to_c5b_all_scopes_still_synthetic(self):
        s = self.session()
        try:
            allowed = s.bind()
            self.assertTrue(allowed["ok"], allowed)
            self.assertEqual(allowed["status"],
                             "C5C_SIGNED_TEST_EXECUTABLE_BOUND_NO_REAL_GRANT")
            for scope, target, epoch in (
                (CAP, "entry", 3), (CAP, "details", 5),
                (PREV, "checkpoint", 0), (CLEAR, "checkpoint", 0),
            ):
                pending = s.tasks(submit(scope, target, epoch))
                self.assertTrue(pending["ok"], pending)
                rid = pending["requestId"]
                self.assertFalse(s.tasks(execute(rid, scope, target, epoch))["ok"])
                self.assertTrue(s.reviewer(approval(rid, scope, target))["ok"])
                self.assertTrue(s.tasks(execute(rid, scope, target, epoch))["ok"])
                self.assertFalse(s.tasks(execute(rid, scope, target, epoch))["ok"])
        finally:
            s.close()

    def test_same_uid_different_unsigned_elf_cannot_bind(self):
        s = self.session(self.stray_binary)
        try:
            denied = s.bind()
            self.assertEqual(denied["status"], "C5C_SIGNED_EXECUTABLE_MISMATCH")
            self.assertFalse(s.tasks(submit())["ok"])
        finally:
            s.close()

    def test_wrong_root_public_key_does_not_override_pre_pinned_root(self):
        self.env["POST_APOLLO_C5C_ROOT_PUBLIC"] = str(self.attacker_public)
        s = self.session()
        try:
            self.assertEqual(s.bind()["status"],
                             "C5C_SIGNED_EXECUTABLE_REFUSED")
            self.assertFalse(s.tasks(submit())["ok"])
        finally:
            s.close()

    def test_wrong_manifest_signer_even_with_valid_root_policy_denied(self):
        tmp_manifest_sig = self.root / "other-signature.sig"
        gpg(self.attacker_key, "--output", str(tmp_manifest_sig),
            "--detach-sign", str(self.manifest))
        self.env["POST_APOLLO_C5C_DELEGATE_PUBLIC"] = str(self.attacker_public)
        self.env["POST_APOLLO_C5C_MANIFEST_SIGNATURE"] = str(tmp_manifest_sig)
        s = self.session()
        try:
            self.assertEqual(s.bind()["status"],
                             "C5C_SIGNED_EXECUTABLE_REFUSED")
            self.assertFalse(s.tasks(submit())["ok"])
        finally:
            s.close()

    def test_signed_manifest_tampering_and_wrong_role_denied(self):
        changed = self.root / "modified-manifest.json"
        json_file(changed, {**self.manifest_data, "role": "postapollo.other"})
        self.env["POST_APOLLO_C5C_MANIFEST"] = str(changed)
        s = self.session()
        try:
            self.assertEqual(s.bind()["status"],
                             "C5C_SIGNED_EXECUTABLE_REFUSED")
        finally:
            s.close()

    def test_release_epoch_or_sequence_downgrade_denied(self):
        for key, value in (("POST_APOLLO_C5C_MIN_EPOCH", "3"),
                           ("POST_APOLLO_C5C_MIN_SEQUENCE", "5")):
            with self.subTest(key=key):
                original = self.env[key]
                self.env[key] = value
                s = self.session()
                try:
                    self.assertEqual(s.bind()["status"],
                                     "C5C_SIGNED_EXECUTABLE_REFUSED")
                    self.assertFalse(s.tasks(submit())["ok"])
                finally:
                    s.close()
                    self.env[key] = original

    def test_operator_bypass_and_unauthenticated_review_forbidden(self):
        s = self.session(self.stray_binary)
        try:
            self.assertFalse(s.bind()["ok"])
            for cmd in (
                {"op": "approve", "requestId": "0" * 32,
                 "scope": CAP, "target": "entry",
                 "ttlMs": 1000, "confirmed": True},
                {"op": "bindClient", "pid": s.client.pid, "uid": os.getuid(),
                 "gid": os.getgid()},
                {"op": "revoke"},
            ):
                self.assertFalse(s.tasks(cmd)["ok"])
        finally:
            s.close()


class C5cProductionDeny(unittest.TestCase):
    def test_uninstalled_source_and_one_existing_writer(self):
        src = HOST.read_text()
        store = (ROOT / "services/hub/ApolloHubTodoStore.qml").read_text()
        broker = (ROOT / "services/connections/ConnectionsBroker.qml").read_text()
        qml = (ROOT / "widgets/tasks/TaskEncryptedDraftAccessPaneM15c.qml").read_text()
        self.assertEqual(store.count("FileView {"), 1)
        self.assertEqual(store.count("todoFile.setText("), 1)
        self.assertIn("readonly property bool credentialActionsEnabled: false", broker)
        self.assertIn("readonly property bool encryptedRecoveryEnabled: false", store)
        self.assertIn("readonly property bool canCaptureDraft: false", qml)
        for p in (store, broker, qml, (ROOT / "shell.qml").read_text()):
            self.assertNotIn("C5cSignedCallerHost", p)
        for forbidden in ("secret-tool", "gnome-keyring", "entryInput.text",
                          "descriptionInput.text", "systemctl", "keyring.get"):
            self.assertNotIn(forbidden, src)

    def test_host_refuses_non_disposable_invocation(self):
        result = subprocess.run(
            [sys.executable, "-I", "-B", str(HOST), "--host", "9", "10"],
            env={**os.environ, "POST_APOLLO_C5C_DISPOSABLE": "0"},
            capture_output=True, text=True, timeout=6)
        self.assertEqual(result.returncode, 2)
        self.assertIn("C5C_REFUSED_OUTSIDE_DISPOSABLE_TEST", result.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
