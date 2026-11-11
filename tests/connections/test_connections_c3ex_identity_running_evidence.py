#!/usr/bin/env python3
"""C3e-X adversarial CI-only running Identity witness and signed-denial tests."""
from __future__ import annotations

import base64
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import unittest

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "tests/connections/c3e_release_trust/C3eXIdentityRunningEvidence.py"
spec = importlib.util.spec_from_file_location("c3ex_runtime", SOURCE)
assert spec and spec.loader
X = importlib.util.module_from_spec(spec)
spec.loader.exec_module(X)


def sha(value: bytes):
    return hashlib.sha256(value).hexdigest()


class C3eXRunningIdentityDenialTests(unittest.TestCase):
    def setUp(self):
        self.key = Ed25519PrivateKey.generate()
        self.issuer = X.Receipt.ReceiptIssuer(self.key)
        self.expected = {
            "rpmSha256": sha(b"signed-ci-rpm"),
            "entrypointSha256": sha(b"installed-deny-only-entrypoint"),
            "exeSha256": sha(b"byte-identical-ci-python"),
            "exePath": X.EXECUTABLE, "unit": X.UNIT,
            "pid": 1484, "startTicks": 543210, "uid": 992, "gid": 995,
            "cgroup": X.CGROUP, "selinux": X.SELINUX,
            "socketPath": X.SOCKET,
        }
        self.records = []
        self.frames = []
        for i, action in enumerate(X.ACTIONS):
            nonce = base64.urlsafe_b64encode(bytes([i + 1]) * 32).decode("ascii").rstrip("=")
            rid = None if i == 0 else X.REQUEST_ID
            self.records.append({
                "action": action, "commandRequestId": rid,
                "clientNonce": nonce,
                "before": copy.deepcopy(self.expected),
                "after": copy.deepcopy(self.expected),
                "peer": {"pid": 1484, "uid": 992, "gid": 995},
            })
            self.frames.append(self._seal(self.issuer, action, rid, nonce))

    def _seal(self, issuer, action, rid, nonce):
        legacy = X.Receipt._canonical({
            "schema": X.Receipt.LEGACY_RECEIPT_SCHEMA,
            "state": "UNAVAILABLE", "requestId": None,
        }) + b"\n"
        return issuer.seal(action, rid, nonce, legacy)

    def encode(self):
        return X._canonical({
            "schema": X.SCHEMA, "role": X.ROLE, "records": self.records,
        }) + b"\n"

    def inspect(self, **changes):
        args = dict(
            evidence_line=self.encode(), signed_receipts=self.frames,
            independently_pinned_receipt_key=self.key.public_key(),
            independently_measured=self.expected,
        )
        args.update(changes)
        return X.inspect_running_denials(**args)

    def refused(self, **changes):
        with self.assertRaises(X.Refused):
            self.inspect(**changes)

    def test_01_four_real_ed25519_denials_and_snapshots_only_return_ci_flags(self):
        result = self.inspect()
        self.assertEqual(result["schema"], X.SCHEMA)
        self.assertIs(result["fourSignedDenialsConsistentInCI"], True)
        self.assertIs(result["fourKernelSnapshotsAgreeWithCallerPinsInCI"], True)
        self.assertIs(result["receiptSequenceBoundInCI"], True)
        for name in X.NEGATIVE:
            self.assertIs(result[name], False)

    def test_02_signer_must_be_explicit_and_correctly_pinned(self):
        self.refused(independently_pinned_receipt_key=None)
        self.refused(independently_pinned_receipt_key=Ed25519PrivateKey.generate().public_key())

    def test_03_tampered_signed_receipt_refused_even_when_snapshots_agree(self):
        self.frames[0] = self.frames[0].replace(b"UNAVAILABLE", b"UNAVAILABLZ")
        self.refused()

    def test_04_duplicate_client_nonce_refused(self):
        self.records[1]["clientNonce"] = self.records[0]["clientNonce"]
        self.refused()

    def test_05_wrong_action_order_and_missing_signed_frames_refused(self):
        self.records[0]["action"] = "STATUS"
        self.refused()
        self.records[0]["action"] = "BEGIN"
        self.refused(signed_receipts=self.frames[:3])
        self.refused(signed_receipts=[*self.frames, self.frames[0]])

    def test_06_snapshot_pid_start_or_uid_replacement_refused(self):
        for name, value in (("pid", 1485), ("startTicks", 543211), ("uid", 994)):
            with self.subTest(name=name):
                old = self.records[2]["after"][name]
                self.records[2]["after"][name] = value
                self.refused()
                self.records[2]["after"][name] = old

    def test_07_wrong_cgroup_selinux_or_executable_checksum_refused(self):
        for name, value in (
            ("cgroup", "/system.slice/evil.service"),
            ("selinux", "system_u:system_r:unconfined_service_t:s0"),
            ("exeSha256", sha(b"changed-python-interpreter")),
            ("rpmSha256", sha(b"different-installed-rpm")),
            ("entrypointSha256", sha(b"different-installed-entrypoint")),
        ):
            with self.subTest(name=name):
                old = self.records[1]["before"][name]
                self.records[1]["before"][name] = value
                self.refused()
                self.records[1]["before"][name] = old

    def test_08_wrong_kernel_socket_peer_refused(self):
        self.records[3]["peer"]["pid"] = 15
        self.refused()

    def test_09_wrong_or_self_reported_independent_pins_cannot_override(self):
        self.refused(independently_measured={**self.expected, "rpmSha256": sha(b"else")})
        self.refused(independently_measured={**self.expected, "uid": True})
        self.refused(independently_measured={**self.expected, "unit": "fake.service"})
        self.refused(independently_measured={**self.expected, "selinux":
                   "system_u:system_r:unconfined_service_t:s0"})
        self.refused(independently_measured={})

    def test_10_host_signer_instance_replacement_refused_even_with_valid_key(self):
        new = X.Receipt.ReceiptIssuer(self.key)
        self._seal(new, "BEGIN", None,
                   base64.urlsafe_b64encode(b"a" * 32).decode().rstrip("="))
        self._seal(new, "BEGIN", None,
                   base64.urlsafe_b64encode(b"b" * 32).decode().rstrip("="))
        self.frames[2] = self._seal(new, "CANCEL", X.REQUEST_ID,
                                    self.records[2]["clientNonce"])
        self.frames[3] = self._seal(new, "RECOVER", X.REQUEST_ID,
                                    self.records[3]["clientNonce"])
        self.refused()

    def test_11_valid_signature_with_noninitial_sequence_refused(self):
        issuer = X.Receipt.ReceiptIssuer(self.key)
        self._seal(issuer, "BEGIN", None,
                   base64.urlsafe_b64encode(b"z" * 32).decode().rstrip("="))
        self.frames = [self._seal(issuer, r["action"], r["commandRequestId"],
                                   r["clientNonce"]) for r in self.records]
        self.refused()

    def test_12_duplicate_noncanonical_or_extra_report_fields_refused(self):
        raw = self.encode()
        self.refused(evidence_line=raw.replace(b'"schema":', b'"schema":"x","schema":', 1))
        self.refused(evidence_line=raw.replace(b',"role":', b', "role":', 1))
        self.refused(evidence_line=raw + b"\n")
        self.refused(evidence_line=b"x" * 16385)
        document = json.loads(raw)
        document["productionAuthority"] = True
        self.refused(evidence_line=X._canonical(document) + b"\n")

    def test_13_strict_record_and_snapshot_rosters_refused(self):
        del self.records[0]["before"]["entrypointSha256"]
        self.refused()
        self.records[0]["before"]["entrypointSha256"] = self.expected["entrypointSha256"]
        self.records[1]["unexpectedGrant"] = True
        self.refused()

    def test_14_receipt_from_other_action_nonce_or_request_refused(self):
        changed = X.Receipt.ReceiptIssuer(self.key)
        self.frames = [self._seal(changed, r["action"], r["commandRequestId"],
                                   r["clientNonce"]) for r in self.records]
        self.records[0]["clientNonce"] = base64.urlsafe_b64encode(b"x" * 32).decode().rstrip("=")
        self.refused()

    def test_15_disabled_credentials_and_no_live_host_or_login_path(self):
        source = SOURCE.read_text()
        for forbidden in (
            "HostBoundary.authenticated(", "SignedIdentityCommandClient(",
            "InstalledIdentityCommandAdapterV1(", "socket.socket(",
            "subprocess.run(", "systemctl start ", "rpm-ostree install",
            "canBeginSignIn\": True", "productionAuthority\": True",
        ):
            self.assertNotIn(forbidden, source)
        for name in X.NEGATIVE:
            self.assertIn('"' + name + '": False', source)
        broker = (ROOT / "services/connections/ConnectionsBroker.qml").read_text()
        self.assertIn("readonly property bool credentialActionsEnabled: false", broker)


if __name__ == "__main__":
    unittest.main(verbosity=2)
