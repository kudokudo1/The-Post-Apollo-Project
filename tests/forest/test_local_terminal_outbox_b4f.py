"""Forest B4f // disposable local terminal outbox transaction tests.

This is NOT signed writer custody, antirollback evidence, a real C5 issuer
or an authorization path for private Forest conversations.
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
import session_journal_v0 as b1
import turn_bridge_b3 as b3


class FakePermit:
    def __init__(self, binding, outcome=True):
        self.binding = binding
        self.outcome = outcome

    def __enter__(self):
        return self

    def terminal(self, reply):
        return self.outcome

    def __exit__(self, exc_type, exc, tb):
        return False


class OutboxTests(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory(prefix="forest-b4f-outbox-test-")
        self.path = Path(self.root.name) / "forest.db"
        self.db = sqlite3.connect(self.path)
        b1.bootstrap_synthetic(self.db)
        b3.bootstrap_attempts_synthetic(self.db)
        b4f.bootstrap_local_terminal_outbox_synthetic(self.db)
        self.journal = b1.ForestSessionJournal(self.db)
        self.sid = self.journal.create_session(
            "owner_a", "CHERRY", "private synthetic title", now_ms=100)["session_id"]
        self.user = self.journal.append_turn(
            "owner_a", self.sid, expected_revision=0, role="user",
            body="sensitive fake user question", now_ms=101)["turn_id"]
        self.now = 200
        self.model_calls = 0
        self.stream_mode = "complete"

        def streamer(*, model, messages, **kwargs):
            self.model_calls += 1
            yield {"event": "STARTED", "model": model, "provider": "ollama"}
            if self.stream_mode == "complete":
                yield {"event": "DELTA", "text": "sensitive fake assistant answer"}
                yield {"event": "COMPLETE", "model": model,
                       "provider": "ollama",
                       "text": "sensitive fake assistant answer"}
            elif self.stream_mode == "invalid":
                yield {"event": "DELTA", "text": 42}
            # Incomplete mode yields only STARTED.

        self.bridge = b3.ForestTurnBridge(
            self.journal, clock_ms=lambda: self.now,
            streamer=streamer, synthetic_terminal_outbox=True)
        self.reader = b4f.ForestLocalTerminalOutboxInspector(self.journal)

    def tearDown(self):
        self.db.close()
        self.root.cleanup()

    def row(self):
        return self.db.execute(
            "SELECT attempt_id,status,reply_turn_id FROM forest_attempts_b3 "
            "WHERE session_id=?", (self.sid,)).fetchone()

    def events(self):
        return self.db.execute(
            "SELECT event_id,attempt_id,owner_key,session_id,user_turn_id,"
            "tree_key,model_key,expected_revision,terminal_state,"
            "reply_turn_id,recorded_at_ms FROM forest_local_terminal_events_b4f "
            "ORDER BY rowid").fetchall()

    def reserve(self):
        attempt, msgs = self.bridge._reserve(
            "owner_a", self.sid, 1, "qwen3:1.7b")
        self.assertEqual(msgs[-1]["role"], "user")
        return attempt

    def commit(self, attempt):
        return self.bridge._commit(
            "owner_a", self.sid, attempt, 1, "qwen3:1.7b",
            "sensitive fake assistant answer")

    def inspect(self, attempt):
        return self.reader.inspect(
            owner="owner_a", session_id=self.sid, attempt_id=attempt)

    def test_commit_inserts_original_attempt_terminal_in_same_transaction(self):
        attempt = self.reserve()
        reply = self.commit(attempt)
        event = self.events()[0]
        self.assertEqual(len(self.events()), 1)
        self.assertTrue(event[0].startswith("e_"))
        self.assertEqual(event[1:9], (
            attempt, "owner_a", self.sid, self.user,
            "CHERRY", "qwen3:1.7b", 1, "COMMITTED"))
        self.assertEqual(event[9], reply["turn_id"])
        self.assertEqual(event[10], 200)
        result = self.inspect(attempt)
        self.assertEqual(result["forestWriteState"], "FOREST_COMMITTED")
        self.assertEqual(result["localTerminalEvent"], "LOCAL_COMMITTED")
        self.assertEqual(result["c5Settlement"], "UNKNOWN_HOLD")
        self.assertFalse(result["terminalReceiptAuthenticated"])

    def test_abort_has_positive_local_event_and_no_assistant_turn(self):
        attempt = self.reserve()
        self.bridge._abort(attempt)
        event = self.events()[0]
        self.assertEqual(event[8], "ABORTED")
        self.assertIsNone(event[9])
        self.assertEqual(self.row()[1], "ABORTED")
        self.assertEqual(self.inspect(attempt)["localTerminalEvent"],
                         "LOCAL_ABORTED")
        self.assertEqual(len(self.journal.turns("owner_a", self.sid)), 1)

    def test_failed_outbox_insert_rolls_back_reply_revision_and_attempt(self):
        attempt = self.reserve()
        self.db.execute(
            "CREATE TRIGGER synthetic_fail_outbox BEFORE INSERT ON "
            "forest_local_terminal_events_b4f BEGIN "
            "SELECT RAISE(ABORT,'failure injected'); END")
        with self.assertRaises(sqlite3.IntegrityError):
            self.commit(attempt)
        self.assertEqual(self.row()[1:], ("RESERVED", None))
        self.assertEqual(self.journal.session("owner_a", self.sid)["revision"], 1)
        self.assertEqual(len(self.journal.turns("owner_a", self.sid)), 1)
        self.assertEqual(self.events(), [])
        self.db.execute("DROP TRIGGER synthetic_fail_outbox")
        self.bridge._abort(attempt)
        self.assertEqual(self.events()[0][8], "ABORTED")

    def test_abort_event_failure_cannot_leave_aborted_without_event(self):
        attempt = self.reserve()
        self.db.execute(
            "CREATE TRIGGER synthetic_deny_abort BEFORE INSERT ON "
            "forest_local_terminal_events_b4f BEGIN "
            "SELECT RAISE(ABORT,'abort denied'); END")
        with self.assertRaises(sqlite3.IntegrityError):
            self.bridge._abort(attempt)
        self.assertEqual(self.row()[1], "RESERVED")
        self.assertEqual(self.events(), [])

    def test_commit_then_abort_never_creates_a_second_event(self):
        attempt = self.reserve()
        self.commit(attempt)
        prior = self.events()
        self.bridge._abort(attempt)
        self.assertEqual(self.row()[1], "COMMITTED")
        self.assertEqual(self.events(), prior)

    def test_abort_twice_keeps_one_terminal_event(self):
        attempt = self.reserve()
        self.bridge._abort(attempt)
        prior = self.events()
        self.bridge._abort(attempt)
        self.assertEqual(self.events(), prior)
        with self.assertRaises(b3.BridgeRefusal):
            self.commit(attempt)

    def test_sql_triggers_deny_event_mutation_or_deletion(self):
        attempt = self.reserve()
        self.commit(attempt)
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute(
                "UPDATE forest_local_terminal_events_b4f "
                "SET terminal_state='ABORTED' WHERE attempt_id=?", (attempt,))
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute(
                "DELETE FROM forest_local_terminal_events_b4f "
                "WHERE attempt_id=?", (attempt,))
        self.assertEqual(len(self.events()), 1)

    def test_unique_attempt_prevents_two_outcomes(self):
        attempt = self.reserve()
        self.commit(attempt)
        e = self.events()[0]
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute(
                "INSERT INTO forest_local_terminal_events_b4f "
                "(event_id,attempt_id,owner_key,session_id,user_turn_id,tree_key,"
                "model_key,expected_revision,terminal_state,reply_turn_id,"
                "recorded_at_ms) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                ("e_extra",attempt,"owner_a",self.sid,self.user,"CHERRY",
                 "qwen3:1.7b",1,"ABORTED",None,200))
        self.assertEqual(self.events()[0], e)

    def test_reservation_is_not_a_terminal_event(self):
        attempt = self.reserve()
        self.assertEqual(self.events(), [])
        self.assertEqual(self.inspect(attempt)["localTerminalEvent"],
                         "LOCAL_EVENT_NOT_OBSERVED")
        self.assertFalse(self.inspect(attempt)["safeToRetryInference"])

    def test_incomplete_stream_aborts_and_records_terminal_without_model_retry(self):
        self.stream_mode = "incomplete"
        observed = []
        with self.assertRaisesRegex(b3.BridgeRefusal, "INCOMPLETE_STREAM"):
            for e in self.bridge.exchange(
                    owner="owner_a", session_id=self.sid,
                    expected_revision=1, model="qwen3:1.7b"):
                observed.append(e)
        attempt = observed[0]["attempt_id"]
        self.assertEqual(self.row()[1], "ABORTED")
        self.assertEqual(self.events()[0][8], "ABORTED")
        self.assertEqual(self.inspect(attempt)["localTerminalEvent"], "LOCAL_ABORTED")
        with self.assertRaises(b3.BridgeRefusal):
            list(self.bridge.exchange(owner="owner_a", session_id=self.sid,
                                      expected_revision=1, model="qwen3:1.7b"))
        self.assertEqual(self.model_calls, 1)

    def test_cancellation_closes_generator_with_atomic_local_abort(self):
        gen = self.bridge.exchange(owner="owner_a", session_id=self.sid,
                                   expected_revision=1, model="qwen3:1.7b")
        reserved = next(gen)["attempt_id"]
        next(gen)  # STARTED
        gen.close()
        self.assertEqual(self.row()[1], "ABORTED")
        self.assertEqual(self.inspect(reserved)["localTerminalEvent"],
                         "LOCAL_ABORTED")

    def test_fenced_lost_ack_preserves_commit_event_and_unknown_settlement(self):
        seen = []
        with self.assertRaisesRegex(b3.BridgeRefusal, "UNKNOWN_HOLD"):
            for e in self.bridge.exchange(
                    owner="owner_a", session_id=self.sid,
                    expected_revision=1, model="qwen3:1.7b",
                    pre_commit=lambda: True,
                    fence_request_id="forest_b4f_request_1234",
                    fence_factory=lambda binding: FakePermit(
                        binding, outcome=False)):
                seen.append(e)
        attempt = seen[0]["attempt_id"]
        self.assertEqual(self.row()[1], "COMMITTED")
        self.assertEqual(self.inspect(attempt)["localTerminalEvent"],
                         "LOCAL_COMMITTED")
        self.assertEqual(self.inspect(attempt)["c5Settlement"], "UNKNOWN_HOLD")
        self.assertNotIn("COMMITTED", [e["event"] for e in seen])
        with self.assertRaises(b3.BridgeRefusal):
            list(self.bridge.exchange(owner="owner_a", session_id=self.sid,
                                      expected_revision=1, model="qwen3:1.7b"))
        self.assertEqual(self.model_calls, 1)

    def test_denied_precommit_rolls_back_reply_then_atomic_abort_event(self):
        with self.assertRaisesRegex(
                b3.BridgeRefusal, "PRE_COMMIT_AUTHORIZATION_DENIED"):
            list(self.bridge.exchange(
                owner="owner_a", session_id=self.sid,
                expected_revision=1, model="qwen3:1.7b",
                pre_commit=lambda: False))
        self.assertEqual(self.row()[1], "ABORTED")
        self.assertEqual(len(self.journal.turns("owner_a", self.sid)), 1)
        self.assertEqual(self.events()[0][8], "ABORTED")

    def test_caller_cannot_access_wrong_owner_or_session_event(self):
        attempt = self.reserve()
        self.commit(attempt)
        for fake in (("owner_b", self.sid), ("owner_a", "s_wrong")):
            with self.subTest(fake=fake):
                with self.assertRaises(b4f.OutboxRefusal):
                    self.reader.inspect(
                        owner=fake[0], session_id=fake[1], attempt_id=attempt)

    def test_original_user_attempt_model_tamper_is_denied(self):
        attempt = self.reserve()
        self.commit(attempt)
        self.db.execute(
            "UPDATE forest_attempts_b3 SET model_key='other:model' "
            "WHERE attempt_id=?", (attempt,))
        self.db.commit()
        with self.assertRaises(b4f.OutboxRefusal):
            self.inspect(attempt)

    def test_event_survives_reopen_but_remains_untrusted(self):
        attempt = self.reserve()
        self.commit(attempt)
        self.db.close()
        db = sqlite3.connect(self.path)
        db.execute("PRAGMA foreign_keys=ON")
        try:
            j = b1.ForestSessionJournal(db)
            x = b4f.ForestLocalTerminalOutboxInspector(j).inspect(
                owner="owner_a", session_id=self.sid, attempt_id=attempt)
            self.assertEqual(x["localTerminalEvent"], "LOCAL_COMMITTED")
            self.assertFalse(x["custodyAuthenticated"])
            self.assertFalse(x["productionAuthority"])
        finally:
            db.close()
        self.db = sqlite3.connect(self.path)
        self.db.execute("PRAGMA foreign_keys=ON")

    def test_inspector_works_on_readonly_sqlite_with_no_changes(self):
        attempt = self.reserve()
        self.commit(attempt)
        db = sqlite3.connect("file:" + str(self.path) + "?mode=ro", uri=True)
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("PRAGMA query_only=ON")
        try:
            changes = db.total_changes
            result = b4f.ForestLocalTerminalOutboxInspector(
                b1.ForestSessionJournal(db)).inspect(
                    owner="owner_a", session_id=self.sid, attempt_id=attempt)
            self.assertEqual(result["localTerminalEvent"], "LOCAL_COMMITTED")
            self.assertEqual(db.total_changes, changes)
        finally:
            db.close()

    def test_snapshot_restoration_cannot_prove_external_custody(self):
        attempt = self.reserve()
        old_snapshot = Path(self.root.name) / "before-commit.db"
        snap_db = sqlite3.connect(old_snapshot)
        self.db.backup(snap_db)
        snap_db.close()
        self.commit(attempt)
        self.assertEqual(self.inspect(attempt)["localTerminalEvent"],
                         "LOCAL_COMMITTED")
        self.db.close()
        shutil.copyfile(old_snapshot, self.path)
        self.db = sqlite3.connect(self.path)
        self.db.execute("PRAGMA foreign_keys=ON")
        self.journal = b1.ForestSessionJournal(self.db)
        self.reader = b4f.ForestLocalTerminalOutboxInspector(self.journal)
        reverted = self.inspect(attempt)
        self.assertEqual(reverted["forestWriteState"], "FOREST_RESERVED")
        self.assertEqual(reverted["localTerminalEvent"], "LOCAL_EVENT_NOT_OBSERVED")
        self.assertEqual(reverted["c5Settlement"], "UNKNOWN_HOLD")
        self.assertFalse(reverted["safeToRetryInference"])
        self.assertFalse(reverted["custodyAuthenticated"])

    def test_only_explicit_fixture_bootstrap_is_permitted(self):
        before = sqlite3.connect(":memory:")
        try:
            b1.bootstrap_synthetic(before)
            with self.assertRaisesRegex(
                    b4f.OutboxRefusal, "B3_SCHEMA_REQUIRED"):
                b4f.bootstrap_local_terminal_outbox_synthetic(before)
            b3.bootstrap_attempts_synthetic(before)
            before.execute("PRAGMA foreign_keys=OFF")
            with self.assertRaisesRegex(
                    b4f.OutboxRefusal, "FOREIGN_KEYS_REQUIRED"):
                b4f.bootstrap_local_terminal_outbox_synthetic(before)
            before.execute("PRAGMA foreign_keys=ON")
            b4f.bootstrap_local_terminal_outbox_synthetic(before)
            with self.assertRaisesRegex(
                    b4f.OutboxRefusal, "LOCAL_OUTBOX_ALREADY_EXISTS"):
                b4f.bootstrap_local_terminal_outbox_synthetic(before)
        finally:
            before.close()

    def test_opt_in_writer_refuses_missing_outbox_but_legacy_fixture_remains(self):
        db = sqlite3.connect(":memory:")
        try:
            b1.bootstrap_synthetic(db)
            b3.bootstrap_attempts_synthetic(db)
            store = b1.ForestSessionJournal(db)
            with self.assertRaisesRegex(
                    b3.BridgeRefusal, "LOCAL_OUTBOX_UNAVAILABLE"):
                b3.ForestTurnBridge(
                    store, clock_ms=lambda: 200,
                    synthetic_terminal_outbox=True)
            legacy = b3.ForestTurnBridge(store, clock_ms=lambda: 200)
            self.assertIsInstance(legacy, b3.ForestTurnBridge)
        finally:
            db.close()

    def test_locally_misbound_event_owner_refuses_instead_of_looking_absent(self):
        attempt = self.reserve()
        self.commit(attempt)
        # A privileged local writer can drop SQL triggers, which is why
        # this event is NOT independently authenticated custody.
        self.db.execute("DROP TRIGGER forest_b4f_deny_update")
        self.db.execute(
            "UPDATE forest_local_terminal_events_b4f "
            "SET owner_key='owner_b' WHERE attempt_id=?", (attempt,))
        self.db.commit()
        with self.assertRaisesRegex(
                b4f.OutboxRefusal, "LOCAL_EVENT_INTEGRITY_HOLD"):
            self.inspect(attempt)

    def test_locally_misbound_event_session_refuses_instead_of_looking_absent(self):
        attempt = self.reserve()
        self.commit(attempt)
        other = self.journal.create_session(
            "owner_a", "MAPLE", "other synthetic", now_ms=101)
        self.db.execute("DROP TRIGGER forest_b4f_deny_update")
        self.db.execute(
            "UPDATE forest_local_terminal_events_b4f "
            "SET session_id=? WHERE attempt_id=?",
            (other["session_id"], attempt))
        self.db.commit()
        with self.assertRaisesRegex(
                b4f.OutboxRefusal, "LOCAL_EVENT_INTEGRITY_HOLD"):
            self.inspect(attempt)

    def test_failed_local_abort_preserves_original_error_and_reserved_hold(self):
        self.stream_mode = "invalid"
        gen = self.bridge.exchange(
            owner="owner_a", session_id=self.sid,
            expected_revision=1, model="qwen3:1.7b")
        attempt = next(gen)["attempt_id"]
        next(gen)  # STARTED
        # An adversarial local writer modifies the original user turn.
        # ABORT event validation will fail and rollback. The original
        # invalid-stream reason must not be replaced by that secondary error.
        self.db.execute(
            "UPDATE forest_turns SET role='assistant' WHERE turn_id=?",
            (self.user,))
        self.db.commit()
        with self.assertRaisesRegex(
                b3.BridgeRefusal, "INVALID_STREAM_EVENT"):
            list(gen)
        self.assertEqual(self.row()[1], "RESERVED")
        self.assertEqual(self.events(), [])
        with self.assertRaises(b3.BridgeRefusal):
            list(self.bridge.exchange(
                owner="owner_a", session_id=self.sid,
                expected_revision=1, model="qwen3:1.7b"))

    def test_no_client_data_prompts_answers_or_authority_in_outbox(self):
        attempt = self.reserve()
        self.commit(attempt)
        data = json.dumps(self.inspect(attempt))
        sqltext = json.dumps(self.events())
        for secret in ("sensitive fake user question",
                       "sensitive fake assistant answer",
                       "private synthetic title"):
            self.assertNotIn(secret, data)
            self.assertNotIn(secret, sqltext)
        result = self.inspect(attempt)
        self.assertFalse(result["terminalReceiptAuthenticated"])
        self.assertFalse(result["safeToReleaseRevocation"])
        self.assertFalse(result["safeToRetryInference"])


if __name__ == "__main__":
    unittest.main()
