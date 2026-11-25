"""R6d disposable retention tests, no installed host or protected operations."""
import copy
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from cpuplus_memory_queue_host_checkpoint_test import ACTION, acknowledgment, QueueError
from memory_queue_checkpoint_generations import CheckpointGenerations, SEAL
from memory_queue_host_checkpoint import SLOTS


def dismissal():
    return dict(acknowledgment(), kind="REVIEW_DISMISS")


def receipt():
    return {"version":2, "review":dismissal()["review"], "dismissed_at_ms":100001,
            "disposition":"LOCAL_PREPARATION_DISMISSED", "adjustment_outcome":"UNVERIFIED",
            "can_execute":False, "startup_unlock":False}


class Tests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.path = Path(tmp.name)
        self.store = CheckpointGenerations(self.path)

    def prepare(self):
        self.store.save(0, ACTION)
        self.store.save(0, acknowledgment())
        self.store.save(0, dismissal())

    def test_exact_receipt_retains_original_and_reopens_storage_only(self):
        self.prepare()
        before = {p.name:p.read_bytes() for p in self.path.iterdir()}
        self.assertEqual(self.store.advance(0, receipt()), 1)
        for name, data in before.items():
            self.assertEqual((self.path/name).read_bytes(), data)
        loaded = CheckpointGenerations(self.path).load()
        self.assertEqual(loaded["generation"], 1)
        self.assertIsNone(loaded["checkpoint"]["action"])
        self.assertFalse(loaded["startup_unlock"])
        self.assertFalse(loaded["can_execute"])
        with self.assertRaisesRegex(QueueError,"CHECKPOINT_ACTION_ALREADY_RETAINED"):
            self.store.save(1, ACTION)
        with self.assertRaisesRegex(QueueError,"CHECKPOINT_GENERATION_NOT_WRITABLE"):
            self.store.save(0, ACTION)
        next_action = copy.deepcopy(ACTION)
        next_action["message"]["action_id"] = "c23683a9-b2ab-4a2c-87ce-31bdf27a3099"
        self.store.save(1, next_action)
        self.assertEqual(self.store.load()["checkpoint"]["action"], next_action)

    def test_intent_without_receipt_or_wrong_receipt_cannot_advance(self):
        self.prepare()
        for wrong in (None, dict(receipt(), can_execute=True),
                      dict(receipt(), dismissed_at_ms=160000),
                      dict(receipt(), review=dict(receipt()["review"], review_id="wrong"))):
            with self.assertRaisesRegex(QueueError,"CHECKPOINT_EXACT_DISMISSAL_REQUIRED"):
                self.store.advance(0, wrong)
        self.assertEqual(self.store.load()["generation"],0)
        self.assertFalse((self.path/SEAL).exists())

    def test_interruption_after_seal_requires_explicit_resume(self):
        self.prepare()
        with mock.patch("memory_queue_checkpoint_generations.os.mkdir",side_effect=OSError("fixture")):
            with self.assertRaises(QueueError):
                self.store.advance(0, receipt())
        self.assertTrue(self.store.load()["sealed"])
        with self.assertRaises(QueueError):
            self.store.save(0, ACTION)
        self.assertEqual(self.store.advance(0, receipt()),1)

    def test_corrupt_seal_or_historical_slot_blocks(self):
        self.prepare()
        self.store.advance(0,receipt())
        slot=self.path/SLOTS["ACTION"]
        slot.write_bytes(b"{")
        with self.assertRaises(QueueError):
            self.store.load()

    def test_partial_seal_blocks_without_overwrite(self):
        self.prepare()
        seal=self.path/SEAL
        seal.write_bytes(b"{")
        seal.chmod(0o600)
        with self.assertRaises(QueueError):
            self.store.advance(0,receipt())
        self.assertEqual(seal.read_bytes(),b"{")

    def test_missing_predecessor_or_symlink_refused(self):
        self.prepare()
        (self.path/"generation-0002").mkdir(mode=0o700)
        with self.assertRaises(QueueError):
            self.store.load()
        (self.path/"generation-0002").rmdir()
        (self.path/"generation-0001").symlink_to(self.path)
        with self.assertRaises(QueueError):
            self.store.load()

    def test_bound_refuses_without_erasure(self):
        self.prepare()
        with mock.patch("memory_queue_checkpoint_generations.MAX_GENERATIONS",1):
            with self.assertRaisesRegex(QueueError,"CHECKPOINT_GENERATION_LIMIT"):
                self.store.advance(0,receipt())
        self.assertEqual(self.store.load()["generation"],0)


if __name__=="__main__":
    unittest.main(verbosity=2)
