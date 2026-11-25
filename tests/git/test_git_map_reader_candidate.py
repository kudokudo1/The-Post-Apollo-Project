#!/usr/bin/env python3
import fcntl
import hashlib
import json
import os
from pathlib import Path
import select
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"scripts"))
import git_map_index_manager as manager
import git_map_reader_candidate as reader


class ReaderCustodyTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base=Path(self.tmp.name)
        self.repo=self.base/"repo"
        self.repo.mkdir()
        self.cache=self.base/"cache"/"post-apollo-git-map-v1"
        self.git("init","-b","main")
        self.git("commit","--allow-empty","-m","first")
        self.old=manager.build(self.repo,self.cache)
        self.git("commit","--allow-empty","-m","second")
        self.new=manager.build(self.repo,self.cache)
        self.path=Path(self.old["directory"])
        self.env=dict(os.environ,XDG_CACHE_HOME=str(self.cache.parent))
        self.before=hashlib.sha256((self.path/manager.index.NAME).read_bytes()).hexdigest()

    def git(self,*args):
        return subprocess.check_output(["/usr/bin/git","-C",str(self.repo),
            "-c","user.name=Fixture","-c","user.email=fixture@example.invalid",*args],
            stderr=subprocess.DEVNULL,text=True).strip()

    def cmd(self,generation):
        return [sys.executable,"-I","-B",str(ROOT/"scripts/git_map_reader_candidate.py"),
                generation["repoId"],generation["key"],generation["manifest"]["snapshot"]]

    def cleanup_process(self,p):
        if p.poll() is None:
            p.kill()
        p.wait(timeout=5)
        for stream in (p.stdin,p.stdout,p.stderr):
            if stream is not None:
                stream.close()

    def start(self,generation):
        p=subprocess.Popen(self.cmd(generation),env=self.env,stdin=subprocess.PIPE,
                           stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        self.addCleanup(self.cleanup_process,p)
        self.assertTrue(select.select([p.stdout],[],[],5)[0],"no reader receipt")
        line=p.stdout.readline()
        self.assertTrue(line,"reader exited without receipt")
        receipt=json.loads(line)
        self.assertEqual(receipt["status"],"HELD")
        self.assertEqual(receipt["snapshot"],generation["manifest"]["snapshot"])
        self.assertEqual(receipt["key"],generation["key"])
        self.assertFalse(receipt["reclamationAllowed"])
        return p,receipt

    def exclusive_available(self,path):
        # Test witness ONLY. Success is not production deletion authority.
        fd=os.open(path,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
        try:
            try:
                fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError:
                return False
            return True
        finally:
            os.close(fd)

    def assert_preserved(self):
        self.assertEqual(hashlib.sha256((self.path/manager.index.NAME).read_bytes()).hexdigest(),self.before)
        self.assertTrue(self.path.exists())
        self.assertTrue(Path(self.new["directory"]).exists())
        self.assertEqual(self.git("status","--porcelain"),"")

    def test_two_readers_between_requests_and_generation_handoff(self):
        first,a=self.start(self.old)
        second,b=self.start(self.old)
        self.assertEqual((a["device"],a["inode"]),(b["device"],b["inode"]))
        self.assertFalse(self.exclusive_available(self.path))
        self.assertTrue(self.exclusive_available(self.new["directory"]))
        # New generation secured before release of old (two host readers).
        replacement,_=self.start(self.new)
        self.assertFalse(self.exclusive_available(self.new["directory"]))
        first.stdin.close()
        self.assertEqual(first.wait(timeout=5),0)
        self.assertFalse(self.exclusive_available(self.path))
        second.stdin.close()
        self.assertEqual(second.wait(timeout=5),0)
        self.assertTrue(self.exclusive_available(self.path))
        self.assertFalse(self.exclusive_available(self.new["directory"]))
        replacement.stdin.close()
        self.assertEqual(replacement.wait(timeout=5),0)
        self.assert_preserved()
        self.assertTrue(all(x["readerStatus"]=="UNKNOWN" and not x["reclamationAllowed"]
                            for x in manager.inventory(self.repo,self.cache)["entries"]))

    def test_sigkill_releases_only_terminated_reader(self):
        first,_=self.start(self.old)
        second,_=self.start(self.old)
        first.kill()
        first.wait(timeout=5)
        self.assertFalse(self.exclusive_available(self.path))
        second.kill()
        second.wait(timeout=5)
        self.assertTrue(self.exclusive_available(self.path))
        self.assert_preserved()

    def test_owner_process_death_closes_lifetime_pipe(self):
        # Owner opens the pipe and is killed; child observes EOF. No
        # production process is involved and no PID guessing is used.
        owner_code = """
import subprocess,sys,time
p=subprocess.Popen(sys.argv[1:],stdin=subprocess.PIPE,stdout=subprocess.PIPE,text=True)
print(p.stdout.readline().strip(),flush=True)
time.sleep(60)
"""
        p=subprocess.Popen([sys.executable,"-c",owner_code,*self.cmd(self.old)],
                           env=self.env,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE,text=True)
        self.addCleanup(self.cleanup_process,p)
        self.assertTrue(select.select([p.stdout],[],[],5)[0])
        receipt=json.loads(p.stdout.readline())
        self.assertEqual(receipt["status"],"HELD")
        self.assertFalse(self.exclusive_available(self.path))
        p.kill()
        p.wait(timeout=5)
        deadline=time.monotonic()+5
        while not self.exclusive_available(self.path):
            self.assertLess(time.monotonic(),deadline,"orphan reader did not release")
            time.sleep(.02)
        self.assert_preserved()

    def test_wrong_identity_busy_and_replacement_refused(self):
        args=(self.cache,self.old["repoId"],self.old["key"],self.old["manifest"]["snapshot"])
        with self.assertRaises(ValueError):
            reader.Reader(*args[:-1],"f"*32)
        fd=os.open(self.path,os.O_RDONLY|os.O_DIRECTORY)
        try:
            fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
            with self.assertRaises(BlockingIOError):
                reader.Reader(*args)
        finally:
            os.close(fd)
        with patch.object(reader,"same_directory",side_effect=[True,False]):
            with self.assertRaises(ValueError):
                reader.Reader(*args)
        self.assertTrue(self.exclusive_available(self.path))
        self.assert_preserved()

    def test_malformed_manifest_refuses_without_receipt_or_lock_leak(self):
        db=self.path/manager.index.NAME
        args=(self.cache,self.old["repoId"],self.old["key"],self.old["manifest"]["snapshot"])
        for value in ("[]","null","true","42",'"string"',"{"):
            with sqlite3.connect(db) as conn:
                conn.execute("UPDATE manifest SET document=?",(value,))
            conn.close()
            digest=hashlib.sha256(db.read_bytes()).hexdigest()
            with self.assertRaises(ValueError): reader.Reader(*args)
            self.assertTrue(self.exclusive_available(self.path))
            result=subprocess.run(self.cmd(self.old),env=self.env,input="",
                    stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=5)
            self.assertEqual(result.returncode,1)
            self.assertEqual(result.stdout,"")
            self.assertIn("Reader custody unavailable",result.stderr)
            self.assertNotIn("Traceback",result.stderr)
            self.assertTrue(self.exclusive_available(self.path))
            self.assertEqual(hashlib.sha256(db.read_bytes()).hexdigest(),digest)
            self.assertTrue(Path(self.new["directory"]).exists())

    def test_symlink_and_unexpected_pipe_data_refused(self):
        args=(self.cache,self.old["repoId"],self.old["key"],self.old["manifest"]["snapshot"])
        relocated=self.path.with_name("relocated")
        self.path.rename(relocated)
        self.path.symlink_to(relocated,target_is_directory=True)
        with self.assertRaises(ValueError):
            reader.Reader(*args)
        self.path.unlink()
        relocated.rename(self.path)
        p,_=self.start(self.old)
        p.stdin.write("x")
        p.stdin.flush()
        p.stdin.close()
        self.assertEqual(p.wait(timeout=5),1)
        self.assertTrue(self.exclusive_available(self.path))
        self.assert_preserved()


if __name__=="__main__":
    unittest.main()
