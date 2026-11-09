#!/usr/bin/env python3
"""C3e-Q: actual detached OpenPGP signatures, negative substitution and replay.

This signs only CI-created synthetic measurement statements and does not claim
a live C4b Silverblue producer or production authority.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parent / "c3e_release_trust/C3eQSignedGuestEvidence.py"
spec = importlib.util.spec_from_file_location("c3eq", SOURCE)
assert spec and spec.loader
Q = importlib.util.module_from_spec(spec)
spec.loader.exec_module(Q)


def gpg(home, *args):
    p = subprocess.run(["gpg", "--homedir", str(home), "--batch",
                        "--yes", "--pinentry-mode", "loopback",
                        "--passphrase", "", *args],
                       capture_output=True, text=True, timeout=20)
    if p.returncode:
        raise AssertionError("TEST_GPG_FAILED: " + p.stderr[-1000:])
    return p.stdout


def make_key(root, label):
    home = root / ("key-" + label)
    home.mkdir(mode=0o700)
    gpg(home, "--quick-generate-key", "C3eQ " + label +
        " <" + label + "@example.invalid>", "ed25519", "sign", "0")
    listing = gpg(home, "--with-colons", "--fingerprint", "--list-keys")
    fprs = [line.split(":")[9] for line in listing.splitlines()
            if line.startswith("fpr:")]
    assert len(fprs) == 1
    pub = root / (label + ".asc")
    pub.write_text(gpg(home, "--armor", "--export", fprs[0]))
    return home, fprs[0], pub


class C3eQSignedEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.keys = tempfile.TemporaryDirectory(prefix="c3eq-test-keys-")
        cls.dir = Path(cls.keys.name)
        cls.home, cls.fpr, cls.pub = make_key(cls.dir, "owner")
        cls.bad_home, cls.bad_fpr, cls.bad_pub = make_key(cls.dir, "attacker")

    @classmethod
    def tearDownClass(cls):
        cls.keys.cleanup()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="c3eq-signed-report-")
        self.addCleanup(self.temp.cleanup)
        base = Path(self.temp.name)
        self.report = base / "evidence.json"
        self.sig = base / "evidence.sig"
        self.challenge = b"CI-challenge-with-fixed-32-bytes"
        self.assertEqual(len(self.challenge), 32)
        self.rpm = "a" * 64
        self.script = "b" * 64
        self.interpreter = "c" * 64
        self.issuer = Q.OneUseTestChallenge(self.challenge)
        self.data = {
            "schema": Q.SCHEMA,
            "challenge_sha256": hashlib.sha256(self.challenge).hexdigest(),
            "release_rpm_sha256": self.rpm,
            "signed_script_sha256": self.script,
            "running_script_sha256": self.script,
            "service_pid": 4881,
            "process_start_ticks": "991337",
            "service_uid": 997,
            "service_gid": 997,
            "interpreter_sha256": self.interpreter,
            "systemd_unit": Q.UNIT,
            "dbus_owner_pid": 4881,
            "selinux_enforcing": True,
            "guest_provenance": Q.GUEST,
            "hostAuthenticated": False,
            "canApprove": False,
            "credentialActionsEnabled": False,
            "productionAuthority": False,
        }
        self._sign()

    def _sign(self, *, signer=None, raw=None):
        statement = (json.dumps(self.data, sort_keys=True,
                    separators=(",", ":")).encode()
                    if raw is None else raw)
        self.report.write_bytes(statement)
        gpg(signer or self.home, "--output", str(self.sig),
            "--detach-sign", str(self.report))

    def _args(self):
        return dict(evidence=self.report, signature=self.sig,
                    public_key=self.pub, pinned_signer=self.fpr,
                    expected_rpm_sha256=self.rpm,
                    expected_script_sha256=self.script,
                    expected_interpreter_sha256=self.interpreter,
                    expected_service_pid=4881,
                    expected_start_ticks="991337")

    def _verify(self, **changes):
        return self.issuer.verify(**{**self._args(), **changes})

    def _refuse(self, code, **changes):
        with self.assertRaises(Q.Refused) as err:
            self._verify(**changes)
        self.assertEqual(str(err.exception), code)

    def test_01_actual_detached_signed_test_report_and_one_use_receipt(self):
        result = self._verify()
        self.assertEqual(result["schema"], Q.RECEIPT_SCHEMA)
        self.assertTrue(result["signedEvidenceValidInCI"])
        self.assertTrue(result["challengeConsumedInMemory"])
        for name in ("signedGuestOriginAuthenticated", "installedGuestMeasured",
                     "hostAuthenticated", "canApprove", "credentialActionsEnabled",
                     "productionAuthority"):
            self.assertIs(result[name], False)
        self._refuse("CHALLENGE_ALREADY_CONSUMED")

    def test_02_replay_to_different_challenge_refused(self):
        self.issuer = Q.OneUseTestChallenge(b"Z" * 32)
        self._refuse("CHALLENGE_NOT_BOUND_TO_SIGNED_EVIDENCE")

    def test_03_unsigned_modified_evidence_refused(self):
        self.data["service_pid"] += 1
        self.report.write_text(json.dumps(self.data, sort_keys=True))
        self._refuse("SIGNED_EVIDENCE_CRYPTO_REFUSED")

    def test_04_other_valid_signer_cannot_claim_pinned_role(self):
        self._sign(signer=self.bad_home)
        self._refuse("SIGNED_EVIDENCE_CRYPTO_REFUSED")

    def test_05_wrong_public_key_refused(self):
        self._refuse("SIGNED_EVIDENCE_SIGNER_MISMATCH", public_key=self.bad_pub)

    def test_06_wrong_explicit_key_pin_refused(self):
        self._refuse("SIGNED_EVIDENCE_SIGNER_MISMATCH", pinned_signer=self.bad_fpr)

    def test_07_different_independently_pinned_script_hash_refused(self):
        self._refuse("SIGNED_ARTIFACT_OR_INTERPRETER_PIN_MISMATCH",
                     expected_script_sha256="d" * 64)

    def test_08_different_independently_pinned_rpm_hash_refused(self):
        self._refuse("SIGNED_ARTIFACT_OR_INTERPRETER_PIN_MISMATCH",
                     expected_rpm_sha256="d" * 64)

    def test_09_different_interpreter_pin_refused(self):
        self._refuse("SIGNED_ARTIFACT_OR_INTERPRETER_PIN_MISMATCH",
                     expected_interpreter_sha256="d" * 64)

    def test_10_process_reuse_pid_or_start_refused(self):
        self._refuse("SIGNED_RUNTIME_PROCESS_PIN_MISMATCH",
                     expected_start_ticks="991338")
        self._refuse("SIGNED_RUNTIME_PROCESS_PIN_MISMATCH",
                     expected_service_pid=4882)

    def test_11_even_valid_signature_claiming_grants_is_refused(self):
        self.data["canApprove"] = True
        self._sign()
        self._refuse("EVIDENCE_CLAIMS_AUTHORITY")

    def test_12_even_valid_signature_with_wrong_script_bytes_refused(self):
        self.data["running_script_sha256"] = "d" * 64
        self._sign()
        self._refuse("RUNNING_SCRIPT_DIFFERS_FROM_SIGNED_PACKAGE")

    def test_13_even_valid_signature_mismatching_dbus_pid_refused(self):
        self.data["dbus_owner_pid"] = 4882
        self._sign()
        self._refuse("DBUS_SYSTEMD_PROCESS_MISMATCH")

    def test_14_even_valid_signature_with_selinux_off_refused(self):
        self.data["selinux_enforcing"] = False
        self._sign()
        self._refuse("EVIDENCE_ROLE_OR_DOMAIN_REFUSED")

    def test_15_duplicate_json_keys_refused_after_signature(self):
        raw = (b'{"service_pid":1,"service_pid":2}')
        self._sign(raw=raw)
        self._refuse("DUPLICATE_EVIDENCE_FIELD")

    def test_16_symlinked_report_refused_without_following(self):
        real = self.report.with_suffix(".real")
        self.report.rename(real)
        self.report.symlink_to(real)
        self._refuse("EVIDENCE_FILE_UNSAFE")

    def test_17_world_writable_signature_refused(self):
        self.sig.chmod(0o666)
        self._refuse("SIGNATURE_FILE_UNSAFE")

    def test_18_explicit_challenge_length_and_pin_validation(self):
        with self.assertRaises(Q.Refused):
            Q.OneUseTestChallenge(b"too-short")
        self._refuse("INDEPENDENT_PIN_INVALID",
                     expected_script_sha256="bad")

    def test_19_signed_schema_cannot_self_claim_installed_guest(self):
        self.data["guest_provenance"] = "signed-production-attestation"
        self._sign()
        self._refuse("EVIDENCE_ROLE_OR_DOMAIN_REFUSED")

    def test_20_production_broker_not_exposed_to_test_receipt(self):
        q = SOURCE.parents[3] / "services/connections"
        self.assertIn("readonly property bool credentialActionsEnabled: false",
                      (q / "ConnectionsBroker.qml").read_text())
        self.assertIn("readonly property bool hostAuthenticated: false",
                      (q / "ConnectionsRequestStatus.qml").read_text())
        self.assertNotIn("C3eQSignedGuestEvidence", (
            q / "ConnectionsBroker.qml").read_text())


if __name__ == "__main__":
    unittest.main(verbosity=2)
