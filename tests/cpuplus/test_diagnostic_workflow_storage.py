import copy
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/"scripts"))
import cpuplus_diagnostic_workflow_catalog as store


def document():
    return {"schema":store.SCHEMA,"nextId":2,"rows":[
        {"id":"user-1","name":"My threads","favorite":True,"execution":"configured",
         "plan":{"durationSeconds":30,"instruments":[{"kind":"threads","intervalMs":1000,"topCount":4}]}},
        {"id":"default-appcontrol","name":"APPCONTROL TEST","favorite":True,
         "execution":"fixed","kind":"appcontrol"}]}


class CatalogStorageTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name)
        self.folder=self.root/"catalog"

    def load(self):
        return store.execute(self.folder,{"action":"load"})

    def save(self,doc,expected=None):
        return store.execute(self.folder,{"action":"save","expected":expected,"document":doc})

    def test_missing_roundtrip_and_private_modes(self):
        self.assertEqual(self.load(),{"status":"MISSING","document":None})
        self.assertFalse(self.folder.exists())
        doc=document()
        self.assertEqual(self.save(doc),{"status":"SAVED","document":doc})
        self.assertEqual(self.load(),{"status":"LOADED","document":doc})
        self.assertEqual(self.folder.stat().st_mode&0o777,0o700)
        for name in ("workflows.json","workflows.lock"):
            self.assertEqual((self.folder/name).stat().st_mode&0o777,0o600)

    def test_empty_not_missing_and_counter(self):
        doc=document()
        self.save(doc)
        empty=dict(doc,rows=[])
        self.save(empty,doc)
        self.assertEqual(self.load(),{"status":"LOADED","document":empty})
        with self.assertRaises(ValueError):
            self.save(dict(empty,nextId=1),empty)

    def test_stale_save_conflict(self):
        first=document()
        self.save(first)
        second=copy.deepcopy(first)
        second["rows"][0]["favorite"]=False
        self.save(second,first)
        self.assertEqual(self.save(first,first),{"status":"CONFLICT","document":second})
        self.assertEqual(self.save(first),{"status":"CONFLICT","document":second})
        self.assertEqual(self.load()["document"],second)

    def test_malformed_refused_without_overwrite(self):
        doc=document()
        self.save(doc)
        for field,value in (("favorite","yes"),("id","user-2"),("argv",["/bin/sh"])):
            bad=copy.deepcopy(doc)
            bad["rows"][0][field]=value
            with self.assertRaises(ValueError):
                self.save(bad,doc)
        bad=copy.deepcopy(doc)
        bad["rows"][1]["kind"]="threads"
        with self.assertRaises(ValueError):
            self.save(bad,doc)
        bad=copy.deepcopy(doc)
        bad["rows"][0]["plan"]["instruments"][0]["intervalMs"]=100
        with self.assertRaises(ValueError):
            self.save(bad,doc)
        self.assertEqual(self.load()["document"],doc)

    def test_target_metadata_preserved_and_invalid_scope_refused(self):
        legacy=document()
        self.save(legacy)
        selected=copy.deepcopy(legacy)
        selected["rows"][0]["targetId"]="quickshell"
        self.assertEqual(self.save(selected,legacy)["status"],"SAVED")
        self.assertEqual(self.load()["document"],selected)
        for target in ("automatic","host-cpu","process-instance","unknown",123):
            bad=copy.deepcopy(selected)
            bad["rows"][0]["targetId"]=target
            with self.assertRaises(ValueError):
                self.save(bad,selected)
        bad=copy.deepcopy(selected)
        bad["rows"][1]["targetId"]="appcontrol"
        with self.assertRaises(ValueError):
            self.save(bad,selected)
        self.assertEqual(self.load()["document"],selected)

    def test_corrupt_and_duplicate_keys(self):
        doc=document()
        self.save(doc)
        path=self.folder/"workflows.json"
        path.write_text('{"schema":"bad","schema":"other"}')
        old=path.read_bytes()
        with self.assertRaises(ValueError):
            self.save(doc,doc)
        self.assertEqual(path.read_bytes(),old)

    def test_symlink_fifo_and_mode_refusal(self):
        doc=document()
        self.save(doc)
        path=self.folder/"workflows.json"
        outside=self.root/"outside"
        outside.write_text("unchanged")
        path.unlink()
        path.symlink_to(outside)
        with self.assertRaises(OSError):
            self.load()
        self.assertEqual(outside.read_text(),"unchanged")
        path.unlink()
        os.mkfifo(path,0o600)
        with self.assertRaises(ValueError):
            self.load()
        path.unlink()
        path.write_text(json.dumps(doc))
        path.chmod(0o644)
        with self.assertRaises(ValueError):
            self.load()

    def test_interrupted_replace_and_staging_recovery(self):
        doc=document()
        self.save(doc)
        changed=dict(doc,rows=[])
        with patch.object(store.os,"replace",side_effect=OSError("fixture")):
            with self.assertRaises(OSError):
                self.save(changed,doc)
        self.assertEqual(self.load()["document"],doc)
        pending=self.folder/".workflows.pending"
        pending.write_bytes(b"interrupted")
        pending.chmod(0o600)
        self.save(changed,doc)
        self.assertFalse(pending.exists())
        self.assertEqual(self.load()["document"],changed)


if __name__=="__main__":
    unittest.main()
