#!/usr/bin/env python3
import fcntl
import hashlib
import json
import os
from pathlib import Path
import select
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"scripts"))
import git_map_isolated_candidate as v2
import git_map_index_manager as v1
import git_map_history_index as index

class Transport(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base=Path(self.tmp.name)
        self.repo=self.base/"repo"
        self.repo.mkdir()
        self.cache=self.base/"cache"
        self.git("init","-b","main")
        self.git("commit","--allow-empty","-m","first")
        self.git("commit","--allow-empty","-m","second")
        self.head=self.git("rev-parse","HEAD").decode().strip()
        self.status=self.git("status","--porcelain")
        self.old=v1.build(self.repo,self.cache/"post-apollo-git-map-v1")
        self.new=v2.build(self.repo,self.cache)
        self.path=Path(self.new["directory"])
        self.digests={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in
            (self.path/v2.NAME,Path(self.old["directory"])/index.NAME)}
        self.env=dict(os.environ,POST_APOLLO_GIT_MAP_SMOKE="CI_DISPOSABLE_ONLY")
        self.addCleanup(self.unchanged)
    def git(self,*args):
        return subprocess.check_output(["git","-C",str(self.repo),"-c","user.name=Fixture",
            "-c","user.email=fixture@example.invalid",*args],stderr=subprocess.DEVNULL)
    def unchanged(self):
        for path,digest in self.digests.items():
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),digest)
        self.assertEqual(self.git("rev-parse","HEAD").decode().strip(),self.head)
        self.assertEqual(self.git("status","--porcelain"),self.status)
    def argv(self,action,*args,receipt=None):
        r=receipt or self.new
        command=[sys.executable,"-I","-B",str(ROOT/"scripts/git_map_v2_reader_candidate.py"),
            "--base",str(self.cache)]
        if "device" in r and "inode" in r:
            command+=["--device",r["device"],"--inode",r["inode"]]
        return command+[action,r["repoId"],r["key"],r["manifest"]["snapshot"],*args]
    def finite(self,action,*args,receipt=None,env=None):
        return subprocess.run(self.argv(action,*args,receipt=receipt),env=env or self.env,
            capture_output=True,text=True,timeout=5,stdin=subprocess.DEVNULL)
    def held(self):
        p=subprocess.Popen(self.argv("hold"),env=self.env,stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        self.addCleanup(self.cleanup_process,p)
        self.assertTrue(select.select([p.stdout],[],[],5)[0],"missing hold receipt")
        m=json.loads(p.stdout.readline())
        self.assertEqual(m,{"schema":"post-apollo-git-map-reader-v2-candidate",
            "status":"HELD","repoId":self.new["repoId"],"key":self.new["key"],
            "snapshot":self.new["manifest"]["snapshot"],"reclamationAllowed":False,
            "device":self.new["device"],"inode":self.new["inode"]})
        return p
    def cleanup_process(self,p):
        if p.poll() is None: p.kill()
        p.wait(timeout=5)
        for stream in (p.stdin,p.stdout,p.stderr):
            if stream and not stream.closed: stream.close()
    def exclusive(self):
        fd=os.open(self.path,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
        try:
            try: fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError: return False
            return True
        finally: os.close(fd)
    def test_finite_payloads_and_legacy_refusal(self):
        expected={"info":self.new["manifest"],"page":None,"locate":None,"search":None}
        cases=[("info",()),("page",("0",)),("locate",(self.head,)),("search",("first","0"))]
        with v2.read(self.cache,self.new["repoId"],self.new["key"]) as (conn,m):
            expected["page"]=index.page(conn,m["snapshot"],0)
            expected["locate"]=index.locate(conn,m["snapshot"],self.head)
            expected["search"]=index.search(conn,m["snapshot"],"first",0)
        for action,args in cases:
            p=self.finite(action,*args)
            self.assertEqual(p.returncode,0,p.stderr)
            receipt=json.loads(p.stdout)
            self.assertEqual(receipt["schema"],"post-apollo-git-map-reader-v2-candidate")
            self.assertEqual(receipt["key"],self.new["key"])
            self.assertEqual(receipt["snapshot"],self.new["manifest"]["snapshot"])
            self.assertIs(receipt["reclamationAllowed"],False)
            self.assertEqual(receipt["result"],expected[action])
            self.assertEqual((receipt["device"],receipt["inode"]),(self.new["device"],self.new["inode"]))
            self.assertTrue(self.exclusive())
        p=self.finite("info",receipt=self.old)
        self.assertEqual(p.returncode,1)
        self.assertEqual(p.stdout,"")
        p=self.finite("hold")
        self.assertEqual(p.returncode,1)
        self.assertEqual(p.stdout,"")
        p=self.finite("info",env=dict(self.env,POST_APOLLO_GIT_MAP_SMOKE=""))
        self.assertEqual(p.returncode,1)
        self.assertEqual(p.stdout,"")
    def test_same_name_replacement_refuses_stale_inode(self):
        self.assertEqual((self.new["device"],self.new["inode"]),
                         (str(self.path.stat().st_dev),str(self.path.stat().st_ino)))
        wrong=dict(self.new,inode=str(int(self.new["inode"])+1))
        result=self.finite("info",receipt=wrong)
        self.assertEqual((result.returncode,result.stdout),(1,""))
        self.assertTrue(self.exclusive())
        holder=self.held()
        displaced=self.path.with_name(".fixture-displaced")
        self.path.rename(displaced)
        shutil.copytree(displaced,self.path)
        # The bytes, manifest, key and pathname all match, but the directory
        # inode is different. Do not mistake the old lock for the new path.
        self.assertNotEqual(self.path.stat().st_ino,displaced.stat().st_ino)
        for action,args in (("info",()),("page",("0",)),("locate",(self.head,)),("search",("first","0"))):
            result=self.finite(action,*args)
            self.assertEqual((result.returncode,result.stdout),(1,""))
        result=subprocess.run(self.argv("hold"),env=self.env,input="",
                              capture_output=True,text=True,timeout=5)
        self.assertEqual((result.returncode,result.stdout),(1,""))
        self.assertTrue(self.exclusive())
        fd=os.open(displaced,os.O_RDONLY|os.O_DIRECTORY)
        try:
            with self.assertRaises(BlockingIOError):
                fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
            holder.stdin.close()
            self.assertEqual(holder.wait(timeout=5),0)
            fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        finally: os.close(fd)
        fresh=v2.lookup(self.repo,self.cache)
        self.assertNotEqual(fresh["inode"],self.new["inode"])
        self.assertEqual(fresh["manifest"],self.new["manifest"])
        result=self.finite("info",receipt=fresh)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(result.stdout)["inode"],fresh["inode"])
    def test_concurrent_process_lifetimes_and_conflict(self):
        a=self.held()
        b=self.held()
        self.assertFalse(self.exclusive())
        self.assertEqual(self.finite("page","0").returncode,0)
        a.kill()
        a.wait(timeout=5)
        self.assertFalse(self.exclusive())
        b.stdin.close()
        self.assertEqual(b.wait(timeout=5),0)
        self.assertTrue(self.exclusive())
        fd=os.open(self.path,os.O_RDONLY|os.O_DIRECTORY)
        try:
            fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
            self.assertEqual(self.finite("info").returncode,1)
            p=subprocess.run(self.argv("hold"),env=self.env,input="",
                capture_output=True,text=True,timeout=5)
            self.assertEqual(p.returncode,1)
            self.assertEqual(p.stdout,"")
        finally: os.close(fd)
        c=self.held()
        c.stdin.write("x")
        c.stdin.flush()
        self.assertEqual(c.wait(timeout=5),1)
        self.assertTrue(self.exclusive())

if __name__=="__main__":
    unittest.main()
