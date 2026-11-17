#!/usr/bin/env python3
"""C3e-AF: adversarial key-role enrollment before existing C3e-Z CI record."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import unittest

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "tests/connections/c3e_release_trust"

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError("C3EAF_TEST_IMPORT_REFUSED")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module

A = load("c3eaf_enrollment", SOURCE / "C3eAFSignedRoleEnrollment.py")
ZTEST = load(
    "c3eaf_z_fixture",
    ROOT / "tests/connections/test_connections_c3ez_release_bound_host_evidence.py",
)

HOST_ID = "postapollo-identity-ci@fixture-host-01"

def public_hex(key):
    return key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw).hex()

class C3eAFRoleEnrollmentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if (sys.platform != "linux" or os.geteuid() != 0
                or os.environ.get("GITHUB_ACTIONS") != "true"):
            raise RuntimeError("C3EAF_DISPOSABLE_ROOT_GITHUB_CI_ONLY")

    def setUp(self):
        self.z = ZTEST.C3eZReleaseBoundIdentityTests(
            "test_01_valid_release_and_signed_host_replay_path_only_yields_ci_diagnostics")
        self.z.setUp()
        self.addCleanup(self.z.doCleanups)
        self.anchor = Ed25519PrivateKey.generate()
        self.doc = {
            "schema": A.SCHEMA,
            "role": A.Z.I.ROLE,
            "purpose": A.PURPOSE,
            "hostId": HOST_ID,
            "releaseEpoch": self.z.y.epoch,
            "releaseSequence": self.z.y.sequence,
            "releaseRootPublicHex": public_hex(self.z.root_key),
            "hostWitnessPublicHex": public_hex(self.z.y.witness_key),
            "receiptPublicHex": public_hex(self.z.y.pair.key),
        }
        self.sign()

    def sign(self):
        self.frame = A._canonical(self.doc)
        self.signature = self.anchor.sign(A.DOMAIN + self.frame)

    def params(self, **changes):
        args = self.z.args()
        for key in ("independently_pinned_release_root",
                    "independently_pinned_witness_key",
                    "independently_pinned_receipt_key"):
            args.pop(key)
        args.update({
            "enrollment": self.frame,
            "enrollment_signature": self.signature,
            "independently_pinned_enrollment_root": self.anchor.public_key(),
            "expected_host_id": HOST_ID,
        })
        args.update(changes)
        return args

    def verify(self, **changes):
        return A.inspect_enrolled_ci_only(**self.params(**changes))

    def denied(self, **changes):
        with self.assertRaises(A.Refused):
            self.verify(**changes)
        self.assertEqual(self.z.state(), ("issued", None))

    def test_01_signed_enrollment_precedes_z_consume_and_never_grants(self):
        before = self.z.state()
        self.assertEqual(before, ("issued", None))
        result = self.verify()
        self.assertTrue(result["signedRoleEnrollmentMatchesCallerPinInCI"])
        self.assertTrue(result["releaseAndSignedHostEvidenceBoundToEnrolledRolesInCI"])
        self.assertTrue(result["oneUseChallengeConsumedInRootLocalCI"])
        self.assertEqual(result["enrollmentSha256"], hashlib.sha256(self.frame).hexdigest())
        self.assertEqual(self.z.state()[0], "consumed")
        for name in (*A.NEGATIVE, *A.Z.NEGATIVE, *A.Z.Y.X.NEGATIVE):
            self.assertIs(result[name], False, name)

    def test_02_wrong_separately_pinned_enrollment_authority_refused(self):
        self.denied(independently_pinned_enrollment_root=
                    Ed25519PrivateKey.generate().public_key())

    def test_03_signature_tamper_refused_without_using_challenge(self):
        self.denied(enrollment_signature=b"\0" * 64)

    def test_04_unsigned_replacement_public_keys_refused(self):
        doc = dict(self.doc)
        doc["hostWitnessPublicHex"] = public_hex(Ed25519PrivateKey.generate())
        self.denied(enrollment=A._canonical(doc))

    def test_05_signed_but_wrong_release_key_cannot_approve_z_release(self):
        self.doc["releaseRootPublicHex"] = public_hex(Ed25519PrivateKey.generate())
        self.sign()
        self.denied()

    def test_06_signed_but_wrong_receipt_key_cannot_approve_four_denials(self):
        self.doc["receiptPublicHex"] = public_hex(Ed25519PrivateKey.generate())
        self.sign()
        self.denied()

    def test_07_signed_but_wrong_witness_key_cannot_approve_host_statement(self):
        self.doc["hostWitnessPublicHex"] = public_hex(Ed25519PrivateKey.generate())
        self.sign()
        self.denied()

    def test_08_replayed_old_release_epoch_or_sequence_refused_before_consume(self):
        for key in ("releaseEpoch", "releaseSequence"):
            original = self.doc[key]
            self.doc[key] = original + 1
            self.sign()
            with self.subTest(key=key):
                self.denied()
            self.doc[key] = original

    def test_09_wrong_host_scope_cannot_reuse_valid_enrollment(self):
        self.denied(expected_host_id="postapollo-identity-ci@different-host")
        self.doc["hostId"] = "postapollo-identity-ci@different-host"
        self.sign()
        self.denied()

    def test_10_reject_alias_between_any_two_roles_including_enrollment_root(self):
        pairs = [
            ("hostWitnessPublicHex", "releaseRootPublicHex"),
            ("receiptPublicHex", "hostWitnessPublicHex"),
            ("receiptPublicHex", "releaseRootPublicHex"),
        ]
        for target, source in pairs:
            original = self.doc[target]
            self.doc[target] = self.doc[source]
            self.sign()
            with self.subTest(target=target):
                self.denied()
            self.doc[target] = original
        self.doc["hostWitnessPublicHex"] = public_hex(self.anchor)
        self.sign()
        self.denied()

    def test_11_boolean_and_missing_floor_are_not_numbers(self):
        for field in ("releaseEpoch", "releaseSequence"):
            for value in (True, False, None, 0, -1, "1"):
                self.doc[field] = value
                self.sign()
                with self.subTest(field=field, value=value):
                    self.denied()
            self.doc[field] = self.z.y.epoch if field == "releaseEpoch" else self.z.y.sequence

    def test_12_noncanonical_duplicate_missing_extra_fields_are_refused(self):
        self.denied(enrollment=self.frame + b"\n")
        self.denied(enrollment=b' ' + self.frame)
        self.denied(enrollment=self.frame.replace(
            b'"schema":', b'"schema":"forged","schema":', 1))
        self.denied(enrollment=self.frame.replace(
            b'"purpose":', b'"extra":0,"purpose":', 1))
        self.denied(enrollment=self.frame.replace(b'"hostId":', b'"missingHostId":', 1))

    def test_13_exact_role_purpose_schema_and_host_syntax(self):
        for field, value in (
            ("schema", "alternate"),
            ("role", "postapollo.connections.status"),
            ("purpose", "production-sign-in"),
            ("hostId", "../escape"),
        ):
            old = self.doc[field]
            self.doc[field] = value
            self.sign()
            with self.subTest(field=field):
                self.denied()
            self.doc[field] = old

    def test_14_malformed_keys_and_signature_lengths_refused(self):
        for key in ("releaseRootPublicHex", "hostWitnessPublicHex", "receiptPublicHex"):
            value = self.doc[key]
            for forged in ("f" * 63, "g" * 64, 5, None):
                self.doc[key] = forged
                self.sign()
                with self.subTest(key=key, value=forged):
                    self.denied()
            self.doc[key] = value
        self.sign()
        self.denied(enrollment_signature=b"x" * 65)
        self.denied(enrollment=b"")

    def test_15_untrusted_artifact_text_is_not_signed_enrollment(self):
        self.denied(enrollment=b"C4B_ID_PASS // REAL_TWO_BOOT_ROLLBACK\n")

    def test_16_release_hash_mismatch_preserves_issuer_challenge(self):
        changed = self.z.args()["signed_release"][:-1] + b"x"
        self.denied(signed_release=changed)

    def test_17_consumed_challenge_cannot_be_replayed_with_valid_keys(self):
        self.assertTrue(self.verify()["oneUseChallengeConsumedInRootLocalCI"])
        with self.assertRaises(A.Refused):
            self.verify()
        self.assertEqual(self.z.state()[0], "consumed")

    def test_18_signed_enrollment_is_not_operator_custody_or_c5(self):
        accepted = A.verify_signed_enrollment_ci_only(
            enrollment=self.frame, signature=self.signature,
            independently_pinned_enrollment_root=self.anchor.public_key(),
            expected_host_id=HOST_ID, expected_release_epoch=self.z.y.epoch,
            expected_release_sequence=self.z.y.sequence)
        self.assertEqual(set(accepted), {"release_root", "witness", "receipt",
                                         "enrollmentSha256"})
        source = (SOURCE / "C3eAFSignedRoleEnrollment.py").read_text()
        for grant in ("\"hostAuthenticated\": True", "\"productionAuthority\": True",
                      "\"canBeginSignIn\": True", "\"credentialActionsEnabled\": True",
                      "socket.socket(", "subprocess.run(", "requests.get("):
            self.assertNotIn(grant, source)

if __name__ == "__main__":
    unittest.main(verbosity=2)
