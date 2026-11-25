import hashlib
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"scripts"))
import git_map_history_index as index

def sha(i):
    return format(i+1,"040x")

def chain(count):
    for i in range(count):
        yield sha(i), [sha(i+1)] if i+1<count else [], i, "Fixture", "Commit "+str(i)

def make_index(rows):
    conn=sqlite3.connect(":memory:")
    conn.row_factory=sqlite3.Row
    index.fill(conn,rows,snapshot="a"*32,repo_id="b"*64,
               roots_digest="c"*64,shallow=False)
    return conn

class HistoryIndexTests(unittest.TestCase):
    def test_large_exact_pages_and_bottom(self):
        with make_index(chain(100000)) as conn:
            m=index.manifest_for(conn)
            self.assertEqual(m["total"],100000)
            self.assertEqual(index.page(conn,m["snapshot"],0)["rows"][0]["sha"],sha(0))
            last=index.page(conn,m["snapshot"],(99999//128)*128)
            self.assertTrue(last["end"])
            self.assertEqual(last["rows"][-1]["sha"],sha(99999))
            self.assertEqual(last["rows"][-1]["parents"],[])
            self.assertEqual(index.locate(conn,m["snapshot"],sha(50000))["ordinal"],50000)
            self.assertIsNone(index.locate(conn,m["snapshot"],"f"*40)["ordinal"])
            for start in (-128,1,100096):
                with self.assertRaises(ValueError):
                    index.page(conn,m["snapshot"],start)
            with self.assertRaises(ValueError):
                index.page(conn,"d"*32,0)

    def test_merge_frontier_across_page_boundary(self):
        def graph():
            for i in range(132):
                parents=([sha(1),sha(130)] if i==0 else
                         [sha(131)] if i in (129,130) else
                         [] if i==131 else [sha(i+1)])
                yield sha(i),parents,i,"Fixture","Merge graph"
        with make_index(graph()) as conn:
            a=index.page(conn,"a"*32,0)
            b=index.page(conn,"a"*32,128)
            edge=a["rows"][0]["parents"][1]
            self.assertEqual(edge["ordinal"],130)
            self.assertIn({"sha":sha(130),"lane":edge["lane"]},b["frontier"])
            self.assertEqual(b["rows"][2]["lane"],edge["lane"])
            self.assertEqual(b["rows"][2]["sha"],edge["sha"])

    def test_invalid_ancestry_refuses(self):
        with self.assertRaises(ValueError):
            make_index([(sha(0),[sha(1)],0,"a","b")])
        with self.assertRaises((ValueError,sqlite3.Error)):
            make_index([(sha(0),[],0,"a","b"),(sha(0),[],0,"a","b")])

    def test_actual_git_and_frozen_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo=Path(tmp)/"repo"
            repo.mkdir()
            def git(*args):
                return subprocess.run(["/usr/bin/git","-C",str(repo),"-c","user.name=Fixture",
                    "-c","user.email=fixture@example.invalid",*args],check=True,
                    stdout=subprocess.PIPE,stderr=subprocess.PIPE).stdout.decode().strip()
            git("init","-b","main")
            git("commit","--allow-empty","-m","root")
            root=git("rev-parse","HEAD")
            git("branch","side")
            git("commit","--allow-empty","-m","main")
            git("checkout","side")
            git("commit","--allow-empty","-m","side")
            git("checkout","main")
            git("merge","--no-ff","side","-m","merge")
            head=git("rev-parse","HEAD")
            before=git("status","--porcelain")
            target=Path(tmp)/"index"
            m=index.build(repo,target)
            self.assertEqual(m["total"],4)
            self.assertFalse(m["shallow"])
            self.assertEqual(git("status","--porcelain"),before)
            self.assertEqual(git("rev-parse","HEAD"),head)
            with index.open_index(target) as conn:
                p=index.page(conn,m["snapshot"],0)
                self.assertEqual(p["rows"][0]["sha"],head)
                self.assertEqual(len(p["rows"][0]["parents"]),2)
                self.assertEqual(p["rows"][-1]["sha"],root)
                self.assertTrue(p["end"])
                with self.assertRaises(sqlite3.OperationalError):
                    conn.execute("DELETE FROM commits")
            with self.assertRaises(FileExistsError):
                index.build(repo,target)
            git("commit","--allow-empty","-m","new")
            second=index.build(repo,Path(tmp)/"new-index")
            self.assertEqual(second["total"],5)
            self.assertNotEqual(second["snapshot"],m["snapshot"])
            self.assertEqual(second["repoId"],m["repoId"])
            with index.open_index(target) as conn:
                self.assertEqual(index.manifest_for(conn)["total"],4)
                self.assertEqual(index.page(conn,m["snapshot"],0)["rows"][0]["sha"],head)

    def test_build_changed_tips_not_published(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo=Path(tmp)
            target=repo/"candidate"
            with patch.object(index,"git_output",return_value=b"/fixture/.git"), \
                    patch.object(index,"shallow_for",return_value=False), \
                    patch.object(index,"roots_for",side_effect=[[sha(0)],[sha(1)]]), \
                    patch.object(index,"log_rows",return_value=chain(1)):
                with self.assertRaises(ValueError):
                    index.build(repo,target)
            self.assertFalse((target/index.NAME).exists())

if __name__=="__main__":
    unittest.main()
