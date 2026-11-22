#!/usr/bin/env python3
"""FP1k.N1: distinguish a missing 100% default from a persisted preference.

Only disposable XDG_DATA_HOME locations are touched. No real financial data.
"""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[2]
SCRIPT=ROOT/"scripts/finance/household_reserve_preference_store.py"
spec=importlib.util.spec_from_file_location("reserve_provenance",SCRIPT)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class SavedProvenance(unittest.TestCase):
    def setUp(self):
        self.sandbox=tempfile.TemporaryDirectory()
        self.addCleanup(self.sandbox.cleanup)
        self.root=Path(self.sandbox.name)
        self.directory=self.root/"post-apollo"/"finance"/"household-reserve-preferences"
    def invoke(self,context="mine",action="list",percent=None,revision=None):
        command={"action":action,"contextId":context}
        if action!="list": command["expectedRevision"]=revision
        if percent is not None: command["marginPercent"]=percent
        env=dict(os.environ,XDG_DATA_HOME=str(self.root))
        p=subprocess.run([sys.executable,"-B",str(SCRIPT)],
            input=json.dumps(command)+"\n",text=True,env=env,
            stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=10)
        if p.returncode:
            return {"ok":False,"error":p.stderr}
        self.assertTrue(p.stdout.startswith("FINANCEW_RESERVE_PREF_RESULT "))
        return {"ok":True,**json.loads(p.stdout.split("RESULT ",1)[1])}
    def test_missing_file_reports_unsaved_default_and_no_write(self):
        result=self.invoke()
        self.assertTrue(result["ok"])
        self.assertFalse(result["savedOnDisk"])
        self.assertEqual(result["marginPercent"],100)
        self.assertEqual(result["revision"],0)
        self.assertFalse(self.directory.exists())
    def test_explicit_100_save_is_saved_not_synthetic(self):
        result=self.invoke(action="save",percent=100,revision=0)
        self.assertTrue(result["ok"])
        self.assertTrue(result["savedOnDisk"])
        self.assertEqual(result["marginPercent"],100)
        self.assertEqual(result["revision"],1)
        record=json.loads((self.directory/"mine.json").read_text())
        self.assertEqual(set(record),{"version","contextId","revision","marginPercent"})
        self.assertNotIn("savedOnDisk",record)
        second=self.invoke()
        self.assertTrue(second["savedOnDisk"])
        self.assertEqual(second["marginPercent"],100)
    def test_saved_125_and_reset_stay_saved(self):
        saved=self.invoke(action="save",percent=125,revision=0)
        self.assertTrue(saved["savedOnDisk"])
        self.assertEqual(saved["marginPercent"],125)
        reset=self.invoke(action="reset",revision=1)
        self.assertTrue(reset["savedOnDisk"])
        self.assertEqual(reset["marginPercent"],100)
        self.assertEqual(reset["revision"],2)
    def test_context_isolation_and_missing_other_context(self):
        self.invoke(action="save",percent=110,revision=0,context="mine")
        family=self.invoke(context="family")
        self.assertFalse(family["savedOnDisk"])
        self.assertEqual(family["marginPercent"],100)
        self.assertFalse((self.directory/"family.json").exists())
        self.assertTrue(self.invoke()["savedOnDisk"])
        self.assertEqual(self.invoke()["marginPercent"],110)
    def test_forged_revision_zero_on_disk_refused_and_unchanged(self):
        self.invoke(action="save",percent=125,revision=0)
        path=self.directory/"mine.json"
        record=json.loads(path.read_text())
        record["revision"]=0
        path.write_text(json.dumps(record))
        before=path.read_bytes()
        self.assertFalse(self.invoke()["ok"])
        self.assertIn("INVALID_STORE",self.invoke()["error"])
        self.assertFalse(self.invoke(action="save",percent=110,revision=0)["ok"])
        self.assertEqual(path.read_bytes(),before)
    def test_forbid_fake_output_key_in_local_document(self):
        self.invoke(action="save",percent=110,revision=0)
        path=self.directory/"mine.json"
        record=json.loads(path.read_text())
        record["savedOnDisk"]=False
        path.write_text(json.dumps(record))
        before=path.read_bytes()
        self.assertFalse(self.invoke()["ok"])
        self.assertIn("INVALID_STORE",self.invoke()["error"])
        self.assertEqual(path.read_bytes(),before)

if __name__=="__main__":
    unittest.main()
