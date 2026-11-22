#!/usr/bin/env python3
"""Three signed Forest writer/enrollment/custody fixture claims, NO authority."""
from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path
import sys
import unittest

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from services.connections.forest import ForestC5SignedEvidencePreflight as S  # noqa
from services.connections.forest import ForestC5TerminalReceiptPreflight as R  # noqa
from services.connections.forest import ForestC5WriterCustodyClaimPreflight as C  # noqa


def original_samples():
    spec = importlib.util.spec_from_file_location(
        "forest_c5_original_samples_custody",
        ROOT / "tests/connections/test_connections_forest_c5_signed_role_preflight.py",
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("SIGNED_ROLE_SAMPLE_MISSING")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def public(key):
    return key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


SAMPLES = original_samples()


class ForestC5UnenrolledWriterCustodyTests(unittest.TestCase):
    def setUp(self):
        self.writer = Ed25519PrivateKey.generate()
        self.enroller = Ed25519PrivateKey.generate()
        self.custodian = Ed25519PrivateKey.generate()
        self.writerpub = public(self.writer)
        self.enrollerpub = public(self.enroller)
        self.custodianpub = public(self.custodian)
        self.intent = SAMPLES.sample_intent()
        self.intentwire = S.canonical_bytes(self.intent)
        self.receipt = {
            "schema": R.RECEIPT_SCHEMA,
            "audience": S.AUDIENCE,
            "role": R.WRITER_ROLE,
            "intentSha256": digest(self.intentwire),
            "permitId": "permit001",
            "attempt": self.intent["attempt"],
            "grant": self.intent["grant"],
            "request": self.intent["request"],
            "principal": self.intent["principal"],
            "tree": self.intent["tree"],
            "model": self.intent["model"],
            "revision": self.intent["revision"],
            "consentEpoch": self.intent["consentEpoch"],
            "challenge": self.intent["challenge"],
            "commitHostReleaseSha256": self.intent["commitHostReleaseSha256"],
            "writerKeySha256": digest(self.writerpub),
            "writerJournalCounter": 5,
            "previousJournalSha256": "0" * 64,
            "terminalOutcome": "COMMIT_CONFIRMED",
            "storageTxnId": "txn001",
            "recordedAtMs": 1900,
        }
        self.enrollment = {
            "schema": C.ENROLLMENT_SCHEMA,
            "audience": S.AUDIENCE,
            "role": C.ENROLLER_ROLE,
            "writerKeySha256": digest(self.writerpub),
            "writerReleaseSha256": self.intent["commitHostReleaseSha256"],
            "writerInstance": "forestwriter1",
            "enrollmentEpoch": 7,
            "validFromMs": 100,
            "validUntilMs": 3000,
            "enrollerKeySha256": digest(self.enrollerpub),
        }

    def make(self, *, receipt_changes=None, enrollment_changes=None,
             custody_changes=None, wire_changes=None):
        receipt = dict(self.receipt, **(receipt_changes or {}))
        enrollment = dict(self.enrollment, **(enrollment_changes or {}))
        receiptwire = S.canonical_bytes(receipt)
        enrollmentwire = S.canonical_bytes(enrollment)
        custody = {
            "schema": C.CUSTODY_SCHEMA,
            "audience": S.AUDIENCE,
            "role": C.CUSTODIAN_ROLE,
            "writerKeySha256": enrollment["writerKeySha256"],
            "writerReleaseSha256": enrollment["writerReleaseSha256"],
            "writerInstance": enrollment["writerInstance"],
            "enrollmentEpoch": enrollment["enrollmentEpoch"],
            "intentSha256": digest(self.intentwire),
            "receiptSha256": digest(receiptwire),
            "permitId": receipt["permitId"],
            "storageTxnId": receipt["storageTxnId"],
            "writerJournalCounter": receipt["writerJournalCounter"],
            "previousJournalSha256": receipt["previousJournalSha256"],
            "terminalOutcome": receipt["terminalOutcome"],
            "recordedAtMs": receipt["recordedAtMs"],
            "custodianKeySha256": digest(self.custodianpub),
        }
        custody.update(custody_changes or {})
        custodywire = S.canonical_bytes(custody)
        result = [
            self.intentwire,
            receiptwire, self.writer.sign(receiptwire), self.writerpub,
            enrollmentwire, self.enroller.sign(enrollmentwire), self.enrollerpub,
            custodywire, self.custodian.sign(custodywire), self.custodianpub,
        ]
        if wire_changes:
            for index, value in wire_changes.items():
                result[index] = value
        return result

    def check(self, args=None, floor=4, **changes):
        if args is None:
            args = self.make(**changes)
        return C.verify_unenrolled_custody_claims(
            *args, claimed_counter_floor=floor,
        )

    def hold(self, reason, args=None, floor=4, **changes):
        with self.assertRaises(C.CustodyHold) as captured:
            self.check(args=args, floor=floor, **changes)
        self.assertIn(reason, str(captured.exception))

    def test_01_three_signatures_consistent_but_no_authority(self):
        result = self.check()
        self.assertEqual(result["status"],
                         "THREE_UNENROLLED_SIGNATURE_CLAIMS_CONSISTENT_NOT_SETTLED")
        self.assertEqual(result["safeActions"], [])
        self.assertTrue(result["enrollmentAndCustodyRootsCallerControlled"])
        self.assertTrue(result["claimedDurableCustodyUntrusted"])
        for name, value in C.NO_AUTHORITY.items():
            self.assertIs(result[name], False, name)

    def test_02_claimed_rollback_still_cannot_settle(self):
        result = self.check(receipt_changes={"terminalOutcome": "ROLLBACK_CONFIRMED"})
        self.assertEqual(result["claimedTerminalOutcomeUntrusted"],
                         "ROLLBACK_CONFIRMED")
        self.assertFalse(result["c5RevocationFenceSettled"])

    def test_03_late_receipt_is_inspectable_but_not_new_permission(self):
        self.assertGreater(self.receipt["recordedAtMs"], self.intent["expiresAtMs"])
        result = self.check()
        self.assertFalse(result["terminalOutcomeAuthenticated"])
        self.assertFalse(result["forestDatabaseCommitAllowed"])

    def test_04_custody_must_bind_every_original_receipt_field(self):
        for name, value in (
            ("intentSha256", "f" * 64), ("receiptSha256", "a" * 64),
            ("permitId", "wrongpermit"), ("storageTxnId", "txnghost"),
            ("writerJournalCounter", 9), ("previousJournalSha256", "b" * 64),
            ("terminalOutcome", "ROLLBACK_CONFIRMED"),
            ("writerReleaseSha256", "c" * 64), ("writerKeySha256", "d" * 64),
        ):
            with self.subTest(field=name):
                self.hold("CUSTODY_RECEIPT_BINDING_MISMATCH",
                          custody_changes={name: value})

    def test_05_custody_enrollment_instance_and_epoch_must_agree(self):
        self.hold("CUSTODY_RECEIPT_BINDING_MISMATCH_writerInstance",
                  custody_changes={"writerInstance": "otherwriter"})
        self.hold("CUSTODY_RECEIPT_BINDING_MISMATCH_enrollmentEpoch",
                  custody_changes={"enrollmentEpoch": 8})

    def test_06_writer_key_cannot_be_replaced_by_new_valid_key(self):
        bad = self.make()
        substitute = Ed25519PrivateKey.generate()
        bad[3] = public(substitute)
        bad[2] = substitute.sign(bad[1])
        self.hold("CLAIMED_KEY_PIN_MISMATCH", args=bad)

    def test_07_caller_fabricated_pins_can_match_without_authority(self):
        # A forger can mint all THREE roles; they are not independently enrolled.
        result = self.check()
        self.assertFalse(result["writerRootIndependentlyEnrolled"])
        self.assertFalse(result["journalCustodianIndependentlyAuthenticated"])

    def test_08_signer_roles_must_be_distinct(self):
        bad = self.make()
        bad[9] = bad[6]
        bad[8] = self.enroller.sign(bad[7])
        self.hold("THREE_DISTINCT_SIGNER_ROLES_REQUIRED", args=bad)

    def test_09_tampered_enrollment_and_custody_signatures_refused(self):
        for index, label in ((5, "ENROLLMENT_INVALID_SIGNATURE"),
                             (8, "CUSTODY_INVALID_SIGNATURE")):
            with self.subTest(index=index):
                bad = self.make()
                bad[index] = bytes([bad[index][0] ^ 1]) + bad[index][1:]
                self.hold(label, args=bad)
        bad = self.make()
        bad[2] = bytes([bad[2][0] ^ 1]) + bad[2][1:]
        self.hold("INVALID_SIGNATURE", args=bad)

    def test_10_replay_or_lower_counter_cannot_pass(self):
        self.hold("STALE_JOURNAL_OR_TIME", floor=5)
        self.hold("STALE_JOURNAL_OR_TIME", floor=6)
        self.hold("INVALID_COUNTER_FLOOR", floor=True)

    def test_11_enrollment_time_must_cover_receipt_recording(self):
        self.hold("CLAIMED_WRITER_ENROLLMENT_TIME_MISMATCH",
                  enrollment_changes={"validUntilMs": 1500})
        self.hold("CLAIMED_WRITER_ENROLLMENT_TIME_MISMATCH",
                  enrollment_changes={"validFromMs": 2000})
        self.hold("CLAIMED_WRITER_ENROLLMENT_TIME_MISMATCH",
                  enrollment_changes={"validUntilMs": 100})

    def test_12_custody_cannot_claim_to_precede_receipt_recording(self):
        self.hold("CUSTODY_CLAIM_PREDATES_RECEIPT",
                  custody_changes={"recordedAtMs": 1899})

    def test_13_wrong_role_audience_schema_are_refused(self):
        for changes in (
            {"role": "postapollo.forest.writer-enroller.v1"},
            {"audience": "postapollo.timew.restore.v1"},
            {"schema": "postapollo.forest.other.v0"},
        ):
            self.hold("WRONG_DOMAIN_OR_ROLE", enrollment_changes=changes)
        for changes in (
            {"role": C.ENROLLER_ROLE},
            {"audience": "postapollo.identity.signin.v1"},
            {"schema": C.ENROLLMENT_SCHEMA},
        ):
            self.hold("WRONG_DOMAIN_OR_ROLE", custody_changes=changes)

    def test_14_wrong_enroller_or_custodian_key_fingerprint_refused(self):
        self.hold("CLAIMED_KEY_PIN_MISMATCH",
                  enrollment_changes={"enrollerKeySha256": "f" * 64})
        self.hold("CLAIMED_KEY_PIN_MISMATCH",
                  custody_changes={"custodianKeySha256": "f" * 64})

    def test_15_noncanonical_and_duplicate_keys_refused(self):
        bad = self.make()
        bad[4] = bad[4].replace(b',"role":', b', "role":')
        self.hold("NONCANONICAL_JSON", args=bad)
        bad = self.make()
        bad[7] = b'{"schema":"a","schema":"b"}'
        self.hold("DUPLICATE_JSON_KEY", args=bad)

    def test_16_extra_missing_and_invalid_types_refused(self):
        self.hold("EXACT_FIELDS_REQUIRED",
                  enrollment_changes={"unexpected": True})
        self.hold("EXACT_FIELDS_REQUIRED",
                  custody_changes={"unexpected": True})
        self.hold("INVALID_ENROLLMENT_EPOCH",
                  enrollment_changes={"enrollmentEpoch": True})
        self.hold("INVALID_writerJournalCounter",
                  custody_changes={"writerJournalCounter": True})

    def test_17_missing_or_malformed_signatures_refused(self):
        bad = self.make()
        bad[6] = b"short"
        self.hold("ENROLLER_PUBLIC_KEY_BOUNDS", args=bad)
        bad = self.make()
        bad[8] = b"short"
        self.hold("CUSTODIAN_SIGNATURE_BOUNDS", args=bad)

    def test_18_no_signer_or_storage_operations_exposed(self):
        result = self.check()
        for key in ("writerJournalDurabilityVerified",
                    "historicalWriterKeyRevocationChecked",
                    "custodyAntirollbackVerified",
                    "nativeWriterPeerAndSeatVerified",
                    "c5RevocationFenceSettled", "productionAuthority"):
            self.assertFalse(result[key])
        for name in ("issue_grant", "settle_permit", "commit_response",
                     "enroll_signer", "write_journal"):
            self.assertNotIn(name, dir(C))


if __name__ == "__main__":
    unittest.main()
