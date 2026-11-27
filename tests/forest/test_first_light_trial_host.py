"""Actual FL3 owner host with disposable transports; no installed model."""
import sqlite3
import sys
import threading
import unittest
from dataclasses import replace
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts/forest"))
import first_light_trial_host as fl
from ollama_chat_transport import stream_chat
from runtime_events_r3 import RuntimeEventRefusal
import turn_bridge_b3 as b3
from test_ollama_chat_transport import FakeOllama, packet


class FirstLightHostTests(unittest.TestCase):
    def peer(self, lines):
        class Peer(FakeOllama):
            pass
        Peer.lines = lines
        Peer.observed = []
        server = ThreadingHTTPServer(("127.0.0.1", 0), Peer)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        def close():
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)
        self.addCleanup(close)
        endpoint = "http://127.0.0.1:%d" % server.server_address[1]

        def transport(**kw):
            # Only the test adapter substitutes the ephemeral peer endpoint.
            # Actual B2 encoding/streaming is exercised, not native custody.
            kw["endpoint"] = endpoint
            yield from stream_chat(**kw)
        return Peer, transport

    def test_fixed_public_exact_request_and_one_original_commit(self):
        peer, transport = self.peer([packet("RE"), packet("ADY", done=True)])
        host = fl.FirstLightTrialHost(test_transport=transport)
        self.addCleanup(lambda: None if host._closed else host.close())
        with self.assertRaisesRegex(fl.FirstLightRefusal, "PUBLIC_INPUT_MISMATCH"):
            host.submit("other text")
        self.assertEqual(peer.observed, [])
        op = host.submit(fl.PROMPT)
        self.assertEqual(host.phase, "PREPARED")
        self.assertEqual(peer.observed, [])
        with self.assertRaisesRegex(fl.FirstLightRefusal, "TRIAL_ALREADY_USED"):
            host.submit(fl.PROMPT)
        frames = list(host.run_internal())
        self.assertEqual([f.payload["event"] for f in frames],
                         ["REQUESTED", "RESERVED", "STARTED", "DELTA",
                          "DELTA", "COMMITTED"])
        self.assertTrue(all(f.operation == op for f in frames))
        self.assertEqual(frames[-1].payload["text"], "READY")
        self.assertEqual(peer.observed, [("POST", "/api/chat", {
            "model": fl.MODEL, "messages": [{"role": "user", "content": fl.PROMPT}],
            "stream": True, "options": {"num_predict": 32, "num_ctx": 2048}})])
        self.assertEqual(host.local_outcome(), "COMMITTED_LOCAL")
        self.assertEqual(host.phase, "LOCAL_COMMITTED")
        with self.assertRaisesRegex(fl.FirstLightRefusal, "TRIAL_ALREADY_USED"):
            list(host.run_internal())
        self.assertEqual(host.close(), "COMMITTED_LOCAL")
        self.assertEqual(len(peer.observed), 1)

    def test_original_stop_and_local_abort_are_not_provider_settlement(self):
        peer, transport = self.peer([packet("partial"), packet(" more", done=True)])
        host = fl.FirstLightTrialHost(test_transport=transport)
        op = host.submit(fl.PROMPT)
        gen = host.run_internal()
        try:
            for event in ("REQUESTED", "RESERVED", "STARTED", "DELTA"):
                frame = next(gen)
                self.assertEqual(frame.payload["event"], event)
            with self.assertRaisesRegex(RuntimeEventRefusal, "OPERATION_MISMATCH"):
                host.request_stop(replace(op, operation_id="other"), frame.attempt_id)
            self.assertEqual(host.request_stop(op, frame.attempt_id), "STOP_LATCHED")
            with self.assertRaisesRegex(fl.FirstLightRefusal, "ORIGINAL_ACTIVE"):
                host.close()
            self.assertEqual(list(gen)[-1].payload["event"], "UNKNOWN_HOLD")
            self.assertEqual(host.phase, "UNKNOWN_HOLD")
            self.assertEqual(host.local_outcome(), "ABORTED_LOCAL")
            with self.assertRaisesRegex(fl.FirstLightRefusal, "TRIAL_ALREADY_USED"):
                list(host.run_internal())
            self.assertEqual(len(peer.observed), 1)
        finally:
            gen.close()
            self.assertEqual(host.close(), "ABORTED_LOCAL")
        self.assertEqual(host.phase, "UNKNOWN_HOLD")

    def test_extra_turn_refused_before_body_read_or_transport(self):
        calls = []
        host = fl.FirstLightTrialHost(test_transport=lambda **kw: calls.append(kw))
        op = host.submit(fl.PROMPT)
        host._db.execute(
            "INSERT INTO forest_turns VALUES (?,?,?,?,?,?,?,?)",
            ("extra", op.context_ref.session_id, 2, "user", "", "", "extra", 3))
        host._db.commit()
        reads = []

        def authorizer(action, table, column, *_):
            if action == sqlite3.SQLITE_READ and table == "forest_turns" and column == "body":
                reads.append(column)
                return sqlite3.SQLITE_DENY
            return sqlite3.SQLITE_OK
        host._db.set_authorizer(authorizer)
        try:
            self.assertEqual(list(host.run_internal())[-1].payload["event"], "UNKNOWN_HOLD")
            self.assertEqual(reads, [])
            self.assertEqual(calls, [])
            self.assertEqual(host.local_outcome(), "UNKNOWN_HOLD")
        finally:
            host._db.set_authorizer(None)
            host.close()

    def test_changed_prompt_same_metadata_refused_before_transport(self):
        calls = []
        host = fl.FirstLightTrialHost(test_transport=lambda **kw: calls.append(kw))
        op = host.submit(fl.PROMPT)
        host._db.execute("UPDATE forest_turns SET body=? WHERE turn_id=?",
                         ("changed", op.context_ref.user_turn_id))
        host._db.commit()
        try:
            frames = list(host.run_internal())
            self.assertEqual([f.payload["event"] for f in frames],
                             ["REQUESTED", "UNKNOWN_HOLD"])
            self.assertEqual(calls, [])
            self.assertEqual(host.local_outcome(), "UNKNOWN_HOLD")
            self.assertEqual(host._db.execute(
                "SELECT count(*) FROM forest_attempts_b3").fetchone(), (0,))
        finally:
            host.close()

    def test_canonical_snapshot_runs_inside_original_reservation(self):
        peer, transport = self.peer([packet("READY", done=True)])
        host = fl.FirstLightTrialHost(test_transport=transport)
        self.addCleanup(lambda: None if host._closed else host.close())
        op = host.submit(fl.PROMPT)
        original = b3.first_light_snapshot_in_transaction
        checked = []

        def observe(journal, requested, *, current, approved_prompt):
            self.assertTrue(host._db.in_transaction)
            self.assertEqual(requested, op.context_ref)
            self.assertEqual(current, requested)
            self.assertEqual(approved_prompt, fl.PROMPT)
            self.assertEqual(host._db.execute(
                "SELECT count(*) FROM forest_attempts_b3").fetchone(), (0,))
            snapshot = original(journal, requested, current=current,
                                approved_prompt=approved_prompt)
            checked.append(snapshot.transport_messages())
            return snapshot

        with patch.object(b3, "first_light_snapshot_in_transaction", side_effect=observe), \
             patch.object(b3, "snapshot_in_transaction", side_effect=AssertionError("fallback")):
            frames = list(host.run_internal())
        self.assertEqual(checked, [[{"role": "user", "content": fl.PROMPT}]])
        self.assertEqual(frames[-1].payload["event"], "COMMITTED")
        self.assertEqual(len(peer.observed), 1)
        self.assertEqual(host.local_outcome(), "COMMITTED_LOCAL")

    def test_first_light_bridge_refuses_legacy_context_and_default_transport(self):
        host = fl.FirstLightTrialHost(test_transport=lambda **kw: iter(()))
        op = host.submit(fl.PROMPT)
        try:
            from session_journal_v0 import ForestSessionJournal
            journal = ForestSessionJournal(host._db)
            with self.assertRaisesRegex(b3.BridgeRefusal, "FIRST_LIGHT_TEST_TRANSPORT_REQUIRED"):
                b3.ForestTurnBridge(journal, clock_ms=host._tick,
                                    first_light_prompt=fl.PROMPT)
            bridge = b3.ForestTurnBridge(
                journal, clock_ms=host._tick, streamer=lambda **kw: iter(()),
                first_light_prompt=fl.PROMPT)
            ref = op.context_ref
            with self.assertRaisesRegex(b3.BridgeRefusal, "CONTEXT_REQUIRED"):
                list(bridge.exchange(owner=fl.OWNER, session_id=ref.session_id,
                                     expected_revision=1, model=fl.MODEL))
            self.assertEqual(host._db.execute(
                "SELECT count(*) FROM forest_attempts_b3").fetchone(), (0,))
        finally:
            host.close()

    def test_original_iterator_rejects_foreign_resume_and_close(self):
        peer, transport = self.peer([packet("READY", done=True)])
        host = fl.FirstLightTrialHost(test_transport=transport)
        host.submit(fl.PROMPT)
        gen = host.run_internal()
        rejected = []

        def foreign():
            for action in (lambda: next(gen), gen.close):
                try:
                    action()
                except fl.FirstLightRefusal as exc:
                    rejected.append(str(exc))

        def check_foreign():
            thread = threading.Thread(target=foreign)
            thread.start()
            thread.join(timeout=2)
            self.assertFalse(thread.is_alive())

        try:
            check_foreign()  # even before first next
            self.assertEqual(next(gen).payload["event"], "REQUESTED")
            self.assertEqual(next(gen).payload["event"], "RESERVED")
            check_foreign()  # paused at original durable reservation
            self.assertEqual(rejected, ["OWNER_ACTION_UNAVAILABLE"] * 4)
            self.assertEqual(peer.observed, [])
            self.assertEqual(host._db.execute(
                "SELECT status FROM forest_attempts_b3").fetchall(),
                [("RESERVED",)])
            self.assertEqual(list(gen)[-1].payload["event"], "COMMITTED")
            self.assertEqual(host.local_outcome(), "COMMITTED_LOCAL")
            self.assertEqual(len(peer.observed), 1)
        finally:
            gen.close()
            host.close()

    def test_close_unstarted_original_spends_iterator_without_dispatch(self):
        calls = []
        host = fl.FirstLightTrialHost(test_transport=lambda **kw: calls.append(kw))
        host.submit(fl.PROMPT)
        gen = host.run_internal()
        try:
            with self.assertRaisesRegex(fl.FirstLightRefusal, "TRIAL_ALREADY_USED"):
                host.run_internal()
            with self.assertRaisesRegex(fl.FirstLightRefusal, "ORIGINAL_ACTIVE"):
                host.close()
            gen.close()
            gen.close()
            self.assertEqual(host.phase, "UNKNOWN_HOLD")
            self.assertEqual(host.local_outcome(), "UNKNOWN_HOLD")
            self.assertEqual(list(gen), [])
            self.assertEqual(host._db.execute(
                "SELECT count(*) FROM forest_attempts_b3").fetchone(), (0,))
            with self.assertRaisesRegex(fl.FirstLightRefusal, "TRIAL_ALREADY_USED"):
                host.run_internal()
            self.assertEqual(calls, [])
        finally:
            gen.close()
            host.close()

    def test_worker_close_early_does_not_allow_retry(self):
        calls = []
        host = fl.FirstLightTrialHost(test_transport=lambda **kw: calls.append(kw))
        host.submit(fl.PROMPT)
        gen = host.run_internal()
        try:
            self.assertEqual(next(gen).payload["event"], "REQUESTED")
            self.assertEqual(next(gen).payload["event"], "RESERVED")
            gen.close()
            self.assertEqual(host.phase, "UNKNOWN_HOLD")
            self.assertEqual(host.local_outcome(), "ABORTED_LOCAL")
            with self.assertRaisesRegex(fl.FirstLightRefusal, "TRIAL_ALREADY_USED"):
                host.submit(fl.PROMPT)
            self.assertEqual(calls, [])
        finally:
            gen.close()
            host.close()


if __name__ == "__main__":
    unittest.main()
