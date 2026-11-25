"""Actual disposable filesystem effects and process-crash boundaries."""
import os
from pathlib import Path
import signal
import tempfile
import unittest
from unittest.mock import patch
from test_reclaim_custody import fixture, helper
import durable_fixture as d

class DurableFixtureTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="cpu-memory-reclaim-fixture-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.write("fixture-marker", d.MARKER)
        self.facts = fixture()

    def write(self, name, raw):
        fd = os.open(self.root / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as f:
            f.write(raw)

    def assert_blocked(self, code):
        self.assertEqual(d.inspect(self.root), {"state":"RECOVERY_REQUIRED","code":code,
                                                "can_execute":False,"can_clear":False})
        with self.assertRaises((ValueError, OSError)):
            d.publish(self.root, helper, self.facts)

    def test_order_and_immutable_records(self):
        stages=[]
        def check(stage):
            stages.append(stage)
            self.assertTrue((self.root/d.ARCHIVE).is_file())
            if stage=="ARCHIVE_DURABLE":
                self.assertFalse((self.root/d.FENCE).exists())
            elif stage=="FENCE_DIRECTORY_DURABLE":
                self.assertFalse((self.root/d.FENCE/d.PREPARED).exists())
            else:
                self.assertTrue((self.root/d.FENCE/d.PREPARED).is_file())
        self.assertEqual(d.publish(self.root,helper,self.facts,check)["can_execute"],False)
        self.assertEqual(stages,["ARCHIVE_DURABLE","FENCE_DIRECTORY_DURABLE","PREPARED_DURABLE"])
        archive=(self.root/d.ARCHIVE).read_bytes()
        marker=(self.root/d.FENCE/d.PREPARED).read_bytes()
        self.assert_blocked("PREPARED_REVIEW_REQUIRED")
        self.assertEqual((self.root/d.ARCHIVE).read_bytes(),archive)
        self.assertEqual((self.root/d.FENCE/d.PREPARED).read_bytes(),marker)

    def crash_at(self, stage, expected):
        pid=os.fork()
        if pid==0:
            try:
                def stop(s):
                    if s==stage:
                        os.kill(os.getpid(),signal.SIGKILL)
                d.publish(self.root,helper,self.facts,stop)
            except BaseException:
                os._exit(3)
            os._exit(4)
        _,status=os.waitpid(pid,0)
        self.assertTrue(os.WIFSIGNALED(status))
        self.assertEqual(os.WTERMSIG(status),signal.SIGKILL)
        self.assert_blocked(expected)

    def test_crash_after_archive(self):
        self.crash_at("ARCHIVE_DURABLE","ARCHIVE_ONLY")

    def test_crash_after_fence_directory(self):
        self.crash_at("FENCE_DIRECTORY_DURABLE","FENCE_INCOMPLETE")

    def test_crash_after_prepared(self):
        self.crash_at("PREPARED_DURABLE","PREPARED_REVIEW_REQUIRED")

    def test_sync_failure_no_fence(self):
        with patch.object(d.os,"fsync",side_effect=OSError("fixture fsync failure")):
            with self.assertRaises(OSError):
                d.publish(self.root,helper,self.facts)
        self.assertFalse((self.root/d.FENCE).exists())
        self.assert_blocked("ARCHIVE_ONLY")

    def test_invalid_proposal_no_publication(self):
        self.facts["boot_id"]="2d934ec2-d18e-441a-9bbf-37e404632201"
        with self.assertRaises(ValueError):
            d.publish(self.root,helper,self.facts)
        self.assertEqual(d.inspect(self.root)["state"],"EMPTY_FIXTURE")

    def test_changed_evidence_before_fence(self):
        def change(stage):
            if stage=="ARCHIVE_DURABLE":
                self.facts["boot_id"]="2d934ec2-d18e-441a-9bbf-37e404632201"
        with self.assertRaises(ValueError):
            d.publish(self.root,helper,self.facts,change)
        self.assert_blocked("ARCHIVE_ONLY")

    def test_symlink_archive_refused(self):
        (self.root/d.ARCHIVE).symlink_to(self.root/"fixture-marker")
        self.assert_blocked("EVIDENCE_UNVERIFIED")
        self.assertEqual((self.root/"fixture-marker").read_bytes(),d.MARKER)

    def test_partial_archive_refused(self):
        self.write(d.ARCHIVE,b"{")
        self.assert_blocked("EVIDENCE_UNVERIFIED")

    def test_bad_fence_refused(self):
        d.publish(self.root,helper,self.facts)
        (self.root/d.FENCE/d.PREPARED).write_bytes(b"{}\n")
        self.assert_blocked("EVIDENCE_UNVERIFIED")

    def test_fence_without_archive(self):
        (self.root/d.FENCE).mkdir(mode=0o700)
        self.assert_blocked("ARCHIVE_MISSING")

    def test_lock_contention(self):
        with d.locked(self.root):
            self.assertEqual(d.inspect(self.root)["code"],"EVIDENCE_UNVERIFIED")
            with self.assertRaises(BlockingIOError):
                d.publish(self.root,helper,self.facts)
        self.assertEqual(d.inspect(self.root)["state"],"EMPTY_FIXTURE")

if __name__=="__main__":
    unittest.main()
