"""R6d disposable retention tests, no installed host or protected operations."""
import copy
import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from cpuplus_memory_queue_host_checkpoint_test import ACTION, acknowledgment, QueueError
from memory_queue_checkpoint_generations import CheckpointGenerations, SEAL, COMMITTED_SEAL
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

    def test_two_complete_generations_retained(self):
        self.prepare()
        self.store.advance(0, receipt())
        next_action = copy.deepcopy(ACTION)
        next_id = "c23683a9-b2ab-4a2c-87ce-31bdf27a3098"
        next_action["message"]["action_id"] = next_id
        dismiss = dismissal()
        review = dismiss["review"]
        review["action_id"] = next_id
        review["review_id"] = "c23683a9-b2ab-4a2c-87ce-31bdf27a3097"
        review["snapshot"]["record"]["message"] = next_action["message"]
        review["review_digest"] = hashlib.sha256(json.dumps(
            review["snapshot"],sort_keys=True,separators=(",",":")).encode("ascii")).hexdigest()
        self.store.save(1, next_action)
        self.store.save(1, dismiss)
        second = dict(receipt(), review=review)
        self.assertEqual(self.store.advance(1, second), 2)
        self.assertTrue((self.path/SEAL).is_file())
        self.assertTrue((self.path/"generation-0001"/SEAL).is_file())
        self.assertEqual(self.store.load()["generation"], 2)
        with self.assertRaisesRegex(QueueError,"CHECKPOINT_ACTION_ALREADY_RETAINED"):
            self.store.save(2, next_action)

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

    def test_committed_ack_seal_distinct_and_exact(self):
        ack=acknowledgment()
        row=ack["review"]["snapshot"]["record"]
        row.update(state="COMMITTED",result_request_id="c23683a9-b2ab-4a2c-87ce-31bdf27a3019",committed_at=101)
        ack["review"]["review_digest"]=hashlib.sha256(json.dumps(
            ack["review"]["snapshot"],sort_keys=True,separators=(",",":")).encode("ascii")).hexdigest()
        self.store.save(0,ACTION)
        self.store.save(0,ack)
        proof={"version":1,"review":ack["review"],"acknowledged_at_ms":100001,
               "disposition":"REVIEW_ACKNOWLEDGED_ONLY","adjustment_outcome":"UNVERIFIED",
               "can_execute":False,"startup_unlock":False}
        before={p.name:p.read_bytes() for p in self.path.iterdir()}
        for wrong in (dict(proof,can_execute=True),dict(proof,acknowledged_at_ms=160000),
                      dict(proof,review=dict(proof["review"],review_digest="0"*64))):
            with self.assertRaises(QueueError):
                self.store.advance(0,wrong)
        self.assertEqual(self.store.advance(0,proof),1)
        self.assertTrue((self.path/COMMITTED_SEAL).is_file())
        self.assertFalse((self.path/SEAL).exists())
        self.assertEqual(self.store.load()["generation"],1)
        for name,data in before.items(): self.assertEqual((self.path/name).read_bytes(),data)
        with self.assertRaisesRegex(QueueError,"CHECKPOINT_ACTION_ALREADY_RETAINED"):
            self.store.save(1,ACTION)
        (self.path/SEAL).write_bytes((self.path/COMMITTED_SEAL).read_bytes())
        with self.assertRaises(QueueError): self.store.load()

    def test_prepared_ack_never_seals(self):
        ack=acknowledgment()
        self.store.save(0,ACTION)
        self.store.save(0,ack)
        proof={"version":1,"review":ack["review"],"acknowledged_at_ms":100001,
               "disposition":"REVIEW_ACKNOWLEDGED_ONLY","adjustment_outcome":"UNVERIFIED",
               "can_execute":False,"startup_unlock":False}
        with self.assertRaisesRegex(QueueError,"CHECKPOINT_EXACT_COMMITTED_REVIEW_REQUIRED"):
            self.store.advance(0,proof)
        self.assertEqual(self.store.load()["generation"],0)

    def test_bound_refuses_without_erasure(self):
        self.prepare()
        with mock.patch("memory_queue_checkpoint_generations.MAX_GENERATIONS",1):
            with self.assertRaisesRegex(QueueError,"CHECKPOINT_GENERATION_LIMIT"):
                self.store.advance(0,receipt())
        self.assertEqual(self.store.load()["generation"],0)


if __name__=="__main__":
    unittest.main(verbosity=2)
