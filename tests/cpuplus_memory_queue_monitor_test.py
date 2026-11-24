"""Monitor fixtures, no native memory changes."""
import copy
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "services/memory"))
from memory_adjustment_queue import Queue, QueueError
from memory_queue_monitor import Monitor

SOURCE = {"boot_id": "c23683a9-b2ab-4a2c-87ce-31bdf27a3012",
          "base": {"device": 42, "inode": 123, "size_kib": 16777212},
          "extension": {"device": 42, "inode": 456, "size_kib": 8388604}}
EVIDENCE = {"targetGiB": 16, "baseSizeKiB": 16777212,
            "extensionSizeKiB": 8388604, "extensionUsedKiB": 0,
            "availableKiB": 10000000, "requiredRamKiB": 8000000,
            "baseFreeKiB": 16000000, "requiredBaseFreeKiB": 2097152,
            "someAvg10": 0.1, "fullAvg10": 0.0}


class MonitorTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.queue = Queue(Path(temp.name) / "queue.db")
        self.wall, self.mono = 100, 10000
        self.calls = 0
        self.hook = None
        self.blocker = None
        self.sample_shift = 0
        self.monitor = self.make_monitor()

    def clock(self):
        return self.wall, self.mono

    def make_monitor(self):
        return Monitor(self.queue, self.observe, clock=self.clock,
                       interval_ms=1000, max_gap_ms=2000,
                       max_age_ms=3000, stable_ms=3000)

    def enqueue(self, expiry=200):
        return self.queue.enqueue(target_gib=16, source=SOURCE, now=self.wall, expires_at=expiry)

    def observe(self, record, observer_id):
        self.calls += 1
        if self.hook:
            self.hook(record)
        return {"version": 1, "request_id": record["id"], "observer_id": observer_id,
                "source": copy.deepcopy(SOURCE), "wall_time": self.wall,
                "monotonic_ms": self.mono + self.sample_shift, "operation_state": "IDLE",
                "preflight": {"version": 1,
                              "state": "WAITING" if self.blocker else "READY_ADVISORY",
                              "code": self.blocker or "FRESH_AUTH_AND_ROOT_CHECK_REQUIRED",
                              "evidence": copy.deepcopy(EVIDENCE)}}

    def tick(self, ms=0):
        self.mono += ms
        self.wall += ms // 1000
        result = self.monitor.tick()
        self.assertFalse(result["can_execute"])
        return result

    def ready(self):
        self.enqueue()
        self.tick()
        self.tick(1000)
        self.tick(1000)
        result = self.tick(1000)
        self.assertEqual(result["state"], "READY_ADVISORY")
        return result

    def test_idle_no_observer_or_schedule(self):
        self.assertIsNone(self.tick()["next_check_monotonic_ms"])
        self.assertEqual(self.tick()["state"], "IDLE")
        self.assertEqual(self.calls, 0)

    def test_cadence_and_transition(self):
        self.enqueue()
        self.assertTrue(self.tick()["transition"])
        result = self.tick(100)
        self.assertFalse(result["transition"])
        self.assertEqual(result["last_checked_at"], 100)
        self.assertEqual(self.calls, 1)
        self.tick(900)
        self.assertEqual(self.calls, 2)

    def test_stability_and_read_only(self):
        ready = self.ready()
        self.assertEqual(ready["ready_valid_before_monotonic_ms"], 14000)
        self.assertEqual(self.queue.pending()["state"], "QUEUED")
        self.assertFalse(self.tick()["transition"])

    def test_blocker_breaks_sequence(self):
        self.ready()
        self.blocker = "EXTENSION_OCCUPIED"
        result = self.tick(1000)
        self.assertEqual(result["code"], "EXTENSION_OCCUPIED")
        self.assertIsNone(result["ready_valid_before_monotonic_ms"])
        self.blocker = None
        self.assertEqual(self.tick(1000)["code"], "STABILITY_INTERVAL")

    def test_missed_sample_breaks_sequence(self):
        self.enqueue()
        self.tick()
        self.tick(1000)
        self.assertEqual(self.tick(3000)["code"], "STABILITY_INTERVAL")
        self.assertEqual(self.tick(1000)["code"], "STABILITY_INTERVAL")

    def test_restart_never_reuses_ready(self):
        self.ready()
        self.monitor = self.make_monitor()
        self.assertEqual(self.tick()["code"], "STABILITY_INTERVAL")

    def test_cancel_during_observation(self):
        old = self.enqueue()
        self.hook = lambda r: self.queue.cancel(old["id"], now=self.wall)
        result = self.tick()
        self.assertEqual(result["state"], "IDLE")
        self.assertIsNone(result["next_check_monotonic_ms"])

    def test_replace_during_observation(self):
        old = self.enqueue()
        self.hook = lambda r: self.queue.replace(old["id"], target_gib=20,
                              source=SOURCE, now=self.wall, expires_at=200)
        result = self.tick()
        self.assertEqual(result["code"], "REQUEST_CHANGED")
        self.assertNotEqual(result["request_id"], old["id"])
        self.assertEqual(result["target_gib"], 20)

    def test_expiry_no_probe_or_write(self):
        self.enqueue(expiry=101)
        self.tick()
        result = self.tick(1000)
        self.assertEqual(result["code"], "EXPIRY_RECONCILIATION_REQUIRED")
        self.assertIsNone(result["next_check_monotonic_ms"])
        self.assertEqual(self.calls, 1)
        self.assertEqual(self.queue.pending()["state"], "QUEUED")

    def test_clock_rollback_stops(self):
        self.ready()
        self.wall -= 1
        result = self.tick()
        self.assertEqual(result["state"], "UNKNOWN")
        self.assertIsNone(result["next_check_monotonic_ms"])

    def test_observer_failure_discards_ready(self):
        self.ready()
        def fail(r):
            raise OSError("fixture")
        self.hook = fail
        result = self.tick(1000)
        self.assertEqual(result["code"], "OBSERVATION_UNAVAILABLE")
        self.assertIsNone(result["ready_valid_before_monotonic_ms"])

    def test_reentrant_observer_refused(self):
        self.enqueue()
        def reenter(r):
            with self.assertRaisesRegex(QueueError, "MONITOR_BUSY"):
                self.monitor.tick()
        self.hook = reenter
        self.assertEqual(self.tick()["code"], "STABILITY_INTERVAL")
        self.assertEqual(self.calls, 1)

    def test_storage_failure_discards_status(self):
        self.ready()
        self.queue.path.unlink()
        result = self.tick()
        self.assertEqual(result["code"], "QUEUE_UNAVAILABLE")
        self.assertIsNone(result["request_id"])
        self.assertIsNone(result["next_check_monotonic_ms"])

    def test_stale_sample_never_ready(self):
        self.ready()
        self.sample_shift = -4000
        self.assertEqual(self.tick(1000)["state"], "UNKNOWN")

    def test_bad_policy_refused(self):
        with self.assertRaises(QueueError):
            Monitor(self.queue, self.observe, interval_ms=1000, max_age_ms=500,
                    max_gap_ms=1000, stable_ms=1000)


if __name__ == "__main__":
    unittest.main(verbosity=2)
