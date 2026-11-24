#!/usr/bin/env python3
"""DOC 3 // actual disposable B4f terminal outbox vs untrusted V1 claims."""
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
import local_terminal_outbox_b4f as b4f
from services.connections.forest import ForestC5B4fOutboxComparison as C


def _fixture_type():
    spec = importlib.util.spec_from_file_location(
        "doc3_b4f_v1_fixture",
        ROOT / "tests/connections/test_connections_forest_c5_exact_session_v1_preflight.py")
    if spec is None or spec.loader is None:
        raise AssertionError("V1_TEST_FIXTURE_NOT_AVAILABLE")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.ForestC5V1SessionReceiptTests


class B4fC5LocalOutboxComparisonTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="doc3-b4f-c5-")
        self.db = sqlite3.connect(Path(self.temp.name) / "fixture.sqlite")
        b1.bootstrap_synthetic(self.db)
        b3.bootstrap_attempts_synthetic(self.db)
        b4f.bootstrap_local_terminal_outbox_synthetic(self.db)
        self.journal = b1.ForestSessionJournal(self.db)
        self.sid = self.journal.create_session(
            "owner_a", "CHERRY", "synthetic private title", now_ms=100)["session_id"]
        self.user_turn = self.journal.append_turn(
            "owner_a", self.sid, expected_revision=0,
            role="user", body="synthetic private question", now_ms=101)["turn_id"]
        self.model_calls = 0

        def _no_model(**_kwargs):
            self.model_calls += 1
            raise AssertionError("MODEL_MUST_NOT_EXECUTE")
        self.bridge = b3.ForestTurnBridge(
            self.journal, clock_ms=lambda: 200, streamer=_no_model,
            synthetic_terminal_outbox=True)
        self.attempt, _ = self.bridge._reserve(
            "owner_a", self.sid, 1, "qwen3:1.7b")
        self.inspector = b4f.ForestLocalTerminalOutboxInspector(self.journal)
        fixture = _fixture_type()
        self.v1 = fixture(
            methodName="test_01_valid_three_signed_fixtures_only_claim_consistency")
        self.v1.setUp()
        self.v1.base.update(
            principal="owner_a", tree="CHERRY", sessionId=self.sid,
            userTurn=self.user_turn, attempt=self.attempt,
            model="qwen3:1.7b", revision=1,
            request="r_0123456789abcdef")

    def tearDown(self):
        self.db.close()
        self.temp.cleanup()

    def observe(self):
        return self.inspector.inspect(
            owner="owner_a", session_id=self.sid, attempt_id=self.attempt)

    def v1_claim(self, *, intent_changes=None, receipt_changes=None):
        parts = self.v1.build(
            intent_changes=intent_changes, receipt_changes=receipt_changes)
        return self.v1.inspect(parts), parts[0]

    def compare(self, *, local=None, claimed=None, wire=None):
        if local is None:
            local = self.observe()
        if claimed is None or wire is None:
            claimed, wire = self.v1_claim()
        return C.compare_untrusted_b4f_event_and_v1_fixture(local, claimed, wire)

    def commit(self):
        return self.bridge._commit(
            "owner_a", self.sid, self.attempt, 1, "qwen3:1.7b",
            "synthetic private assistant answer")

    def abort(self):
        self.bridge._abort(self.attempt)

    def expect_hold(self, text, **kwargs):
        with self.assertRaises(C.B4fC5Hold) as ctx:
            self.compare(**kwargs)
        self.assertIn(text, str(ctx.exception))

    def assert_no_authority(self, result):
        self.assertEqual(result["status"], C.STATUS_HOLD)
        self.assertEqual(result["safeActions"], [])
        for name in C.NO_AUTHORITY:
            self.assertIs(result[name], False, name)
        self.assertIs(result["independentB4fWriterCustodyAvailable"], False)
        self.assertIs(result["localEventIdIsOnlyUntrustedCorrelation"], True)
        for secret in ("synthetic private title", "synthetic private question",
                       "synthetic private assistant answer", self.sid, self.attempt):
            self.assertNotIn(secret, str(result))
        self.assertEqual(self.model_calls, 0)

    def test_01_local_reserved_no_event_is_unknown_hold(self):
        obs = self.observe()
        self.assertEqual(obs["localTerminalEvent"], "LOCAL_EVENT_NOT_OBSERVED")
        result = self.compare(local=obs)
        self.assertEqual(result["reason"], "EXPECTED_EVENT_UNKNOWN_LEGACY_OR_MISSING_HOLD")
        self.assert_no_authority(result)

    def test_02_actual_same_transaction_commit_plus_signed_claim_holds(self):
        self.commit()
        obs = self.observe()
        self.assertEqual(obs["localTerminalEvent"], "LOCAL_COMMITTED")
        self.assertEqual(obs["forestWriteState"], "FOREST_COMMITTED")
        self.assertTrue(obs["localEventId"].startswith("e_"))
        result = self.compare(local=obs)
        self.assertEqual(result["reason"], "EVENT_AND_SIGNED_CLAIM_MATCH_BUT_NOT_AUTHENTICATED_HOLD")
        self.assert_no_authority(result)

    def test_03_actual_abort_plus_signed_rollback_holds(self):
        self.abort()
        claimed, wire = self.v1_claim(
            receipt_changes={"terminalOutcome": "ROLLBACK_CONFIRMED"})
        result = self.compare(claimed=claimed, wire=wire)
        self.assertEqual(result["reason"], "EVENT_AND_SIGNED_CLAIM_MATCH_BUT_NOT_AUTHENTICATED_HOLD")
        self.assertEqual(result["localTerminalObservationUntrusted"], "LOCAL_ABORTED")
        self.assert_no_authority(result)

    def test_04_actual_abort_vs_signed_commit_is_conflict_hold(self):
        self.abort()
        result = self.compare()
        self.assertTrue(result["localAndSignedClaimsConflict"])
        self.assertEqual(result["reason"], "LOCAL_B4F_EVENT_AND_V1_CLAIM_CONFLICT_HOLD")
        self.assert_no_authority(result)

    def test_05_actual_commit_vs_signed_rollback_is_conflict_hold(self):
        self.commit()
        claimed, wire = self.v1_claim(
            receipt_changes={"terminalOutcome": "ROLLBACK_CONFIRMED"})
        result = self.compare(claimed=claimed, wire=wire)
        self.assertTrue(result["localAndSignedClaimsConflict"])
        self.assert_no_authority(result)

    def test_06_missing_event_after_commit_is_not_legacy_or_rollback_proof(self):
        self.commit()
        # Disposable corruption to simulate a missing expected terminal row.
        self.db.execute("DROP TRIGGER forest_b4f_deny_delete")
        self.db.execute(
            "DELETE FROM forest_local_terminal_events_b4f WHERE attempt_id=?",
            (self.attempt,))
        self.db.commit()
        obs = self.observe()
        self.assertEqual(obs["forestWriteState"], "FOREST_COMMITTED")
        self.assertEqual(obs["localTerminalEvent"], "LOCAL_EVENT_NOT_OBSERVED")
        result = self.compare(local=obs)
        self.assertEqual(result["reason"], "EXPECTED_EVENT_UNKNOWN_LEGACY_OR_MISSING_HOLD")
        self.assert_no_authority(result)

    def test_07_uninstrumented_legacy_commit_is_indistinguishable_without_provenance(self):
        legacy = b3.ForestTurnBridge(
            self.journal, clock_ms=lambda: 200,
            streamer=lambda **kwargs: iter(()),
            synthetic_terminal_outbox=False)
        legacy._commit(
            "owner_a", self.sid, self.attempt, 1,
            "qwen3:1.7b", "synthetic private assistant answer")
        self.assertEqual(self.observe()["localTerminalEvent"], "LOCAL_EVENT_NOT_OBSERVED")
        self.assert_no_authority(self.compare())

    def test_08_old_database_snapshot_restores_both_attempt_and_outbox(self):
        backup = sqlite3.connect(":memory:")
        try:
            self.db.backup(backup)  # BEFORE the commit.
            signed, wire = self.v1_claim()
            self.commit()
            self.assertEqual(self.observe()["localTerminalEvent"], "LOCAL_COMMITTED")
            self.assert_no_authority(self.compare(claimed=signed, wire=wire))
            backup.backup(self.db)  # Restores attempt and outbox together.
            self.assertEqual(self.observe()["forestWriteState"], "FOREST_RESERVED")
            self.assertEqual(self.observe()["localTerminalEvent"], "LOCAL_EVENT_NOT_OBSERVED")
            self.assert_no_authority(self.compare(claimed=signed, wire=wire))
        finally:
            backup.close()

    def test_09_outbox_event_and_local_attempt_must_agree(self):
        self.commit()
        original = self.observe()
        self.expect_hold(
            "LOCAL_OUTBOX_EVENT_AND_ATTEMPT_CONTRADICT",
            local=dict(original, localTerminalEvent="LOCAL_ABORTED"))

    def test_10_reserved_cannot_claim_terminal_event(self):
        orig = self.observe()
        self.expect_hold(
            "LOCAL_OUTBOX_EVENT_AND_ATTEMPT_CONTRADICT",
            local=dict(orig, localTerminalEvent="LOCAL_COMMITTED",
                       localEventId="e_" + "1" * 32))

    def test_11_missing_event_must_not_carry_an_event_id(self):
        orig = self.observe()
        self.expect_hold(
            "MISSING_EVENT_WITH_NONEMPTY_ID",
            local=dict(orig, localEventId="e_" + "0" * 32))

    def test_12_present_event_must_have_writer_shaped_id(self):
        self.commit()
        orig = self.observe()
        for bad in (None, "fake", "e_" + "x" * 32, "e_" + "0" * 31, True):
            with self.subTest(bad=bad):
                self.expect_hold(
                    "EVENT_ID_INVALID_OR_MISSING",
                    local=dict(orig, localEventId=bad))

    def test_13_custody_issuer_receipt_and_retry_flags_must_be_false(self):
        self.commit()
        orig = self.observe()
        for name in (
            "custodyAuthenticated", "terminalReceiptAuthenticated",
            "safeToRetryInference", "safeToReleaseRevocation",
            "productionAuthority",
        ):
            with self.subTest(name=name):
                self.expect_hold(
                    "LOCAL_OUTBOX_AUTHORITY_PROMOTION_REFUSED",
                    local=dict(orig, **{name: True}))

    def test_14_unknown_extra_fields_and_private_body_denied(self):
        original = self.observe()
        self.expect_hold(
            "LOCAL_OUTBOX_EXACT_FIELDS_REQUIRED",
            local=dict(original, owner="owner_a"))
        self.expect_hold(
            "LOCAL_OUTBOX_EXACT_FIELDS_REQUIRED",
            local=dict(original, reply="synthetic private assistant answer"))
        incomplete = dict(original)
        incomplete.pop("custodyAuthenticated")
        self.expect_hold("LOCAL_OUTBOX_EXACT_FIELDS_REQUIRED", local=incomplete)

    def test_15_v1_session_mutation_cannot_match_original_outbox(self):
        signed, wire = self.v1_claim(intent_changes={"sessionId": "s_other"})
        self.expect_hold("V1_OR_ORIGINAL_ATTEMPT_MISMATCH",
                         claimed=signed, wire=wire)

    def test_16_v1_attempt_mutation_cannot_match_original_outbox(self):
        signed, wire = self.v1_claim(intent_changes={"attempt": "a_other"})
        self.expect_hold("V1_OR_ORIGINAL_ATTEMPT_MISMATCH",
                         claimed=signed, wire=wire)

    def test_17_false_signed_issuer_authority_flag_rejected(self):
        signed, wire = self.v1_claim()
        signed["forestProtectedTerminalReconciled"] = True
        self.expect_hold("V1_OR_ORIGINAL_ATTEMPT_MISMATCH",
                         claimed=signed, wire=wire)

    def test_18_other_owner_or_session_denied_by_original_b4f_inspector(self):
        self.commit()
        for owner, session in (("owner_other", self.sid),
                               ("owner_a", "s_other")):
            with self.subTest(owner=owner, session=session):
                with self.assertRaises(b4f.OutboxRefusal):
                    self.inspector.inspect(
                        owner=owner, session_id=session, attempt_id=self.attempt)

    def test_19_b4f_original_lineage_corruption_refused_before_c5_comparison(self):
        reply = self.commit()
        self.db.execute(
            "UPDATE forest_turns SET provider_key='unrecognized' WHERE turn_id=?",
            (reply["turn_id"],))
        self.db.commit()
        with self.assertRaises(b4f.OutboxRefusal):
            self.observe()

    def test_20_neither_comparison_nor_b4f_inspection_runs_model_or_writes(self):
        self.commit()
        before = self.db.total_changes
        for _ in range(4):
            self.assert_no_authority(self.compare())
        self.assertEqual(self.db.total_changes, before)
        source = (ROOT / "services/connections/forest/ForestC5B4fOutboxComparison.py").read_text()
        for forbidden in ("sqlite3.connect(", "write_journal(",
                          "ForestTurnBridge(", "subprocess.run(",
                          "socket.connect("):
            self.assertNotIn(forbidden, source)



    def test_21_outbox_keys_and_count_checked_before_equality(self):
        class HostileKey(str):
            armed = False
            __hash__ = str.__hash__

            def __eq__(self, other):
                if self.armed:
                    raise AssertionError("unexpected outbox key comparison")
                return super().__eq__(other)

        local = self.observe()
        key = HostileKey("schema")
        local[key] = local.pop("schema")
        key.armed = True
        self.expect_hold("LOCAL_OUTBOX_EXACT_FIELDS_REQUIRED", local=local)
        local = self.observe()
        local.update({f"extra{i}": None for i in range(2048)})
        self.expect_hold("LOCAL_OUTBOX_EXACT_FIELDS_REQUIRED", local=local)

    def test_22_outbox_scalar_types_precede_comparison(self):
        class HostileValue:
            def __eq__(self, other):
                raise AssertionError("unexpected outbox value equality")

            def __ne__(self, other):
                raise AssertionError("unexpected outbox value inequality")

        for field in ("schema", "c5Settlement", "attemptId",
                      "sessionId", "forestWriteState", "localTerminalEvent"):
            with self.subTest(field=field):
                self.expect_hold("LOCAL_OUTBOX_SHAPE_OR_STATUS_INVALID",
                                 local=dict(self.observe(), **{field: HostileValue()}))
        self.assert_no_authority(self.compare())

    def test_23_nested_recovery_refusal_does_not_chain(self):
        signed, _ = self.v1_claim()
        for wire in (b'{"private":"SYNTHETIC_PRIVATE',
                     b'{"private":"SYNTHETIC_PRIVATE\xff"}'):
            with self.subTest(size=len(wire)):
                with self.assertRaises(C.B4fC5Hold) as caught:
                    self.compare(claimed=signed, wire=wire)
                self.assertEqual(str(caught.exception),
                                 "FOREST_B4F_C5_UNKNOWN_HOLD // "
                                 "V1_OR_ORIGINAL_ATTEMPT_MISMATCH")
                self.assertIsNone(caught.exception.__cause__)
                self.assertIsNone(caught.exception.__context__)


if __name__ == "__main__":
    unittest.main()
