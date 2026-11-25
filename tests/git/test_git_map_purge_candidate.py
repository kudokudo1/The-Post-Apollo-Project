#!/usr/bin/env python3
import fcntl
import hashlib
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"scripts"))
import git_map_isolated_candidate as v2
import git_map_quarantine_candidate as q
import git_map_purge_candidate as p

class Purge(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix="gitw-purge-fixture-")
        self.addCleanup(self.tmp.cleanup)
        self.base=Path(self.tmp.name).resolve()
        self.repo=self.base/"repo"
        self.repo.mkdir()
        self.cache=self.base/"cache"
        self.git("init","-b","main")
        self.git("commit","--allow-empty","-m","old")
        self.old=v2.build(self.repo,self.cache)
        self.git("commit","--allow-empty","-m","new")
        self.current=v2.build(self.repo,self.cache)
        self.head=self.git("rev-parse","HEAD")
        self.status=self.git("status","--porcelain")
        self.current_db=Path(self.current["directory"])/v2.NAME
        self.digest=hashlib.sha256(self.current_db.read_bytes()).hexdigest()
        self.args=(self.repo,self.cache,self.old["key"],self.old["manifest"]["snapshot"],
                   self.old["device"],self.old["inode"])
        self.live=Path(self.old["directory"])
        self.retired=Path(q.move(*self.args)["directory"])
        self.pending=self.live.with_name(".purging-"+"-".join(self.args[2:]))
        self.addCleanup(self.preserved)
    def git(self,*args):
        return subprocess.check_output(["git","-C",str(self.repo),"-c","user.name=Fixture",
            "-c","user.email=fixture@example.invalid",*args],stderr=subprocess.DEVNULL)
    def preserved(self):
        self.assertEqual(hashlib.sha256(self.current_db.read_bytes()).hexdigest(),self.digest)
        self.assertEqual(self.git("rev-parse","HEAD"),self.head)
        self.assertEqual(self.git("status","--porcelain"),self.status)
    def purge(self,**kw):
        return p.purge(*self.args,confirmation="PURGE",**kw)
    def interrupted(self,action):
        code="""import os,signal,sys
from pathlib import Path
sys.path.insert(0,sys.argv[1])
import git_map_purge_candidate as p
action=sys.argv[2]
original=getattr(os,action)
def interrupted(*args,**kwargs):
    result=original(*args,**kwargs)
    os.kill(os.getpid(),signal.SIGKILL)
    return result
setattr(os,action,interrupted)
p.purge(Path(sys.argv[3]),Path(sys.argv[4]),*sys.argv[5:],confirmation="PURGE")
"""
        run=subprocess.run([sys.executable,"-I","-B","-c",code,str(ROOT/"scripts"),action,*map(str,self.args)],
                           capture_output=True,text=True,timeout=10)
        self.assertEqual(run.returncode,-signal.SIGKILL,run.stderr)
    def test_explicit_refusals_and_purge(self):
        with self.assertRaises(ValueError): p.purge(*self.args,confirmation="NO")
        with self.assertRaises(ValueError): self.purge(recover=True)
        fd=os.open(self.retired,os.O_RDONLY|os.O_DIRECTORY)
        try:
            fcntl.flock(fd,fcntl.LOCK_SH|fcntl.LOCK_NB)
            with self.assertRaises(BlockingIOError): self.purge()
        finally: os.close(fd)
        extra=self.retired/"extra"
        extra.touch()
        with self.assertRaises(ValueError): self.purge()
        extra.unlink()
        with self.assertRaises(ValueError):
            p.purge(*self.args[:-1],str(int(self.args[-1])+1),confirmation="PURGE")
        self.assertEqual(self.purge()["status"],"PURGED")
        self.assertFalse(self.retired.exists() or self.pending.exists() or self.live.exists())
        with self.assertRaises(ValueError): self.purge(recover=True)
        print("GIT_MAP_PURGE_EXPLICIT_PASS",flush=True)
    def test_current_and_rebuilt_refusal(self):
        old_head=self.git("rev-parse","HEAD~1").decode().strip()
        self.git("reset","--hard",old_head)
        try:
            with self.assertRaises(ValueError): self.purge()
            self.assertTrue((self.retired/v2.NAME).is_file())
            rebuilt=v2.build(self.repo,self.cache)
            self.assertEqual(rebuilt["key"],self.old["key"])
        finally:
            self.git("reset","--hard",self.head.decode().strip())
        with self.assertRaises(ValueError): self.purge()
        self.assertTrue((self.retired/v2.NAME).is_file())
        self.assertTrue((self.live/v2.NAME).is_file())
    def test_kill_after_rename(self):
        self.interrupted("rename")
        self.assertTrue((self.pending/v2.NAME).is_file())
        self.assertFalse(self.retired.exists())
        with self.assertRaises(ValueError): self.purge()
        self.assertEqual(self.purge(recover=True)["status"],"PURGED")
        self.assertFalse(self.pending.exists())
        print("GIT_MAP_PURGE_RENAME_RECOVERY_PASS",flush=True)
    def test_kill_after_unlink(self):
        self.interrupted("unlink")
        self.assertTrue(self.pending.is_dir())
        self.assertEqual(list(self.pending.iterdir()),[])
        self.assertEqual(self.purge(recover=True)["status"],"PURGED")
        self.assertFalse(self.pending.exists())
        print("GIT_MAP_PURGE_UNLINK_RECOVERY_PASS",flush=True)
    def test_kill_after_rmdir(self):
        self.interrupted("rmdir")
        self.assertFalse(self.pending.exists() or self.retired.exists())
        # No durable success receipt: absence is not a replay authorization.
        with self.assertRaises(ValueError): self.purge(recover=True)
        print("GIT_MAP_PURGE_ABSENCE_UNCONFIRMED_PASS",flush=True)
if __name__=="__main__":
    unittest.main()
