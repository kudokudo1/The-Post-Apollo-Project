#!/usr/bin/env python3
"""CI-only real OpenPGP tests of out-of-band root pin and release policy.

All three keys are created by GnuPG in TemporaryDirectory and discarded after
test completion. No production release identity, operator key, RPM install, or
credential permission is present in this suite.
"""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "tests/connections/c3e_release_trust/C3eReleaseAdmission.py"
spec = importlib.util.spec_from_file_location("c3e_release_policy", SOURCE)
assert spec and spec.loader
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


def run(cmd, timeout=25):
    result = subprocess.run(cmd, check=False, capture_output=True, text=True,
                            timeout=timeout, stdin=subprocess.DEVNULL)
    if result.returncode:
        raise AssertionError("test fixture command failed: " +
                             " ".join(cmd[:4]) + "\n" +
                             result.stderr[-1200:])
    return result.stdout


def gpg(home, *args):
    return run(["gpg", "--homedir", str(home), "--batch", "--yes",
                "--pinentry-mode", "loopback", "--passphrase", "", *args])


def create_identity(home, identity):
    home.mkdir(mode=0o700)
    os.chmod(home, 0o700)
    gpg(home, "--quick-generate-key", identity, "ed25519", "sign", "0")
    listed = gpg(home, "--with-colons", "--fingerprint", "--list-keys")
    fingerprints = [line.split(":")[9] for line in listed.splitlines()
                    if line.startswith("fpr:")]
    if len(fingerprints) != 1:
        raise AssertionError("test signer has wrong fingerprint count")
    return fingerprints[0]


