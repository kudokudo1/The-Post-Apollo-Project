"""Private temporary files, actual shared flock, simulated root ownership only."""
import fcntl
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from test_observation import helper, fixture
import reader as r

class Reader(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix="cpu-memory-read-only-")
        self.addCleanup(self.temp.cleanup)
        self.parent=Path(self.temp.name)
        self.lock=self.parent/"lock"
        self.lock.touch(mode=0o600)
        self.archive=self.parent/"archive"
        self.fence=self.parent/"fence"
        self.ext=self.parent/"extension"
        self.base=self.parent/"base"
        for p in (patch.multiple(r,PARENT=self.parent,LOCK=self.lock,ARCHIVE=self.archive,
                    FENCE=self.fence,EXT=self.ext,BASE=self.base),
                  patch.multiple(helper,PARENT=self.parent,LOCK=self.lock,RECLAIM_ARCHIVE=self.archive,
                    RECLAIM_FENCE=self.fence,EXT_DIRECTORY=self.ext,SWAPFILE=self.base),
                  patch.object(helper,"secure_parent"),patch.object(helper,"current_boot_id",
                    return_value=fixture()["boot_id"]),patch.object(r.os,"geteuid",return_value=0),
                  patch.object(r,"trusted",side_effect=self.trusted)):
            p.start()
            self.addCleanup(p.stop)

    def trusted(self,s,private=False,kind=r.stat.S_ISDIR):
        r.require(kind(s.st_mode) and not s.st_mode & (0o077 if private else 0o022))
        if kind is r.stat.S_ISREG:
            r.require(s.st_nlink==1)

    def state(self,code):
        output=r.inspect_candidate(helper)
        self.assertEqual(output["code"],code)
        self.assertFalse(output["can_execute"])
        self.assertFalse(output["can_clear"])
        self.assertFalse(output["storage_release_verified"])

    def put(self,path,raw):
        path.write_bytes(raw)
        path.chmod(0o600)

    def test_missing_lock_never_created(self):
        self.lock.unlink()
        self.state("PROTECTED_OBSERVATION_UNVERIFIED")
        self.assertFalse(self.lock.exists())

    def test_exclusive_mutation_lock_refused(self):
        fd=os.open(self.lock,os.O_RDWR)
        try:
            fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
            self.state("PROTECTED_OBSERVATION_UNVERIFIED")
        finally:
            os.close(fd)

    def test_no_custody_no_side_effect(self):
        before=set(self.parent.iterdir())
        self.state("NO_CUSTODY_OBSERVED")
        self.assertEqual(set(self.parent.iterdir()),before)

    def test_partial_archive_retained(self):
        self.put(self.archive,b"{")
        self.state("CUSTODY_UNVERIFIED")
        self.assertEqual(self.archive.read_bytes(),b"{")

    def test_symlink_refused(self):
        self.archive.symlink_to(self.lock)
        self.state("PROTECTED_OBSERVATION_UNVERIFIED")
        self.assertTrue(self.archive.is_symlink())

    def test_fence_without_archive_retained(self):
        self.fence.mkdir(mode=0o700)
        self.state("FENCE_WITHOUT_ARCHIVE")
        self.assertTrue(self.fence.is_dir())

    def test_stable_double_capture_required(self):
        real=r.capture
        def changing(*args):
            a,ids=real(*args)
            self.put(self.archive,b"{")
            return a,ids
        with patch.object(r,"capture",side_effect=changing):
            self.state("PROTECTED_OBSERVATION_UNVERIFIED")
        self.assertEqual(self.archive.read_bytes(),b"{")

    def test_reader_cannot_issue_mutation(self):
        with patch.object(helper,"mutation_lock") as lock,patch.object(helper,"run") as run:
            self.state("NO_CUSTODY_OBSERVED")
            lock.assert_not_called()
            run.assert_not_called()

if __name__=="__main__":
    unittest.main()
