"""Forest B3 // disposable-only durable reservation and completed-turn tests."""
from __future__ import annotations

import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts/forest"))
import session_journal_v0 as journal  # noqa: E402
import turn_bridge_b3 as b3  # noqa: E402


def standard_stream(*, model, messages, **kwargs):
    yield {"event": "STARTED", "provider": "ollama", "model": model}
    yield {"event": "DELTA", "text": "Hello"}
    yield {"event": "DELTA", "text": " Forest"}
    yield {"event": "COMPLETE", "provider": "ollama", "model": model,
           "text": "Hello Forest"}


class BridgeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="forest-b3-synthetic-")
        self.path = Path(self.temp.name) / "synthetic.db"
        self.db = sqlite3.connect(self.path, timeout=2)
        journal.bootstrap_synthetic(self.db)
        b3.bootstrap_attempts_synthetic(self.db)
        self.store = journal.ForestSessionJournal(self.db)
        self.now = 200
        self.requests = []
        self.events_override = None
        self.fail_during_stream = None

        def fake_streamer(**kwargs):
            self.requests.append(kwargs)
            stream = self.events_override
            if stream is None:
                stream = list(standard_stream(**kwargs))
            for event in stream:
                yield event
            if self.fail_during_stream is not None:
                raise self.fail_during_stream

        self.bridge = b3.ForestTurnBridge(
            self.store, clock_ms=lambda: self.now, streamer=fake_streamer)

    def tearDown(self):
        self.db.close()
        self.temp.cleanup()

    def new_session(self, owner="owner_a"):
        s = self.store.create_session(owner, "CHERRY", "Fixture", now_ms=100)
        self.store.append_turn(
            owner, s["session_id"], expected_revision=0,
            role="user", body="Help with a test", now_ms=101)
        return s["session_id"]

    def exchange(self, session_id, *, owner="owner_a", revision=1,
                 model="qwen3:1.7b", **kwargs):
        return self.bridge.exchange(
            owner=owner, session_id=session_id,
            expected_revision=revision, model=model, **kwargs)

    def attempt(self, session_id):
        return self.db.execute(
            "SELECT status,reply_turn_id,expected_revision FROM "
            "forest_attempts_b3 WHERE session_id=?", (session_id,)
        ).fetchone()

    def test_complete_stream_is_one_atomic_committed_reply(self):
        sid = self.new_session()
        events = list(self.exchange(sid))
        self.assertEqual([e["event"] for e in events],
                         ["RESERVED", "STARTED", "DELTA", "DELTA", "COMMITTED"])
        self.assertIs(events[3]["provisional"], True)
        self.assertEqual(events[-1]["text"], "Hello Forest")
        self.assertEqual(events[-1]["revision"], 2)
        self.assertEqual(self.attempt(sid)[0], "COMMITTED")
        self.assertEqual(self.attempt(sid)[1], events[-1]["turn_id"])
        turns = self.store.turns("owner_a", sid)
        self.assertEqual([x["role"] for x in turns], ["user", "assistant"])
        self.assertEqual(turns[-1]["model"], "qwen3:1.7b")
        self.assertEqual(self.store.session("owner_a", sid)["revision"], 2)
        self.assertEqual(len(self.requests), 1)
        self.assertEqual([m["content"] for m in self.requests[0]["messages"]],
                         ["Help with a test"])

    def test_committed_reply_survives_database_reopen(self):
        sid = self.new_session()
        receipt = list(self.exchange(sid))[-1]
        self.db.close()
        self.db = sqlite3.connect(self.path, timeout=2)
        self.store = journal.ForestSessionJournal(self.db)
        self.assertEqual(self.store.turns("owner_a", sid)[-1]["body"], "Hello Forest")
        self.assertEqual(self.attempt(sid)[1], receipt["turn_id"])

    def test_no_double_reply_to_same_user_turn(self):
        sid = self.new_session()
        list(self.exchange(sid))
        with self.assertRaisesRegex(b3.BridgeRefusal, "USER_TURN_REQUIRED"):
            list(self.exchange(sid, revision=2))
        self.assertEqual(len(self.requests), 1)
        self.assertEqual(len(self.store.turns("owner_a", sid)), 2)

    def test_aborted_stream_retains_user_and_blocks_automatic_retry(self):
        sid = self.new_session()
        self.events_override = [
            {"event": "STARTED", "provider": "ollama", "model": "qwen3:1.7b"},
            {"event": "DELTA", "text": "incomplete"},
        ]
        with self.assertRaisesRegex(b3.BridgeRefusal, "INCOMPLETE_STREAM"):
            list(self.exchange(sid))
        self.assertEqual(self.attempt(sid)[0], "ABORTED")
        self.assertEqual(len(self.store.turns("owner_a", sid)), 1)
        with self.assertRaisesRegex(b3.BridgeRefusal, "ATTEMPT_ALREADY_EXISTS"):
            list(self.exchange(sid))
        self.assertEqual(len(self.requests), 1)

    def test_cancellation_while_streaming_is_durable_refusal(self):
        sid = self.new_session()
        gen = self.exchange(sid)
        self.assertEqual(next(gen)["event"], "RESERVED")
        self.assertEqual(next(gen)["event"], "STARTED")
        self.assertEqual(next(gen)["event"], "DELTA")
        gen.close()
        self.assertEqual(self.attempt(sid)[0], "ABORTED")
        self.assertEqual(len(self.store.turns("owner_a", sid)), 1)
        with self.assertRaisesRegex(b3.BridgeRefusal, "ATTEMPT_ALREADY_EXISTS"):
            list(self.exchange(sid))

    def test_close_before_network_does_not_call_model(self):
        sid = self.new_session()
        gen = self.exchange(sid)
        self.assertEqual(next(gen)["event"], "RESERVED")
        gen.close()
        self.assertEqual(self.attempt(sid)[0], "ABORTED")
        self.assertEqual(self.requests, [])

    def test_duplicate_worker_on_second_db_connection_is_refused(self):
        sid = self.new_session()
        first = self.exchange(sid)
        self.assertEqual(next(first)["event"], "RESERVED")
        second_db = sqlite3.connect(self.path, timeout=2)
        try:
            second_journal = journal.ForestSessionJournal(second_db)
            other_calls = []

            def second_stream(**kwargs):
                other_calls.append(kwargs)
                yield from standard_stream(**kwargs)

            second_bridge = b3.ForestTurnBridge(
                second_journal, clock_ms=lambda: 200, streamer=second_stream)
            with self.assertRaisesRegex(b3.BridgeRefusal, "ATTEMPT_ALREADY_EXISTS"):
                list(second_bridge.exchange(
                    owner="owner_a", session_id=sid,
                    expected_revision=1, model="qwen3:1.7b"))
            self.assertEqual(other_calls, [])
        finally:
            first.close()
            second_db.close()
        self.assertEqual(self.attempt(sid)[0], "ABORTED")

    def test_trusted_owner_scope_is_not_client_authentication(self):
        sid = self.new_session()
        with self.assertRaisesRegex(b3.BridgeRefusal, "NOT_FOUND"):
            list(self.exchange(sid, owner="other_owner"))
        self.assertIsNone(self.attempt(sid))
        self.assertEqual(self.requests, [])

    def test_stale_revision_fails_before_any_model_invocation(self):
        sid = self.new_session()
        with self.assertRaisesRegex(b3.BridgeRefusal, "STALE_REVISION"):
            list(self.exchange(sid, revision=0))
        self.assertEqual(self.requests, [])
        self.assertIsNone(self.attempt(sid))

    def test_concurrent_user_append_rejects_inflight_completion(self):
        sid = self.new_session()
        gen = self.exchange(sid)
        self.assertEqual(next(gen)["event"], "RESERVED")
        self.assertEqual(next(gen)["event"], "STARTED")
        self.store.append_turn(
            "owner_a", sid, expected_revision=1,
            role="user", body="Newer request", now_ms=201)
        self.now = 202
        with self.assertRaisesRegex(b3.BridgeRefusal,
                                    "STALE_OR_CLOSED_SESSION"):
            list(gen)
        self.assertEqual(self.attempt(sid)[0], "ABORTED")
        turns = self.store.turns("owner_a", sid)
        self.assertEqual([row["body"] for row in turns],
                         ["Help with a test", "Newer request"])

    def test_paused_session_rejected_before_model_invocation(self):
        sid = self.new_session()
        self.store.set_state(
            "owner_a", sid, expected_revision=1,
            next_state="PAUSED", now_ms=150)
        with self.assertRaisesRegex(b3.BridgeRefusal, "SESSION_NOT_OPEN"):
            list(self.exchange(sid, revision=2))
        self.assertEqual(self.requests, [])

    def test_failed_final_sql_transaction_rolls_back_reply_and_revision(self):
        sid = self.new_session()
        self.db.execute(
            "CREATE TRIGGER deny_commit BEFORE UPDATE ON forest_attempts_b3 "
            "WHEN NEW.status='COMMITTED' "
            "BEGIN SELECT RAISE(ABORT,'test-only failure'); END"
        )
        self.db.commit()
        with self.assertRaisesRegex(b3.BridgeRefusal,
                                    "BRIDGE_STORAGE_OR_STREAM_ERROR"):
            list(self.exchange(sid))
        self.assertEqual(self.attempt(sid)[0], "ABORTED")
        self.assertEqual(len(self.store.turns("owner_a", sid)), 1)
        self.assertEqual(self.store.session("owner_a", sid)["revision"], 1)

    def test_invalid_stream_events_never_commit(self):
        cases = [
            [{"event": "DELTA", "text": "no start"}],
            [{"event": "STARTED", "provider": "ollama", "model": "wrong"}],
            list(standard_stream(model="qwen3:1.7b", messages=[])) +
            [{"event": "DELTA", "text": "after terminal"}],
            [{"event": "STARTED", "provider": "ollama", "model": "qwen3:1.7b"},
             {"event": "COMPLETE", "provider": "ollama",
              "model": "qwen3:1.7b", "text": "invented"}],
            [{"event": "STARTED", "provider": "ollama", "model": "qwen3:1.7b"},
             {"event": "TOOLS", "tool_calls": [{"name": "shell"}]}],
        ]
        for events in cases:
            with self.subTest(events=str(events)[:100]):
                sid = self.new_session()
                self.events_override = events
                with self.assertRaises(b3.BridgeRefusal):
                    list(self.exchange(sid))
                self.assertEqual(len(self.store.turns("owner_a", sid)), 1)
                self.assertEqual(self.attempt(sid)[0], "ABORTED")

    def test_completed_reply_larger_than_journal_limit_rejected(self):
        sid = self.new_session()
        huge = "x" * (journal.MAX_BODY + 1)
        self.events_override = [
            {"event": "STARTED", "provider": "ollama", "model": "qwen3:1.7b"},
            {"event": "DELTA", "text": huge},
            {"event": "COMPLETE", "provider": "ollama",
             "model": "qwen3:1.7b", "text": huge},
        ]
        with self.assertRaisesRegex(b3.BridgeRefusal, "ANSWER_TOO_LARGE"):
            list(self.exchange(sid))
        self.assertEqual(self.attempt(sid)[0], "ABORTED")
        self.assertEqual(len(self.store.turns("owner_a", sid)), 1)

    def test_transport_failure_cannot_be_claimed_complete(self):
        sid = self.new_session()
        self.events_override = [
            {"event": "STARTED", "provider": "ollama", "model": "qwen3:1.7b"},
            {"event": "DELTA", "text": "provisional"},
        ]
        self.fail_during_stream = b3.ChatRefusal("OLLAMA_STREAM_TRUNCATED")
        with self.assertRaisesRegex(b3.BridgeRefusal,
                                    "OLLAMA_STREAM_TRUNCATED"):
            list(self.exchange(sid))
        self.assertEqual(self.attempt(sid)[0], "ABORTED")
        self.assertEqual(len(self.store.turns("owner_a", sid)), 1)

    def test_preflight_refuses_invalid_endpoint_and_resources_without_reservation(self):
        sid = self.new_session()
        for attrs in (
            {"endpoint": "https://example.com:11434"},
            {"endpoint": "http://127.0.0.1:11434/api/chat"},
            {"max_predict": 999},
            {"max_predict": True},
            {"num_ctx": 0},
            {"num_ctx": "4096"},
            {"model": "invalid model"},
        ):
            with self.subTest(attrs=attrs):
                with self.assertRaises(b3.BridgeRefusal):
                    list(self.exchange(sid, **attrs))
        self.assertIsNone(self.attempt(sid))
        self.assertEqual(self.requests, [])

    def test_user_message_must_already_be_durable(self):
        s = self.store.create_session(
            "owner_a", "CHERRY", "No user message", now_ms=100)
        with self.assertRaisesRegex(b3.BridgeRefusal, "USER_TURN_REQUIRED"):
            list(self.exchange(s["session_id"], revision=0))
        self.assertIsNone(self.attempt(s["session_id"]))

    def test_legacy_db_with_no_attempt_schema_rejected(self):
        temp = sqlite3.connect(":memory:")
        try:
            journal.bootstrap_synthetic(temp)
            store = journal.ForestSessionJournal(temp)
            with self.assertRaisesRegex(b3.BridgeRefusal, "ATTEMPT_SCHEMA_MISSING"):
                b3.ForestTurnBridge(store, clock_ms=lambda: 100)
            b3.bootstrap_attempts_synthetic(temp)
            with self.assertRaisesRegex(b3.BridgeRefusal, "ATTEMPT_SCHEMA_EXISTS"):
                b3.bootstrap_attempts_synthetic(temp)
        finally:
            temp.close()

    def test_attempt_status_is_durable_across_restarts(self):
        sid = self.new_session()
        gen = self.exchange(sid)
        next(gen)  # RESERVATION WRITTEN
        gen.close()
        self.db.close()
        self.db = sqlite3.connect(self.path)
        self.store = journal.ForestSessionJournal(self.db)
        restarted = b3.ForestTurnBridge(
            self.store, clock_ms=lambda: 203, streamer=standard_stream)
        with self.assertRaisesRegex(b3.BridgeRefusal, "ATTEMPT_ALREADY_EXISTS"):
            list(restarted.exchange(owner="owner_a", session_id=sid,
                                    expected_revision=1, model="qwen3:1.7b"))
        self.assertEqual(self.attempt(sid)[0], "ABORTED")

    def test_no_user_data_paths_model_runtime_or_hospital_authority(self):
        source = (Path(__file__).resolve().parents[2] /
                  "scripts/forest/turn_bridge_b3.py").read_text()
        for forbidden in ("subprocess", "FileView", "quickshell",
                          "HospitalRoomConversationAdapter", "/api/pull",
                          "os.makedirs", "sqlite3.connect("):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
