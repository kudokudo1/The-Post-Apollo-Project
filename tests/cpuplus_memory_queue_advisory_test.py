"""Advisory lifecycle fixtures, no host probes or execution."""
import copy
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "services/memory"))
from memory_adjustment_queue import Queue
from memory_queue_advisory import evaluate

SOURCE = {"boot_id": "c23683a9-b2ab-4a2c-87ce-31bdf27a3012",
          "base": {"device": 42, "inode": 123, "size_kib": 16777212},
          "extension": {"device": 42, "inode": 456, "size_kib": 8388604}}
EVIDENCE = {"targetGiB": 16, "baseSizeKiB": 16777212,
            "extensionSizeKiB": 8388604, "extensionUsedKiB": 0,
            "availableKiB": 10000000, "requiredRamKiB": 8000000,
            "baseFreeKiB": 16000000, "requiredBaseFreeKiB": 2097152,
            "someAvg10": 0.1, "fullAvg10": 0.0}


class AdvisoryTest(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.queue = Queue(Path(temp.name) / "queue.db")
        self.record = self.queue.enqueue(target_gib=16, source=SOURCE, now=100, expires_at=200)
        self.sample = {"version": 1, "request_id": self.record["id"],
                       "observer_id": "c23683a9-b2ab-4a2c-87ce-31bdf27a3013",
                       "source": copy.deepcopy(SOURCE), "wall_time": 110,
                       "monotonic_ms": 11000, "operation_state": "IDLE",
                       "preflight": {"version": 1, "state": "READY_ADVISORY",
                                     "code": "FRESH_AUTH_AND_ROOT_CHECK_REQUIRED",
                                     "evidence": copy.deepcopy(EVIDENCE)}}
        self.previous = copy.deepcopy(self.sample)
        self.previous.update(wall_time=109, monotonic_ms=10000)

    def result(self, **changes):
        args = dict(now=110, monotonic_ms=11000, max_age_ms=3000, previous=self.previous)
        args.update(changes)
        result = evaluate(self.record, self.sample, **args)
        self.assertFalse(result["can_execute"])
        return result

    def test_two_samples_advisory_only(self):
        self.assertEqual(self.result()["state"], "READY_ADVISORY")
        self.assertEqual(self.queue.pending()["state"], "QUEUED")

    def test_restart_discards_continuity(self):
        self.assertEqual(self.result(previous=None)["code"], "CONTINUITY_REQUIRED")
        self.previous["observer_id"] = SOURCE["boot_id"]
        self.assertEqual(self.result()["code"], "CONTINUITY_REQUIRED")

    def test_expiry_and_clock_rollback(self):
        self.assertEqual(self.result(now=200)["code"], "EXPIRY_RECONCILIATION_REQUIRED")
        self.assertEqual(self.result(now=99)["code"], "CLOCK_ROLLBACK")
        self.assertEqual(self.queue.pending()["state"], "QUEUED")

    def test_stale_and_future_sample(self):
        self.assertEqual(self.result(monotonic_ms=15000)["code"], "STALE_OBSERVATION")
        self.assertEqual(self.result(monotonic_ms=10999)["code"], "STALE_OBSERVATION")

    def test_repeated_sample_not_continuity(self):
        self.assertEqual(self.result(previous=self.sample)["code"], "OBSERVATION_ORDER_INVALID")

    def test_boot_change(self):
        self.sample["source"]["boot_id"] = self.sample["observer_id"]
        self.assertEqual(self.result()["code"], "BOOT_CHANGED")

    def test_inode_change(self):
        self.sample["source"]["base"]["inode"] += 1
        self.assertEqual(self.result()["code"], "SOURCE_CHANGED")

    def test_busy_unknown(self):
        self.sample["operation_state"] = "BUSY"
        self.assertEqual(self.result()["code"], "OPERATION_BUSY")
        self.sample["operation_state"] = "UNKNOWN"
        self.assertEqual(self.result()["state"], "UNKNOWN")

    def test_waiting_regresses(self):
        self.sample["preflight"].update(state="WAITING", code="EXTENSION_OCCUPIED")
        self.assertEqual(self.result()["code"], "EXTENSION_OCCUPIED")

    def test_inconsistent_ready(self):
        self.sample["preflight"]["evidence"]["extensionUsedKiB"] = 1
        self.assertEqual(self.result()["state"], "UNKNOWN")

    def test_invalid_version(self):
        self.sample["version"] = True
        self.assertEqual(self.result()["state"], "UNKNOWN")

    def test_wrong_request(self):
        self.sample["request_id"] = SOURCE["boot_id"]
        self.assertEqual(self.result()["state"], "UNKNOWN")


if __name__ == "__main__":
    unittest.main(verbosity=2)
