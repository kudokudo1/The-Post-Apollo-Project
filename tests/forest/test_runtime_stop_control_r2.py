"""Disposable arbitration tests; no native model, database or sender."""
import sys
import threading
import unittest
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts/forest"))
from shared_context_b6r1 import TaskContext
from runtime_stop_control_r2 import RuntimeStopControl, StopArbitrationRefusal


class StopControlTests(unittest.TestCase):
    def setUp(self):
        self.ctx = TaskContext("principal", "tree", None, "task",
                               "execution", 1, "INTERACTIVE")
        self.op = "operation"
        self.attempt = "a_fixture"
        self.control = RuntimeStopControl(self.ctx, self.op)

    def bind(self):
        self.control.bind_reserved_attempt(self.ctx, self.op, self.attempt)

    def stop(self):
        return self.control.request_stop(self.ctx, self.op, self.attempt)

    def enter(self):
        return self.control.try_enter_commit(self.ctx, self.op, self.attempt)

    def test_stop_before_reserve_is_latched_after_binding(self):
        self.assertEqual(self.control.request_stop(self.ctx, self.op, None),
                         "STOP_LATCHED")
        self.bind()
        self.assertTrue(self.control.transport_event.is_set())
        self.assertFalse(self.enter())

    def test_stop_before_entry_is_idempotent(self):
        self.bind()
        self.assertEqual(self.stop(), "STOP_LATCHED")
        self.assertEqual(self.stop(), "STOP_LATCHED")
        self.assertFalse(self.enter())

    def test_entry_before_stop_cannot_claim_rollback(self):
        self.bind()
        self.assertTrue(self.enter())
        self.assertEqual(self.stop(), "COMMIT_ENTRY_ALREADY_WON")
        self.assertFalse(self.control.transport_event.is_set())
        self.assertFalse(self.enter())

    def test_wrong_task_operation_attempt_or_generation_refused(self):
        self.bind()
        for ctx, op, attempt in (
            (replace(self.ctx, tree_key="other"), self.op, self.attempt),
            (replace(self.ctx, task_id="other"), self.op, self.attempt),
            (replace(self.ctx, generation=2), self.op, self.attempt),
            (self.ctx, "other", self.attempt),
            (self.ctx, self.op, "a_other"),
            (self.ctx, self.op, None),
        ):
            with self.assertRaises(StopArbitrationRefusal):
                self.control.request_stop(ctx, op, attempt)
            with self.assertRaises(StopArbitrationRefusal):
                self.control.try_enter_commit(ctx, op, attempt)
        self.assertFalse(self.control.transport_event.is_set())
        self.assertTrue(self.enter())

    def test_no_entry_without_attempt_and_no_rebind(self):
        with self.assertRaises(StopArbitrationRefusal):
            self.control.try_enter_commit(self.ctx, self.op, None)
        self.bind()
        with self.assertRaises(StopArbitrationRefusal):
            self.bind()

    def test_closed_is_not_cancelled_or_committed(self):
        self.bind()
        self.control.close(self.ctx, self.op, self.attempt)
        self.assertEqual(self.stop(), "CONTROL_CLOSED")
        self.assertFalse(self.enter())
        self.assertFalse(self.control.transport_event.is_set())

    def test_other_control_unchanged(self):
        self.bind()
        other = RuntimeStopControl(replace(self.ctx, task_id="other"), "other")
        other.bind_reserved_attempt(replace(self.ctx, task_id="other"),
                                    "other", "a_other")
        self.stop()
        self.assertFalse(other.transport_event.is_set())
        self.assertTrue(other.try_enter_commit(
            replace(self.ctx, task_id="other"), "other", "a_other"))

    def test_racing_stop_and_commit_entry_have_one_winner(self):
        for _ in range(32):
            control = RuntimeStopControl(self.ctx, self.op)
            control.bind_reserved_attempt(self.ctx, self.op, self.attempt)
            barrier = threading.Barrier(3, timeout=3)
            results = {}

            def stop():
                barrier.wait()
                results["stop"] = control.request_stop(
                    self.ctx, self.op, self.attempt)

            def entry():
                barrier.wait()
                results["entry"] = control.try_enter_commit(
                    self.ctx, self.op, self.attempt)

            workers = [threading.Thread(target=f, daemon=True)
                       for f in (stop, entry)]
            for worker in workers:
                worker.start()
            barrier.wait()
            for worker in workers:
                worker.join(3)
                self.assertFalse(worker.is_alive())
            self.assertIn(results, (
                {"stop": "STOP_LATCHED", "entry": False},
                {"stop": "COMMIT_ENTRY_ALREADY_WON", "entry": True},
            ))
            self.assertEqual(control.transport_event.is_set(),
                             not results["entry"])


if __name__ == "__main__":
    unittest.main()