class C3eReleaseTrustTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.storage = tempfile.TemporaryDirectory(prefix="c3e-crypto-ci-")
        cls.temp = Path(cls.storage.name)
        cls.keys = {}
        cls.fprs = {}
        for name in ("root", "signerA", "signerB"):
            home = cls.temp / name
            cls.keys[name] = home
            cls.fprs[name] = create_identity(home, "C3e Disposable " + name +
                                             " <" + name + "@example.invalid>")
            cls.public = getattr(cls, "public", {})
            keyfile = cls.temp / (name + ".asc")
            keyfile.write_text(gpg(home, "--armor", "--export", cls.fprs[name]))
            cls.public[name] = keyfile

    @classmethod
    def tearDownClass(cls):
        cls.storage.cleanup()

    def setUp(self):
        self.work = tempfile.TemporaryDirectory(prefix="c3e-case-", dir=self.temp)
        self.directory = Path(self.work.name)
        self.artifact = self.directory / "synthetic-test-package.rpm"
        self.artifact.write_bytes(b"C3e offline fake RPM marker; not installable\n")
        self.policy_file = self.directory / "policy.json"
        self.policy_sig = self.directory / "policy.sig"
        self.manifest_file = self.directory / "manifest.json"
        self.manifest_sig = self.directory / "manifest.sig"
        self.policy = {
            "schema": gate.POLICY_SCHEMA,
            "release_id": gate.RELEASE_ID,
            "epoch": 3,
            "min_sequence": 8,
            "signers": [{"fingerprint": self.fprs["signerA"], "state": "active"}],
            "approved_artifacts": [self.metadata(8)],
        }
        self.manifest = {
            "schema": gate.MANIFEST_SCHEMA, "release_id": gate.RELEASE_ID,
            **self.metadata(8),
        }
        self.root_signer = "root"
        self.release_signer = "signerA"
        self.root_pin = self.fprs["root"]
        self.trusted_root_file = self.public["root"]
        self.trusted_epoch_floor = 3
        self.trusted_sequence_floor = 8

    def tearDown(self):
        self.work.cleanup()

    def metadata(self, sequence):
        data = self.artifact.read_bytes()
        return {"sequence": sequence, "sha256": hashlib.sha256(data).hexdigest(),
                "size": len(data)}

    def write_signed_policy(self):
        self.policy_file.write_text(json.dumps(self.policy, sort_keys=True,
                                               separators=(",", ":")))
        gpg(self.keys[self.root_signer], "--output", str(self.policy_sig),
            "--detach-sign", str(self.policy_file))

    def write_signed_manifest(self):
        self.manifest_file.write_text(json.dumps(self.manifest, sort_keys=True,
                                                 separators=(",", ":")))
        gpg(self.keys[self.release_signer], "--output", str(self.manifest_sig),
            "--detach-sign", str(self.manifest_file))

    def result(self, *, reissue=True):
        if reissue:
            self.write_signed_policy()
            self.write_signed_manifest()
        try:
            return gate.verify(
                self.trusted_root_file, self.root_pin,
                self.policy_file, self.policy_sig,
                self.public[self.release_signer], self.manifest_file,
                self.manifest_sig, self.artifact, self.trusted_epoch_floor,
                self.trusted_sequence_floor)
        except gate.Refused as error:
            return "REFUSED:" + str(error)

    def assertRefused(self, reason, *, reissue=True):
        self.assertEqual(self.result(reissue=reissue), "REFUSED:" + reason)

    def test_01_signed_root_delegation_and_digest_admitted_ci_only(self):
        self.assertEqual(self.result(), "C3E_TEST_POLICY_ACCEPTED_NO_PRODUCTION_AUTH")

    def test_02_swapped_trust_root_public_key_cannot_self_authorize(self):
        self.trusted_root_file = self.public["signerB"]
        self.assertRefused("ROOT_PIN_MISMATCH")

    def test_03_candidate_cannot_supply_a_replacement_root(self):
        self.root_signer = "signerA"
        self.assertRefused("INVALID_DETACHED_SIGNATURE")

    def test_04_policy_rewrite_without_trusted_root_signature_fails(self):
        self.write_signed_policy()
        self.write_signed_manifest()
        self.policy_file.write_text(self.policy_file.read_text() + " ")
        self.assertRefused("INVALID_DETACHED_SIGNATURE", reissue=False)

    def test_05_unapproved_candidate_signer_even_with_valid_signature_fails(self):
        self.release_signer = "signerB"
        self.assertRefused("UNAPPROVED_SIGNER")

    def test_06_revoked_candidate_signer_fails_despite_valid_signature(self):
        self.policy["signers"][0]["state"] = "revoked"
        self.assertRefused("REVOKED_SIGNER")

    def test_07_root_signed_rotation_can_admit_b_then_revoke_a(self):
        self.policy["signers"] = [
            {"fingerprint": self.fprs["signerA"], "state": "revoked"},
            {"fingerprint": self.fprs["signerB"], "state": "active"},
        ]
        self.release_signer = "signerB"
        self.assertEqual(self.result(), "C3E_TEST_POLICY_ACCEPTED_NO_PRODUCTION_AUTH")
        self.release_signer = "signerA"
        self.assertRefused("REVOKED_SIGNER")

    def test_08_old_root_signed_policy_epoch_fails_external_floor(self):
        self.policy["epoch"] = 2
        self.assertRefused("POLICY_ROLLBACK_REFUSED")

    def test_09_old_release_sequence_fails_external_floor(self):
        self.manifest["sequence"] = 7
        self.policy["min_sequence"] = 7
        self.policy["approved_artifacts"] = [self.metadata(7)]
        self.assertRefused("RELEASE_ROLLBACK_REFUSED")

    def test_10_tampered_artifact_fails_even_with_original_valid_signatures(self):
        self.write_signed_policy()
        self.write_signed_manifest()
        self.artifact.write_bytes(self.artifact.read_bytes() + b"MODIFIED")
        self.assertRefused("ARTIFACT_SIZE_MISMATCH", reissue=False)

    def test_11_root_approved_digest_refuses_otherwise_valid_signed_release(self):
        self.policy["approved_artifacts"][0]["sha256"] = "f" * 64
        self.assertRefused("RELEASE_NOT_APPROVED_BY_ROOT")

    def test_12_unsigned_manifest_mutation_fails_openpgp(self):
        self.write_signed_policy()
        self.write_signed_manifest()
        self.manifest_file.write_text(self.manifest_file.read_text() + " ")
        self.assertRefused("INVALID_DETACHED_SIGNATURE", reissue=False)

    def test_13_duplicate_policy_signer_records_are_refused(self):
        self.policy["signers"].append(copy.deepcopy(self.policy["signers"][0]))
        self.assertRefused("DUPLICATE_SIGNER")

    def test_14_untrusted_additional_json_data_fails(self):
        self.manifest["activateService"] = True
        self.assertRefused("MANIFEST_SHAPE_REFUSED")

    def test_15_no_external_monotonic_policy_floor_is_denied(self):
        self.trusted_epoch_floor = 0
        self.assertRefused("NO_EXTERNAL_EPOCH_FLOOR")

    def test_16_no_external_monotonic_release_floor_is_denied(self):
        self.trusted_sequence_floor = 0
        self.assertRefused("NO_EXTERNAL_SEQUENCE_FLOOR")

    def test_17_missing_root_key_or_signature_is_denied(self):
        self.trusted_root_file = self.directory / "unknown.asc"
        self.assertRefused("UNTRUSTED_KEY_FILE")

    def test_18_production_broker_remains_disabled(self):
        base = ROOT / "services/connections"
        self.assertIn("readonly property bool credentialActionsEnabled: false",
                      (base / "ConnectionsBroker.qml").read_text())
        self.assertIn("readonly property bool hostAuthenticated: false",
                      (base / "ConnectionsRequestStatus.qml").read_text())
        source = SOURCE.read_text()
        self.assertNotIn("rpm --import", source)
        self.assertNotIn("systemctl start", source)
        self.assertNotIn("secret-tool", source)
        for item in (*base.glob("*.qml"), *base.glob("*.js"), base / "qmldir"):
            self.assertNotIn("C3eReleaseAdmission", item.read_text(), item)


if __name__ == "__main__":
    unittest.main(verbosity=2)
