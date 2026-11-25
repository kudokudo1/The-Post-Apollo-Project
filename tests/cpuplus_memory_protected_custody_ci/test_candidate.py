"""Only private temporary filesystem tests; no production helper execution."""
import importlib.machinery
import importlib.util
from contextlib import contextmanager
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import candidate as c

class CandidateTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix="cpu-memory-protected-custody-")
        self.addCleanup(self.tmp.cleanup)
        self.parent=Path(self.tmp.name)
        self.ext=self.parent/"extension"
        self.ext.mkdir(mode=0o700)
        self.archive=self.parent/"archive.json"
        self.fence=self.parent/"fence"
        self.events=[]
        self.evidence={"boot_id":"1d934ec2-d18e-441a-9bbf-37e404632201","can_execute":False}
        self.helper=type("Stub",(),{})()
        @contextmanager
        def lock(*,inspection):
            self.assertTrue(inspection)
            self.events.append("lock")
            try: yield
            finally: self.events.append("unlock")
        self.helper.mutation_lock=lock
        def observe(*args):
            self.events.append("observe")
            return dict(self.evidence)
        for p in (patch.multiple(c,PARENT=self.parent,EXT=self.ext,ARCHIVE=self.archive,FENCE=self.fence),
                  patch.object(c,"load_verified_helper",return_value=self.helper),patch.object(c,"secure_dir",return_value=None),
                  patch.object(c,"observe",side_effect=observe),
                  patch.object(c,"read",side_effect=self.read_private)):
            p.start(); self.addCleanup(p.stop)
        # secure_dir identity is only needed for final fence comparison.
        c.secure_dir.side_effect=lambda fd,**kw: (os.fstat(fd).st_dev,os.fstat(fd).st_ino)

    def read_private(self,fd,name,limit=c.LIMIT,sync=False):
        item=os.open(name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=fd)
        try:
            if sync: os.fsync(item)
            return os.read(item,limit+1)
        finally: os.close(item)

    def test_archive_before_fence_and_no_authority(self):
        real=c.write_once
        def record(fd,name,data):
            if name=="prepared.json":
                self.assertTrue(self.archive.is_file())
                self.assertTrue(self.fence.is_dir())
                self.assertEqual(self.events,["lock","observe","observe"])
            else:
                self.assertFalse(self.fence.exists())
            real(fd,name,data)
        with patch.object(c,"write_once",side_effect=record):
            result=c.prepare_candidate()
        self.assertEqual(result,{"state":"PREPARED_REVIEW_REQUIRED","can_execute":False,"can_clear":False})
        marker=c.strict_object((self.fence/"prepared.json").read_bytes())
        self.assertEqual(marker["archive_sha256"],c.digest(self.archive.read_bytes()))
        self.assertFalse(marker["can_execute"])
        self.assertEqual(self.events[-1],"unlock")

    def test_duplicate_refused_without_overwrite(self):
        c.prepare_candidate()
        original=self.archive.read_bytes()
        with self.assertRaises(c.CustodyRefused):
            c.prepare_candidate()
        self.assertEqual(self.archive.read_bytes(),original)

    def test_changed_observation_refuses_before_fence(self):
        with patch.object(c,"observe",side_effect=[self.evidence,dict(self.evidence,boot_id="changed")]):
            with self.assertRaises(c.CustodyRefused):
                c.prepare_candidate()
        self.assertTrue(self.archive.exists())
        self.assertFalse(self.fence.exists())
        with self.assertRaises(c.CustodyRefused):
            c.prepare_candidate()

    def test_archive_sync_failure_preserves_partial(self):
        with patch.object(c.os,"fsync",side_effect=OSError("fixture")):
            with self.assertRaises(OSError):
                c.prepare_candidate()
        self.assertTrue(self.archive.exists())
        self.assertFalse(self.fence.exists())

    def test_marker_failure_leaves_fence(self):
        real=c.write_once
        def fail(fd,name,data):
            if name=="prepared.json": raise OSError("fixture")
            real(fd,name,data)
        with patch.object(c,"write_once",side_effect=fail):
            with self.assertRaises(OSError):
                c.prepare_candidate()
        self.assertTrue(self.archive.exists())
        self.assertTrue(self.fence.is_dir())
        self.assertFalse((self.fence/"prepared.json").exists())
        with self.assertRaises(c.CustodyRefused):
            c.prepare_candidate()

    def test_existing_symlink_or_fence_refused(self):
        self.archive.symlink_to(self.ext)
        with self.assertRaises(c.CustodyRefused):
            c.prepare_candidate()
        self.assertTrue(self.archive.is_symlink())

    def test_duplicate_json_keys(self):
        with self.assertRaises(c.CustodyRefused):
            c.strict_object(b'{"x":1,"x":2}')

    def test_final_fence_identity_mismatch_keeps_custody(self):
        original=c.secure_dir.side_effect
        def mismatch(fd,**kw):
            identity=original(fd,**kw)
            return (identity[0],identity[1]+1) if kw.get("private") else identity
        c.secure_dir.side_effect=mismatch
        with self.assertRaisesRegex(c.CustodyRefused,"FENCE_IDENTITY_CHANGED"):
            c.prepare_candidate()
        self.assertTrue(self.archive.is_file())
        self.assertTrue((self.fence/"prepared.json").is_file())

    def test_final_fence_contents_mismatch_keeps_custody(self):
        real=c.write_once
        def extra(fd,name,data):
            real(fd,name,data)
            if name=="prepared.json":
                (self.fence/"unexpected").write_bytes(b"fixture")
        with patch.object(c,"write_once",side_effect=extra):
            with self.assertRaisesRegex(c.CustodyRefused,"FENCE_CONTENTS_CHANGED"):
                c.prepare_candidate()
        self.assertTrue(self.archive.is_file())
        self.assertTrue((self.fence/"prepared.json").is_file())

    def test_final_marker_readback_mismatch_keeps_custody(self):
        real=c.write_once
        def changed(fd,name,data):
            real(fd,name,data)
            if name=="prepared.json":
                (self.fence/name).write_bytes(b"changed")
        with patch.object(c,"write_once",side_effect=changed):
            with self.assertRaisesRegex(c.CustodyRefused,"PREPARED_READBACK_CHANGED"):
                c.prepare_candidate()
        self.assertTrue(self.archive.is_file())
        self.assertTrue(self.fence.is_dir())

    def test_final_archive_readback_mismatch_keeps_custody(self):
        real=c.write_once
        def changed(fd,name,data):
            real(fd,name,data)
            if name=="prepared.json":
                self.archive.write_bytes(b"changed")
        with patch.object(c,"write_once",side_effect=changed):
            with self.assertRaisesRegex(c.CustodyRefused,"ARCHIVE_READBACK_CHANGED"):
                c.prepare_candidate()
        self.assertTrue((self.fence/"prepared.json").is_file())

    def test_no_cli(self):
        self.assertFalse(hasattr(c,"main"))

if __name__=="__main__":
    unittest.main()
