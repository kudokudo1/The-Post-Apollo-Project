"""One-attempt delivery tests; no native Hub, memory or privilege writes."""
from pathlib import Path
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "services/memory"))
from memory_adjustment_queue import Queue, QueueError
from memory_queue_events import Events
from memory_queue_delivery import Delivery

SOURCE = {"boot_id": "c23683a9-b2ab-4a2c-87ce-31bdf27a3012",
          "base": {"device": 42, "inode": 123, "size_kib": 16777212},
          "extension": {"device": 42, "inode": 456, "size_kib": 8388604}}


class DeliveryTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.path = Path(temp.name) / "queue.db"
        self.queue = Queue(self.path)
        self.events = Events(self.queue)
        self.r = self.queue.enqueue(target_gib=16, source=SOURCE, now=100, expires_at=200)
        self.status = dict(version=1, request_id=self.r["id"], target_gib=16,
                           actual_kib=self.r["actual_kib"], expires_at=200,
                           state="READY_ADVISORY", code="FRESH_AUTH_AND_ROOT_CHECK_REQUIRED",
                           last_checked_at=110, can_execute=False,
                           ready_valid_before_monotonic_ms=12000)
        self.event = self.events.stage(self.status, now=110, monotonic_ms=11000,
                                       max_age_seconds=3)["event"]
        self.d = Delivery(self.events)
        self.wall, self.mono = 110100, 11100
        self.packets = []

    def offer(self, packet):
        self.packets.append(packet)
        return "HISTORY_OBSERVED"

    def attempt(self, d=None, **kw):
        args = dict(read_status=lambda: self.status, clock=lambda: (self.wall, self.mono),
                    max_age_ms=3000, offer=self.offer)
        args.update(kw)
        return (d or self.d).attempt(self.event["event_id"], **args)

    def test_reservation_survives_reopen(self):
        self.assertEqual(self.attempt(), "HISTORY_OBSERVED")
        self.assertEqual(self.attempt(Delivery(Events(Queue(self.path)))), "ALREADY_RESERVED")
        self.assertEqual(len(self.packets), 1)
        self.assertFalse(self.packets[0]["can_execute"])
        self.assertEqual(self.packets[0]["valid_before_wall_ms"], 111000)
        self.assertEqual(self.events.for_request(self.r["id"])[0]["delivery_state"], "CANDIDATE_ONLY")

    def test_expired_ready_deadline(self):
        self.mono = 12000
        with self.assertRaisesRegex(QueueError, "STALE_EVENT"):
            self.attempt()
        self.assertEqual(self.packets, [])

    def test_regression_refused(self):
        self.status.update(state="WAITING", code="RAM_HEADROOM")
        with self.assertRaisesRegex(QueueError, "STALE_EVENT"):
            self.attempt()

    def test_cancel_before_reservation(self):
        self.queue.cancel(self.r["id"], now=110)
        with self.assertRaisesRegex(QueueError, "STALE_EVENT"):
            self.attempt()

    def test_regression_after_reservation(self):
        reads = []
        def read():
            reads.append(1)
            return self.status if len(reads) == 1 else dict(self.status, state="WAITING")
        self.assertEqual(self.attempt(read_status=read), "RESERVED_NOT_OFFERED")
        self.assertEqual(self.packets, [])
        self.assertEqual(self.attempt(), "ALREADY_RESERVED")

    def test_unknown_offer_never_retried(self):
        def fail(packet):
            self.packets.append(packet)
            raise OSError("fixture")
        self.assertEqual(self.attempt(offer=fail), "OFFER_OUTCOME_UNKNOWN")
        self.assertEqual(self.attempt(), "ALREADY_RESERVED")
        self.assertEqual(len(self.packets), 1)

    def test_blocked_or_unready_offer_never_replayed(self):
        self.assertEqual(self.attempt(offer=lambda p: "BLOCKED"), "BLOCKED")
        self.assertEqual(self.attempt(), "ALREADY_RESERVED")

    def test_terminal_is_persisted(self):
        self.queue.cancel(self.r["id"], now=110)
        self.event = self.events.stage_terminal(self.r["id"])["event"]
        self.assertEqual(self.attempt(read_status=lambda: None), "HISTORY_OBSERVED")
        self.assertEqual(self.packets[0]["kind"], "CANCELLED")

    def test_expired_terminal_candidate_not_sent_late(self):
        self.queue.cancel(self.r["id"], now=110)
        self.event = self.events.stage_terminal(self.r["id"])["event"]
        self.wall = 114000
        with self.assertRaisesRegex(QueueError, "STALE_EVENT"):
            self.attempt(read_status=lambda: None)

    def test_concurrent_reservation(self):
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: self.attempt(Delivery(Events(Queue(self.path)))), range(2)))
        self.assertCountEqual(results, ["HISTORY_OBSERVED", "ALREADY_RESERVED"])
        self.assertEqual(len(self.packets), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
