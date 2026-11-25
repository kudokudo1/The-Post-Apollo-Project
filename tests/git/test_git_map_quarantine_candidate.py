#!/usr/bin/env python3
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"scripts"))
import git_map_isolated_candidate as v2
import git_map_quarantine_candidate as q

class Quarantine(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
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
        self.path=Path(self.old["directory"])
        self.retired=self.path.with_name(".retired-"+self.old["key"])
        self.digest=self.hash(self.path)
        self.current_digest=self.hash(Path(self.current["directory"]))
        self.addCleanup(self.preserved)
    def git(self,*args):
        return subprocess.check_output(["git","-C",str(self.repo),"-c","user.name=Fixture",
            "-c","user.email=fixture@example.invalid",*args],stderr=subprocess.DEVNULL)
    def hash(self,path):
        return hashlib.sha256((path/v2.NAME).read_bytes()).hexdigest()
    def preserved(self):
        self.assertEqual(self.hash(self.path if self.path.exists() else self.retired),self.digest)
        self.assertEqual(self.hash(Path(self.current["directory"])),self.current_digest)
        self.assertEqual(self.git("rev-parse","HEAD"),self.head)
        self.assertEqual(self.git("status","--porcelain"),self.status)
    def move(self,r=None,**kw):
        r=r or self.old
        return q.move(self.repo,self.cache,r["key"],r["manifest"]["snapshot"],r["device"],r["inode"],**kw)
    def test_reversible_and_reader_conflict(self):
        with v2.read(self.cache,self.old["repoId"],self.old["key"]):
            with self.assertRaises(BlockingIOError): self.move()
        result=self.move()
        self.assertEqual(result["status"],"QUARANTINED")
        self.assertFalse(self.path.exists())
        self.assertEqual(str(self.retired.stat().st_ino),self.old["inode"])
        with self.assertRaises(FileNotFoundError):
            with v2.read(self.cache,self.old["repoId"],self.old["key"]): pass
        self.assertEqual(v2.lookup(self.repo,self.cache),self.current)
        self.assertEqual(self.move(restore=True)["status"],"RESTORED")
        self.assertEqual(v2.receipt(self.cache,self.old["repoId"],self.old["key"]),self.old)
    def test_current_wrong_identity_and_collision(self):
        with self.assertRaises(ValueError): self.move(self.current)
        with self.assertRaises(ValueError): self.move(dict(self.old,inode=str(int(self.old["inode"])+1)))
        self.retired.mkdir()
        try:
            with self.assertRaises(ValueError): self.move()
        finally: self.retired.rmdir()
        extra=self.path/"unexpected"
        extra.touch()
        try:
            with self.assertRaises(ValueError): self.move()
        finally: extra.unlink()
        self.assertTrue(self.path.exists())
    def test_missing_gate(self):
        old=os.environ.pop("POST_APOLLO_GIT_MAP_SMOKE")
        try:
            with self.assertRaises(ValueError): self.move()
        finally: os.environ["POST_APOLLO_GIT_MAP_SMOKE"]=old
        self.assertTrue(self.path.exists())
if __name__=="__main__":
    unittest.main()
