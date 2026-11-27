"""Forest B3 // disposable-only durable reservation and completed-turn tests."""
from __future__ import annotations

import sqlite3
import sys
import tempfile
from dataclasses import replace
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts/forest"))
import session_journal_v0 as journal  # noqa: E402
import turn_bridge_b3 as b3  # noqa: E402
from shared_context_b6r1 import TaskContext
from context_first_tree_m2 import SessionContextRef
from runtime_stop_control_r2 import RuntimeStopControl


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

    def context_args(self, sid, *, revision=1):
        latest = self.db.execute(
            "SELECT turn_id FROM forest_turns WHERE session_id=? "
            "ORDER BY ordinal DESC LIMIT 1", (sid,)).fetchone()[0]
        ctx = TaskContext("owner_a", "CHERRY", None, "task", "execution",
                          1, "INTERACTIVE")
        ref = SessionContextRef(ctx, sid, revision, latest)
        control = RuntimeStopControl(ctx, "operation")
        return dict(context_ref=ref, current_context_ref=ref,
                    resolve_current_context=lambda: ref,
                    stop_control=control, operation_id="operation")

    def test_context_bound_exchange_never_reads_title(self):
        sid = self.new_session()
        args = self.context_args(sid)

        def authorizer(action, table, column, *_):
            if action == sqlite3.SQLITE_READ and table == "forest_sessions" and column == "title":
                return sqlite3.SQLITE_DENY
            return sqlite3.SQLITE_OK

        self.db.set_authorizer(authorizer)
        try:
            events = list(self.exchange(sid, **args))
        finally:
            self.db.set_authorizer(None)
        self.assertEqual(events[-1]["event"], "COMMITTED")
        self.assertEqual(self.attempt(sid)[0], "COMMITTED")
        self.assertIs(self.requests[0]["cancel_event"],
                      args["stop_control"].transport_event)

    def test_context_wrong_tree_latest_user_and_stale_generation(self):
        for kind in ("tree", "latest", "generation"):
            sid = self.new_session()
            args = self.context_args(sid)
            ref = args["context_ref"]
            if kind == "tree":
                ref = replace(ref, context=replace(ref.context, tree_key="other"))
            elif kind == "latest":
                ref = replace(ref, user_turn_id="wrong")
            else:
                args["resolve_current_context"] = lambda: replace(
                    ref, context=replace(ref.context, generation=2))
            args["context_ref"] = args["current_context_ref"] = ref
            args["stop_control"] = RuntimeStopControl(ref.context, "operation")
            if kind != "generation":
                args["resolve_current_context"] = lambda: ref
            with self.assertRaises(b3.BridgeRefusal):
                list(self.exchange(sid, **args))
            self.assertIsNone(self.attempt(sid))
        self.assertEqual(self.requests, [])

    def test_context_older_large_turn_omitted_without_mutating_history(self):
        sid = self.new_session()
        self.store.append_turn("owner_a", sid, expected_revision=1,
            role="assistant", body="x" * 5000, provider="ollama",
            model="qwen3:1.7b", now_ms=102)
        self.store.append_turn("owner_a", sid, expected_revision=2,
            role="user", body="new", now_ms=103)
        args = self.context_args(sid, revision=3)
        self.assertEqual(list(self.exchange(sid, revision=3, **args))[-1]["event"],
                         "COMMITTED")
        self.assertEqual(self.requests[0]["messages"],
                         [{"role": "user", "content": "new"}])
        self.assertEqual(self.store.turns("owner_a", sid)[1]["body"], "x" * 5000)

    def test_context_oversized_latest_refuses_before_reservation(self):
        sid = self.new_session()
        self.store.append_turn("owner_a", sid, expected_revision=1,
            role="user", body="x" * 5000, now_ms=102)
        with self.assertRaisesRegex(b3.BridgeRefusal, "LATEST_USER_TOO_LARGE"):
            list(self.exchange(sid, revision=2, **self.context_args(sid, revision=2)))
        self.assertIsNone(self.attempt(sid))
        self.assertEqual(self.requests, [])

    def test_context_stop_before_reserve_and_after_reserve(self):
        sid = self.new_session()
        args = self.context_args(sid)
        ref, control = args["context_ref"], args["stop_control"]
        control.request_stop(ref.context, "operation", None)
        with self.assertRaisesRegex(b3.BridgeRefusal, "OLLAMA_CANCELLED"):
            list(self.exchange(sid, **args))
        self.assertIsNone(self.attempt(sid))
        args = self.context_args(sid)
        ref, control = args["context_ref"], args["stop_control"]
        gen = self.exchange(sid, **args)
        attempt = next(gen)["attempt_id"]
        control.request_stop(ref.context, "operation", attempt)
        with self.assertRaisesRegex(b3.BridgeRefusal, "OLLAMA_CANCELLED"):
            list(gen)
        self.assertEqual(self.attempt(sid)[0], "ABORTED")
        self.assertEqual(self.requests, [])

    def test_context_stop_after_delta_aborts_without_retry(self):
        sid = self.new_session()
        args = self.context_args(sid)
        ref, control = args["context_ref"], args["stop_control"]
        gen = self.exchange(sid, **args)
        attempt = next(gen)["attempt_id"]
        self.assertEqual(next(gen)["event"], "STARTED")
        self.assertEqual(next(gen)["event"], "DELTA")
        control.request_stop(ref.context, "operation", attempt)
        with self.assertRaisesRegex(b3.BridgeRefusal, "OLLAMA_CANCELLED"):
            list(gen)
        self.assertEqual(self.attempt(sid)[0], "ABORTED")
        self.assertEqual(len(self.store.turns("owner_a", sid)), 1)
        with self.assertRaisesRegex(b3.BridgeRefusal, "ATTEMPT_ALREADY_EXISTS"):
            list(self.exchange(sid, **self.context_args(sid)))
        self.assertEqual(len(self.requests), 1)

    def test_context_change_after_reservation_blocks_dispatch(self):
        sid = self.new_session()
        args = self.context_args(sid)
        ref = args["context_ref"]
        current = [ref]
        args["resolve_current_context"] = lambda: current[0]
        gen = self.exchange(sid, **args)
        self.assertEqual(next(gen)["event"], "RESERVED")
        current[0] = replace(ref, context=replace(ref.context, generation=2))
        with self.assertRaisesRegex(b3.BridgeRefusal, "CONTEXT_CHANGED"):
            list(gen)
        self.assertEqual(self.attempt(sid)[0], "ABORTED")
        self.assertEqual(self.requests, [])

    def test_stop_after_commit_entry_does_not_replace_authorization(self):
        sid = self.new_session()
        args = self.context_args(sid)
        ref, control = args["context_ref"], args["stop_control"]
        attempts = []
        dispositions = []

        def refuse():
            dispositions.append(control.request_stop(
                ref.context, "operation", attempts[0]))
            return False

        gen = self.exchange(sid, pre_commit=refuse, **args)
        attempts.append(next(gen)["attempt_id"])
        with self.assertRaisesRegex(b3.BridgeRefusal, "PRE_COMMIT_AUTHORIZATION_DENIED"):
            list(gen)
        self.assertEqual(dispositions, ["COMMIT_ENTRY_ALREADY_WON"])
        self.assertEqual(self.attempt(sid)[0], "ABORTED")
        self.assertEqual(len(self.store.turns("owner_a", sid)), 1)

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

    def test_r7j_distinct_trigger_still_blocked_by_live_session_reservation(self):
        # Existing B3 behavior, not a group queue or a new admission grant.
        # A different durable trigger avoids the per-user-turn unique key,
        # but the original RESERVED attempt still occupies the session slot.
        sid = self.new_session()
        original_trigger = self.store.turns("owner_a", sid)[0]["turn_id"]
        first = self.exchange(sid)
        original = next(first)["attempt_id"]
        second_db = sqlite3.connect(self.path, timeout=2)
        try:
            other = journal.ForestSessionJournal(second_db)
            other_calls = []

            def second_stream(**kwargs):
                other_calls.append(kwargs)
                yield from standard_stream(**kwargs)

            bridge = b3.ForestTurnBridge(
                other, clock_ms=lambda: 203, streamer=second_stream)
            new = other.append_turn(
                "owner_a", sid, expected_revision=1, role="user",
                body="Independent later trigger", now_ms=201)
            self.assertNotEqual(new["turn_id"], original_trigger)
            with self.assertRaisesRegex(b3.BridgeRefusal, "ATTEMPT_ALREADY_EXISTS"):
                list(bridge.exchange(owner="owner_a", session_id=sid,
                                     expected_revision=2, model="other-model"))
            self.assertEqual(other_calls, [])
            self.assertEqual(second_db.execute(
                "SELECT attempt_id,user_turn_id,status FROM forest_attempts_b3 "
                "WHERE session_id=?", (sid,)).fetchall(),
                [(original, original_trigger, "RESERVED")])
            first.close()
            self.assertEqual(self.requests, [])
            self.assertEqual(list(bridge.exchange(
                owner="owner_a", session_id=sid, expected_revision=2,
                model="other-model"))[-1]["event"], "COMMITTED")
            self.assertEqual(len(other_calls), 1)
            self.assertEqual(second_db.execute(
                "SELECT user_turn_id,status FROM forest_attempts_b3 "
                "WHERE session_id=? ORDER BY created_at_ms", (sid,)).fetchall(),
                [(original_trigger, "ABORTED"), (new["turn_id"], "COMMITTED")])
            self.assertEqual(other.session("owner_a", sid)["revision"], 3)
        finally:
            first.close()
            second_db.close()

    def test_r7j_intervening_assistant_append_does_not_settle_original_attempt(self):
        # B1 can append an assistant row without B3's attempt identity.
        # It is a disposable legacy row, NOT an authenticated peer message.
        sid = self.new_session()
        first = self.exchange(sid)
        original = next(first)["attempt_id"]
        self.assertEqual(next(first)["event"], "STARTED")
        self.assertEqual(next(first)["event"], "DELTA")
        second_db = sqlite3.connect(self.path, timeout=2)
        try:
            other = journal.ForestSessionJournal(second_db)
            row = other.append_turn(
                "owner_a", sid, expected_revision=1, role="assistant",
                body="Independent legacy append", provider="ollama",
                model="other-model", now_ms=201)
            self.assertEqual(second_db.execute(
                "SELECT attempt_id,status,reply_turn_id FROM forest_attempts_b3 "
                "WHERE session_id=?", (sid,)).fetchall(),
                [(original, "RESERVED", None)])
            self.now = 202
            with self.assertRaisesRegex(b3.BridgeRefusal, "STALE_OR_CLOSED_SESSION"):
                list(first)
            self.assertEqual(second_db.execute(
                "SELECT attempt_id,status,reply_turn_id FROM forest_attempts_b3 "
                "WHERE session_id=?", (sid,)).fetchall(),
                [(original, "ABORTED", None)])
            self.assertEqual(other.session("owner_a", sid)["revision"], 2)
            turns = other.turns("owner_a", sid)
            self.assertEqual(len(turns), 2)
            self.assertEqual(turns[-1]["turn_id"], row["turn_id"])
            self.assertEqual(turns[-1]["body"], "Independent legacy append")
            with self.assertRaisesRegex(b3.BridgeRefusal, "USER_TURN_REQUIRED"):
                list(self.exchange(sid, revision=2))
            self.assertEqual(len(self.requests), 1)
        finally:
            first.close()
            second_db.close()

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
