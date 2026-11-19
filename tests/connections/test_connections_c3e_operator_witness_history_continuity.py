#!/usr/bin/env python3
"""C3e: signed external history continuity with independent CI pin refusals."""
from __future__ import annotations

import hashlib
import importlib.util
import os
from pathlib import Path
import secrets
import sys
import unittest

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "tests/connections/c3e_release_trust"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError("C3E_HISTORY_TEST_SOURCE_MISSING")
    out = importlib.util.module_from_spec(spec)
    sys.modules[name] = out
    spec.loader.exec_module(out)
    return out


M = load("c3e_history_continuity", SRC / "C3eOperatorWitnessHistoryContinuity.py")
FIXTURE = load(
    "c3e_history_operator_fixture",
    ROOT / "tests/connections/test_connections_c3e_operator_witness_enrollment_preflight.py",
)


def sha_of_key(key):
    return hashlib.sha256(
        key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)).hexdigest()


class C3eWitnessHistoryContinuityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if (sys.platform != "linux" or os.geteuid() != 0
                or os.environ.get("GITHUB_ACTIONS") != "true"):
            raise RuntimeError("C3E_HISTORY_DISPOSABLE_ROOT_GITHUB_CI_ONLY")

    def setUp(self):
        self.enrollment = FIXTURE.C3eOperatorWitnessPreflightTests(
            "test_01_valid_signatures_and_external_test_pins_still_never_grant")
        self.enrollment.setUp()
        self.addCleanup(self.enrollment.doCleanups)
        self.inputs = dict(self.enrollment.params)
        enrolled = M.P.inspect_enrollment_preflight_ci_only(**self.inputs)
        self.signer = Ed25519PrivateKey.generate()
        self.challenge = secrets.token_bytes(32)
        self.previous_head = hashlib.sha256(b"enrolled-external-prior-head").hexdigest()
        self.previous_sequence = 41
        self.doc = {
            "schema": M.SCHEMA,
            "purpose": M.PURPOSE,
            "hostId": enrolled["hostId"],
            "releaseEpoch": enrolled["releaseEpoch"],
            "releaseSequence": enrolled["releaseSequence"],
            "enrollmentSha256": enrolled["enrollmentSha256"],
            "runtimeSnapshotSha256": enrolled["runtimeSnapshotSha256"],
            "releaseRootSha256": enrolled["rolePublicKeySha256"]["releaseRoot"],
            "hostWitnessSha256": enrolled["rolePublicKeySha256"]["hostWitness"],
            "receiptKeySha256": enrolled["rolePublicKeySha256"]["receipt"],
            "historyAuthoritySha256": sha_of_key(self.signer),
            "historySequence": self.previous_sequence + 1,
            "previousHeadSha256": self.previous_head,
            "challengeSha256": hashlib.sha256(self.challenge).hexdigest(),
        }
        self.sign()
        self.params = dict(
            enrollment_inputs=self.inputs,
            signed_history_record=self.frame,
            history_signature=self.signature,
            independently_pinned_history_authority=self.signer.public_key(),
            separately_expected_history_authority_sha256=sha_of_key(self.signer),
            independently_pinned_previous_head_sha256=self.previous_head,
            independently_pinned_previous_sequence=self.previous_sequence,
            independently_issued_challenge=self.challenge,
            revoked_history_authority_sha256=(),
        )

    def sign(self):
        self.frame = M._canonical(self.doc)
        self.signature = self.signer.sign(M.DOMAIN + self.frame)

    def updated(self):
        self.sign()
        self.params["signed_history_record"] = self.frame
        self.params["history_signature"] = self.signature

    def verify(self, **changes):
        return M.inspect_next_history_proposal_ci_only(
            **{**self.params, **changes})

    def refused(self, reason, **changes):
        with self.assertRaisesRegex(M.Refused, reason):
            self.verify(**changes)
        # Reading evidence never spends or reissues the C3e-Y local nonce.
        self.assertEqual(self.enrollment.fixture.z.state(), ("issued", None))

    def test_01_signed_next_head_and_all_grants_still_false(self):
        out = self.verify()
        self.assertEqual(out["status"], M.STATUS)
        self.assertEqual(out["nextHistorySequence"], 42)
        self.assertEqual(out["nextHistoryHeadSha256"],
                         hashlib.sha256(
                             M.DOMAIN + self.frame + self.signature).hexdigest())
        for key in (*M.DENIED, *M.P.DENIED, *M.P.AF.NEGATIVE):
            self.assertIs(out[key], False, key)
        self.assertEqual(self.enrollment.fixture.z.state(), ("issued", None))

    def test_02_unsigned_record_tamper_refused(self):
        self.refused("SIGNED_CONTINUITY_REFUSED",
                     signed_history_record=self.frame + b"x")

    def test_03_signed_unexpected_authority_field_refused(self):
        self.doc["productionAuthority"] = True
        self.updated()
        self.refused("NONCANONICAL_OR_PARTIAL_SIGNED_RECORD")

    def test_04_signed_history_with_wrong_host_refused(self):
        self.doc["hostId"] = "postapollo-identity-ci@unexpected"
        self.updated()
        self.refused("SIGNED_RECORD_MISMATCH_OR_REPLAY")

    def test_05_signed_history_with_wrong_enrollment_hash_refused(self):
        self.doc["enrollmentSha256"] = "1"*64
        self.updated()
        self.refused("SIGNED_RECORD_MISMATCH_OR_REPLAY")

    def test_06_signed_history_with_wrong_runtime_hash_refused(self):
        self.doc["runtimeSnapshotSha256"] = "a"*64
        self.updated()
        self.refused("SIGNED_RECORD_MISMATCH_OR_REPLAY")

    def test_07_signed_release_floor_swap_refused(self):
        for key in ("releaseEpoch", "releaseSequence"):
            old = self.doc[key]
            self.doc[key] += 1
            self.updated()
            with self.subTest(field=key):
                self.refused("SIGNED_RECORD_MISMATCH_OR_REPLAY")
            self.doc[key] = old

    def test_08_signed_role_fingerprints_must_match_enrollment(self):
        for key in ("releaseRootSha256", "hostWitnessSha256",
                    "receiptKeySha256"):
            old = self.doc[key]
            self.doc[key] = "f"*64
            self.updated()
            with self.subTest(field=key):
                self.refused("SIGNED_RECORD_MISMATCH_OR_REPLAY")
            self.doc[key] = old

    def test_09_wrong_independent_authority_pin_refused(self):
        self.refused("SUBSTITUTED_AUTHORITY_ROOT",
                     separately_expected_history_authority_sha256="f"*64)

    def test_10_wrong_authority_public_key_refused(self):
        self.refused("SUBSTITUTED_AUTHORITY_ROOT",
                     independently_pinned_history_authority=
                     Ed25519PrivateKey.generate().public_key())

    def test_11_revoked_history_signer_refused(self):
        self.refused("REVOKED_HISTORY_AUTHORITY",
                     revoked_history_authority_sha256=(sha_of_key(self.signer),))

    def test_12_noncanonical_history_revocation_roster_refused(self):
        for values in ((sha_of_key(self.signer),)*2, ("f"*64,"a"*64),
                       ["a"*64], ("Z"*64,), ("a"*63,)):
            with self.subTest(values=values):
                self.refused("AUTHORITY_OR_REVOCATION_REFUSED",
                             revoked_history_authority_sha256=values)

    def test_13_signed_old_or_skipped_sequence_refused(self):
        for number in (41, 43, True):
            self.doc["historySequence"] = number
            self.updated()
            with self.subTest(sequence=number):
                self.refused("SIGNED_RECORD_MISMATCH_OR_REPLAY")
        self.doc["historySequence"] = 42

    def test_14_wrong_or_replayed_previous_head_refused(self):
        self.refused("SIGNED_RECORD_MISMATCH_OR_REPLAY",
                     independently_pinned_previous_head_sha256="c"*64)
        self.doc["previousHeadSha256"] = "d"*64
        self.updated()
        self.refused("SIGNED_RECORD_MISMATCH_OR_REPLAY")

    def test_15_wrong_or_malformed_fresh_challenge_refused(self):
        self.refused("SIGNED_RECORD_MISMATCH_OR_REPLAY",
                     independently_issued_challenge=secrets.token_bytes(32))
        self.refused("EXTERNAL_HEAD_SEQUENCE_OR_CHALLENGE_REQUIRED",
                     independently_issued_challenge=b"short")

    def test_16_missing_external_prior_anchor_refused(self):
        for bad in ("", "a"*63, "F"*64, True):
            with self.subTest(bad=bad):
                self.refused("EXTERNAL_HEAD_SEQUENCE_OR_CHALLENGE_REQUIRED",
                             independently_pinned_previous_head_sha256=bad)
        for bad in (0, True, -1, "41", 2**63-1):
            with self.subTest(bad=bad):
                self.refused("EXTERNAL_HEAD_SEQUENCE_OR_CHALLENGE_REQUIRED",
                             independently_pinned_previous_sequence=bad)

    def test_17_signed_role_alias_to_history_authority_refused(self):
        self.refused("AUTHORITY_MUST_HAVE_DISTINCT_SIGNING_ROLE",
                     independently_pinned_history_authority=
                     self.enrollment.fixture.anchor.public_key(),
                     separately_expected_history_authority_sha256=
                     sha_of_key(self.enrollment.fixture.anchor))

    def test_18_forged_c3e_operator_enrollment_preflight_refused(self):
        bad=dict(self.inputs)
        bad["signed_enrollment"]=bad["signed_enrollment"]+b"x"
        self.refused("SIGNED_ENROLLMENT_PREFLIGHT_REFUSED",
                     enrollment_inputs=bad)

    def test_19_changed_independent_process_identity_refused(self):
        bad=dict(self.inputs)
        snap=dict(bad["independently_measured_snapshot"])
        snap["pid"] += 1
        bad["independently_measured_snapshot"]=snap
        self.refused("SIGNED_ENROLLMENT_PREFLIGHT_REFUSED",
                     enrollment_inputs=bad)

    def test_20_signed_nonce_reuse_refused_with_new_external_challenge(self):
        self.verify()
        self.refused("SIGNED_RECORD_MISMATCH_OR_REPLAY",
                     independently_issued_challenge=secrets.token_bytes(32))
        self.assertEqual(self.enrollment.fixture.z.state(), ("issued", None))

    def test_21_duplicate_or_noncanonical_signed_json_refused(self):
        payload=self.frame.replace(
            b'"hostId":', b'"hostId":"duplicate","hostId":',1)
        signature=self.signer.sign(M.DOMAIN+payload)
        self.refused("DUPLICATE_SIGNED_FIELD",
                     signed_history_record=payload,history_signature=signature)
        payload=b" "+self.frame
        signature=self.signer.sign(M.DOMAIN+payload)
        self.refused("NONCANONICAL_OR_PARTIAL_SIGNED_RECORD",
                     signed_history_record=payload,history_signature=signature)

    def test_22_signed_false_purpose_refused(self):
        self.doc["purpose"]="activate-native-sign-in"
        self.updated()
        self.refused("SIGNED_RECORD_MISMATCH_OR_REPLAY")

    def test_23_signed_numeric_boolean_coercion_refused(self):
        self.doc["releaseEpoch"]=True
        self.updated()
        self.refused("SIGNED_RECORD_MISMATCH_OR_REPLAY")

    def test_24_history_diagnostic_alone_never_records_externally(self):
        first=self.verify()
        second=self.verify()
        self.assertEqual(first["nextHistoryHeadSha256"],
                         second["nextHistoryHeadSha256"])
        self.assertIs(first["externallyRecordedNextHeadVerified"],False)
        self.assertIs(first["externalRollbackResistanceVerified"],False)
        self.assertEqual(self.enrollment.fixture.z.state(), ("issued",None))


if __name__ == "__main__":
    unittest.main(verbosity=2)
