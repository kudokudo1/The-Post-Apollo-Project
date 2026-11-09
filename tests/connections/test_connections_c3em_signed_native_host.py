#!/usr/bin/env python3
"""C3e-M real GPG signed native Linux host + C3e-L observation, CI only.

Use only the disposable GitHub Ubuntu runner through sudo -n python3 -B.
All signing keys, signed binaries and root-owned sockets are generated inside
ephemeral test directories. Not a Fedora installation or real enrollment.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
HERE = ROOT / "tests/connections/c3e_release_trust"
SOURCE = HERE / "C3eMSignedHostOrigin.py"
NATIVE = ROOT / "tests/connections/fixtures/C3eMSignedNativeStatusHost.c"
LTEST = ROOT / "tests/connections/test_connections_c3el_host_status_observation.py"


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


M = load(SOURCE, "c3em_host_verifier")
L = load(LTEST, "c3em_previous_c3el")


def command(args, *, timeout=25):
    result = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            text=True, timeout=timeout, stdin=subprocess.DEVNULL)
    if result.returncode:
        raise AssertionError("C3EM_TEST_TOOL_FAILED " + repr(args[:3]) +
                             " stderr=" + result.stderr[-900:])
    return result.stdout


def gpg(home, *args):
    return command(["gpg", "--homedir", str(home), "--batch", "--yes",
                    "--pinentry-mode", "loopback", "--passphrase", "", *args])


def issue_key(root, name):
    home = root / ("gpg-" + name)
    home.mkdir(mode=0o700)
    gpg(home, "--quick-generate-key",
        "C3eM " + name + " <" + name + "@example.invalid>",
        "ed25519", "sign", "0")
    raw = gpg(home, "--with-colons", "--fingerprint", "--list-keys")
    pins = [line.split(":")[9] for line in raw.splitlines()
            if line.startswith("fpr:")]
    assert len(pins) == 1
    exported = root / (name + "-public.asc")
    exported.write_text(gpg(home, "--armor", "--export", pins[0]))
    return home, exported, pins[0]


def document(path, body):
    path.write_text(json.dumps(body, sort_keys=True,
                               separators=(",", ":")) + "\n")
    path.chmod(0o600)


class C3eMSignedHostTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if os.geteuid() != 0 or not sys.platform.startswith("linux"):
            raise RuntimeError("C3EM_DISPOSABLE_GITHUB_ROOT_REQUIRED")
        L.C3eLHostStatusObservationTests.setUpClass()
        cls.keys_temp = tempfile.TemporaryDirectory(prefix="c3em-keys-", dir="/run")
        cls.home = Path(cls.keys_temp.name)
        cls.home.chmod(0o700)
        cls.root_key, cls.root_public, cls.root_pin = issue_key(cls.home, "root")
        cls.delegate_key, cls.delegate_public, cls.delegate_pin = issue_key(
            cls.home, "delegate")
        cls.attacker_key, cls.attacker_public, cls.attacker_pin = issue_key(
            cls.home, "attacker")
        cls.native = cls.home / "signed-native-status-host"
        cls.alt_native = cls.home / "different-native-status-host"
        for binary, level in ((cls.native, "-O2"), (cls.alt_native, "-O0")):
            command(["gcc", "-std=gnu11", "-Wall", "-Wextra", "-Werror",
                     level, "-fPIE", "-pie", "-o", str(binary), str(NATIVE)])
        assert cls.native.read_bytes() != cls.alt_native.read_bytes()
        cls.policy = cls.home / "policy.json"
        cls.policy_sig = cls.home / "policy.sig"
        cls.manifest = cls.home / "manifest.json"
        cls.manifest_sig = cls.home / "manifest.sig"
        cls.policy_doc = {
            "schema": M.POLICY_SCHEMA, "role": M.ROLE, "epoch": 2,
            "min_sequence": 4, "delegated_fingerprint": cls.delegate_pin,
        }
        cls.manifest_doc = {
            "schema": M.MANIFEST_SCHEMA, "role": M.ROLE,
            "epoch": 2, "sequence": 4,
            "sha256": hashlib.sha256(cls.native.read_bytes()).hexdigest(),
            "size": cls.native.stat().st_size,
        }
        document(cls.policy, cls.policy_doc)
        document(cls.manifest, cls.manifest_doc)
        gpg(cls.root_key, "--output", str(cls.policy_sig), "--detach-sign",
            str(cls.policy))
        gpg(cls.delegate_key, "--output", str(cls.manifest_sig),
            "--detach-sign", str(cls.manifest))

    @classmethod
    def tearDownClass(cls):
        cls.keys_temp.cleanup()

    def setUp(self):
        self.previous = L.C3eLHostStatusObservationTests(
            "test_01_reverse_kernel_host_identity_and_floor_observed")
        self.previous.setUp()
        self.addCleanup(self.previous.doCleanups)
        self.fx = self.previous.fx
        self.marker = self.fx.private / ".c3em-test-only"
        self.marker.write_text(M.MARKER + "\n")
        self.marker.chmod(0o600)

    def _start(self, binary=None):
        client = self.previous._start_client()
        enrolled = hashlib.sha256(json.dumps([
            "c3ek-runner-test-01", "A" * 40, "B" * 40
        ], separators=(",", ":")).encode()).hexdigest()
        host = subprocess.Popen([
            str(binary or self.native), str(self.fx.socket), "--read-only",
            str(client.pid), str(self.fx.client_uid), str(self.fx.client_gid),
            enrolled, "4", "9",
        ], stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, bufsize=1)
        self.addCleanup(self.fx._stop, host)
        ready = host.stdout.readline().strip()
        if ready != "C3EM_READY // SIGNED_NATIVE_SYNTHETIC_READ_ONLY":
            self.fail("C3EM_NATIVE_HOST_STARTUP rc=%r stderr=%r" % (
                host.poll(), host.stderr.read()[-1400:]))
        return client, host, self.previous._pins(host)

    def _verify(self, host, *, paths=None, **overrides):
        args = {
            "ci_fixture_root": self.fx.base,
            "host_pid": host.pid,
            "host_start": self.previous._pins(host)["expected_host_start"],
            "root_public": self.root_public,
            "root_pin": self.root_pin,
            "policy": self.policy,
            "policy_signature": self.policy_sig,
            "delegate_public": self.delegate_public,
            "manifest": self.manifest,
            "manifest_signature": self.manifest_sig,
            "minimum_epoch": 2,
            "minimum_sequence": 4,
        }
        if paths:
            args.update(paths)
        args.update(overrides)
        return M.verify(**args)

    def refused(self, expected, host, *, paths=None, **changes):
        with self.assertRaises(M.Refused) as ex:
            self._verify(host, paths=paths, **changes)
        self.assertEqual(str(ex.exception), expected)

    def test_01_actual_signed_native_elf_and_nonroot_status_transport(self):
        before = hashlib.sha256(self.fx.witness.read_bytes()).hexdigest()
        client, host, pins = self._start()
        verification = self._verify(host)
        self.assertTrue(verification["signed_native_elf_verified_in_ci"])
        self.assertEqual(verification["host_pid"], pins["expected_host_pid"])
        self.assertIs(verification["hostAuthenticated"], False)
        self.assertIs(verification["canApprove"], False)
        self.assertIs(verification["credentialActionsEnabled"], False)
        observation = self.previous._ask(client, pins)["evidence"]
        self.assertEqual(observation["host_uid_observed"], 0)
        self.assertEqual(observation["observed_policy_epoch"], 4)
        self.assertEqual(observation["observed_release_sequence"], 9)
        self.assertEqual(observation["enrollment_sha256"],
                         pins["expected_enrollment_sha256"])
        self.assertIs(observation["hostAuthenticated"], False)
        self.assertEqual(host.wait(timeout=5), 0)
        self.assertEqual(hashlib.sha256(self.fx.witness.read_bytes()).hexdigest(),
                         before)

    def test_02_same_uid_other_native_elf_cannot_claim_signed_host_role(self):
        client, host, pins = self._start(self.alt_native)
        self.refused("SIGNED_RUNNING_HOST_BYTES_MISMATCH", host)

    def test_03_root_public_key_substitution_refused(self):
        client, host, pins = self._start()
        self.refused("PINNED_ROOT_IDENTITY_REFUSED", host, paths={
            "root_public": self.attacker_public,
        })

    def test_04_false_root_pin_does_not_create_new_trust(self):
        client, host, pins = self._start()
        self.refused("PINNED_ROOT_IDENTITY_REFUSED", host,
                     root_pin=self.attacker_pin)

    def test_05_wrong_manifest_signer_rejected(self):
        client, host, pins = self._start()
        bad_sig = self.fx.private / "attacker-manifest.sig"
        gpg(self.attacker_key, "--output", str(bad_sig), "--detach-sign",
            str(self.manifest))
        self.refused("UNAPPROVED_HOST_DELEGATE", host, paths={
            "delegate_public": self.attacker_public,
            "manifest_signature": bad_sig,
        })

    def test_06_changed_manifest_after_signing_refused(self):
        client, host, pins = self._start()
        changed = self.fx.private / "changed-manifest.json"
        document(changed, {**self.manifest_doc, "sha256": "0" * 64})
        self.refused("SIGNED_RELEASE_CRYPTO_REFUSED", host, paths={
            "manifest": changed,
        })

    def test_07_valid_root_signature_wrong_host_role_denied(self):
        client, host, pins = self._start()
        wrong = self.fx.private / "other-role-policy.json"
        wrong_sig = self.fx.private / "other-role-policy.sig"
        document(wrong, {**self.policy_doc, "role": "postapollo.other"})
        gpg(self.root_key, "--output", str(wrong_sig), "--detach-sign",
            str(wrong))
        self.refused("SIGNED_HOST_ROLE_OR_POLICY_FLOOR_REFUSED", host, paths={
            "policy": wrong, "policy_signature": wrong_sig,
        })

    def test_08_epoch_floor_refuses_signed_old_policy(self):
        client, host, pins = self._start()
        self.refused("SIGNED_HOST_ROLE_OR_POLICY_FLOOR_REFUSED", host,
                     minimum_epoch=3)

    def test_09_sequence_floor_refuses_signed_old_executable(self):
        client, host, pins = self._start()
        self.refused("SIGNED_HOST_RELEASE_FLOOR_REFUSED", host,
                     minimum_sequence=5)

    def test_10_kernel_start_pin_changed_refused(self):
        client, host, pins = self._start()
        self.refused("HOST_PROCESS_IDENTITY_CHANGED", host, host_start="1")

    def test_11_test_marker_removed_blocks_even_valid_signed_host(self):
        client, host, pins = self._start()
        self.marker.unlink()
        self.refused("TEST_ENROLLMENT_MARKER_MISSING", host)

    def test_12_symlink_source_signature_refused_not_followed(self):
        client, host, pins = self._start()
        alias = self.fx.private / "delegate-alias.asc"
        alias.symlink_to(self.delegate_public)
        self.refused("SIGNING_INPUT_UNAVAILABLE", host, paths={
            "delegate_public": alias,
        })

    def test_13_running_python_interpreter_cannot_masquerade_as_signed_elf(self):
        client = self.previous._start_client()
        # A *Python interpreter* may itself be a valid ELF, but it is not
        # the separately delegated signed native host executable.
        self.refused("SIGNED_RUNNING_HOST_BYTES_MISMATCH", client,
                     host_pid=client.pid,
                     host_start=self.previous.fx.kernel_start(client.pid)
                     if hasattr(self.previous.fx, "kernel_start")
                     else L.k.kernel_start(client.pid))

    def test_14_same_uid_client_cannot_read_root_private_ledger(self):
        client = self.previous._start_client()
        outcome = self.previous._ask(client, {
            "socket_path": str(self.fx.socket),
            "expected_host_pid": os.getpid(),
            "expected_host_uid": 0,
            "expected_host_gid": 0,
            "expected_host_start": L.k.kernel_start(os.getpid()),
            "expected_enrollment_sha256": "0" * 64,
            "minimum_policy_epoch": 4,
            "minimum_release_sequence": 9,
        })
        self.assertIn("refused", outcome)
        self.assertEqual(self.fx.witness.stat().st_uid, 0)

    def test_15_production_broker_and_silverblue_owners_untouched(self):
        services = ROOT / "services/connections"
        self.assertIn("readonly property bool credentialActionsEnabled: false",
                      (services / "ConnectionsBroker.qml").read_text())
        self.assertIn("readonly property bool hostAuthenticated: false",
                      (services / "ConnectionsRequestStatus.qml").read_text())
        for path in (*services.glob("*.qml"), *services.glob("*.js"),
                     services / "qmldir"):
            self.assertNotIn("C3eMSignedHostOrigin", path.read_text())


if __name__ == "__main__":
    unittest.main(verbosity=2)
