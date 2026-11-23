"""Forest B4g // disposable expectation marker and recovery classification.

No native host, real model, personal data, C5 issuer, independent writer
custody, or automatic replay. SQLite evidence is deliberately untrusted.
"""
from __future__ import annotations

import json
import shutil
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts/forest"))
import local_terminal_outbox_b4f as b4f
import recovery_outbox_expectation_b4g as b4g
import session_journal_v0 as b1
import turn_bridge_b3 as b3


class RecoveryExpectationTests(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory(prefix="forest-b4g-test-")
        self.path = Path(self.root.name) / "forest.db"
        self.db = sqlite3.connect(self.path)
        b1.bootstrap_synthetic(self.db)
        b3.bootstrap_attempts_synthetic(self.db)
        b4f.bootstrap_local_terminal_outbox_synthetic(self.db)
        self.journal = b1.ForestSessionJournal(self.db)
        self.sid = self.journal.create_session(
            "owner_a", "CHERRY", "private fake title", now_ms=100)["session_id"]
        self.journal.append_turn(
            "owner_a", self.sid, expected_revision=0,
            role="user", body="private fake question", now_ms=101)
        self.bridge = b3.ForestTurnBridge(
            self.journal, clock_ms=lambda: 200,
            synthetic_terminal_outbox=True,
            synthetic_outbox_expectation_b4g=True)
        self.reader = b4g.ForestOutboxExpectationInspector(self.journal)

    def tearDown(self):
        self.db.close()
        self.root.cleanup()

    def reserve(self, bridge=None):
        bridge = bridge or self.bridge
        attempt, _ = bridge._reserve("owner_a", self.sid, 1, "qwen3:1.7b")
        return attempt

    def commit(self, attempt, bridge=None):
        (bridge or self.bridge)._commit(
            "owner_a", self.sid, attempt, 1, "qwen3:1.7b",
            "private fake response")

    def inspect(self, attempt):
        return self.reader.inspect(
            owner="owner_a", session_id=self.sid, attempt_id=attempt)

    def remove_event_as_privileged_local_writer(self):
        self.db.execute("DROP TRIGGER forest_b4f_deny_delete")
        self.db.execute("DELETE FROM forest_local_terminal_events_b4f")
        self.db.commit()

    def test_marker_is_atomic_with_original_reservation(self):
        attempt = self.reserve()
        row = self.db.execute(
            "SELECT status,outbox_expectation_b4g FROM forest_attempts_b3 "
            "WHERE attempt_id=?", (attempt,)).fetchone()
        self.assertEqual(row, ("RESERVED", b3.OUTBOX_EXPECTATION_B4G))
        x = self.inspect(attempt)
        self.assertEqual(x["recoveryClassification"], "EXPECTED_EVENT_PENDING_HOLD")
        self.assertEqual(x["c5Settlement"], "UNKNOWN_HOLD")
        self.assertFalse(x["safeToRetryInference"])

    def test_atomic_reservation_failure_cannot_leave_orphan_marker(self):
        self.db.execute(
            "CREATE TRIGGER fail_b4g_reserve BEFORE INSERT ON forest_attempts_b3 "
            "WHEN NEW.outbox_expectation_b4g='OUTBOX_EXPECTED_V1' "
            "BEGIN SELECT RAISE(ABORT,'synthetic refused'); END")
        with self.assertRaises(b3.BridgeRefusal):
            self.reserve()
        self.assertEqual(self.db.execute(
            "SELECT COUNT(*) FROM forest_attempts_b3").fetchone()[0], 0)
        self.assertEqual(self.journal.session("owner_a", self.sid)["revision"], 1)

    def test_successful_commit_is_local_only(self):
        attempt = self.reserve()
        self.commit(attempt)
        x = self.inspect(attempt)
        self.assertEqual(x["localTerminalEvent"], "LOCAL_COMMITTED")
        self.assertEqual(x["recoveryClassification"],
                         "EXPECTED_EVENT_OBSERVED_LOCAL_ONLY")
        self.assertFalse(x["terminalReceiptAuthenticated"])
        self.assertFalse(x["productionAuthority"])

    def test_positive_abort_is_local_only(self):
        attempt = self.reserve()
        self.bridge._abort(attempt)
        x = self.inspect(attempt)
        self.assertEqual(x["localTerminalEvent"], "LOCAL_ABORTED")
        self.assertEqual(x["recoveryClassification"],
                         "EXPECTED_EVENT_OBSERVED_LOCAL_ONLY")
        self.assertFalse(x["safeToReleaseRevocation"])

    def test_missing_expected_commit_event_is_explicit_hold(self):
        attempt = self.reserve()
        self.commit(attempt)
        self.remove_event_as_privileged_local_writer()
        x = self.inspect(attempt)
        self.assertEqual(x["forestWriteState"], "FOREST_COMMITTED")
        self.assertEqual(x["recoveryClassification"],
                         "EXPECTED_TERMINAL_EVENT_MISSING_HOLD")
        self.assertFalse(x["safeToRetryInference"])
        self.assertEqual(x["c5Settlement"], "UNKNOWN_HOLD")

    def test_missing_expected_abort_event_is_explicit_hold(self):
        attempt = self.reserve()
        self.bridge._abort(attempt)
        self.remove_event_as_privileged_local_writer()
        self.assertEqual(self.inspect(attempt)["recoveryClassification"],
                         "EXPECTED_TERMINAL_EVENT_MISSING_HOLD")

    def test_b4f_without_marker_is_undetermined_not_confirmed_legacy(self):
        old = b3.ForestTurnBridge(
            self.journal, clock_ms=lambda: 200, synthetic_terminal_outbox=True)
        attempt = self.reserve(old)
        self.commit(attempt, old)
        x = self.inspect(attempt)
        self.assertEqual(x["localOutboxExpectation"],
                         "INSTRUMENTATION_UNDETERMINED")
        self.assertEqual(x["recoveryClassification"],
                         "EVENT_OBSERVED_EXPECTATION_UNDETERMINED")
        self.assertEqual(x["c5Settlement"], "UNKNOWN_HOLD")

    def test_missing_marker_after_commit_downgrades_to_unknown(self):
        attempt = self.reserve()
        self.commit(attempt)
        self.db.execute(
            "UPDATE forest_attempts_b3 SET outbox_expectation_b4g=NULL "
            "WHERE attempt_id=?", (attempt,))
        self.db.commit()
        x = self.inspect(attempt)
        self.assertEqual(x["localOutboxExpectation"],
                         "INSTRUMENTATION_UNDETERMINED")
        self.assertFalse(x["safeToRetryInference"])

    def test_invalid_local_marker_is_integrity_hold(self):
        attempt = self.reserve()
        self.commit(attempt)
        self.db.execute("PRAGMA ignore_check_constraints=ON")
        self.db.execute(
            "UPDATE forest_attempts_b3 SET outbox_expectation_b4g='FORGED' "
            "WHERE attempt_id=?", (attempt,))
        self.db.commit()
        self.db.execute("PRAGMA ignore_check_constraints=OFF")
        with self.assertRaisesRegex(
                b4f.OutboxRefusal, "LOCAL_EXPECTATION_INTEGRITY_HOLD"):
            self.inspect(attempt)

    def test_missing_marker_field_on_old_fixture_refuses_new_writer(self):
        other = sqlite3.connect(":memory:")
        try:
            b1.bootstrap_synthetic(other)
            column = (
                "    outbox_expectation_b4g TEXT CHECK(\\n"
                "        outbox_expectation_b4g IS NULL OR\\n"
                "        outbox_expectation_b4g='OUTBOX_EXPECTED_V1'),\\n"
            ).replace("\\n", "\n")
            self.assertIn(column, b3.ATTEMPT_SCHEMA)
            ddl = b3.ATTEMPT_SCHEMA.replace(column, "")
            other.executescript("BEGIN IMMEDIATE;\n" + ddl + "\nCOMMIT;")
            b4f.bootstrap_local_terminal_outbox_synthetic(other)
            old_journal = b1.ForestSessionJournal(other)
            with self.assertRaisesRegex(
                    b3.BridgeRefusal, "OUTBOX_EXPECTATION_SCHEMA_MISSING"):
                b3.ForestTurnBridge(
                    old_journal, clock_ms=lambda: 200,
                    synthetic_terminal_outbox=True,
                    synthetic_outbox_expectation_b4g=True)
            self.assertIsInstance(
                b4g.ForestOutboxExpectationInspector(old_journal),
                b4g.ForestOutboxExpectationInspector)
        finally:
            other.close()

    def test_mode_requires_outbox_flag_and_boolean(self):
        with self.assertRaisesRegex(
                b3.BridgeRefusal, "OUTBOX_EXPECTATION_REQUIRES_OUTBOX"):
            b3.ForestTurnBridge(
                self.journal, clock_ms=lambda: 200,
                synthetic_outbox_expectation_b4g=True)
        with self.assertRaisesRegex(
                b3.BridgeRefusal, "INVALID_DEPENDENCY"):
            b3.ForestTurnBridge(
                self.journal, clock_ms=lambda: 200,
                synthetic_terminal_outbox=True,
                synthetic_outbox_expectation_b4g="yes")

    def test_read_only_inspector_does_not_mutate_database(self):
        attempt = self.reserve()
        self.commit(attempt)
        db = sqlite3.connect("file:" + str(self.path) + "?mode=ro", uri=True)
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("PRAGMA query_only=ON")
        try:
            changes = db.total_changes
            value = b4g.ForestOutboxExpectationInspector(
                b1.ForestSessionJournal(db)).inspect(
                owner="owner_a", session_id=self.sid, attempt_id=attempt)
            self.assertEqual(value["recoveryClassification"],
                             "EXPECTED_EVENT_OBSERVED_LOCAL_ONLY")
            self.assertEqual(changes, db.total_changes)
        finally:
            db.close()

    def test_old_snapshot_restore_never_proves_noncommit(self):
        attempt = self.reserve()
        snapshot = Path(self.root.name) / "reserved.db"
        copy = sqlite3.connect(snapshot)
        self.db.backup(copy)
        copy.close()
        self.commit(attempt)
        self.db.close()
        shutil.copyfile(snapshot, self.path)
        self.db = sqlite3.connect(self.path)
        self.db.execute("PRAGMA foreign_keys=ON")
        self.journal = b1.ForestSessionJournal(self.db)
        self.reader = b4g.ForestOutboxExpectationInspector(self.journal)
        x = self.inspect(attempt)
        self.assertEqual(x["forestWriteState"], "FOREST_RESERVED")
        self.assertEqual(x["recoveryClassification"], "EXPECTED_EVENT_PENDING_HOLD")
        self.assertFalse(x["safeToRetryInference"])
        self.assertFalse(x["custodyAuthenticated"])

    def test_owner_and_session_scope_is_not_bypassed(self):
        attempt = self.reserve()
        self.commit(attempt)
        for owner, session in (
            ("wrong_owner", self.sid), ("owner_a", "wrong_session")
        ):
            with self.subTest(owner=owner, session=session):
                with self.assertRaises(b4f.OutboxRefusal):
                    self.reader.inspect(
                        owner=owner, session_id=session, attempt_id=attempt)

    def test_return_values_never_contain_private_body_or_authority(self):
        attempt = self.reserve()
        self.commit(attempt)
        data = json.dumps(self.inspect(attempt))
        for secret in ("private fake question", "private fake response",
                       "private fake title"):
            self.assertNotIn(secret, data)
        x = self.inspect(attempt)
        for field in ("terminalReceiptAuthenticated", "custodyAuthenticated",
                      "safeToRetryInference", "safeToReleaseRevocation",
                      "productionAuthority"):
            self.assertIs(x[field], False)
        self.assertEqual(x["c5Settlement"], "UNKNOWN_HOLD")


if __name__ == "__main__":
    unittest.main()
