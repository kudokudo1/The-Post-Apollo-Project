"""R1 runtime fixtures. No native writes, commands, scheduler or Hub."""
import copy
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "services/memory"))
from memory_adjustment_queue import Queue, QueueError
from memory_queue_runtime import Runtime
from memory_queue_delivery import Delivery

SOURCE = {"boot_id": "c23683a9-b2ab-4a2c-87ce-31bdf27a3012",
          "base": {"device": 42, "inode": 123, "size_kib": 16777212},
          "extension": {"device": 42, "inode": 456, "size_kib": 8388604}}
EVIDENCE = {"targetGiB": 16, "baseSizeKiB": 16777212,
            "extensionSizeKiB": 8388604, "extensionUsedKiB": 0,
            "availableKiB": 10000000, "requiredRamKiB": 8000000,
            "baseFreeKiB": 16000000, "requiredBaseFreeKiB": 2097152,
            "someAvg10": 0.1, "fullAvg10": 0.0}


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.path = Path(tmp.name) / "queue.db"
        self.queue = Queue(self.path)
        self.wall, self.mono = 100000, 10000
        self.captures = self.samples = 0
        self.source = copy.deepcopy(SOURCE)
        self.blocker = None
        self.source_shift = 0
        self.runtime = self.make_runtime()

    def clock(self):
        return self.wall, self.mono

    def capture(self):
        self.captures += 1
        return {"version": 1, "source": self.source, "wall_ms": self.wall,
                "monotonic_ms": self.mono + self.source_shift}

    def observe(self, record, observer_id):
        self.samples += 1
        return {"version": 1, "request_id": record["id"], "observer_id": observer_id,
                "source": self.source, "wall_time": self.wall // 1000,
                "monotonic_ms": self.mono, "operation_state": "IDLE",
                "preflight": {"version": 1, "state": "WAITING" if self.blocker else "READY_ADVISORY",
                              "code": self.blocker or "FRESH_AUTH_AND_ROOT_CHECK_REQUIRED",
                              "evidence": copy.deepcopy(EVIDENCE)}}

    def make_runtime(self):
        return Runtime(self.queue, self.capture, self.observe, interval_ms=1000,
                       max_age_ms=3000, max_gap_ms=2000, stable_ms=3000, clock=self.clock)

    def enqueue(self, expires_at=200):
        return self.runtime.enqueue(target_gib=16, expires_at=expires_at)["request"]

    def tick(self, ms=0, **kw):
        self.wall += ms
        self.mono += ms
        result = self.runtime.tick(**kw)
        self.assertFalse(result["can_execute"])
        self.assertEqual(result["adjustment_outcome"], "UNVERIFIED")
        return result

    def test_idle_never_captures_or_samples(self):
        r = self.tick()
        self.assertEqual(r["status"]["state"], "IDLE")
        self.assertIsNone(r["status"]["next_check_monotonic_ms"])
        self.assertEqual((self.captures, self.samples), (0, 0))

    def test_explicit_queue_captures_once(self):
        record = self.enqueue()
        self.assertEqual(self.captures, 1)
        self.assertEqual(self.samples, 0)
        self.assertEqual(self.queue.pending(), record)
        self.assertEqual(self.tick()["status"]["original_actual_kib"], record["actual_kib"])

    def test_missing_source_never_fabricated(self):
        self.source["extension"] = None
        with self.assertRaisesRegex(QueueError, "SOURCE_IDENTITY_UNAVAILABLE"):
            self.enqueue()
        self.assertIsNone(self.queue.pending())

    def test_stale_capture_refused(self):
        self.source_shift = -1
        with self.assertRaisesRegex(QueueError, "STALE_SOURCE"):
            self.enqueue()
        self.assertIsNone(self.queue.pending())

    def test_unsupported_target_refused(self):
        with self.assertRaisesRegex(QueueError, "UNSUPPORTED_TARGET"):
            self.runtime.enqueue(target_gib=20, expires_at=200)
        self.assertIsNone(self.queue.pending())

    def test_no_implicit_replace(self):
        self.enqueue()
        with self.assertRaisesRegex(QueueError, "PENDING_EXISTS"):
            self.enqueue()
        self.assertEqual(self.captures, 1)

    def test_explicit_replace_new_id(self):
        old = self.enqueue()
        new = self.runtime.replace(old["id"], target_gib=16, expires_at=201)["request"]
        self.assertNotEqual(new["id"], old["id"])
        self.assertEqual(self.runtime.detail(old["id"])["request"]["state"], "REPLACED")

    def test_transition_staged_once(self):
        record = self.enqueue()
        self.blocker = "EXTENSION_OCCUPIED"
        result = self.tick()
        self.assertTrue(result["notification_candidate"]["created"])
        self.assertIsNone(self.tick(1000)["notification_candidate"])
        self.runtime = self.make_runtime()
        self.assertFalse(self.tick()["notification_candidate"]["created"])
        self.assertEqual(len(self.runtime.detail(record["id"])["notification_events"]), 1)

    def test_stability_not_alert_and_ready_is_advisory(self):
        self.enqueue()
        self.assertIsNone(self.tick()["notification_candidate"])
        self.tick(1000)
        self.tick(1000)
        ready = self.tick(1000)
        self.assertEqual(ready["status"]["state"], "READY_ADVISORY")
        self.assertEqual(ready["notification_candidate"]["event"]["kind"], "READY_ADVISORY")
        self.assertFalse(ready["status"]["can_execute"])

    def test_manual_recheck_does_not_accelerate_stability(self):
        self.enqueue()
        self.tick()
        self.tick(1000)
        self.tick(1000)
        manual = self.tick(100, recheck=True)
        self.assertEqual(manual["status"]["code"], "STABILITY_INTERVAL")
        self.assertEqual(self.samples, 4)
        self.assertEqual(self.tick(1000)["status"]["code"], "STABILITY_INTERVAL")

    def test_expiry_explicit_and_terminal_event(self):
        record = self.enqueue(expires_at=101)
        self.tick()
        status = self.tick(1000)["status"]
        self.assertEqual(status["code"], "EXPIRY_RECONCILIATION_REQUIRED")
        self.assertIsNone(status["next_check_monotonic_ms"])
        self.assertEqual(self.queue.pending()["state"], "QUEUED")
        result = self.runtime.expire(record["id"])
        self.assertEqual(result["request"]["state"], "EXPIRED")
        self.assertEqual(result["notification_candidate"]["event"]["kind"], "EXPIRED")

    def test_cancel_keeps_intent_and_stops_schedule(self):
        record = self.enqueue()
        self.tick()
        result = self.runtime.cancel(record["id"])
        self.assertEqual(result["request"]["state"], "CANCELLED")
        self.assertEqual(self.tick()["status"]["state"], "IDLE")

    def test_terminal_stage_failure_not_intent_failure(self):
        record = self.enqueue()
        def fail(_):
            raise QueueError("FIXTURE")
        self.runtime.events.stage_terminal = fail
        result = self.runtime.cancel(record["id"])
        self.assertEqual(result["request"]["state"], "CANCELLED")
        self.assertEqual(result["notification_error"], "EVENT_STAGE_UNAVAILABLE")
        self.assertIsNone(self.queue.pending())

    def test_reopen_discards_readiness(self):
        self.enqueue()
        self.tick()
        self.tick(1000)
        self.tick(1000)
        self.assertEqual(self.tick(1000)["status"]["state"], "READY_ADVISORY")
        self.queue = Queue(self.path)
        self.runtime = self.make_runtime()
        self.assertEqual(self.tick()["status"]["code"], "STABILITY_INTERVAL")

    def ready_event(self):
        record = self.enqueue()
        self.tick()
        self.tick(1000)
        self.tick(1000)
        result = self.tick(1000)
        self.assertEqual(result["status"]["state"], "READY_ADVISORY")
        self.assertNotIn("actual_kib", result["status"])
        return record, result["notification_candidate"]["event"]

    def offer_event(self, event, *, read=None, offer=None):
        return Delivery(self.runtime.events).attempt(
            event["event_id"], read_status=read or (lambda: self.runtime.tick()["status"]),
            clock=self.clock, max_age_ms=3000,
            offer=offer or (lambda packet: "HISTORY_OBSERVED"))

    def test_composed_ready_projection_to_delivery(self):
        record, event = self.ready_event()
        packets = []
        def offer(packet):
            packets.append(packet)
            return "HISTORY_OBSERVED"
        self.assertEqual(self.offer_event(event, offer=offer), "HISTORY_OBSERVED")
        self.assertEqual(len(packets), 1)
        self.assertEqual(packets[0]["original_actual_kib"], record["actual_kib"])
        self.assertFalse(packets[0]["can_execute"])
        self.assertEqual(self.runtime.detail(record["id"])["adjustment_outcome"], "UNVERIFIED")
        self.assertEqual(self.offer_event(event, offer=offer), "ALREADY_RESERVED")
        self.assertEqual(len(packets), 1)

    def test_composed_deferred_projection_to_delivery(self):
        self.enqueue()
        self.blocker = "EXTENSION_OCCUPIED"
        result = self.tick()
        event = result["notification_candidate"]["event"]
        self.assertEqual(event["kind"], "DEFERRED")
        self.assertEqual(self.offer_event(event), "HISTORY_OBSERVED")

    def test_composed_mismatched_capacity_refused(self):
        record, event = self.ready_event()
        def read():
            status = self.runtime.tick()["status"]
            status["original_actual_kib"] = record["actual_kib"] + 1
            return status
        with self.assertRaisesRegex(QueueError, "STALE_EVENT"):
            self.offer_event(event, read=read)
        self.assertEqual(self.offer_event(event), "HISTORY_OBSERVED")

    def test_composed_dual_capacity_even_if_equal_refused(self):
        record, event = self.ready_event()
        def read():
            return dict(self.runtime.tick()["status"], actual_kib=record["actual_kib"])
        with self.assertRaisesRegex(QueueError, "STALE_EVENT"):
            self.offer_event(event, read=read)
        self.assertEqual(self.offer_event(event), "HISTORY_OBSERVED")

    def test_composed_readiness_regression_refused(self):
        record, event = self.ready_event()
        self.blocker = "RAM_HEADROOM"
        self.tick(1000)
        with self.assertRaisesRegex(QueueError, "STALE_EVENT"):
            self.offer_event(event)
        rows = self.runtime.detail(record["id"])["notification_events"]
        saved = next(row for row in rows if row["event_id"] == event["event_id"])
        self.assertIsNone(saved["attempt_reserved_at_ms"])

    def test_composed_restart_does_not_replay_ready(self):
        record, event = self.ready_event()
        self.assertEqual(self.offer_event(event), "HISTORY_OBSERVED")
        self.queue = Queue(self.path)
        self.runtime = self.make_runtime()
        self.assertEqual(self.tick()["status"]["code"], "STABILITY_INTERVAL")
        self.assertEqual(self.offer_event(event), "ALREADY_RESERVED")


if __name__ == "__main__":
    unittest.main(verbosity=2)
