#!/usr/bin/env python3
"""C3e operator witness enrollment preflight: disposable-root hostile cases."""
from __future__ import annotations

import hashlib
import importlib.util
import os
from pathlib import Path
import sys
import unittest

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "tests/connections/c3e_release_trust"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError("C3E_OPERATOR_REQUIRED_TEST_SOURCE_MISSING")
    obj = importlib.util.module_from_spec(spec)
    sys.modules[name] = obj
    spec.loader.exec_module(obj)
    return obj


C = load("c3e_operator_preflight", SRC / "C3eOperatorWitnessEnrollmentPreflight.py")
F = load("c3e_operator_af_fixture",
         ROOT / "tests/connections/test_connections_c3eaf_signed_role_enrollment.py")


def digest(key):
    return hashlib.sha256(
        key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)).hexdigest()


class C3eOperatorWitnessPreflightTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if (sys.platform != "linux" or os.geteuid() != 0
                or os.environ.get("GITHUB_ACTIONS") != "true"):
            raise RuntimeError("C3E_OPERATOR_DISPOSABLE_GITHUB_ROOT_TEST_ONLY")

    def setUp(self):
        self.fixture = F.C3eAFRoleEnrollmentTests(
            "test_18_signed_enrollment_is_not_operator_custody_or_c5")
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.params = dict(
            signed_enrollment=self.fixture.frame,
            enrollment_signature=self.fixture.signature,
            independently_pinned_enrollment_root=self.fixture.anchor.public_key(),
            separately_expected_enrollment_root_sha256=digest(self.fixture.anchor),
            expected_host_id=F.HOST_ID,
            expected_release_epoch=self.fixture.z.y.epoch,
            expected_release_sequence=self.fixture.z.y.sequence,
            independently_measured_snapshot=dict(self.fixture.z.y.pair.expected),
            minimum_external_epoch=self.fixture.z.y.epoch,
            minimum_external_sequence=self.fixture.z.y.sequence,
            revoked_root_sha256=(),
            revoked_role_sha256=(),
        )

    def verify(self, **changes):
        return C.inspect_enrollment_preflight_ci_only(
            **{**self.params, **changes})

    def refused(self, expected, **changes):
        with self.assertRaisesRegex(C.Refused, expected):
            self.verify(**changes)
        self.assertEqual(self.fixture.z.state(), ("issued", None))

    def resign(self):
        self.fixture.sign()
        self.params["signed_enrollment"] = self.fixture.frame
        self.params["enrollment_signature"] = self.fixture.signature

    def test_01_valid_signatures_and_external_test_pins_still_never_grant(self):
        out = self.verify()
        self.assertEqual(out["status"], C.STATUS)
        self.assertTrue(out["testOnlySignedRoleEnrollmentMatchesCallerPins"])
        self.assertEqual(self.fixture.z.state(), ("issued", None))
        self.assertEqual(set(out["rolePublicKeySha256"]),
                         {"releaseRoot", "hostWitness", "receipt"})
        for k in (*C.DENIED, *C.AF.NEGATIVE):
            self.assertIs(out[k], False, k)

    def test_02_external_root_hash_substitution_refused(self):
        self.refused("UNTRUSTED_OR_SUBSTITUTED",
                     separately_expected_enrollment_root_sha256="f"*64)

    def test_03_signed_enrollment_under_wrong_pinned_root_refused(self):
        key = Ed25519PrivateKey.generate().public_key()
        self.refused("UNTRUSTED_OR_SUBSTITUTED",
                     independently_pinned_enrollment_root=key)

    def test_04_revoked_enrollment_root_refused(self):
        self.refused("REVOKED_ENROLLMENT_ROOT",
                     revoked_root_sha256=(digest(self.fixture.anchor),))

    def test_05_revoked_release_root_refused(self):
        self.refused("REVOKED_OR_ALIASED_ROLE", revoked_role_sha256=(
            digest(self.fixture.z.root_key),))

    def test_06_revoked_witness_root_refused(self):
        self.refused("REVOKED_OR_ALIASED_ROLE", revoked_role_sha256=(
            digest(self.fixture.z.y.witness_key),))

    def test_07_revoked_receipt_key_refused(self):
        self.refused("REVOKED_OR_ALIASED_ROLE", revoked_role_sha256=(
            digest(self.fixture.z.y.pair.key),))

    def test_08_role_revoked_through_root_roster_refused(self):
        self.refused("REVOKED_OR_ALIASED_ROLE", revoked_root_sha256=(
            digest(self.fixture.z.y.pair.key),))

    def test_09_duplicate_or_unordered_revocations_refused(self):
        key = "1"*64
        for roster in ((key,key), ("f"*64,"a"*64), ["1"*64],
                       ("ABC",), ("A"*64,), (None,), ("e"*65,)):
            with self.subTest(roster=roster):
                self.refused("REVOCATION_ROSTER_INVALID",
                             revoked_role_sha256=roster)

    def test_10_forged_signature_refused(self):
        self.refused("EXISTING_SIGNED_ROLE_ENROLLMENT_REFUSED",
                     enrollment_signature=b"0"*64)

    def test_11_unsigned_key_replacement_refused(self):
        doc = dict(self.fixture.doc)
        doc["receiptPublicHex"] = F.public_hex(Ed25519PrivateKey.generate())
        self.refused("EXISTING_SIGNED_ROLE_ENROLLMENT_REFUSED",
                     signed_enrollment=C.AF._canonical(doc))

    def test_12_valid_signature_for_wrong_host_refused(self):
        self.refused("EXISTING_SIGNED_ROLE_ENROLLMENT_REFUSED",
                     expected_host_id="postapollo-identity-ci@otherhost")

    def test_13_release_epoch_downgrade_refused(self):
        self.refused("RELEASE_FLOOR_DOWNGRADE",
                     minimum_external_epoch=self.fixture.z.y.epoch+1)

    def test_14_release_sequence_downgrade_refused(self):
        self.refused("RELEASE_FLOOR_DOWNGRADE",
                     minimum_external_sequence=self.fixture.z.y.sequence+1)

    def test_15_invalid_external_floors_refused(self):
        for key in ("minimum_external_epoch","minimum_external_sequence"):
            for invalid in (True, False, None, 0, -1, "1", 2**63):
                with self.subTest(field=key, value=invalid):
                    self.refused("EXTERNAL_RELEASE_FLOOR_INVALID", **{key:invalid})

    def test_16_invalid_candidate_floors_refused(self):
        for key in ("expected_release_epoch","expected_release_sequence"):
            for invalid in (True, -1, "1", 2**63):
                with self.subTest(field=key, value=invalid):
                    self.refused("EXTERNAL_RELEASE_FLOOR_INVALID", **{key:invalid})

    def test_17_signed_enrollment_cannot_alias_release_to_receipt(self):
        self.fixture.doc["receiptPublicHex"] = (
            self.fixture.doc["releaseRootPublicHex"])
        self.resign()
        self.refused("EXISTING_SIGNED_ROLE_ENROLLMENT_REFUSED")

    def test_18_changed_independent_process_snapshot_refused(self):
        modified = dict(self.fixture.z.y.pair.expected)
        modified["pid"] += 1
        self.refused("EXISTING_SIGNED_ROLE_ENROLLMENT_REFUSED",
                     independently_measured_snapshot=modified)

    def test_19_partial_or_extra_signed_fields_refused(self):
        # Even if the attacker controls the disposable root and correctly
        # signs a modified enrollment, extra authority fields must refuse.
        self.fixture.doc["productionAuthority"] = True
        self.resign()
        self.refused("EXISTING_SIGNED_ROLE_ENROLLMENT_REFUSED")

    def test_20_missing_or_invalid_out_of_band_root_fingerprint(self):
        for bad in (None, True, "", "a"*63, "F"*64):
            with self.subTest(bad=bad):
                self.refused("OUT_OF_BAND_ROOT_FINGERPRINT_REQUIRED",
                             separately_expected_enrollment_root_sha256=bad)

    def test_21_preflight_cannot_spend_or_issue_legacy_challenge(self):
        self.assertEqual(self.fixture.z.state(), ("issued", None))
        self.verify()
        self.verify()
        self.assertEqual(self.fixture.z.state(), ("issued", None))

    def test_22_guest_can_sign_own_enrollment_but_cannot_earn_custody(self):
        # Synthetic root+all keys are created in this ONE runner; source
        # must preserve the distinction between syntax and real custody.
        out = self.verify()
        self.assertTrue(out["testOnlyRevocationAndMinimumFloorInputsConsistent"])
        for k in ("operatorEnrollmentRootCustodyVerified",
                  "independentWitnessSigningKeyCustodyVerified",
                  "independentReleaseFloorCustodyVerified",
                  "realInstalledHostAuthenticated",
                  "c5HumanConsentVerified","productionAuthority"):
            self.assertIs(out[k], False)


if __name__ == "__main__":
    unittest.main(verbosity=2)
