"""Signed enrollment and real /proc identity tests for Identity gateway.

A disposable Python child is used solely to verify Linux PID/start/argv and
actual script bytes against an independent signed manifest. CI keys and script
are NOT a production release, secure signed RPM, C5 operator intent or live
Identity Center service installation.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "identity"))

from desktop_command_gateway_v0 import KernelPeer
from signed_gateway_origin_probe_v0 import (
    _DOMAIN, _start_ticks, canonical, SCHEMA, PURPOSE,
    GatewayOriginObservation, OriginRefused, SignedGatewayOriginProbe,
)


def key_digest(key):
    raw = key.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    return hashlib.sha256(raw).hexdigest()


class GatewayProcessOriginTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="identity-live-probe-ci-")
        self.addCleanup(tmp.cleanup)
        self.root_path = Path(tmp.name)
        self.script = self.root_path / "identity-command-test-host.py"
        self.script.write_text("import time\ntime.sleep(20)\n", encoding="utf-8")
        self.script.chmod(0o644)
        self.process = subprocess.Popen(
            [sys.executable, str(self.script)],
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL)
        self.addCleanup(self._stop_process)
        self.release_root = Ed25519PrivateKey.generate()
        self.signer = Ed25519PrivateKey.generate()
        self.start_ticks = _start_ticks(self.process.pid)
        self.peer = KernelPeer(self.process.pid, os.getuid(), os.getgid())
        self.policy = dict(
            schema=SCHEMA, purpose=PURPOSE,
            releaseEpoch=3, releaseSequence=7,
            entrypointPath=str(self.script),
            entrypointSha256=hashlib.sha256(self.script.read_bytes()).hexdigest(),
            interpreterPath=os.path.realpath(sys.executable),
            receiptKeySha256=key_digest(self.signer),
            uid=os.getuid(), gid=os.getgid(),
        )

    def _stop_process(self):
        if self.process.poll() is None:
            self.process.terminate()
        try:
            self.process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait(timeout=3)

    def _probe(self, *, policy=None, root=None, signer=None,
               signature=None, expected_pid=None, expected_ticks=None,
               min_epoch=3, min_sequence=7, disposable=True):
        value = canonical(self.policy if policy is None else policy)
        private_root = self.release_root if root is None else root
        return SignedGatewayOriginProbe(
            signed_policy=value,
            policy_signature=private_root.sign(_DOMAIN + value)
                if signature is None else signature,
            pinned_release_root=self.release_root.public_key(),
            pinned_receipt_key=(signer or self.signer).public_key(),
            minimum_epoch=min_epoch,
            minimum_sequence=min_sequence,
            expected_pid=self.process.pid if expected_pid is None else expected_pid,
            expected_start_ticks=self.start_ticks if expected_ticks is None else expected_ticks,
            disposable_test_mode=disposable,
        )

    def test_real_linux_process_matches_independent_signed_entrypoint_and_key(self):
        probe = self._probe()
        result = probe.inspect(self.peer)
        self.assertIsInstance(result, GatewayOriginObservation)
        self.assertTrue(result.process_matches_enrollment)
        self.assertTrue(result.signer_matches_enrollment)
        self.assertEqual(result.observed_pid, self.process.pid)
        self.assertEqual(result.observed_start_ticks, self.start_ticks)
        self.assertFalse(result.production_authority)
        self.assertFalse(result.can_begin_sign_in)
        self.assertFalse(result.can_connect_provider)
        self.assertTrue(probe.consistent(self.peer))

    def test_disposable_script_never_counts_as_root_owned_installed_service(self):
        self.assertFalse(self._probe(disposable=False).consistent(self.peer))
        with self.assertRaises(OriginRefused):
            self._probe(disposable=False).inspect(self.peer)

    def test_reject_wrong_signer_or_release_authority(self):
        with self.assertRaises(OriginRefused):
            self._probe(signer=Ed25519PrivateKey.generate())
        with self.assertRaises(OriginRefused):
            self._probe(root=Ed25519PrivateKey.generate())
        with self.assertRaises(OriginRefused):
            self._probe(signature=b"\x00" * 64)

    def test_reject_policy_downgrade_role_and_foreign_script(self):
        with self.assertRaises(OriginRefused):
            self._probe(min_epoch=4)
        with self.assertRaises(OriginRefused):
            self._probe(min_sequence=8)
        for modification in (
            {"purpose": "post-apollo.connections.status-host.v0"},
            {"entrypointPath": "/../../tmp/host"},
            {"entrypointSha256": "0" * 64},
            {"releaseSequence": False},
            {"uid": True},
            {"receiptKeySha256": "n" * 64},
            {"newAdminOverride": True},
        ):
            with self.subTest(modification=modification):
                policy = dict(self.policy, **modification)
                if "entrypointSha256" in modification:
                    # An authority-signed wrong digest is allowed to parse,
                    # but MUST fail when it meets the actual process bytes.
                    self.assertFalse(self._probe(policy=policy).consistent(self.peer))
                else:
                    with self.assertRaises(OriginRefused):
                        self._probe(policy=policy)

    def test_kernel_pid_start_and_uid_gid_cannot_be_forged(self):
        probe = self._probe()
        self.assertFalse(probe.consistent(KernelPeer(
            self.process.pid + 1, self.peer.uid, self.peer.gid)))
        self.assertFalse(probe.consistent(KernelPeer(
            self.process.pid, self.peer.uid + 1, self.peer.gid)))
        self.assertFalse(probe.consistent(KernelPeer(
            self.process.pid, self.peer.uid, self.peer.gid + 1)))
        self.assertFalse(self._probe(expected_ticks=str(
            int(self.start_ticks) + 1)).consistent(self.peer))
        self.assertFalse(self._probe(expected_pid=self.process.pid + 1
                                      ).consistent(self.peer))

    def test_script_file_mutation_and_symlink_are_denied(self):
        probe = self._probe()
        self.assertTrue(probe.consistent(self.peer))
        self.script.write_text("import time\ntime.sleep(21)\n", encoding="utf-8")
        self.assertFalse(probe.consistent(self.peer))
        self.script.unlink()
        replacement = self.root_path / "replacement.py"
        replacement.write_text("import time\ntime.sleep(20)\n", encoding="utf-8")
        self.script.symlink_to(replacement)
        self.assertFalse(probe.consistent(self.peer))

    def test_wrong_interpreter_and_extra_argv_denied(self):
        bad = dict(self.policy, interpreterPath="/bin/false")
        self.assertFalse(self._probe(policy=bad).consistent(self.peer))
        second = subprocess.Popen(
            [sys.executable, str(self.script), "unapproved-extra-arg"],
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL)
        self.addCleanup(lambda: self._stop_extra(second))
        other_start = _start_ticks(second.pid)
        probe = self._probe(expected_pid=second.pid, expected_ticks=other_start)
        self.assertFalse(probe.consistent(
            KernelPeer(second.pid, os.getuid(), os.getgid())))

    @staticmethod
    def _stop_extra(process):
        if process.poll() is None:
            process.terminate()
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=3)

    def test_terminated_pid_never_revives_prior_evidence(self):
        probe = self._probe()
        self.assertTrue(probe.consistent(self.peer))
        self._stop_process()
        self.assertFalse(probe.consistent(self.peer))


if __name__ == "__main__":
    unittest.main()
