"""R2a local ownership and transport reference fixtures (Linux)."""
import copy
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import uuid
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "services/memory"))
from memory_adjustment_queue import Queue, QueueError
from memory_queue_runtime import Runtime
from memory_queue_owner import Owner

SOURCE = {"boot_id": "c23683a9-b2ab-4a2c-87ce-31bdf27a3012",
          "base": {"device": 42, "inode": 123, "size_kib": 16777212},
          "extension": {"device": 42, "inode": 456, "size_kib": 8388604}}


class OwnerTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.path = Path(tmp.name) / "queue.db"
        self.queue = Queue(self.path)
        self.owner = Owner(self.queue, self.factory)
        self.addCleanup(self.owner.close)

    def factory(self, queue):
        return Runtime(queue, lambda: {"version": 1, "source": copy.deepcopy(SOURCE),
                                       "wall_ms": 100000, "monotonic_ms": 10000},
                       lambda record, observer: None, interval_ms=1000,
                       max_age_ms=3000, max_gap_ms=2000, stable_ms=3000,
                       clock=lambda: (100000, 10000))

    def message(self, kind="QUEUE", expected=None, seq=1, owner=None):
        return {"version": 1, "owner_id": (owner or self.owner).owner_id,
                "action_id": str(uuid.uuid4()), "action_sequence": seq,
                "kind": kind, "expected_request_id": expected,
                "target_gib": 16 if kind in {"QUEUE", "REPLACE"} else None,
                "expires_at": 200 if kind in {"QUEUE", "REPLACE"} else None}

    def test_second_owner_refused(self):
        with self.assertRaisesRegex(QueueError, "OWNER_BUSY"):
            Owner(Queue(self.path), self.factory)

    def test_separate_process_lock(self):
        code = """import fcntl, os, sys
fd = os.open(sys.argv[1], os.O_RDONLY)
try:
    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
except BlockingIOError:
    sys.exit(42)
sys.exit(0)
"""
        args = [sys.executable, "-c", code, str(self.path)]
        self.assertEqual(subprocess.run(args, check=False, timeout=5).returncode, 42)
        self.owner.close()
        self.assertEqual(subprocess.run(args, check=False, timeout=5).returncode, 0)

    def test_close_and_new_epoch(self):
        old = self.message()
        self.owner.close()
        with self.assertRaisesRegex(QueueError, "OWNER_LOST"):
            self.owner.publish()
        with Owner(Queue(self.path), self.factory) as other:
            self.assertNotEqual(other.owner_id, self.owner.owner_id)
            with self.assertRaisesRegex(QueueError, "STALE_OR_INVALID_OWNER"):
                other.action(old)

    def test_action_and_status_envelopes(self):
        status = self.owner.publish()
        self.assertEqual(status["projection"]["status"]["state"], "IDLE")
        msg = self.message()
        reply = self.owner.action(msg)
        self.assertEqual(reply["action_id"], msg["action_id"])
        self.assertEqual(reply["disposition"], "REPORTED")
        self.assertTrue(reply["invalidate"])
        self.assertFalse(reply["can_execute"])
        pending = self.owner.publish()
        self.assertGreater(pending["sequence"], reply["sequence"])
        self.assertEqual(pending["next_action_sequence"], 2)
        self.assertEqual(pending["projection"]["status"]["request_id"], self.queue.pending()["id"])
        self.assertFalse(pending["projection"]["status"]["can_execute"])

    def test_duplicate_action_not_replayed(self):
        msg = self.message()
        self.owner.action(msg)
        original = self.queue.pending()
        with self.assertRaisesRegex(QueueError, "STALE_ACTION_SEQUENCE"):
            self.owner.action(msg)
        self.assertEqual(self.queue.pending(), original)

    def test_stale_cancel_refused(self):
        self.owner.action(self.message())
        original = self.queue.pending()
        reply = self.owner.action(self.message("CANCEL", str(uuid.uuid4()), 2))
        self.assertEqual(reply["disposition"], "REFUSED")
        self.assertEqual(self.queue.pending(), original)
        self.assertEqual(reply["next_action_sequence"], 3)

    def test_cancel_exact_request(self):
        self.owner.action(self.message())
        record = self.queue.pending()
        result = self.owner.action(self.message("CANCEL", record["id"], 2))
        self.assertEqual(result["result"]["request"]["state"], "CANCELLED")
        self.assertEqual(self.owner.publish()["projection"]["status"]["state"], "IDLE")
        self.assertEqual(self.owner.detail(record["id"])["detail"]["adjustment_outcome"], "UNVERIFIED")

    def test_lost_reply_reconcile_without_replay(self):
        original = self.owner.runtime.enqueue
        def interrupted(**kw):
            original(**kw)
            raise OSError("lost reply")
        self.owner.runtime.enqueue = interrupted
        msg = self.message()
        reply = self.owner.action(msg)
        self.assertEqual(reply["disposition"], "UNKNOWN")
        self.assertIsNotNone(self.queue.pending())
        with self.assertRaisesRegex(QueueError, "STALE_ACTION_SEQUENCE"):
            self.owner.action(msg)
        self.assertEqual(self.owner.publish()["projection"]["status"]["request_id"], self.queue.pending()["id"])

    def test_invalid_fields_refused(self):
        msg = self.message()
        msg["command"] = "unsupported"
        with self.assertRaisesRegex(QueueError, "STALE_OR_INVALID_OWNER"):
            self.owner.action(msg)
        self.assertIsNone(self.queue.pending())

    def test_database_path_replacement_invalidates_owner(self):
        os.rename(self.path, self.path.with_suffix(".old"))
        Queue(self.path)
        with self.assertRaises(QueueError):
            self.owner.publish()

    def test_passive_read_no_monitor_or_new_revision(self):
        self.assertIsNone(self.owner.status())
        first = self.owner.publish()
        def fail(*args, **kwargs):
            self.fail("passive status must not tick")
        self.owner.runtime.tick = fail
        cached = self.owner.status()
        self.assertEqual(cached, first)
        cached["projection"]["status"]["state"] = "FORGED"
        self.assertEqual(self.owner.status(), first)

    def test_action_invalidates_publication(self):
        self.owner.publish()
        reply = self.owner.action(self.message())
        self.assertIsNone(self.owner.status())
        self.assertNotIn("source", reply["result"]["request"])
        self.assertNotIn("notification_candidate", reply["result"])
        self.assertEqual(reply["result"]["request"]["id"], self.queue.pending()["id"])
        self.assertGreater(self.owner.publish()["sequence"], reply["sequence"])

    def test_due_boundary_read_invalidates_without_tick(self):
        self.owner.action(self.message())
        status = self.owner.publish()
        due = status["projection"]["status"]["next_check_monotonic_ms"]
        self.assertIsNotNone(due)
        self.owner.runtime.clock = lambda: (101000, due)
        def fail(*args, **kwargs):
            self.fail("due passive read must not tick")
        self.owner.runtime.tick = fail
        self.assertIsNone(self.owner.status())

    def test_explicit_invalidation(self):
        self.owner.publish()
        self.owner.invalidate()
        self.assertIsNone(self.owner.status())
        self.assertEqual(self.owner.publish()["projection"]["status"]["state"], "IDLE")


if __name__ == "__main__":
    unittest.main(verbosity=2)
