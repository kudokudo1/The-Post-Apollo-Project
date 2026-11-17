#!/usr/bin/env python3
"""C3e-AH: signed release ↔ real Linux process join, deny-only adversarial CI."""
from __future__ import annotations

import hashlib
import importlib.util
import os
from pathlib import Path
import sys
import unittest
from unittest import mock

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

ROOT = Path(__file__).resolve().parents[2]

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError("C3EAH_REQUIRED_TEST_FIXTURE_UNAVAILABLE")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod

H = load("c3eah_source_live", ROOT / "tests/connections/c3e_release_trust/C3eAHSignedReleaseLiveOrigin.py")
AGTEST = load("c3eah_existing_real_process_fixture", ROOT / "tests/connections/test_connections_c3eag_identity_kernel_observer.py")

class C3eAHSignedReleaseRealLinuxTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        AGTEST.C3eAGIdentityKernelObserverTests.setUpClass()

    def setUp(self):
        self.real = AGTEST.C3eAGIdentityKernelObserverTests(
            "test_01_real_nonroot_linux_python_process_matches_caller_pins_no_grants")
        self.real.setUp()
        self.addCleanup(self.real.doCleanups)
        self.root_key = Ed25519PrivateKey.generate()
        self.receipt_key = Ed25519PrivateKey.generate().public_key().public_bytes_raw()
        self.files = {
            p: hashlib.sha256(("independently-pinned:" + p).encode()).hexdigest()
            for p in H.I.FILES
        }
        self.files[H.GATEWAY] = self.real.pins["entrypointSha256"]
        self.rpm = hashlib.sha256(b"disposable-ci-signed-RPM-fixture").hexdigest()
        self.doc = {
            "schema": H.I.SCHEMA,
            "role": H.I.ROLE,
            "package": H.I.PACKAGE,
            "unit": H.I.UNIT,
            "epoch": 3,
            "sequence": 7,
            "rpmSha256": self.rpm,
            "receiptKeySha256": hashlib.sha256(self.receipt_key).hexdigest(),
            "files": dict(self.files),
        }
        self.sign()

    def sign(self):
        self.frame = H.I._canonical(self.doc)
        self.sig = self.root_key.sign(H.I.DOMAIN + self.frame)

    def params(self, **kwargs):
        args = {
            "signed_release": self.frame,
            "release_signature": self.sig,
            "independently_pinned_release_root": self.root_key.public_key(),
            "independently_pinned_receipt_key": self.receipt_key,
            "independently_measured_rpm_sha256": self.rpm,
            "independently_measured_release_files": self.files,
            "minimum_release_epoch": 3,
            "minimum_release_sequence": 7,
            "expected_process": self.real.pins,
        }
        args.update(kwargs)
        return args

    def verify(self, **kwargs):
        return H.inspect_ci_only(**self.params(**kwargs))

    def refuse(self, **kwargs):
        with self.assertRaises(H.Refused):
            self.verify(**kwargs)

    def test_01_signed_release_and_real_kernel_observation_only_yield_diagnostic(self):
        result = self.verify()
        self.assertTrue(result["signedReleaseAndRealProcessScriptBytesMatchInCI"])
        self.assertTrue(result["realKernelProcessMatchesCallerPinsInCI"])
        self.assertEqual(result["releaseEpoch"], 3)
        self.assertEqual(result["releaseSequence"], 7)
        self.assertEqual(result["gatewayEntrySha256"], self.real.pins["entrypointSha256"])
        for name in (*H.NEGATIVE, *H.AG.NEGATIVE):
            self.assertIs(result[name], False, name)

    def test_02_source_pin_not_equal_to_process_pin_refused_before_observation(self):
        source = {**self.files, H.GATEWAY: "0" * 64}
        self.refuse(independently_measured_release_files=source)

    def test_03_wrong_signature_refused(self):
        self.refuse(release_signature=b"\0" * 64)

    def test_04_different_release_root_refused(self):
        self.refuse(independently_pinned_release_root=Ed25519PrivateKey.generate().public_key())

    def test_05_receipt_fingerprint_mismatch_refused(self):
        wrong = Ed25519PrivateKey.generate().public_key().public_bytes_raw()
        self.refuse(independently_pinned_receipt_key=wrong)

    def test_06_wrong_rpm_source_pin_refused(self):
        self.refuse(independently_measured_rpm_sha256="f" * 64)

    def test_07_signed_manifest_tampering_refused(self):
        tampered = self.frame.replace(b'"epoch":3', b'"epoch":4')
        self.refuse(signed_release=tampered)

    def test_08_wrong_signed_release_roster_refused(self):
        self.doc["files"].pop(H.I.UNIT_PATH)
        self.sign()
        self.refuse()

    def test_09_old_release_epoch_refused(self):
        self.doc["epoch"] = 2
        self.sign()
        self.refuse()

    def test_10_old_release_sequence_refused(self):
        self.doc["sequence"] = 6
        self.sign()
        self.refuse()

    def test_11_corrupted_observed_script_with_matching_old_signature_refused(self):
        self.real.script.chmod(0o755)
        self.real.script.write_text("import time\ntime.sleep(51)\n", encoding="ascii")
        self.real.script.chmod(0o555)
        self.refuse()

    def test_12_wrong_process_pid_refused(self):
        self.refuse(expected_process={**self.real.pins, "pid": self.real.pins["pid"] + 555555})

    def test_13_wrong_interpreter_sha_refused(self):
        self.refuse(expected_process={**self.real.pins, "exeSha256": "0" * 64})

    def test_14_closed_or_exited_real_process_refused(self):
        self.real._stop()
        self.refuse()

    def test_15_c4b_official_guest_mode_refuses_ubuntu_fixture(self):
        self.refuse(mode="c4b-guest-candidate")

    def test_16_boolean_release_floor_refused(self):
        self.refuse(minimum_release_epoch=True)
        self.refuse(minimum_release_sequence=True)

    def test_17_partial_process_pins_refused(self):
        source = dict(self.real.pins)
        del source["startTicks"]
        self.refuse(expected_process=source)

    def test_18_partial_signed_module_roster_refused(self):
        source = dict(self.files)
        del source[H.I.UNIT_PATH]
        self.refuse(independently_measured_release_files=source)

    def test_19_freeze_pins_between_release_validation_and_kernel_observation(self):
        raw = H.I.assess_synthetic_release
        def mutate_caller_after_valid_crypto(*args, **kw):
            result = raw(*args, **kw)
            self.files[H.GATEWAY] = "0" * 64
            self.real.pins["exeSha256"] = "0" * 64
            return result
        with mock.patch.object(H.I, "assess_synthetic_release",
                               side_effect=mutate_caller_after_valid_crypto):
            self.assertTrue(self.verify()["realKernelProcessMatchesCallerPinsInCI"])

    def test_20_signed_alternate_script_hash_does_not_make_real_script_match(self):
        substitute = hashlib.sha256(b"different-gateway-code").hexdigest()
        self.doc["files"][H.GATEWAY] = substitute
        self.files[H.GATEWAY] = substitute
        self.sign()
        self.refuse(expected_process={**self.real.pins, "entrypointSha256": substitute})

    def test_21_missing_signing_key_or_frame_refused(self):
        self.refuse(independently_pinned_release_root=None)
        self.refuse(signed_release=b"")

    def test_22_no_network_signin_or_installed_host_grants(self):
        source = (ROOT / "tests/connections/c3e_release_trust/C3eAHSignedReleaseLiveOrigin.py").read_text()
        for token in ("subprocess.Popen(", "systemctl start", "rpm-ostree install",
                      '"hostAuthenticated": True', '"canBeginSignIn": True',
                      '"credentialActionsEnabled": True', '"productionAuthority": True'):
            self.assertNotIn(token, source)
        self.assertEqual(H.GATEWAY, "/usr/libexec/post-apollo/identity/identity-gateway-ci")
        self.assertEqual(H.AG.C4B_SCRIPT, H.GATEWAY)

if __name__ == "__main__":
    unittest.main(verbosity=2)
