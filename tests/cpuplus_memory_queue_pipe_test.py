"""R3a session fixtures; no live desktop or privileged provider."""
import copy
import json
import os
from pathlib import Path
import select
import sys
import tempfile
import threading
import unittest
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "services/memory"))
from memory_adjustment_queue import Queue, QueueError
from memory_queue_runtime import Runtime
from memory_queue_owner import Owner
from memory_queue_pipe import Session, decode, encode, serve, MAX_FRAME

SOURCE = {"boot_id": "c23683a9-b2ab-4a2c-87ce-31bdf27a3012",
          "base": {"device": 42, "inode": 9007199254740993, "size_kib": 16777212},
          "extension": {"device": 42, "inode": 9007199254740995, "size_kib": 8388604}}


class PipeTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.queue = Queue(Path(tmp.name) / "queue.db")
        self.wall, self.mono = 100000, 10000
        self.captures = self.samples = 0
        self.owner = Owner(self.queue, self.factory)
        self.addCleanup(self.owner.close)
        self.sent = []
        self.session = Session(self.owner, self.sent.append)

    def clock(self):
        return self.wall, self.mono

    def capture(self):
        self.captures += 1
        return {"version": 1, "source": copy.deepcopy(SOURCE),
                "wall_ms": self.wall, "monotonic_ms": self.mono}

    def observe(self, record, observer):
        self.samples += 1
        return None

    def factory(self, queue):
        return Runtime(queue, self.capture, self.observe, interval_ms=1000,
                       max_age_ms=3000, max_gap_ms=2000, stable_ms=3000, clock=self.clock)

    def message(self, kind="QUEUE", request_id=None, seq=1, expiry=200):
        return {"version": 1, "kind": "ACTION",
                "message": {"version": 1, "owner_id": self.owner.owner_id,
                            "action_id": str(uuid.uuid4()), "action_sequence": seq,
                            "kind": kind, "expected_request_id": request_id,
                            "target_gib": 16 if kind in {"QUEUE", "REPLACE"} else None,
                            "expires_at": expiry if kind in {"QUEUE", "REPLACE"} else None}}

    def send(self, obj):
        self.session.receive(encode(obj)[:-1])

    def test_idle_no_schedule(self):
        self.session.start()
        self.assertEqual([p["kind"] for p in self.sent], ["HELLO", "INVALIDATE", "STATUS"])
        self.assertIsNone(self.session.wait_seconds())
        for _ in range(20):
            self.session.due()
        self.assertEqual((self.captures, self.samples), (0, 0))
        self.assertEqual(len(self.sent), 3)

    def test_ui_cannot_trigger_poll(self):
        self.session.start()
        with self.assertRaisesRegex(QueueError, "WIRE_COMMAND"):
            self.send({"version": 1, "kind": "STATUS"})
        self.assertEqual(self.samples, 0)

    def test_action_order_and_safe_history(self):
        self.session.start()
        msg = self.message()
        self.send(msg)
        self.assertEqual([p["kind"] for p in self.sent[-3:]], ["ACTION", "INVALIDATE", "STATUS"])
        self.assertEqual(self.sent[-3]["disposition"], "REPORTED")
        self.assertNotIn("source", self.sent[-3]["result"]["request"])
        self.assertIsNone(self.sent[-1]["projection"]["notification_candidate"])
        request_id = self.queue.pending()["id"]
        self.send({"version": 1, "kind": "HISTORY",
                   "owner_id": self.owner.owner_id, "request_id": request_id})
        detail = self.sent[-1]["detail"]
        self.assertEqual(detail["request"]["id"], request_id)
        self.assertNotIn("source", detail["request"])
        self.assertEqual(detail["adjustment_outcome"], "UNVERIFIED")
        self.assertEqual(self.samples, 1)
        self.assertNotIn(b"inode", encode(self.sent[-1]))
        with self.assertRaisesRegex(QueueError, "STALE_ACTION_SEQUENCE"):
            self.send(msg)

    def test_due_and_cancel_no_polling(self):
        self.session.start()
        self.send(self.message())
        self.assertEqual(self.session.wait_seconds(), 1)
        self.session.due()
        self.assertEqual(self.samples, 1)
        self.wall += 1000
        self.mono += 1000
        self.session.due()
        self.assertEqual(self.samples, 2)
        self.send(self.message("CANCEL", self.queue.pending()["id"], 2))
        self.assertEqual(self.sent[-1]["projection"]["status"]["state"], "IDLE")
        self.assertIsNone(self.session.wait_seconds())
        self.session.due()
        self.assertEqual(self.samples, 2)

    def test_expiry_stops_without_implicit_write(self):
        self.session.start()
        self.send(self.message(expiry=101))
        self.wall += 1000
        self.mono += 1000
        self.session.due()
        self.assertIsNone(self.session.wait_seconds())
        self.assertEqual(self.sent[-1]["projection"]["status"]["code"],
                         "EXPIRY_RECONCILIATION_REQUIRED")
        record = self.queue.pending()
        self.assertEqual(record["state"], "QUEUED")
        self.send(self.message("EXPIRE", record["id"], 2))
        self.assertIsNone(self.queue.pending())
        self.assertIsNone(self.session.wait_seconds())

    def test_codec_strict(self):
        for raw in (b'{"version":1,"version":1}', b'{"version":1,"x":NaN}',
                    b'{"version":1,"x":9007199254740993}', b'{"version":1,"x":1.5}',
                    b'{"version":true}', b'x' * MAX_FRAME, b'{"version":1}\r'):
            with self.subTest(raw=raw[:80]), self.assertRaises(QueueError):
                decode(raw)
        with self.assertRaises(QueueError):
            encode({"inode": 9007199254740993})

    def test_actual_pipes_idle_eof(self):
        r, w = os.pipe()
        out_r, out_w = os.pipe()
        errors = []
        def target():
            try:
                serve(self.owner, r, out_w, io_timeout_ms=1000)
            except Exception as exc:
                errors.append(exc)
            finally:
                os.close(r)
                os.close(out_w)
        worker = threading.Thread(target=target, daemon=True)
        worker.start()
        try:
            data = b""
            while data.count(b"\n") < 3:
                self.assertTrue(select.select([out_r], [], [], 3)[0])
                chunk = os.read(out_r, 4096)
                self.assertTrue(chunk)
                data += chunk
            self.assertEqual([json.loads(line)["kind"] for line in data.splitlines()],
                             ["HELLO", "INVALIDATE", "STATUS"])
            self.assertEqual((self.captures, self.samples), (0, 0))
        finally:
            os.close(w)
            worker.join(4)
            os.close(out_r)
        self.assertFalse(worker.is_alive())
        self.assertEqual(errors, [])
        with self.assertRaisesRegex(QueueError, "OWNER_LOST"):
            self.owner.status()

    def durable(self):
        self.owner.close()
        self.queue = Queue(self.queue.path)
        self.owner = Owner(self.queue, self.factory, durable_actions=True)
        self.addCleanup(self.owner.close)
        self.sent = []
        self.session = Session(self.owner, self.sent.append)
        self.session.start()

    def inventory(self, limit=16):
        self.send({"version": 1, "kind": "INVENTORY", "owner_id": self.owner.owner_id,
                   "limit": limit})
        return self.sent[-1]

    def lookup(self, action_id):
        self.send({"version": 1, "kind": "LOCAL_ACTION", "owner_id": self.owner.owner_id,
                   "action_id": action_id})
        return self.sent[-1]

    def test_durable_recovery_reads_no_poll_or_action_sequence(self):
        self.durable()
        first = self.inventory()
        self.assertEqual(first["inventory"]["recent"], [])
        self.assertFalse(first["inventory"]["startup_unlock"])
        self.assertIsNone(self.session.wait_seconds())
        self.assertIsNone(self.lookup(str(uuid.uuid4()))["record"])
        self.assertEqual(self.sent[-1]["next_action_sequence"], 1)
        self.assertEqual((self.captures, self.samples), (0, 0))
        message = self.message()
        self.send(message)
        rid = self.queue.pending()["id"]
        due = self.session.deadline
        counts = self.captures, self.samples
        previous = self.sent[-1]["sequence"]
        for _ in range(50):
            packet = self.inventory(1)
            self.assertGreater(packet["sequence"], previous)
            previous = packet["sequence"]
            self.assertEqual(packet["next_action_sequence"], 2)
            self.assertEqual(packet["inventory"]["pending_request_id"], rid)
        self.assertEqual((self.captures, self.samples), counts)
        self.assertEqual(self.session.deadline, due)
        self.assertEqual(self.lookup(message["message"]["action_id"])["record"]["result_request_id"], rid)
        self.assertNotIn(b"inode", encode(self.sent[-1]))

    def test_durable_lost_queue_reply_recovery_new_epoch(self):
        self.durable()
        message = self.message()
        self.send(message)
        rid = self.queue.pending()["id"]
        # Drop all replies, close and construct a different owner.
        self.durable()
        packet = self.inventory()
        self.assertNotEqual(packet["owner_id"], message["message"]["owner_id"])
        self.assertEqual(packet["inventory"]["recent"][0]["result_request_id"], rid)
        self.assertEqual(self.lookup(message["message"]["action_id"])["record"]["state"], "COMMITTED")
        with self.assertRaisesRegex(QueueError, "STALE_OR_INVALID_OWNER"):
            self.send(message)
        self.assertEqual(self.captures, 1)

    def test_recovery_reads_refuse_invalid_commands(self):
        self.durable()
        for bad in (
            {"version":1,"kind":"INVENTORY","owner_id":self.owner.owner_id,"limit":17},
            {"version":1,"kind":"INVENTORY","owner_id":str(uuid.uuid4()),"limit":1},
            {"version":1,"kind":"LOCAL_ACTION","owner_id":self.owner.owner_id,"action_id":"wrong"},
            {"version":1,"kind":"INVENTORY","owner_id":self.owner.owner_id,"limit":1,"unlock":True},
            {"version":1,"kind":"ACKNOWLEDGE","owner_id":self.owner.owner_id},
        ):
            with self.subTest(bad=bad), self.assertRaises(QueueError):
                self.send(bad)
        self.assertEqual((self.captures,self.samples),(0,0))

    def test_recovery_reads_legacy_owner_refused(self):
        self.session.start()
        with self.assertRaisesRegex(QueueError,"DURABLE_ACTION_MODE_REQUIRED"):
            self.inventory()
        with self.assertRaisesRegex(QueueError,"DURABLE_ACTION_MODE_REQUIRED"):
            self.lookup(str(uuid.uuid4()))


if __name__ == "__main__":
    unittest.main(verbosity=2)
