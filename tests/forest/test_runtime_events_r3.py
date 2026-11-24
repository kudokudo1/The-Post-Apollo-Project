"""R3 uses real B3/M2/R2 and disposable SQLite, fake transport only."""
import sqlite3
import sys
import unittest
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts/forest"))
from session_journal_v0 import ForestSessionJournal, bootstrap_synthetic
from shared_context_b6r1 import TaskContext
from context_first_tree_m2 import SessionContextRef
from turn_bridge_b3 import ForestTurnBridge, bootstrap_attempts_synthetic
from runtime_events_r3 import OperationRef, RuntimeExchange, RuntimeEventRefusal


class RuntimeEventsTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        bootstrap_synthetic(self.db)
        bootstrap_attempts_synthetic(self.db)
        self.journal = ForestSessionJournal(self.db)
        session = self.journal.create_session("owner", "CHERRY", "fixture",
                                              now_ms=100)
        self.sid = session["session_id"]
        self.journal.append_turn("owner", self.sid, expected_revision=0,
                                 role="user", body="public", now_ms=101)
        user = self.db.execute("SELECT turn_id FROM forest_turns").fetchone()[0]
        self.ref = SessionContextRef(
            TaskContext("owner", "CHERRY", None, "task", "execution", 1,
                        "INTERACTIVE"), self.sid, 1, user)
        self.op = OperationRef(self.ref, "operation")
        self.calls = []

        def fake(**kwargs):
            self.calls.append(kwargs)
            model = kwargs["model"]
            yield {"event": "STARTED", "model": model, "provider": "ollama"}
            yield {"event": "DELTA", "text": "fixture reply"}
            yield {"event": "COMPLETE", "model": model, "provider": "ollama",
                   "text": "fixture reply"}

        self.bridge = ForestTurnBridge(
            self.journal, clock_ms=lambda: 200, streamer=fake)

    def tearDown(self):
        self.db.close()

    def exchange(self, resolver=None):
        return RuntimeExchange(self.bridge, self.op,
            resolve_current_context=resolver or (lambda: self.ref),
            model="fixture:small")

    def status(self):
        return self.db.execute("SELECT status FROM forest_attempts_b3").fetchone()

    def test_real_bridge_correlates_all_frames_and_receipt(self):
        x = self.exchange()
        frames = list(x.run())
        self.assertEqual([f.payload["event"] for f in frames],
                         ["REQUESTED", "RESERVED", "STARTED", "DELTA", "COMMITTED"])
        self.assertEqual([f.ordinal for f in frames], list(range(1, 6)))
        self.assertTrue(all(f.operation == self.op for f in frames))
        self.assertIsNone(frames[0].attempt_id)
        self.assertTrue(all(f.attempt_id == frames[1].attempt_id
                            for f in frames[1:]))
        self.assertTrue(frames[3].payload["provisional"])
        self.assertEqual(self.status(), ("COMMITTED",))
        with self.assertRaises(TypeError):
            frames[3].payload["text"] = "changed"
        with self.assertRaises(RuntimeEventRefusal):
            list(x.run())
        self.assertEqual(len(self.calls), 1)

    def test_stop_before_reserve_does_not_dispatch(self):
        x = self.exchange()
        g = x.run()
        self.assertEqual(next(g).payload["event"], "REQUESTED")
        self.assertEqual(x.request_stop(self.op, None), "STOP_LATCHED")
        end = list(g)
        self.assertEqual([f.payload["event"] for f in end], ["UNKNOWN_HOLD"])
        self.assertEqual(self.calls, [])
        self.assertIsNone(self.status())

    def test_stop_exact_reserved_attempt_blocks_dispatch(self):
        x = self.exchange()
        g = x.run()
        next(g)
        f = next(g)
        self.assertEqual(x.request_stop(self.op, f.attempt_id), "STOP_LATCHED")
        last = list(g)[-1]
        self.assertEqual(last.payload["event"], "UNKNOWN_HOLD")
        self.assertEqual(last.attempt_id, f.attempt_id)
        self.assertEqual(self.status(), ("ABORTED",))
        self.assertEqual(self.calls, [])

    def test_stop_after_delta_no_false_terminal_success(self):
        x = self.exchange()
        g = x.run()
        frames = [next(g) for _ in range(4)]
        self.assertEqual(frames[-1].payload["event"], "DELTA")
        x.request_stop(self.op, frames[-1].attempt_id)
        self.assertEqual(list(g)[-1].payload["event"], "UNKNOWN_HOLD")
        self.assertEqual(self.status(), ("ABORTED",))
        self.assertEqual(len(self.journal.turns("owner", self.sid)), 1)
        self.assertEqual(len(self.calls), 1)

    def test_wrong_operation_and_attempt_do_not_cancel(self):
        x = self.exchange()
        g = x.run()
        next(g)
        f = next(g)
        with self.assertRaises(ValueError):
            x.request_stop(replace(self.op, operation_id="other"), f.attempt_id)
        with self.assertRaises(ValueError):
            x.request_stop(self.op, "wrong")
        self.assertEqual(list(g)[-1].payload["event"], "COMMITTED")

    def test_stale_context_after_reservation_fails_closed(self):
        current = [self.ref]
        x = self.exchange(lambda: current[0])
        g = x.run()
        next(g)
        f = next(g)
        current[0] = replace(self.ref, context=replace(self.ref.context,
                                                      generation=2))
        last = list(g)[-1]
        self.assertEqual(last.payload["event"], "UNKNOWN_HOLD")
        self.assertEqual(last.attempt_id, f.attempt_id)
        self.assertEqual(self.status(), ("ABORTED",))
        self.assertEqual(self.calls, [])

    def test_close_during_stream_aborts_without_retry(self):
        x = self.exchange()
        g = x.run()
        frames = [next(g) for _ in range(4)]
        g.close()
        self.assertEqual(self.status(), ("ABORTED",))
        self.assertEqual(x.request_stop(self.op, frames[-1].attempt_id),
                         "CONTROL_CLOSED")
        with self.assertRaises(RuntimeEventRefusal):
            list(x.run())

    def test_resolver_exception_not_exposed_as_event_text(self):
        def bad():
            raise RuntimeError("private diagnostic")
        frames = list(self.exchange(bad).run())
        self.assertEqual(dict(frames[-1].payload), {"event": "UNKNOWN_HOLD"})
        self.assertEqual(self.calls, [])


if __name__ == "__main__":
    unittest.main()
