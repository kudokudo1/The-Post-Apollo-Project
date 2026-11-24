"""History/evidence fixtures only; no root access, swap changes or Hub calls."""
import copy
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "services/memory"))
from memory_adjustment_queue import Queue, QueueError
from memory_queue_events import Events
from memory_queue_delivery import Delivery
from memory_queue_history import History

SOURCE = {"boot_id": "c23683a9-b2ab-4a2c-87ce-31bdf27a3012",
          "base": {"device": 42, "inode": 123, "size_kib": 16777212},
          "extension": {"device": 42, "inode": 456, "size_kib": 8388604}}
RECEIPT = {"version": 1, "state": "VERIFIED", "targetGiB": 16,
           "sizeKiB": 16777212, "basePriority": 10,
           "extensionActive": False, "fileRetained": True, "timeNs": 110000000000}


class HistoryTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.path = Path(tmp.name) / "queue.db"
        self.queue = Queue(self.path)
        self.r = self.queue.enqueue(target_gib=16, source=SOURCE, now=100, expires_at=200)
        self.history = History(self.queue)

    def capture(self, receipt=RECEIPT, **kw):
        return self.history.record_candidate(self.r["id"], receipt, **dict({"observed_at": 112}, **kw))

    def test_intent_without_evidence(self):
        detail = self.history.detail(self.r["id"])
        self.assertEqual(detail["request"], self.r)
        self.assertIsNone(detail["withdrawal_evidence"])
        self.assertEqual(detail["notification_events"], [])
        self.assertEqual(detail["adjustment_outcome"], "UNVERIFIED")
        with sqlite3.connect(self.path) as db:
            self.assertIsNone(db.execute("SELECT 1 FROM sqlite_master WHERE name='memory_queue_events_v1'").fetchone())

    def test_matching_receipt_is_unbound_and_durable(self):
        evidence = self.capture()
        self.assertEqual(evidence["state"], "UNBOUND_EVIDENCE")
        self.assertFalse(evidence["kernel_verified_for_request"])
        self.assertFalse(evidence["can_execute"])
        detail = History(Queue(self.path)).detail(self.r["id"])
        self.assertEqual(detail["withdrawal_evidence"], evidence)
        self.assertEqual(detail["request"]["state"], "QUEUED")
        self.assertEqual(detail["adjustment_outcome"], "UNVERIFIED")

    def test_duplicate_idempotent(self):
        first = self.capture()
        self.assertEqual(first, self.capture(observed_at=113))

    def test_conflicting_receipt_refused(self):
        first = self.capture()
        with self.assertRaisesRegex(QueueError, "CONFLICTING_RECEIPT"):
            self.capture(dict(RECEIPT, timeNs=111000000000))
        self.assertEqual(self.history.detail(self.r["id"])["withdrawal_evidence"], first)

    def test_duplicate_association_refused(self):
        self.capture()
        self.queue.cancel(self.r["id"], now=111)
        other = self.queue.enqueue(target_gib=16, source=SOURCE, now=109, expires_at=200)
        with self.assertRaisesRegex(QueueError, "RECEIPT_ALREADY_ASSOCIATED"):
            self.history.record_candidate(other["id"], RECEIPT, observed_at=112)

    def test_malformed_receipt_refused(self):
        for delta in ({"version": True}, {"extensionActive": 0},
                      {"sizeKiB": 1}, {"targetGiB": 20}, {"timeNs": 99000000000},
                      {"timeNs": 113000000000}, {"fileRetained": False},
                      {"request_id": self.r["id"]}):
            with self.subTest(delta=delta), self.assertRaises(QueueError):
                self.capture(dict(RECEIPT, **delta))
        self.assertIsNone(self.history.detail(self.r["id"])["withdrawal_evidence"])

    def test_digest_tamper_refused(self):
        self.capture()
        with sqlite3.connect(self.path) as db:
            db.execute("UPDATE memory_queue_receipt_candidates_v1 SET digest='fake'")
        with self.assertRaisesRegex(QueueError, "RECEIPT_DIGEST_MISMATCH"):
            self.history.detail(self.r["id"])

    def test_notification_attempt_not_adjustment_attempt(self):
        events = Events(self.queue)
        self.queue.cancel(self.r["id"], now=110)
        event = events.stage_terminal(self.r["id"])["event"]
        Delivery(events).attempt(event["event_id"], read_status=lambda: None,
                                 clock=lambda: (110100, 10000), max_age_ms=3000,
                                 offer=lambda p: "HISTORY_OBSERVED")
        detail = self.history.detail(self.r["id"])
        self.assertEqual(detail["notification_events"][0]["delivery_outcome"], "UNKNOWN")
        self.assertEqual(detail["notification_events"][0]["attempt_reserved_at_ms"], 110100)
        self.assertEqual(detail["adjustment_outcome"], "UNVERIFIED")
        self.assertEqual(detail["request"]["state"], "CANCELLED")

    def test_terminal_history_retained(self):
        self.capture()
        self.queue.cancel(self.r["id"], now=113)
        self.assertEqual(self.history.detail(self.r["id"])["request"]["state"], "CANCELLED")
        self.assertEqual(self.history.detail(self.r["id"])["withdrawal_evidence"]["state"], "UNBOUND_EVIDENCE")


if __name__ == "__main__":
    unittest.main(verbosity=2)
