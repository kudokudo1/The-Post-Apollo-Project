#!/usr/bin/env python3
"""DOC 3 C5 ↔ Forest B4e: actual disposable SQLite, always UNKNOWN_HOLD."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts/forest"))

import session_journal_v0 as b1
import turn_bridge_b3 as b3
import recovery_inspect_b4d as b4e

from services.connections.forest import ForestC5LocalRecoveryComparison as C
from services.connections.forest import ForestC5ExactSessionV1Preflight as V


def _v1_fixture():
    spec = importlib.util.spec_from_file_location(
        "c5_recovery_v1_sample_writer",
        ROOT / "tests/connections/test_connections_forest_c5_exact_session_v1_preflight.py",
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("DOC3_V1_TEST_FIXTURE_UNAVAILABLE")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.ForestC5V1SessionReceiptTests


class ForestC5B4eRecoveryInteropTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="forest-c5-b4e-untrusted-")
        self.db = sqlite3.connect(Path(self.temp.name) / "synthetic.sqlite")
        b1.bootstrap_synthetic(self.db)
        b3.bootstrap_attempts_synthetic(self.db)
        self.store = b1.ForestSessionJournal(self.db)
        self.session = self.store.create_session(
            "owner_a", "CHERRY", "secret title", now_ms=100)["session_id"]
        self.user_turn = self.store.append_turn(
            "owner_a", self.session, expected_revision=0,
            role="user", body="secret user prompt", now_ms=101)["turn_id"]
        self.model_calls = 0

        def never_stream(**_kwargs):
            self.model_calls += 1
            raise AssertionError("MODEL_INFERENCE_NOT_PERMITTED")
        self.bridge = b3.ForestTurnBridge(
            self.store, clock_ms=lambda: 200, streamer=never_stream)
        self.attempt, _messages = self.bridge._reserve(
            "owner_a", self.session, 1, "qwen3:1.7b")
        self.inspector = b4e.ForestLocalRecoveryInspector(self.store)
        Fixture = _v1_fixture()
        self.fixture = Fixture(methodName="test_01_valid_three_signed_fixtures_only_claim_consistency")
        self.fixture.setUp()
        # Only disposable keys and claim inputs; never the native writer.
        self.fixture.base.update(
            principal="owner_a", tree="CHERRY",
            sessionId=self.session, userTurn=self.user_turn,
            attempt=self.attempt, model="qwen3:1.7b",
            revision=1, request="r_0123456789abcdef",
        )

    def tearDown(self):
        self.db.close()
        self.temp.cleanup()

    def report(self):
        return self.inspector.inspect(
            owner="owner_a", session_id=self.session, attempt_id=self.attempt)

    def signed(self, *, intent_changes=None, receipt_changes=None):
        parts = self.fixture.build(
            intent_changes=intent_changes, receipt_changes=receipt_changes)
        return self.fixture.inspect(parts), parts[0]

    def compare(self, local=None, signed=None, intent=None):
        if local is None:
            local = self.report()
        if signed is None or intent is None:
            signed, intent = self.signed()
        return C.compare_untrusted_local_with_v1_claim(local, signed, intent)

    def assert_denied(self, result):
        self.assertEqual(result["status"], C.STATUS_HOLD)
        self.assertEqual(result["safeActions"], [])
        for name in C.NO_AUTHORITY:
            self.assertIs(result[name], False, name)
        self.assertTrue(result["sourceObservationsBothUntrusted"])
        serialized = str(result)
        for secret in ("secret title", "secret user prompt", "secret assistant reply"):
            self.assertNotIn(secret, serialized)

    def write_committed(self):
        # Actual B3 SQLite INSERTs and transaction on a disposable test DB,
        # without ever calling a model or authenticating a native writer.
        return self.bridge._commit(
            "owner_a", self.session, self.attempt, 1,
            "qwen3:1.7b", "secret assistant reply")

    def hold(self, phrase, local=None, signed=None, intent=None):
        with self.assertRaises(C.RecoveryComparisonHold) as ctx:
            self.compare(local, signed, intent)
        self.assertIn(phrase, str(ctx.exception))

    def test_01_real_local_reserved_plus_signed_commit_does_not_settle(self):
        self.assertEqual(self.report()["forestWriteState"], "FOREST_RESERVED")
        result = self.compare()
        self.assertEqual(result["reason"], "LOCAL_RESERVED_NO_TERMINAL_PROOF_HOLD")
        self.assert_denied(result)

    def test_02_real_sqlite_commit_and_lost_client_ack_never_release_c5(self):
        # Suppress any caller-visible B3 result, mirroring a lost ACK.
        self.write_committed()
        self.assertEqual(self.report()["forestWriteState"], "FOREST_COMMITTED")
        result = self.compare()
        self.assertEqual(result["reason"], "LOCAL_AND_SIGNED_CLAIM_AGREE_BUT_UNTRUSTED_HOLD")
        self.assertEqual(result["signedWriterTerminalClaimUntrusted"], "COMMIT_CONFIRMED")
        self.assert_denied(result)

    def test_03_local_abort_and_forged_signed_commit_are_conflicting_holds(self):
        self.bridge._abort(self.attempt)
        result = self.compare()
        self.assertTrue(result["localAndSignedClaimsConflict"])
        self.assertEqual(result["reason"], "LOCAL_AND_SIGNED_CLAIM_CONFLICT_HOLD")
        self.assert_denied(result)

    def test_04_local_abort_and_signed_rollback_still_cannot_clear_issuer(self):
        self.bridge._abort(self.attempt)
        claim, wire = self.signed(receipt_changes={"terminalOutcome": "ROLLBACK_CONFIRMED"})
        result = self.compare(signed=claim, intent=wire)
        self.assertFalse(result["localAndSignedClaimsConflict"])
        self.assert_denied(result)

    def test_05_real_local_commit_and_signed_rollback_are_conflicting_holds(self):
        self.write_committed()
        claim, wire = self.signed(receipt_changes={"terminalOutcome": "ROLLBACK_CONFIRMED"})
        result = self.compare(signed=claim, intent=wire)
        self.assertTrue(result["localAndSignedClaimsConflict"])
        self.assert_denied(result)

    def test_06_original_session_swap_even_with_three_valid_fixture_signatures(self):
        signed, intent = self.signed(intent_changes={"sessionId": "sessionOther"})
        self.hold("ATTEMPT_OR_SESSION_OR_INTENT_MISMATCH",
                  signed=signed, intent=intent)

    def test_07_original_attempt_swap_even_with_valid_fixture_signatures(self):
        signed, intent = self.signed(intent_changes={"attempt": "a_other"})
        self.hold("ATTEMPT_OR_SESSION_OR_INTENT_MISMATCH",
                  signed=signed, intent=intent)

    def test_08_mutated_v1_intent_digest_is_not_trusted(self):
        signed, wire = self.signed()
        signed["claimedIntentSha256Untrusted"] = "f" * 64
        self.hold("ATTEMPT_OR_SESSION_OR_INTENT_MISMATCH",
                  signed=signed, intent=wire)

    def test_09_fake_signed_authority_true_is_rejected(self):
        signed, wire = self.signed()
        signed["v1WriterTerminalOutcomeProven"] = True
        self.hold("SIGNED_AUTHORITY_PROMOTION_REFUSED",
                  signed=signed, intent=wire)

    def test_10_fake_signed_actions_or_extra_fields_refused(self):
        signed, wire = self.signed()
        signed["safeActions"] = ["SETTLE"]
        self.hold("SIGNED_NOT_UNTRUSTED_DIAGNOSTIC", signed=signed, intent=wire)
        signed, wire = self.signed()
        signed["productionGrant"] = True
        self.hold("SIGNED_EXACT_FIELDS_REQUIRED", signed=signed, intent=wire)

    def test_11_local_c5_settlement_promotion_or_retry_refused(self):
        for field, value, message in (
            ("c5Settlement", "COMMIT_CONFIRMED", "LOCAL_SCHEMA_OR_STATE_UNTRUSTED"),
            ("safeToRetryInference", True, "LOCAL_AUTHORITY_PROMOTION_REFUSED"),
            ("terminalReceiptAuthenticated", True, "LOCAL_AUTHORITY_PROMOTION_REFUSED"),
            ("safeToReleaseRevocation", True, "LOCAL_AUTHORITY_PROMOTION_REFUSED"),
        ):
            with self.subTest(field=field):
                local = dict(self.report(), **{field: value})
                self.hold(message, local=local)

    def test_12_local_extra_private_field_or_missing_evidence_refused(self):
        local = dict(self.report(), prompt="secret user prompt")
        self.hold("LOCAL_EXACT_FIELDS_REQUIRED", local=local)
        local = dict(self.report())
        del local["attemptId"]
        self.hold("LOCAL_EXACT_FIELDS_REQUIRED", local=local)

    def test_13_wrong_owner_or_session_is_denied_by_actual_b4e_inspector(self):
        for owner, sess in (("wrong_owner", self.session),
                            ("owner_a", "other_session")):
            with self.subTest(owner=owner, sess=sess):
                with self.assertRaises(b4e.RecoveryRefusal):
                    self.inspector.inspect(
                        owner=owner, session_id=sess, attempt_id=self.attempt)

    def test_14_real_b4e_rejects_corrupt_assistant_reply_lineage(self):
        result = self.write_committed()
        self.db.execute(
            "UPDATE forest_turns SET provider_key='fake' WHERE turn_id=?",
            (result["turn_id"],))
        self.db.commit()
        with self.assertRaisesRegex(b4e.RecoveryRefusal, "LOCAL_INTEGRITY_HOLD"):
            self.report()
        self.assertEqual(self.model_calls, 0)

    def test_15_whole_disposable_sqlite_rollback_changes_local_view_not_c5(self):
        snap = sqlite3.connect(":memory:")
        try:
            self.db.backup(snap)  # before commit
            signed, intent = self.signed()
            self.write_committed()
            self.assertEqual(self.report()["forestWriteState"], "FOREST_COMMITTED")
            self.assert_denied(self.compare(signed=signed, intent=intent))
            snap.backup(self.db)
            self.assertEqual(self.report()["forestWriteState"], "FOREST_RESERVED")
            self.assert_denied(self.compare(signed=signed, intent=intent))
        finally:
            snap.close()

    def test_16_unknown_or_malformed_local_schema_cannot_grant(self):
        for field, value in (
            ("schema", "postapollo.forest.commit-terminal-receipt.v1"),
            ("forestWriteState", "COMMIT_CONFIRMED"),
            ("forestWriteState", ["FOREST_COMMITTED"]),
        ):
            with self.subTest(field=field):
                self.hold("LOCAL_SCHEMA_OR_STATE_UNTRUSTED",
                          local=dict(self.report(), **{field: value}))

    def test_17_fake_v1_receipt_public_key_does_not_match_valid_signature(self):
        parts = self.fixture.build()
        parts[10] = bytes([42]) * 32
        with self.assertRaises(V.V1Hold):
            self.fixture.inspect(parts)
        self.assertEqual(self.model_calls, 0)

    def test_18_comparing_evidence_never_mutates_database_or_calls_model(self):
        signed, intent = self.signed()
        before = self.db.total_changes
        for _ in range(3):
            self.assert_denied(self.compare(signed=signed, intent=intent))
        self.assertEqual(self.db.total_changes, before)
        self.assertEqual(self.model_calls, 0)

    def test_19_invalid_or_v0_intent_never_considered_v1(self):
        signed, wire = self.signed()
        self.hold("INTENT_V1_UNTRUSTED_OR_MALFORMED",
                  signed=signed,
                  intent=wire.replace(b"commit-intent.v1", b"commit-intent.v0"))

    def test_20_no_foreign_production_import_or_private_body_returns(self):
        source = (ROOT / "services/connections/forest/ForestC5LocalRecoveryComparison.py").read_text()
        for forbidden in ("sqlite3.connect(", "write_journal(",
                          "create_service(", "safeActions=['COMMIT']"):
            self.assertNotIn(forbidden, source)
        self.write_committed()
        self.assert_denied(self.compare())


if __name__ == "__main__":
    unittest.main()
