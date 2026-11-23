"""Forest B4e // synthetic recovery lineage adversarial tests.

All data is disposable; no host, installed C5 issuer or production authority.
Foreign keys stay enabled while tests create valid-but-wrong relationships.
"""
from __future__ import annotations

import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts/forest"))
import recovery_inspect_b4d as recovery
import session_journal_v0 as b1
import turn_bridge_b3 as b3


class RecoveryLineageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="forest-b4e-lineage-")
        self.db = sqlite3.connect(Path(self.temp.name) / "synthetic.db")
        b1.bootstrap_synthetic(self.db)
        b3.bootstrap_attempts_synthetic(self.db)
        self.store = b1.ForestSessionJournal(self.db)
        self.session = self.store.create_session(
            "owner_a", "CHERRY", "synthetic", now_ms=100)["session_id"]
        self.user = self.store.append_turn(
            "owner_a", self.session, expected_revision=0,
            role="user", body="fixture user text", now_ms=101)["turn_id"]
        self.bridge = b3.ForestTurnBridge(
            self.store, clock_ms=lambda: 200,
            streamer=lambda **kwargs: iter(()))
        self.attempt, _ = self.bridge._reserve(
            "owner_a", self.session, 1, "qwen3:1.7b")
        self.inspector = recovery.ForestLocalRecoveryInspector(self.store)

    def tearDown(self):
        self.db.close()
        self.temp.cleanup()

    def report(self):
        return self.inspector.inspect(
            owner="owner_a", session_id=self.session,
            attempt_id=self.attempt)

    def committed(self):
        return self.bridge._commit(
            "owner_a", self.session, self.attempt,
            1, "qwen3:1.7b", "synthetic output")

    def expect_hold(self):
        with self.assertRaisesRegex(recovery.RecoveryRefusal,
                                    "LOCAL_INTEGRITY_HOLD"):
            self.report()

    def write(self, sql, *args):
        self.db.execute(sql, args)
        self.db.commit()
        self.assertEqual(self.db.execute("PRAGMA foreign_keys").fetchone()[0], 1)

    def additional_turn(self, role, *, body="later", model="qwen3:1.7b"):
        rev = self.store.session("owner_a", self.session)["revision"]
        return self.store.append_turn(
            "owner_a", self.session, expected_revision=rev,
            role=role, body=body, now_ms=201,
            **({"provider": "ollama", "model": model}
               if role == "assistant" else {}))["turn_id"]

    def test_committed_original_lineage_passes(self):
        self.committed()
        self.assertEqual(self.report()["forestWriteState"], "FOREST_COMMITTED")

    def test_reserved_original_lineage_passes_without_reinference(self):
        self.assertEqual(self.report()["forestWriteState"], "FOREST_RESERVED")

    def test_aborted_original_lineage_passes(self):
        self.bridge._abort(self.attempt)
        self.assertEqual(self.report()["forestWriteState"], "FOREST_ABORTED")

    def test_committed_allows_later_session_revision_from_state_change(self):
        self.committed()
        self.store.set_state(
            "owner_a", self.session, expected_revision=2,
            next_state="PAUSED", now_ms=202)
        self.assertEqual(self.report()["forestWriteState"], "FOREST_COMMITTED")

    def test_reply_replaced_with_later_valid_assistant_in_same_session_refused(self):
        self.committed()
        self.additional_turn("user")
        wrong = self.additional_turn("assistant")
        self.write(
            "UPDATE forest_attempts_b3 SET reply_turn_id=? "
            "WHERE attempt_id=?", wrong, self.attempt)
        self.expect_hold()

    def test_original_user_replaced_with_later_same_session_user_refused(self):
        self.committed()
        wrong = self.additional_turn("user")
        self.write(
            "UPDATE forest_attempts_b3 SET user_turn_id=? "
            "WHERE attempt_id=?", wrong, self.attempt)
        self.expect_hold()

    def test_original_user_replaced_with_assistant_refused(self):
        receipt = self.committed()
        self.write(
            "UPDATE forest_attempts_b3 SET user_turn_id=? "
            "WHERE attempt_id=?", receipt["turn_id"], self.attempt)
        self.expect_hold()

    def test_original_user_replaced_with_other_session_user_refused(self):
        other = self.store.create_session(
            "owner_a", "MAPLE", "other", now_ms=100)["session_id"]
        wrong = self.store.append_turn(
            "owner_a", other, expected_revision=0, role="user",
            body="other user", now_ms=101)["turn_id"]
        self.write(
            "UPDATE forest_attempts_b3 SET user_turn_id=? "
            "WHERE attempt_id=?", wrong, self.attempt)
        self.expect_hold()

    def test_reply_replaced_with_other_session_assistant_refused(self):
        self.committed()
        other = self.store.create_session(
            "owner_a", "MAPLE", "other", now_ms=100)["session_id"]
        self.store.append_turn(
            "owner_a", other, expected_revision=0, role="user",
            body="other user", now_ms=101)
        wrong = self.store.append_turn(
            "owner_a", other, expected_revision=1, role="assistant",
            body="other assistant", provider="ollama",
            model="qwen3:1.7b", now_ms=102)["turn_id"]
        self.write(
            "UPDATE forest_attempts_b3 SET reply_turn_id=? "
            "WHERE attempt_id=?", wrong, self.attempt)
        self.expect_hold()

    def test_attempt_model_drift_is_rejected(self):
        self.committed()
        self.write(
            "UPDATE forest_attempts_b3 SET model_key='granite4:small-h' "
            "WHERE attempt_id=?", self.attempt)
        self.expect_hold()

    def test_reply_model_drift_is_rejected(self):
        receipt = self.committed()
        self.write(
            "UPDATE forest_turns SET model_key='granite4:small-h' "
            "WHERE turn_id=?", receipt["turn_id"])
        self.expect_hold()

    def test_reply_provider_drift_is_rejected(self):
        receipt = self.committed()
        self.write(
            "UPDATE forest_turns SET provider_key='remote' "
            "WHERE turn_id=?", receipt["turn_id"])
        self.expect_hold()

    def test_reply_timestamp_earlier_than_reservation_rejected(self):
        receipt = self.committed()
        self.write(
            "UPDATE forest_turns SET recorded_at_ms=199 WHERE turn_id=?",
            receipt["turn_id"])
        self.expect_hold()

    def test_reservation_timestamp_earlier_than_user_turn_rejected(self):
        self.write(
            "UPDATE forest_attempts_b3 SET created_at_ms=100 "
            "WHERE attempt_id=?", self.attempt)
        self.expect_hold()

    def test_reservation_updated_before_created_rejected(self):
        self.write(
            "UPDATE forest_attempts_b3 SET updated_at_ms=199 "
            "WHERE attempt_id=?", self.attempt)
        self.expect_hold()

    def test_expected_revision_less_than_user_ordinal_rejected(self):
        self.committed()
        self.write(
            "UPDATE forest_attempts_b3 SET expected_revision=0 "
            "WHERE attempt_id=?", self.attempt)
        self.expect_hold()

    def test_expected_revision_larger_than_current_revision_rejected(self):
        self.write(
            "UPDATE forest_attempts_b3 SET expected_revision=999 "
            "WHERE attempt_id=?", self.attempt)
        self.expect_hold()

    def test_committed_session_revision_must_advance_past_reservation(self):
        self.committed()
        self.write(
            "UPDATE forest_sessions SET revision=1 WHERE session_id=?",
            self.session)
        self.expect_hold()

    def test_reserved_with_corrupt_user_reference_fails(self):
        self.additional_turn("user")
        wrong = self.store.append_turn(
            "owner_a", self.session, expected_revision=2,
            role="assistant", body="fake", provider="ollama",
            model="qwen3:1.7b", now_ms=202)["turn_id"]
        self.write(
            "UPDATE forest_attempts_b3 SET user_turn_id=? "
            "WHERE attempt_id=?", wrong, self.attempt)
        self.expect_hold()

    def test_every_local_success_still_disclaims_c5_settlement(self):
        self.committed()
        report = self.report()
        self.assertEqual(report["c5Settlement"], "UNKNOWN_HOLD")
        self.assertFalse(report["safeToRetryInference"])
        self.assertFalse(report["safeToReleaseRevocation"])
        self.assertFalse(report["terminalReceiptAuthenticated"])
        self.assertFalse(report["productionAuthority"])

    def test_no_message_body_is_selected_by_inspector(self):
        source = (Path(__file__).resolve().parents[2] /
                  "scripts/forest/recovery_inspect_b4d.py").read_text()
        self.assertNotIn("t.body", source)
        self.assertNotIn("u.body", source)
        self.assertNotIn("SELECT *", source)
        self.assertNotIn("sqlite3.connect(", source)


if __name__ == "__main__":
    unittest.main()
