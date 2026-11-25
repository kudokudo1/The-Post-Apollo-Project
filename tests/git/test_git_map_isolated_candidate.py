#!/usr/bin/env python3
import fcntl
import hashlib
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"scripts"))
import git_map_history_index as index
import git_map_index_manager as manager
import git_map_isolated_candidate as v2
import git_map_reader_candidate as legacy_reader

class IsolatedCandidate(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base=Path(self.tmp.name)
        self.repo=self.base/"repo"
        self.repo.mkdir()
        self.cache=self.base/"cache"
        self.v1=self.cache/"post-apollo-git-map-v1"
        self.git("init","-b","main")
        self.git("commit","--allow-empty","-m","first")
        self.git("commit","--allow-empty","-m","second")
    def git(self,*args):
        return subprocess.check_output(["git","-C",str(self.repo),"-c","user.name=Fixture",
            "-c","user.email=fixture@example.invalid",*args],stderr=subprocess.DEVNULL)
    def frozen(self,path):
        return hashlib.sha256(path.read_bytes()).hexdigest()
    def test_namespace_and_legacy_cli_refusal(self):
        old=manager.build(self.repo,self.v1)
        old_db=Path(old["directory"])/index.NAME
        original=self.frozen(old_db)
        head=self.git("rev-parse","HEAD")
        status=self.git("status","--porcelain")
        self.assertEqual(v2.lookup(self.repo,self.cache)["status"],"MISSING")
        self.assertFalse((self.cache/v2.ROOT_NAME).exists())
        new=v2.build(self.repo,self.cache)
        path=Path(new["directory"])
        self.assertNotEqual(new["key"],old["key"])
        self.assertFalse((path/index.NAME).exists())
        self.assertEqual(new,v2.lookup(self.repo,self.cache))
        self.assertEqual(new,v2.build(self.repo,self.cache))
        self.assertEqual(manager.lookup(self.repo,self.v1),old)
        env=dict(os.environ,XDG_CACHE_HOME=str(self.cache))
        for command in (["info",str(path)],["page",str(path),new["manifest"]["snapshot"],"0"],
                        ["locate",str(path),new["manifest"]["snapshot"],head.decode().strip()],
                        ["search",str(path),new["manifest"]["snapshot"],"first","0"]):
            p=subprocess.run([sys.executable,"-I","-B",str(ROOT/"scripts/git_map_history_index.py"),*command],
                env=env,capture_output=True,text=True,timeout=5)
            self.assertEqual(p.returncode,1,p.stderr)
            self.assertEqual(p.stdout,"")
        with self.assertRaises(OSError):
            legacy_reader.Reader(self.cache/v2.ROOT_NAME,new["repoId"],new["key"],new["manifest"]["snapshot"])
        with v2.read(self.cache,new["repoId"],new["key"],new["manifest"]["snapshot"]) as (conn,m):
            with index.locked_index(old["directory"]) as before:
                a=index.page(before,old["manifest"]["snapshot"],0)
                b=index.page(conn,m["snapshot"],0)
                self.assertEqual(a["rows"],b["rows"])
                self.assertEqual(a["frontier"],b["frontier"])
            self.assertEqual(index.search(conn,m["snapshot"],"first",0)["match"]["ordinal"],1)
        self.assertEqual(self.frozen(old_db),original)
        self.assertEqual(self.git("rev-parse","HEAD"),head)
        self.assertEqual(self.git("status","--porcelain"),status)
        self.assertFalse(new["reclamationAllowed"])
    def test_lock_and_protocol_refusal(self):
        new=v2.build(self.repo,self.cache)
        path=Path(new["directory"])
        args=(self.cache,new["repoId"],new["key"],new["manifest"]["snapshot"])
        db=path/v2.NAME
        digest=self.frozen(db)
        fd=os.open(path,os.O_RDONLY|os.O_DIRECTORY)
        try:
            with v2.read(*args):
                with self.assertRaises(BlockingIOError):
                    fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
            fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
            with self.assertRaises(BlockingIOError):
                with v2.read(*args): pass
            fcntl.flock(fd,fcntl.LOCK_UN)
            with self.assertRaises(ValueError):
                with v2.read(*args[:-1],"f"*32): pass
            fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
            fcntl.flock(fd,fcntl.LOCK_UN)
        finally: os.close(fd)
        self.assertEqual(self.frozen(db),digest)
        with sqlite3.connect(db) as conn:
            conn.execute("PRAGMA application_id=0")
        conn.close()
        with self.assertRaises(ValueError):
            with v2.read(*args): pass
        with self.assertRaises(ValueError):
            v2.build(self.repo,self.cache)
    def test_mixed_generation_and_shallow_refused(self):
        new=v2.build(self.repo,self.cache)
        path=Path(new["directory"])
        (path/index.NAME).write_bytes(b"legacy alias")
        with self.assertRaises(ValueError):
            v2.lookup(self.repo,self.cache)
        shallow=self.base/"shallow"
        subprocess.run(["git","clone","--depth=1",self.repo.as_uri(),str(shallow)],
                       check=True,capture_output=True)
        with self.assertRaises(ValueError):
            v2.build(shallow,self.cache)

if __name__=="__main__":
    unittest.main()
