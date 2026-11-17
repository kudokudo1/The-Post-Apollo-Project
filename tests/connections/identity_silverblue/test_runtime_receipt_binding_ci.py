#!/usr/bin/env python3
"""C4b successor: reject release/actual guest receipt signer mismatches."""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import sys
import unittest
from unittest import mock

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

sys.path.insert(0, str(Path(__file__).resolve().parent))
import runtime_receipt_binding_ci as B

ACTIONS = ("BEGIN", "STATUS", "CANCEL", "RECOVER")

class RuntimeReceiptBindingTests(unittest.TestCase):
    def setUp(self):
        self.root = Ed25519PrivateKey.generate()
        self.runtime = Ed25519PrivateKey.generate()
        self.runtime_pub = self.runtime.public_key().public_bytes_raw()
        self.other_pub = Ed25519PrivateKey.generate().public_key().public_bytes_raw()
        self.rpm = hashlib.sha256(b"discarded-signed-ci-rpm").hexdigest()
        self.files = {
            name: hashlib.sha256(("installed-verified:" + name).encode()).hexdigest()
            for name in B.I.FILES
        }
        self.doc = {
            "schema": B.I.SCHEMA, "role": B.I.ROLE,
            "package": B.I.PACKAGE, "unit": B.I.UNIT,
            "epoch": 2, "sequence": 8,
            "rpmSha256": self.rpm,
            "receiptKeySha256": hashlib.sha256(self.runtime_pub).hexdigest(),
            "files": dict(self.files),
        }
        self.sign()

    def sign(self):
        self.raw = B.I._canonical(self.doc)
        self.sig = self.root.sign(B.I.DOMAIN + self.raw)

    def args(self, **changed):
        params = {
            "signed_release": self.raw,
            "release_signature": self.sig,
            "independently_pinned_release_root": self.root.public_key(),
            "release_receipt_public": self.runtime_pub,
            "actual_runtime_receipt_public": self.runtime_pub,
            "rpm_sha256": self.rpm,
            "installed_file_sha256": self.files,
            "minimum_epoch": 2, "minimum_sequence": 8,
            "verified_actions": ACTIONS,
        }
        params.update(changed)
        return params

    def check(self, **changed):
        return B.verify_runtime_binding_ci_only(**self.args(**changed))

    def refused(self, **changed):
        with self.assertRaises(B.Refused):
            self.check(**changed)

    def test_01_valid_different_root_and_runtime_receipt_key_remain_deny_only(self):
        result = self.check()
        self.assertIs(result["guestLocalSignedReleaseContainsRuntimeReceiptKeyInCI"], True)
        self.assertIs(result["fourActualNativeDenialActionsSignedBySameRuntimeKeyInGuestCI"], True)
        self.assertEqual((result["releaseEpoch"], result["releaseSequence"]), (2, 8))
        for field in B.DENIED:
            self.assertIs(result[field], False, field)

    def test_02_actual_guest_signer_different_from_release_pin_refused(self):
        self.refused(actual_runtime_receipt_public=self.other_pub)

    def test_03_controller_fixture_pub_substituted_for_real_guest_refused(self):
        self.refused(release_receipt_public=self.other_pub)

    def test_04_controller_key_and_actual_key_independently_replaced_refused(self):
        self.refused(release_receipt_public=self.other_pub,
                     actual_runtime_receipt_public=self.other_pub)

    def test_05_different_signed_release_root_refused(self):
        self.refused(independently_pinned_release_root=
                     Ed25519PrivateKey.generate().public_key())

    def test_06_wrong_signed_release_signature_refused(self):
        self.refused(release_signature=b"\0" * 64)

    def test_07_modified_canonical_release_frame_refused(self):
        self.refused(signed_release=self.raw + b"\n")

    def test_08_wrong_release_rpm_digest_refused(self):
        self.refused(rpm_sha256="f" * 64)

    def test_09_wrong_signed_release_entrypoint_file_refused(self):
        altered = {**self.files, B.I.PREFIX+"identity-gateway-ci":"0"*64}
        self.refused(installed_file_sha256=altered)

    def test_10_missing_or_extra_module_refused(self):
        missing = dict(self.files)
        missing.pop(B.I.UNIT_PATH)
        self.refused(installed_file_sha256=missing)
        self.refused(installed_file_sha256={**self.files, "/tmp/other":"f"*64})

    def test_11_retired_release_epoch_or_sequence_refused(self):
        self.refused(minimum_epoch=3)
        self.refused(minimum_sequence=9)

    def test_12_boolean_floors_refused(self):
        self.refused(minimum_epoch=True)
        self.refused(minimum_sequence=False)

    def test_13_host_role_and_wrong_source_schema_refused(self):
        for key, val in (
            ("schema", "postapollo.identity.production"),
            ("role", "postapollo.connections.server"),
            ("unit", "other.service"),
            ("package", "other-package"),
        ):
            old = self.doc[key]
            self.doc[key] = val
            self.sign()
            with self.subTest(field=key):
                self.refused()
            self.doc[key] = old
        self.sign()

    def test_14_signed_wrong_receipt_key_fingerprint_refused(self):
        self.doc["receiptKeySha256"] = hashlib.sha256(self.other_pub).hexdigest()
        self.sign()
        self.refused()

    def test_15_missing_one_denial_refused(self):
        self.refused(verified_actions=("BEGIN", "STATUS", "RECOVER"))

    def test_16_reordered_duplicate_or_unknown_denial_refused(self):
        self.refused(verified_actions=("STATUS", "BEGIN", "CANCEL", "RECOVER"))
        self.refused(verified_actions=("BEGIN", "STATUS", "STATUS", "RECOVER"))
        self.refused(verified_actions=("BEGIN", "STATUS", "CANCEL", "LOGIN"))

    def test_17_malformed_runtime_key_refused(self):
        for key in (b"", None, b"x"*31, "x"*32):
            with self.subTest(key=repr(key)):
                self.refused(actual_runtime_receipt_public=key)

    def test_18_malformed_manifest_key_refused(self):
        self.refused(release_receipt_public=b"z"*34)
        self.refused(release_receipt_public=None)

    def test_19_duplicate_manifest_field_refused(self):
        bad=self.raw.replace(b'"epoch":2', b'"epoch":2,"epoch":2', 1)
        self.refused(signed_release=bad,
                     release_signature=self.root.sign(B.I.DOMAIN+bad))

    def test_20_source_validation_does_not_trust_undeclared_flags(self):
        self.doc["productionAuthority"] = True
        self.sign()
        self.refused()

    def test_21_rehearsal_rejects_non_guest_instead_of_emitting_test_authority(self):
        with mock.patch.dict(os.environ, {"POST_APOLLO_C4B_TEST_GUEST":"0",
                                          "GITHUB_ACTIONS":"true"}):
            with self.assertRaises(B.Refused):
                B.rehearse_guest_local_ci_only(
                    actual_runtime_receipt_public=self.runtime_pub,
                    verified_actions=ACTIONS,
                    signed_rpm_archive=Path(
                        "/var/lib/postapollo-id-ci-assets/identity-silverblue-ci.rpm"),
                )

    def test_22_wrong_runtime_rpm_location_refused_before_io(self):
        with mock.patch.object(B, "_digest_file", side_effect=AssertionError("unexpected read")):
            with mock.patch.dict(os.environ, {"POST_APOLLO_C4B_TEST_GUEST":"1",
                                              "GITHUB_ACTIONS":"true"}):
                with mock.patch.object(B.Path, "exists", return_value=True):
                    with self.assertRaisesRegex(
                        B.Refused, "C4B_BINDING_UNTRUSTED_RPM_ARCHIVE_PATH",
                    ):
                        B.rehearse_guest_local_ci_only(
                            actual_runtime_receipt_public=self.runtime_pub,
                            verified_actions=ACTIONS,
                            signed_rpm_archive=Path("/tmp/untrusted.rpm"),
                        )

    def test_23_guest_probe_never_transports_private_key_to_rpm_or_uart(self):
        source=(Path(__file__).resolve().parent/"runtime_receipt_binding_ci.py").read_text()
        for forbidden in (
            '"productionAuthority": True', '"hostAuthenticated": True',
            '"credentialActionsEnabled": True', '"canBeginSignIn": True',
            "private_bytes(", "subprocess.run(", "requests.get(",
        ):
            self.assertNotIn(forbidden, source)

    def test_25_release_root_cannot_be_same_as_runtime_receipt_signer(self):
        signed = self.runtime.sign(B.I.DOMAIN + self.raw)
        self.refused(
            independently_pinned_release_root=self.runtime.public_key(),
            release_signature=signed,
        )

    def test_24_source_signer_role_is_not_c4b_rpm_signer_or_prod_key(self):
        self.assertEqual(B.I.PACKAGE, "post-apollo-identity-silverblue-ci")
        self.assertEqual(B.I.UNIT, "post-apollo-identity-silverblue-ci.service")
        self.assertEqual(len(B.I.FILES), 9)

if __name__ == "__main__":
    unittest.main(verbosity=2)
