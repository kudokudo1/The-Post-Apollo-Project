"""Disposable host pre-send persistence tests. No desktop or memory writes."""
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"services/memory"))
from memory_adjustment_queue import QueueError
from memory_queue_host_checkpoint import HostCheckpoint, SLOTS

A="c23683a9-b2ab-4a2c-87ce-31bdf27a3012"
B="c23683a9-b2ab-4a2c-87ce-31bdf27a3013"
X="c23683a9-b2ab-4a2c-87ce-31bdf27a3015"
R="c23683a9-b2ab-4a2c-87ce-31bdf27a3014"
MESSAGE={"version":1,"owner_id":A,"action_id":X,"action_sequence":1,"kind":"QUEUE",
         "expected_request_id":None,"target_gib":16,"expires_at":200}
ACTION={"version":1,"kind":"ACTION","message":MESSAGE}


def acknowledgment():
    row={"version":1,"ordinal":1,"message":dict(MESSAGE),"state":"PREPARED","prepared_at":100,
         "result_request_id":None,"committed_at":None,"adjustment_outcome":"UNVERIFIED","can_execute":False}
    snap={"version":1,"record":row,"pending_request_id":None,
          "pending_digest":hashlib.sha256(b"null").hexdigest(),"adjustment_outcome":"UNVERIFIED",
          "can_execute":False,"startup_unlock":False}
    digest=hashlib.sha256(json.dumps(snap,sort_keys=True,separators=(",",":")).encode("ascii")).hexdigest()
    return {"version":1,"kind":"REVIEW_ACK","review":{"version":1,"review_id":R,"owner_id":B,
            "action_id":X,"snapshot":snap,"review_digest":digest,"reviewed_at_ms":100000,
            "can_execute":False,"startup_unlock":False}}


class Tests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.path=Path(tmp.name)
        self.store=HostCheckpoint(self.path)

    def test_roundtrip_and_write_once(self):
        self.assertIsNone(self.store.load()["action"])
        self.store.save(ACTION)
        ack=acknowledgment()
        self.store.save(ack)
        saved=HostCheckpoint(self.path).load()
        self.assertEqual(saved["action"],ACTION)
        self.assertEqual(saved["acknowledgment"],ack)
        self.assertFalse(saved["startup_unlock"])
        for record in (ACTION,ack):
            with self.assertRaisesRegex(QueueError,"HOST_CHECKPOINT_OCCUPIED"):
                self.store.save(record)
        self.assertEqual(self.store.load(),saved)

    def test_bad_review_digest_refused(self):
        ack=acknowledgment()
        ack["review"]["review_digest"]="0"*64
        with self.assertRaisesRegex(QueueError,"INVALID_HOST_CHECKPOINT_DIGEST"):
            self.store.save(ack)
        self.assertIsNone(self.store.load()["acknowledgment"])

    def test_conflicting_review_refused(self):
        self.store.save(dict(ACTION,message=dict(MESSAGE,target_gib=20)))
        with self.assertRaisesRegex(QueueError,"HOST_CHECKPOINT_ACTION_MISMATCH"):
            self.store.save(acknowledgment())
        self.assertIsNone(self.store.load()["acknowledgment"])

    def test_partial_and_corrupt_fail_closed(self):
        slot=self.path/SLOTS["ACTION"]
        slot.write_bytes(b'{')
        slot.chmod(0o600)
        with self.assertRaises(QueueError):
            self.store.load()
        with self.assertRaises(QueueError):
            self.store.save(ACTION)
        self.assertEqual(slot.read_bytes(),b'{')

    def test_unsafe_paths_refused(self):
        target=self.path/"target"
        target.write_bytes(b"x")
        target.chmod(0o600)
        slot=self.path/SLOTS["ACTION"]
        slot.symlink_to(target)
        with self.assertRaises(QueueError):
            self.store.load()
        slot.unlink()
        os.link(target,slot)
        with self.assertRaisesRegex(QueueError,"UNSAFE_HOST_CHECKPOINT"):
            self.store.load()
        slot.unlink()
        os.mkfifo(slot,0o600)
        with self.assertRaises(QueueError):
            self.store.load()
        slot.unlink()
        self.path.chmod(0o755)
        with self.assertRaisesRegex(QueueError,"UNSAFE_HOST_CHECKPOINT"):
            self.store.load()

    def test_fsync_failure_leaves_slot_and_no_success(self):
        with mock.patch("memory_queue_host_checkpoint.os.fsync",side_effect=OSError("test")):
            with self.assertRaises(QueueError):
                self.store.save(ACTION)
        self.assertTrue((self.path/SLOTS["ACTION"]).exists())
        with self.assertRaises(QueueError):
            self.store.save(ACTION)

    def test_process_sigkill_after_durable_checkpoint(self):
        code=("import sys,json,time;sys.path.insert(0,sys.argv[1]);"
              "from memory_queue_host_checkpoint import HostCheckpoint;"
              "s=HostCheckpoint(sys.argv[2]);s.save(json.loads(sys.argv[3]));"
              "print('DURABLE',flush=True);time.sleep(60)")
        for record in (ACTION,acknowledgment()):
            child=subprocess.Popen([sys.executable,"-B","-c",code,str(ROOT/"services/memory"),
                                   str(self.path),json.dumps(record)],stdout=subprocess.PIPE,text=True)
            try:
                import select
                self.assertTrue(select.select([child.stdout],[],[],5)[0])
                self.assertEqual(child.stdout.readline().strip(),"DURABLE")
                child.send_signal(signal.SIGKILL)
                self.assertEqual(child.wait(timeout=5),-signal.SIGKILL)
            finally:
                if child.poll() is None:
                    child.kill()
                    child.wait(timeout=5)
                child.stdout.close()
        self.assertEqual(self.store.load()["action"],ACTION)
        self.assertEqual(self.store.load()["acknowledgment"],acknowledgment())

if __name__=="__main__":
    unittest.main(verbosity=2)
