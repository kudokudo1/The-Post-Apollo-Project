#!/usr/bin/env python3
import hashlib
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"scripts"))
import git_map_history_index as index
import git_map_incremental_candidate as candidate


class PrefixReuseTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.base=Path(temp.name)
        self.repo=self.base/"repo"
        self.repo.mkdir()
        self.git("init","-b","main")

    def git(self,*args):
        return subprocess.check_output(["/usr/bin/git","-C",str(self.repo),
            "-c","user.name=Fixture","-c","user.email=fixture@example.invalid",*args],
            stderr=subprocess.DEVNULL,text=True).strip()

    def commit(self,subject):
        self.git("commit","--allow-empty","-m",subject)
        return self.git("rev-parse","HEAD")

    def compare(self,actual,expected):
        with index.open_index(actual) as a,index.open_index(expected) as b:
            ma,mb=index.manifest_for(a),index.manifest_for(b)
            self.assertEqual({k:v for k,v in ma.items() if k!="snapshot"},
                             {k:v for k,v in mb.items() if k!="snapshot"})
            for start in range(0,ma["total"],index.PAGE):
                pa=index.page(a,ma["snapshot"],start)
                pb=index.page(b,mb["snapshot"],start)
                self.assertEqual({k:v for k,v in pa.items() if k!="snapshot"},
                                 {k:v for k,v in pb.items() if k!="snapshot"})
        a.close(); b.close()

    def test_merge_suffix_and_new_prefix_cross_page(self):
        # Real Git history, old merge lanes and shifted page boundaries.
        lines=[]
        for i in range(1,261):
            lines.extend(["commit refs/heads/main",f"mark :{i}",
                f"committer Fixture <fixture@example.invalid> {1700000000+i} +0000",
                "data 1","x"])
            if i>1: lines.append(f"from :{i-1}")
            lines.append("")
        subprocess.run(["/usr/bin/git","-C",str(self.repo),"fast-import","--quiet"],
                       input=("\n".join(lines)+"\n").encode(),check=True,capture_output=True)
        self.git("reset","--hard","HEAD")
        self.git("branch","side")
        self.commit("main")
        self.git("checkout","side")
        self.commit("side")
        self.git("checkout","main")
        self.git("merge","--no-ff","side","-m","merge")
        old=self.base/"old"
        old_manifest=index.build(self.repo,old)
        digest=hashlib.sha256((old/index.NAME).read_bytes()).hexdigest()
        for i in range(3): self.commit("new "+str(i))
        incremental=self.base/"incremental"
        fresh=self.base/"fresh"
        head=self.git("rev-parse","HEAD")
        state=self.git("status","--porcelain")
        started=time.monotonic()
        result=candidate.build(self.repo,old,incremental)
        reuse_ms=round((time.monotonic()-started)*1000)
        started=time.monotonic()
        index.build(self.repo,fresh)
        full_ms=round((time.monotonic()-started)*1000)
        self.assertEqual(result["prefixRows"],3)
        self.assertEqual(result["reusedRows"],old_manifest["total"])
        self.compare(incremental,fresh)
        self.assertEqual(hashlib.sha256((old/index.NAME).read_bytes()).hexdigest(),digest)
        self.assertEqual(self.git("rev-parse","HEAD"),head)
        self.assertEqual(self.git("status","--porcelain"),state)
        print(f"Prefix reuse/full rebuild exact page parity; fixture ms {reuse_ms}/{full_ms}")

    def test_rewrite_and_no_new_rows_refused(self):
        base=self.commit("base")
        self.commit("old")
        old=self.base/"old"
        index.build(self.repo,old)
        for name in ("same","rewrite"):
            if name=="rewrite":
                self.git("reset","--hard",base)
                self.commit("replacement")
            dest=self.base/name
            with self.assertRaises(candidate.ReuseRefused):
                candidate.build(self.repo,old,dest)
            self.assertFalse((dest/index.NAME).exists())

    def test_stale_or_changed_suffix_refused(self):
        self.commit("base")
        old=self.base/"old"
        index.build(self.repo,old)
        self.commit("new")
        roots=index.roots_for(self.repo)
        rows=list(index.log_rows(self.repo,roots))
        last=rows[-1]
        rows[-1]=(*last[:-1],"changed metadata")
        dest=self.base/"changed"
        with patch.object(index,"log_rows",side_effect=lambda *args:(r for r in rows)):
            with self.assertRaises(candidate.ReuseRefused):
                candidate.build(self.repo,old,dest)
        self.assertFalse((dest/index.NAME).exists())

    def test_changed_roots_after_proof_refused(self):
        self.commit("base")
        old=self.base/"old"
        index.build(self.repo,old)
        self.commit("new")
        roots=index.roots_for(self.repo)
        dest=self.base/"stale"
        with patch.object(index,"roots_for",side_effect=[roots,["f"*40]]):
            with self.assertRaises(candidate.ReuseRefused):
                candidate.build(self.repo,old,dest)
        self.assertFalse((dest/index.NAME).exists())

if __name__=="__main__":
    unittest.main()
