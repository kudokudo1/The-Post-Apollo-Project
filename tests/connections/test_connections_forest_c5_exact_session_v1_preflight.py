#!/usr/bin/env python3
"""Forest C5 v1 signed exact-session fixtures, deliberately NO native authority."""
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
from services.connections.forest import ForestC5ExactSessionV1Preflight as V  # noqa
from services.connections.forest import ForestC5SignedEvidencePreflight as S  # noqa
from services.connections.forest import ForestC5TerminalReceiptPreflight as R  # noqa


def _samples():
    spec = importlib.util.spec_from_file_location(
        "forest_v1_original_signed_fixture",
        ROOT / "tests/connections/test_connections_forest_c5_signed_role_preflight.py",
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("SIGNED_ROLE_SAMPLE_MISSING")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SAMPLES = _samples()


def pub(key):
    return key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


class ForestC5V1SessionReceiptTests(unittest.TestCase):
    def setUp(self):
        self.requester = Ed25519PrivateKey.generate()
        self.reviewer = Ed25519PrivateKey.generate()
        self.writer = Ed25519PrivateKey.generate()
        self.source_public = pub(self.requester)
        self.review_public = pub(self.reviewer)
        self.writer_public = pub(self.writer)
        self.base = SAMPLES.sample_intent(request="r_0123456789abcdef")
        self.base.update(schema=V.INTENT_SCHEMA_V1, sessionId="sessionA")
        self.previous = "0" * 64

    def build(self, *, intent_changes=None, binding_changes=None,
              source_changes=None, review_changes=None, receipt_changes=None):
        intent = dict(self.base, **(intent_changes or {}))
        intent_wire = S.canonical_bytes(intent)
        digest = sha(intent_wire)
        binding = {
            "owner_key": intent["principal"],
            "tree_key": intent["tree"],
            "session_id": intent["sessionId"],
            "user_turn_id": intent["userTurn"],
            "attempt_id": intent["attempt"],
            "request_id": intent["request"],
            "model_key": intent["model"],
            "expected_revision": intent["revision"],
        }
        binding.update(binding_changes or {})

        def role_record(role, decision, key, changes):
            record = {
                "schema": V.ROLE_SCHEMA_V1,
                "audience": S.AUDIENCE,
                "role": role,
                "decision": decision,
                "intentSha256": digest,
                "signerKeySha256": sha(pub(key)),
                "consentEpoch": intent["consentEpoch"],
                "challenge": intent["challenge"],
            }
            record.update(changes or {})
            wire = S.canonical_bytes(record)
            return wire, key.sign(wire)

        source_wire, source_sig = role_record(
            S.SOURCE_ROLE, "SOURCE_FIXTURE", self.requester, source_changes)
        review_wire, review_sig = role_record(
            S.REVIEW_ROLE, "REVIEW_FIXTURE", self.reviewer, review_changes)
        receipt = {
            "schema": V.RECEIPT_SCHEMA_V1,
            "audience": S.AUDIENCE,
            "role": R.WRITER_ROLE,
            "intentSha256": digest,
            "permitId": "permit01",
            "attempt": intent["attempt"],
            "grant": intent["grant"],
            "request": intent["request"],
            "principal": intent["principal"],
            "tree": intent["tree"],
            "sessionId": intent["sessionId"],
            "model": intent["model"],
            "revision": intent["revision"],
            "consentEpoch": intent["consentEpoch"],
            "challenge": intent["challenge"],
            "commitHostReleaseSha256": intent["commitHostReleaseSha256"],
            "writerKeySha256": sha(self.writer_public),
            "writerJournalCounter": 5,
            "previousJournalSha256": self.previous,
            "terminalOutcome": "COMMIT_CONFIRMED",
            "storageTxnId": "txn01",
            "recordedAtMs": 1900,
        }
        receipt.update(receipt_changes or {})
        receipt_wire = S.canonical_bytes(receipt)
        return [
            intent_wire, binding,
            source_wire, source_sig, self.source_public,
            review_wire, review_sig, self.review_public,
            receipt_wire, self.writer.sign(receipt_wire), self.writer_public,
        ]

    def inspect(self, parts=None, **changes):
        if parts is None:
            parts = self.build(**changes)
        return V.inspect_unenrolled_v1_claims(
            *parts,
            claimed_previous_journal_sha256=self.previous,
            claimed_minimum_journal_counter=4,
        )

    def hold(self, reason, parts=None, **changes):
        with self.assertRaises(V.V1Hold) as captured:
            self.inspect(parts, **changes)
        self.assertIn(reason, str(captured.exception))

    def denied(self, result):
        self.assertEqual(result["safeActions"], [])
        for key in V.NO_AUTHORITY:
            self.assertIs(result[key], False, key)
        self.assertTrue(result["claimedForestBindingCallerControlled"])
        self.assertTrue(result["claimedSignerKeysAndJournalCallerControlled"])

    def test_01_valid_three_signed_fixtures_only_claim_consistency(self):
        r = self.inspect()
        self.assertEqual(r["status"], "V1_SESSION_BOUND_FIXTURE_CONSISTENT_NOT_AUTHENTICATED")
        self.assertEqual(r["claimedSessionIdUntrusted"], "sessionA")
        self.denied(r)

    def test_02_claimed_rollback_not_proven(self):
        r = self.inspect(receipt_changes={"terminalOutcome": "ROLLBACK_CONFIRMED"})
        self.assertEqual(r["claimedTerminalOutcomeUntrusted"], "ROLLBACK_CONFIRMED")
        self.denied(r)

    def test_03_late_receipt_after_expiry_can_inspect_but_not_authorize(self):
        self.assertGreater(1900, self.base["expiresAtMs"])
        self.denied(self.inspect())

    def test_04_exact_original_session_mismatch_holds(self):
        self.hold("V1_SESSION_OR_ATTEMPT_BINDING_MISMATCH_session_id",
                  binding_changes={"session_id": "sessionB"})

    def test_05_signed_session_mutation_cannot_reuse_old_receipt(self):
        self.hold("V1_RECEIPT_BINDING_MISMATCH_sessionId",
                  intent_changes={"sessionId": "sessionB"},
                  receipt_changes={"sessionId": "sessionA"})

    def test_06_receipt_session_swap_with_recomputed_signature_holds(self):
        self.hold("V1_RECEIPT_BINDING_MISMATCH_sessionId",
                  receipt_changes={"sessionId": "sessionB"})

    def test_07_every_persisted_b4c_field_must_match_exact_intent(self):
        for name, other in (
            ("owner_key", "bob"), ("tree_key", "treeB"),
            ("user_turn_id", "u999"), ("attempt_id", "a999"),
            ("request_id", "r_9999999999999999"), ("model_key", "llama3:8b"),
            ("expected_revision", 40),
        ):
            with self.subTest(name=name):
                self.hold("V1_SESSION_OR_ATTEMPT_BINDING_MISMATCH_" + name,
                          binding_changes={name: other})

    def test_08_terminal_receipt_full_binding_cannot_diverge(self):
        for name, new in (
            ("intentSha256", "f" * 64), ("attempt", "a999"),
            ("grant", "g999"), ("request", "r999"),
            ("principal", "bob"), ("tree", "treeB"),
            ("model", "llama3:8b"), ("revision", 43),
            ("consentEpoch", 99), ("challenge", "nonce_9999999999abcd"),
            ("commitHostReleaseSha256", "e" * 64),
            ("writerKeySha256", "f" * 64),
            ("previousJournalSha256", "f" * 64),
        ):
            with self.subTest(name=name):
                self.hold("V1_RECEIPT_BINDING_MISMATCH_" + name,
                          receipt_changes={name: new})

    def test_09_v0_intent_and_v0_receipt_not_implicitly_promoted(self):
        self.hold("INVALID_V1_INTENT",
                  intent_changes={"schema": S.INTENT_SCHEMA})
        self.hold("V1_RECEIPT_WRONG_DOMAIN",
                  receipt_changes={"schema": R.RECEIPT_SCHEMA})
        self.hold("INVALID_V1_INTENT",
                  intent_changes={"v0Only": True})

    def test_10_v0_role_records_not_reused_as_v1(self):
        self.hold("V1_ROLE_WRONG_DOMAIN",
                  source_changes={"schema": S.RECORD_SCHEMA})
        self.hold("V1_ROLE_WRONG_DOMAIN",
                  review_changes={"schema": S.RECORD_SCHEMA})

    def test_11_role_cross_domain_and_wrong_decision_refused(self):
        self.hold("V1_ROLE_WRONG_DOMAIN",
                  source_changes={"role": S.REVIEW_ROLE})
        self.hold("V1_ROLE_WRONG_DOMAIN",
                  review_changes={"audience": "postapollo.timew.restore.v1"})
        self.hold("V1_ROLE_WRONG_DOMAIN",
                  review_changes={"decision": "CONSENT_GRANTED"})

    def test_12_role_intent_digest_and_epoch_mismatch_refused(self):
        self.hold("V1_ROLE_INTENT_OR_KEY_MISMATCH",
                  source_changes={"intentSha256": "a" * 64})
        self.hold("V1_ROLE_INTENT_OR_KEY_MISMATCH",
                  review_changes={"consentEpoch": 999})
        self.hold("V1_ROLE_INTENT_OR_KEY_MISMATCH",
                  source_changes={"signerKeySha256": "f" * 64})

    def test_13_changing_valid_public_key_fails_signature_or_pin(self):
        parts = self.build()
        parts[4] = pub(Ed25519PrivateKey.generate())
        self.hold("V1_ROLE_INTENT_OR_KEY_MISMATCH", parts)

    def test_14_tampered_ed25519_signatures_refused(self):
        for index, label in ((3, "INVALID_REQUESTER_SIGNATURE"),
                             (6, "INVALID_REVIEWER_SIGNATURE"),
                             (9, "INVALID_WRITER_SIGNATURE")):
            with self.subTest(index=index):
                parts = self.build()
                parts[index] = bytes([parts[index][0] ^ 1]) + parts[index][1:]
                self.hold(label, parts)

    def test_15_three_roles_cannot_share_same_key(self):
        parts = self.build()
        parts[7] = self.source_public
        self.hold("V1_THREE_DISTINCT_ROLE_KEYS_REQUIRED", parts)

    def test_16_replay_floor_predecessor_and_outcome_checks(self):
        self.hold("V1_UNTRUSTED_JOURNAL_FLOOR_OR_TIME_MISMATCH",
                  receipt_changes={"writerJournalCounter": 4})
        self.hold("V1_UNTRUSTED_JOURNAL_FLOOR_OR_TIME_MISMATCH",
                  receipt_changes={"recordedAtMs": 899})
        self.hold("V1_RECEIPT_BINDING_MISMATCH_previousJournalSha256",
                  receipt_changes={"previousJournalSha256": "f" * 64})
        self.hold("V1_RECEIPT_NOT_A_TERMINAL_OUTCOME",
                  receipt_changes={"terminalOutcome": "UNKNOWN_HOLD"})

    def test_17_session_type_boolean_epoch_and_request_grammar_rejected(self):
        self.hold("INVALID_sessionId", intent_changes={"sessionId": True})
        self.hold("INVALID_consentEpoch", intent_changes={"consentEpoch": True})
        self.hold("V1_B4C_REQUEST_ID_INVALID",
                  intent_changes={"request": "short"})
        self.hold("INVALID_sessionId",
                  intent_changes={"sessionId": "other/session"})

    def test_18_noncanonical_duplicate_and_extra_fields_refused(self):
        parts = self.build()
        parts[0] = parts[0].replace(b',"grant":', b', "grant":')
        self.hold("INVALID_V1_INTENT", parts)
        parts = self.build()
        parts[8] = b'{"schema":"a","schema":"b"}'
        self.hold("INVALID_V1_RECEIPT", parts)
        self.hold("INVALID_V1_INTENT", intent_changes={"productionAuthority": True})
        self.hold("INVALID_V1_RECEIPT",
                  receipt_changes={"humanConsentVerified": True})

    def test_19_wrong_action_audience_future_phase_or_unbounded_lease(self):
        self.hold("V1_INTENT_WRONG_DOMAIN_OR_PHASE",
                  intent_changes={"phase": "PREPARE_GENERATE"})
        self.hold("V1_INTENT_WRONG_DOMAIN_OR_PHASE",
                  intent_changes={"audience": "postapollo.identity.signin.v1"})
        self.hold("INVALID_OR_UNBOUNDED_ORIGINAL_LEASE",
                  intent_changes={"expiresAtMs": 400000})

    def test_20_caller_controls_all_three_keys_so_even_replayed_positive_denies(self):
        for _ in range(3):
            self.denied(self.inspect())
        for forbidden in ("issue_grant", "settle_permit", "commit_response",
                          "write_journal", "authorize_reader", "production_admission"):
            self.assertNotIn(forbidden, dir(V))


if __name__ == "__main__":
    unittest.main()
