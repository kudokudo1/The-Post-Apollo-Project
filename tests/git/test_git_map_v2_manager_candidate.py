#!/usr/bin/env python3
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"scripts"))
import git_map_isolated_candidate as v2
import git_map_index_manager as v1
import git_map_history_index as index

class ManagerTransport(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base=Path(self.tmp.name).resolve()
        self.repo=self.base/"repo"
        self.repo.mkdir()
        self.cache=self.base/"cache"
        self.env=dict(os.environ,POST_APOLLO_GIT_MAP_SMOKE="CI_DISPOSABLE_ONLY",
                      XDG_CACHE_HOME=str(self.base/"unused"))
        self.git("init","-b","main")
        self.git("commit","--allow-empty","-m","fixture")
        self.head=self.git("rev-parse","HEAD")
        self.status=self.git("status","--porcelain")
        self.addCleanup(self.preserved)
    def git(self,*args):
        return subprocess.check_output(["git","-C",str(self.repo),"-c","user.name=Fixture",
            "-c","user.email=fixture@example.invalid",*args],stderr=subprocess.DEVNULL)
    def preserved(self):
        self.assertEqual(self.git("rev-parse","HEAD"),self.head)
        self.assertEqual(self.git("status","--porcelain"),self.status)
        self.assertFalse((self.base/"unused").exists())
    def run_manager(self,action,*,base=None,repo=None,env=None):
        return subprocess.run([sys.executable,"-I","-B",str(ROOT/"scripts/git_map_v2_manager_candidate.py"),
             "--base",str(self.cache if base is None else base),action,str(self.repo if repo is None else repo)],
             env=env or self.env,capture_output=True,text=True,timeout=10)
    def accepted(self,action,**kw):
        p=self.run_manager(action,**kw)
        self.assertEqual(p.returncode,0,p.stderr)
        m=json.loads(p.stdout)
        self.assertEqual(m["schema"],v2.PROTOCOL)
        self.assertIs(m["reclamationAllowed"],False)
        return m
    def refused(self,action,**kw):
        p=self.run_manager(action,**kw)
        self.assertNotEqual(p.returncode,0)
        self.assertEqual(p.stdout,"")
    def test_missing_then_explicit_build_and_read(self):
        self.assertEqual(self.accepted("lookup")["status"],"MISSING")
        self.assertFalse(self.cache.exists())
        ready=self.accepted("build")
        self.assertEqual(ready["status"],"READY")
        self.assertEqual(ready,v2.lookup(self.repo,self.cache))
        self.assertEqual(ready,self.accepted("lookup"))
        self.assertEqual(ready,self.accepted("build"))
        directory=Path(ready["directory"])
        self.assertEqual(directory,(self.cache/v2.ROOT_NAME/ready["repoId"]/ready["key"]))
        self.assertEqual((ready["device"],ready["inode"]),
                         (str(directory.stat().st_dev),str(directory.stat().st_ino)))
        p=subprocess.run([sys.executable,"-I","-B",str(ROOT/"scripts/git_map_v2_reader_candidate.py"),
            "--base",str(self.cache),"--device",ready["device"],"--inode",ready["inode"],
            "page",ready["repoId"],ready["key"],ready["manifest"]["snapshot"],"0"],
            env=self.env,capture_output=True,text=True,timeout=5)
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertEqual(json.loads(p.stdout)["result"]["total"],1)
        self.assertFalse((self.cache/"post-apollo-git-map-v1").exists())
    def test_v1_not_reused_and_fault_not_rebuilt(self):
        old=v1.build(self.repo,self.cache/"post-apollo-git-map-v1")
        db=Path(old["directory"])/index.NAME
        digest=hashlib.sha256(db.read_bytes()).hexdigest()
        self.assertEqual(self.accepted("lookup")["status"],"MISSING")
        ready=self.accepted("build")
        path=Path(ready["directory"])
        (path/v2.NAME).rename(path/"fixture-displaced")
        self.refused("lookup")
        self.refused("build")
        self.assertFalse((path/v2.NAME).exists())
        self.assertEqual(hashlib.sha256(db.read_bytes()).hexdigest(),digest)
    def test_disabled_and_noncanonical_refused(self):
        self.refused("lookup",env=dict(self.env,POST_APOLLO_GIT_MAP_SMOKE=""))
        self.refused("build",env=dict(self.env,POST_APOLLO_GIT_MAP_SMOKE=""))
        self.refused("build",base="relative")
        self.refused("build",repo="relative")
        link=self.base/"alias"
        link.symlink_to(self.repo,target_is_directory=True)
        self.refused("build",repo=link)
        self.assertFalse(self.cache.exists())
if __name__=="__main__":
    unittest.main()
