#!/usr/bin/env python3
"""Forest B4c signed terminal receipts: disposable byte-consistency only."""
from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path
import sys
import unittest

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

ROOT = Path(__file__).resolve().parents[2]
# An installed process imports from its managed Python path; this is only CI.
sys.path.insert(0, str(ROOT))
from services.connections.forest import ForestC5SignedEvidencePreflight as S  # noqa
from services.connections.forest import ForestC5TerminalReceiptPreflight as R  # noqa


def _load_samples():
    spec = importlib.util.spec_from_file_location(
        "forest_c5_original_samples",
        ROOT / "tests/connections/test_connections_forest_c5_signed_role_preflight.py",
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("SIGNED_ROLE_SAMPLE_MISSING")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


SAMPLES = _load_samples()


def _public_bytes(key):
    return key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )


class ForestC5WriterTerminalReceiptTests(unittest.TestCase):
    def setUp(self):
        self.key = Ed25519PrivateKey.generate()
        self.public = _public_bytes(self.key)
        self.keysha = hashlib.sha256(self.public).hexdigest()
        self.intent = SAMPLES.sample_intent()
        self.intentwire = S.canonical_bytes(self.intent)
        self.previous = "0" * 64
        self.permit = "p100"
        self.counter_floor = 4
        self.receipt = {
            "schema": R.RECEIPT_SCHEMA,
            "audience": S.AUDIENCE,
            "role": R.WRITER_ROLE,
            "intentSha256": hashlib.sha256(self.intentwire).hexdigest(),
            "permitId": self.permit,
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
            "writerKeySha256": self.keysha,
            "writerJournalCounter": 5,
            "previousJournalSha256": self.previous,
            "terminalOutcome": "COMMIT_CONFIRMED",
            "storageTxnId": "txn100",
            # A delayed terminal receipt is legal after original grant expiry.
            "recordedAtMs": 1900,
        }

    def signed(self, **changes):
        record = dict(self.receipt, **changes)
        wire = S.canonical_bytes(record)
        return wire, self.key.sign(wire)

    def check(self, wire=None, sig=None, **overrides):
        if wire is None:
            wire, sig = self.signed()
        kwargs = dict(
            expected_writer_key_sha256=self.keysha,
            expected_previous_journal_sha256=self.previous,
            expected_writer_release_sha256=self.intent["commitHostReleaseSha256"],
            expected_permit_id=self.permit,
            expected_minimum_journal_counter=self.counter_floor,
        )
        kwargs.update(overrides)
        return R.verify_unenrolled_terminal_receipt(
            self.intentwire, wire, sig, self.public, **kwargs,
        )

    def hold(self, reason, wire=None, sig=None, **overrides):
        with self.assertRaises(R.ReceiptHold) as captured:
            self.check(wire=wire, sig=sig, **overrides)
        if reason:
            self.assertIn(reason, str(captured.exception))

    def test_01_exact_ed25519_writer_signature_consistent_without_grant(self):
        result = self.check()
        self.assertEqual(
            result["status"], "UNENROLLED_RECEIPT_SIGNATURE_CONSISTENT_NOT_SETTLED")
        self.assertEqual(result["claimedTerminalOutcomeUntrusted"], "COMMIT_CONFIRMED")
        self.assertEqual(result["safeActions"], [])
        for key, value in R.RECEIPT_NO_AUTHORITY.items():
            self.assertIs(result[key], False, key)

    def test_02_rollback_result_is_equally_untrusted(self):
        wire, sig = self.signed(terminalOutcome="ROLLBACK_CONFIRMED")
        result = self.check(wire, sig)
        self.assertEqual(result["claimedTerminalOutcomeUntrusted"], "ROLLBACK_CONFIRMED")
        self.assertFalse(result["c5RevocationFenceSettled"])

    def test_03_receipt_after_original_expiry_is_not_lost(self):
        self.assertGreater(self.receipt["recordedAtMs"],
                           self.intent["expiresAtMs"])
        self.assertFalse(self.check()["terminalOutcomeAuthenticated"])

    def test_04_misbound_principal_tree_model_revision_attempt_refused(self):
        for key, value in (
            ("principal", "bob"), ("tree", "otherTree"),
            ("model", "llama3:8b"), ("revision", 19),
            ("attempt", "a999"), ("request", "r999"),
            ("grant", "g999"), ("consentEpoch", 14),
            ("challenge", "different_nonce"),
            ("intentSha256", "f" * 64),
        ):
            with self.subTest(key=key):
                self.hold("EXACT_RECEIPT_BINDING_MISMATCH",
                          *self.signed(**{key: value}))

    def test_05_wrong_role_audience_and_nonnative_outcome_refused(self):
        for key, value in (
            ("role", S.REVIEW_ROLE),
            ("audience", "postapollo.identity.signin.v1"),
            ("schema", "postapollo.other.v1"),
        ):
            with self.subTest(key=key):
                self.hold("WRONG_WRITER_DOMAIN", *self.signed(**{key: value}))
        self.hold("NONTERMINAL_OR_FORGED_OUTCOME",
                  *self.signed(terminalOutcome="UNKNOWN_HOLD"))
        self.hold("OUTCOME_TYPE", *self.signed(terminalOutcome=["COMMIT_CONFIRMED"]))

    def test_06_modified_signed_record_refused(self):
        wire, sig = self.signed()
        modified = wire.replace(b'"txn100"', b'"txn101"')
        self.assertNotEqual(modified, wire)
        self.hold("INVALID_SIGNATURE", modified, sig)

    def test_07_other_valid_writer_key_cannot_substitute_for_pinned_one(self):
        other = _public_bytes(Ed25519PrivateKey.generate())
        wire, sig = self.signed()
        with self.assertRaisesRegex(R.ReceiptHold, "UNPINNED_WRITER_KEY"):
            R.verify_unenrolled_terminal_receipt(
                self.intentwire, wire, sig, other,
                expected_writer_key_sha256=self.keysha,
                expected_previous_journal_sha256=self.previous,
                expected_writer_release_sha256=self.intent["commitHostReleaseSha256"],
                expected_permit_id=self.permit,
                expected_minimum_journal_counter=4,
            )
        # Changing the expected pin first mismatches the signed record's
        # own writer key fingerprint; the independent substituted-public-key
        # path above reaches the UNPINNED_WRITER_KEY check.
        self.hold("EXACT_RECEIPT_BINDING_MISMATCH", wire, sig,
                  expected_writer_key_sha256="f" * 64)

    def test_08_permit_and_released_writer_must_be_exact(self):
        self.hold("EXACT_RECEIPT_BINDING_MISMATCH", expected_permit_id="otherpermit")
        self.hold("WRITER_RELEASE_MISMATCH",
                  expected_writer_release_sha256="f" * 64)
        self.hold("EXACT_RECEIPT_BINDING_MISMATCH",
                  *self.signed(commitHostReleaseSha256="a" * 64))

    def test_09_journal_floor_and_predecessor_reject_replay(self):
        self.hold("STALE_JOURNAL_OR_TIME", expected_minimum_journal_counter=5)
        self.hold("STALE_JOURNAL_OR_TIME", expected_minimum_journal_counter=6)
        self.hold("EXACT_RECEIPT_BINDING_MISMATCH",
                  expected_previous_journal_sha256="a" * 64)
        self.hold("EXACT_RECEIPT_BINDING_MISMATCH",
                  *self.signed(previousJournalSha256="1" * 64))

    def test_10_receipt_without_real_journal_can_never_settle(self):
        # No Forest database, real protected writer, or issuer is contacted.
        for _ in range(3):
            result = self.check()
            self.assertTrue(result["fixturePinsCallerControlled"])
            self.assertFalse(result["writerJournalDurabilityVerified"])
            self.assertFalse(result["terminalOutcomeAuthenticated"])
            self.assertFalse(result["c5RevocationFenceSettled"])

    def test_11_wrong_record_times_and_counters_refused(self):
        self.hold("STALE_JOURNAL_OR_TIME", *self.signed(recordedAtMs=899))
        self.hold("INVALID_writerJournalCounter",
                  *self.signed(writerJournalCounter=True))
        self.hold("INVALID_writerJournalCounter",
                  *self.signed(writerJournalCounter=0))
        self.hold("INVALID_recordedAtMs",
                  *self.signed(recordedAtMs=False))

    def test_12_unknown_extra_key_duplicate_key_and_noncanonical_refused(self):
        self.hold("EXACT_FIELDS_REQUIRED",
                  *self.signed(productionAuthority=True))
        wire, sig = self.signed()
        duplicate = b'{"schema":"a","schema":"b"}'
        self.hold("DUPLICATE_JSON_KEY", duplicate, sig)
        altered = wire.replace(b',"grant":', b', "grant":')
        self.assertNotEqual(altered, wire)
        self.hold("NONCANONICAL_JSON", altered, sig)

    def test_13_missing_signature_or_public_key_refused(self):
        wire, sig = self.signed()
        self.hold("WRITER_SIGNATURE_BOUNDS", wire, sig[:12])
        with self.assertRaisesRegex(R.ReceiptHold, "WRITER_PUBLIC_KEY_BOUNDS"):
            R.verify_unenrolled_terminal_receipt(
                self.intentwire, wire, sig, b"short",
                expected_writer_key_sha256=self.keysha,
                expected_previous_journal_sha256=self.previous,
                expected_writer_release_sha256=self.intent["commitHostReleaseSha256"],
                expected_permit_id=self.permit,
                expected_minimum_journal_counter=4,
            )

    def test_14_bad_original_intent_rejected_even_with_valid_writer_signature(self):
        original = self.intentwire
        self.intentwire = S.canonical_bytes(
            SAMPLES.sample_intent(phase="PREPARE_GENERATE"))
        with self.assertRaises(R.ReceiptHold):
            self.check()
        self.intentwire = S.canonical_bytes(
            SAMPLES.sample_intent(model="bad model"))
        with self.assertRaises(R.ReceiptHold):
            self.check()
        self.intentwire = original

    def test_15_expected_root_values_are_not_enrolled_evidence(self):
        # Caller controls ALL pins/counters here, so no positive authority.
        fake = self.check(expected_minimum_journal_counter=0)
        self.assertFalse(fake["writerRootIndependentlyEnrolled"])
        self.assertFalse(fake["protectedWriterProcessAuthenticated"])
        self.assertFalse(fake["productionAuthority"])

    def test_16_enforced_scope_does_not_allow_read_memory_tools_or_replay(self):
        result = self.check()
        self.assertFalse(result["forestReadSessionAllowed"])
        self.assertFalse(result["forestToolExecutionAllowed"])
        self.assertFalse(result["forestDatabaseCommitAllowed"])
        self.assertFalse(result["c5HumanConsentVerified"])
        self.assertNotIn("issue_grant", dir(R))
        self.assertNotIn("settle_permit", dir(R))
        self.assertNotIn("commit_response", dir(R))



    def test_17_denial_constants_and_result_isolation(self):
        for key in R.RECEIPT_NO_AUTHORITY:
            with self.assertRaises(TypeError):
                R.RECEIPT_NO_AUTHORITY[key] = True
        result = self.check()
        result["terminalOutcomeAuthenticated"] = True
        result["safeActions"].append("SETTLE")
        fresh = self.check()
        self.assertFalse(fresh["terminalOutcomeAuthenticated"])
        self.assertEqual(fresh["safeActions"], [])

    def test_18_terminal_refusals_do_not_chain(self):
        wire, sig = self.signed()
        for malformed, reason in (
            (b'{"private":"SYNTHETIC_PRIVATE', "INVALID_JSON"),
            (b'{"private":"SYNTHETIC_PRIVATE\xff"}', "INVALID_JSON"),
            (b'{"schema":"a","schema":"b"}', "DUPLICATE_JSON_KEY"),
        ):
            with self.assertRaises(R.ReceiptHold) as caught:
                self.check(malformed, sig)
            self.assertIn(reason, str(caught.exception))
            self.assertIsNone(caught.exception.__cause__)
            self.assertIsNone(caught.exception.__context__)
        with self.assertRaises(R.ReceiptHold) as caught:
            self.check(wire, bytes([sig[0] ^ 1]) + sig[1:])
        self.assertIn("INVALID_SIGNATURE", str(caught.exception))
        self.assertIsNone(caught.exception.__cause__)
        self.assertIsNone(caught.exception.__context__)


if __name__ == "__main__":
    unittest.main()
