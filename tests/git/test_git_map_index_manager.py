#!/usr/bin/env python3
import os
import hashlib
import sqlite3
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"scripts"))
import git_map_index_manager as manager

class ManagedCacheTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base=Path(self.tmp.name)
        self.repo=self.base/"repo"
        self.repo.mkdir()
        self.root=self.base/"cache"/"map"
        self.git("init","-b","main")
        self.git("commit","--allow-empty","-m","first")

    def git(self,*args):
        return subprocess.check_output(["/usr/bin/git","-C",str(self.repo),
            "-c","user.name=Fixture","-c","user.email=fixture@example.invalid",*args],
            stderr=subprocess.DEVNULL,text=True).strip()

    def test_read_only_lookup_and_reuse(self):
        missing=manager.lookup(self.repo,self.root)
        self.assertEqual(missing["status"],"MISSING")
        self.assertFalse(self.root.exists())
        head=self.git("rev-parse","HEAD")
        before=self.git("status","--porcelain")
        ready=manager.build(self.repo,self.root)
        self.assertEqual(ready["status"],"READY")
        self.assertEqual(ready["manifest"]["total"],1)
        self.assertEqual(manager.lookup(self.repo,self.root),ready)
        with patch.object(manager.index,"build",side_effect=AssertionError("unexpected traversal")):
            self.assertEqual(manager.build(self.repo,self.root),ready)
        self.assertEqual(self.git("rev-parse","HEAD"),head)
        self.assertEqual(self.git("status","--porcelain"),before)
        self.assertEqual(Path(ready["directory"]).stat().st_mode&0o777,0o700)

    def test_new_tip_new_generation_old_preserved(self):
        old=manager.build(self.repo,self.root)
        self.git("commit","--allow-empty","-m","second")
        self.assertEqual(manager.lookup(self.repo,self.root)["status"],"MISSING")
        new=manager.build(self.repo,self.root)
        self.assertNotEqual(new["key"],old["key"])
        self.assertEqual(new["manifest"]["total"],2)
        with manager.index.open_index(old["directory"]) as conn:
            self.assertEqual(manager.index.manifest_for(conn),old["manifest"])
        with patch.object(manager,"MAX_GENERATIONS",2):
            self.git("commit","--allow-empty","-m","third")
            self.assertEqual(manager.build(self.repo,self.root)["status"],"CACHE LIMIT")
        self.assertTrue(Path(old["directory"]).exists())
        self.assertTrue(Path(new["directory"]).exists())

    def test_incomplete_and_unsafe_refuse(self):
        identity=manager.identity(self.repo)
        self.root.mkdir(parents=True,mode=0o700)
        folder=self.root/identity[0]
        folder.mkdir(mode=0o700)
        target=folder/identity[3]
        target.mkdir(mode=0o700)
        with self.assertRaises(FileNotFoundError):
            manager.lookup(self.repo,self.root)
        with self.assertRaises(FileNotFoundError):
            manager.build(self.repo,self.root)
        target.rmdir()
        target.symlink_to(self.repo,target_is_directory=True)
        with self.assertRaises(ValueError):
            manager.lookup(self.repo,self.root)
        with self.assertRaises(ValueError):
            manager.build(self.repo,self.root)

    def test_inventory_missing_never_creates_cache(self):
        result=manager.inventory(self.repo,self.root)
        self.assertEqual(result["observedSlots"],0)
        self.assertFalse(result["reclamationAllowed"])
        self.assertFalse(self.root.exists())

    def test_inventory_current_history_staging_and_unsafe(self):
        old=manager.build(self.repo,self.root)
        self.git("commit","--allow-empty","-m","second")
        current=manager.build(self.repo,self.root)
        folder=Path(current["directory"]).parent
        stage=folder/(".candidate-"+"a"*32)
        stage.mkdir(mode=0o700)
        (stage/".building.sqlite3").write_bytes(b"incomplete")
        (stage/".building.sqlite3").chmod(0o600)
        unsafe=folder/("e"*64)
        unsafe.symlink_to(self.repo,target_is_directory=True)
        incomplete=folder/("f"*64)
        incomplete.mkdir(mode=0o700)
        (folder/"unknown-entry").write_text("not a generation")
        def frozen():
            return {str(p):hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in (Path(old["directory"])/manager.index.NAME,
                              Path(current["directory"])/manager.index.NAME,
                              stage/".building.sqlite3",folder/"unknown-entry")}
        before=frozen()
        names=set(p.name for p in folder.iterdir())
        head=self.git("rev-parse","HEAD")
        state=self.git("status","--porcelain")
        result=manager.inventory(self.repo,self.root)
        rows={r["key"]:r for r in result["entries"]}
        self.assertEqual(result["observedSlots"],6)
        self.assertFalse(result["truncated"])
        self.assertEqual(rows[old["key"]]["state"],"HISTORICAL")
        self.assertEqual(rows[current["key"]]["state"],"CURRENT")
        self.assertEqual(rows[stage.name]["state"],"STAGING")
        self.assertEqual(rows[unsafe.name]["state"],"UNSAFE OR INVALID")
        self.assertEqual(rows[incomplete.name]["state"],"INCOMPLETE OR MOVED")
        self.assertEqual(rows[None]["state"],"UNKNOWN ENTRY")
        self.assertEqual(result["observedDatabaseBytes"],
                         sum(Path(p).stat().st_size for p in before if not p.endswith("unknown-entry")))
        self.assertTrue(all(row["readerStatus"]=="UNKNOWN" and not row["reclamationAllowed"]
                            for row in rows.values()))
        self.assertEqual(frozen(),before)
        self.assertEqual(set(p.name for p in folder.iterdir()),names)
        self.assertEqual(self.git("rev-parse","HEAD"),head)
        self.assertEqual(self.git("status","--porcelain"),state)
        with patch.object(manager,"MAX_INVENTORY_ENTRIES",2):
            limited=manager.inventory(self.repo,self.root)
        self.assertEqual(limited["observedSlots"],2)
        self.assertTrue(limited["truncated"])
        self.assertFalse(limited["reclamationAllowed"])

    def test_inventory_preserves_good_entries_and_refuses_malformed_manifest(self):
        old=manager.build(self.repo,self.root)
        self.git("commit","--allow-empty","-m","next")
        current=manager.build(self.repo,self.root)
        db=Path(old["directory"])/manager.index.NAME
        for value in ("[]","null","true","42",'"string"',"{"):
            with sqlite3.connect(db) as conn:
                conn.execute("UPDATE manifest SET document=?",(value,))
            conn.close()
            before=hashlib.sha256(db.read_bytes()).hexdigest()
            result=manager.inventory(self.repo,self.root)
            entries={row["key"]:row for row in result["entries"]}
            self.assertEqual(entries[old["key"]]["state"],"UNSAFE OR INVALID")
            self.assertEqual(entries[current["key"]]["state"],"CURRENT")
            self.assertFalse(result["reclamationAllowed"])
            self.assertEqual(hashlib.sha256(db.read_bytes()).hexdigest(),before)

    def test_inventory_rejects_changed_repo_identity(self):
        ident=manager.identity(self.repo)
        with patch.object(manager,"identity",side_effect=[ident,(*ident[:3],"f"*64)]):
            with self.assertRaises(ValueError):
                manager.inventory(self.repo,self.root)

    def test_shallow_deepen_changes_key_without_new_tip(self):
        for n in range(3):
            self.git("commit","--allow-empty","-m",str(n))
        clone=self.base/"shallow"
        subprocess.run(["/usr/bin/git","clone","--depth=1",self.repo.as_uri(),str(clone)],
                       check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        first=manager.identity(clone)
        subprocess.run(["/usr/bin/git","-C",str(clone),"fetch","--deepen=1"],
                       check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        second=manager.identity(clone)
        self.assertEqual(first[:3],second[:3])
        self.assertNotEqual(first[3],second[3])

if __name__=="__main__":
    unittest.main()
