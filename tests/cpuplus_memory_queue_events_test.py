"""Durable event candidates: temporary DB only, no Hub or live swap."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "services/memory"))
from memory_adjustment_queue import Queue, QueueError
from memory_queue_events import Events

SOURCE = {"boot_id": "c23683a9-b2ab-4a2c-87ce-31bdf27a3012",
          "base": {"device": 42, "inode": 123, "size_kib": 16777212},
          "extension": {"device": 42, "inode": 456, "size_kib": 8388604}}


class EventTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.path = Path(temp.name) / "queue.db"
        self.queue = Queue(self.path)
        self.r = self.queue.enqueue(target_gib=16, source=SOURCE, now=100, expires_at=200)
        self.events = Events(self.queue)
        self.status = {"version": 1, "request_id": self.r["id"], "target_gib": 16,
                       "actual_kib": self.r["actual_kib"], "expires_at": 200,
                       "state": "WAITING", "code": "EXTENSION_OCCUPIED",
                       "last_checked_at": 110, "can_execute": False,
                       "ready_valid_before_monotonic_ms": None}

    def stage(self, events=None, **kw):
        args = dict(now=110, monotonic_ms=11000, max_age_seconds=3)
        args.update(kw)
        return (events or self.events).stage(self.status, **args)

    def ready(self):
        self.status.update(state="READY_ADVISORY",
                           code="FRESH_AUTH_AND_ROOT_CHECK_REQUIRED",
                           ready_valid_before_monotonic_ms=12000)

    def test_dedup_survives_reopen(self):
        first = self.stage()
        self.assertTrue(first["created"])
        second = self.stage(Events(Queue(self.path)))
        self.assertFalse(second["created"])
        self.assertEqual(first["event"], second["event"])
        self.assertEqual(first["event"]["delivery_state"], "CANDIDATE_ONLY")
        self.assertFalse(first["event"]["can_execute"])

    def test_separate_ready_and_deferred(self):
        self.stage()
        self.ready()
        self.assertTrue(self.stage()["created"])
        self.assertEqual(len(self.events.for_request(self.r["id"])), 2)
        self.assertEqual(self.queue.pending()["state"], "QUEUED")

    def test_ready_regression_no_repeat(self):
        self.ready()
        self.stage()
        self.status.update(state="WAITING", code="RAM_HEADROOM")
        self.assertTrue(self.stage()["created"])
        self.ready()
        self.assertFalse(self.stage()["created"])

    def test_deadline_and_age(self):
        self.ready()
        with self.assertRaisesRegex(QueueError, "STALE_STATUS"):
            self.stage(monotonic_ms=12000)
        with self.assertRaisesRegex(QueueError, "STALE_STATUS"):
            self.stage(now=114)
        self.assertEqual(self.events.for_request(self.r["id"]), [])

    def test_expired_pending_refused(self):
        self.status["last_checked_at"] = 200
        with self.assertRaisesRegex(QueueError, "EXPIRED_REQUEST"):
            self.stage(now=200)

    def test_replaced_request_refused(self):
        self.queue.replace(self.r["id"], target_gib=20, source=SOURCE, now=110, expires_at=200)
        with self.assertRaisesRegex(QueueError, "STALE_REQUEST"):
            self.stage()

    def test_terminal_not_fabricated(self):
        self.assertIsNone(self.events.stage_terminal(self.r["id"]))
        self.queue.expire(self.r["id"], now=200)
        self.assertTrue(self.events.stage_terminal(self.r["id"])["created"])
        self.assertFalse(Events(Queue(self.path)).stage_terminal(self.r["id"])["created"])

    def test_cancelled_history(self):
        first = self.stage()
        self.queue.cancel(self.r["id"], now=111)
        cancelled = self.events.stage_terminal(self.r["id"])
        self.assertEqual(cancelled["event"]["kind"], "CANCELLED")
        self.assertIn(first["event"], self.events.for_request(self.r["id"]))

    def test_mismatch_and_authority_refused(self):
        self.status["target_gib"] = 20
        with self.assertRaisesRegex(QueueError, "STATUS_REQUEST_MISMATCH"):
            self.stage()
        self.status.update(target_gib=16, can_execute=True)
        with self.assertRaisesRegex(QueueError, "INVALID_STATUS"):
            self.stage()

    def test_unimplemented_completed_refused(self):
        self.status.update(state="VERIFIED", code="COMPLETED")
        self.assertIsNone(self.stage())

    def test_corrupt_event_not_silently_returned(self):
        self.stage()
        with sqlite3.connect(self.path) as db:
            db.execute("UPDATE memory_queue_events_v1 SET code='FAKE'")
        with self.assertRaisesRegex(QueueError, "INVALID_EVENT"):
            self.events.for_request(self.r["id"])
        with self.assertRaisesRegex(QueueError, "INVALID_EVENT"):
            self.stage()

    def test_concurrent_dedup(self):
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: self.stage(Events(Queue(self.path))), range(2)))
        self.assertEqual(sum(r["created"] for r in results), 1)
        self.assertEqual(len(self.events.for_request(self.r["id"])), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
