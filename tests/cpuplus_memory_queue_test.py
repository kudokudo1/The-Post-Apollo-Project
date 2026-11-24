"""Source-only tests. No live swap, shell or host settings are touched."""
import copy
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "services/memory"))
from memory_adjustment_queue import Queue, QueueError

SOURCE = {"boot_id": "c23683a9-b2ab-4a2c-87ce-31bdf27a3012",
          "base": {"device": 42, "inode": 123, "size_kib": 16777212},
          "extension": {"device": 42, "inode": 456, "size_kib": 8388604}}


class TestQueue(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "queue.db"
        self.queue = Queue(self.path)

    def enqueue(self, **overrides):
        return self.queue.enqueue(**dict({"target_gib": 16, "source": SOURCE,
                                          "now": 100, "expires_at": 200}, **overrides))

    def test_durable_intent_not_authority(self):
        record = self.enqueue()
        self.assertEqual(record["actual_kib"], 25165816)
        self.assertEqual(record["authorization_mode"], "fresh-explicit")
        self.assertEqual(Queue(self.path).pending(), record)
        self.assertEqual(record["state"], "QUEUED")
        self.assertEqual(self.path.stat().st_mode & 0o777, 0o600)

    def test_duplicate_and_stale_request(self):
        old = self.enqueue()
        other = Queue(self.path)
        with self.assertRaisesRegex(QueueError, "PENDING_EXISTS"):
            other.enqueue(target_gib=20, source=SOURCE, now=101, expires_at=201)
        new = self.queue.replace(old["id"], target_gib=20, source=SOURCE, now=101, expires_at=201)
        with self.assertRaisesRegex(QueueError, "STALE_REQUEST"):
            other.cancel(old["id"], now=102)
        self.assertEqual(other.pending(), new)
        terminal = other.lookup(old["id"])
        self.assertEqual(terminal["state"], "REPLACED")
        self.assertEqual(terminal["replaced_by"], new["id"])

    def test_cancel_persists(self):
        record = self.enqueue()
        self.queue.cancel(record["id"], now=101)
        other = Queue(self.path)
        self.assertIsNone(other.pending())
        self.assertEqual(other.lookup(record["id"])["state"], "CANCELLED")

    def test_expiry_explicit_and_exact(self):
        record = self.enqueue()
        other = Queue(self.path)
        with self.assertRaisesRegex(QueueError, "NOT_EXPIRED"):
            other.expire(record["id"], now=199)
        self.assertEqual(other.pending(), record)
        other.expire(record["id"], now=200)
        self.assertEqual(Queue(self.path).lookup(record["id"])["state"], "EXPIRED")
        self.assertIsNone(other.pending())

    def test_invalid_targets(self):
        for target in (-4, 65, 17, True, "16", 16.0):
            with self.subTest(target=target), self.assertRaises(QueueError):
                self.enqueue(target_gib=target)
        self.assertIsNone(self.queue.pending())

    def test_invalid_identity_and_secret_field(self):
        for source in ({"boot_id": "bad", "base": None, "extension": None},
                       dict(SOURCE, password="not allowed"),
                       dict(SOURCE, extension=SOURCE["base"])):
            with self.subTest(source=source), self.assertRaises(QueueError):
                self.enqueue(source=source)
        self.assertIsNone(self.queue.pending())

    def test_invalid_times(self):
        for now, expires in ((100, 100), (100, 99), (-1, 100), (True, 200)):
            with self.subTest(now=now, expires=expires), self.assertRaises(QueueError):
                self.enqueue(now=now, expires_at=expires)

    def test_failed_replace_preserves_pending(self):
        record = self.enqueue()
        with self.assertRaises(QueueError):
            self.queue.replace(record["id"], target_gib=20, source=SOURCE, now=99, expires_at=200)
        self.assertEqual(Queue(self.path).pending(), record)

    def test_storage_failure_rolls_back_replacement(self):
        record = self.enqueue()
        with sqlite3.connect(self.path) as db:
            db.execute("CREATE TRIGGER refuse_insert BEFORE INSERT ON requests BEGIN SELECT RAISE(ABORT, 'test failure'); END")
        with self.assertRaisesRegex(QueueError, "QUEUE_STORAGE_ERROR"):
            self.queue.replace(record["id"], target_gib=20, source=SOURCE, now=101, expires_at=200)
        self.assertEqual(Queue(self.path).pending(), record)

    def test_corrupt_pending_fails_closed(self):
        self.enqueue()
        with sqlite3.connect(self.path) as db:
            db.execute("UPDATE requests SET payload='{}'")
        with self.assertRaises(QueueError):
            Queue(self.path)
        with self.assertRaises(QueueError):
            self.enqueue()
        with sqlite3.connect(self.path) as db:
            self.assertEqual(db.execute("SELECT payload FROM requests").fetchone(), ("{}",))

    def test_missing_schema_not_reinitialized(self):
        path = Path(self.temp.name) / "invalid.db"
        path.touch(mode=0o600)
        with self.assertRaisesRegex(QueueError, "UNSUPPORTED_QUEUE_SCHEMA"):
            Queue(path)

    def test_symlink_refused(self):
        link = self.path.with_suffix(".link")
        link.symlink_to(self.path)
        with self.assertRaisesRegex(QueueError, "UNSAFE_QUEUE_FILE"):
            Queue(link)

    def test_private_parent_required(self):
        parent = Path(self.temp.name) / "public"
        parent.mkdir(mode=0o755)
        with self.assertRaisesRegex(QueueError, "UNSAFE_QUEUE_PARENT"):
            Queue(parent / "queue.db")
        self.assertFalse((parent / "queue.db").exists())

    def test_terminal_corruption_detected_on_reopen(self):
        record = self.enqueue()
        self.queue.cancel(record["id"], now=101)
        with sqlite3.connect(self.path) as db:
            db.execute("UPDATE requests SET payload='{}'")
        with self.assertRaises(QueueError):
            Queue(self.path)
        with self.assertRaises(QueueError):
            self.queue.audit_history()

    def test_broken_replacement_detected(self):
        record = self.enqueue()
        new = self.queue.replace(record["id"], target_gib=20, source=SOURCE, now=101, expires_at=201)
        with sqlite3.connect(self.path) as db:
            db.execute("DELETE FROM requests WHERE id=?", (new["id"],))
        with self.assertRaisesRegex(QueueError, "BROKEN_REPLACEMENT_CHAIN"):
            Queue(self.path)

    def test_path_replacement_refused(self):
        old = self.path.with_suffix(".old")
        self.path.rename(old)
        Queue(self.path)
        with self.assertRaisesRegex(QueueError, "QUEUE_FILE_REPLACED"):
            self.queue.pending()

    def test_observation_is_not_live(self):
        source = copy.deepcopy(SOURCE)
        record = self.enqueue(source=source, target_gib=0)
        source["base"]["size_kib"] = 1
        self.assertEqual(self.queue.pending()["actual_kib"], record["actual_kib"])
        self.assertEqual(self.queue.pending()["target_gib"], 0)
        self.assertFalse(hasattr(self.queue, "execute"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
