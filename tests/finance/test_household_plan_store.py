#!/usr/bin/env python3
"""FP1b isolated temporary tests: never touch real financial data."""
import importlib.util
import json
from pathlib import Path
import os
import stat
import tempfile
import unittest

path=Path(__file__).resolve().parents[2]/"scripts/finance/household_plan_store.py"
spec=importlib.util.spec_from_file_location("household_plan_store",path)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class TestStore(unittest.TestCase):
    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.dir=Path(self.temporary.name)/"plans"
    def list(self,id):
        return m.run(self.dir,{"action":"list","contextId":id})
    def add(self,id,rev=0,kind="goal",title="Car",target="12000.00",
            saved="1000.00",monthly="250.00"):
        return m.run(self.dir,{"action":"add","contextId":id,
            "expectedRevision":rev,"kind":kind,"title":title,
            "targetText":target,"savedText":saved,"monthlyText":monthly})
    def test_read_never_creates_store(self):
        self.assertEqual(self.list("mine")["revision"],0)
        self.assertFalse(self.dir.exists())
    def test_persist_and_context_separation(self):
        a=self.add("mine")
        self.assertEqual(a["revision"],1)
        self.assertEqual(a["rows"][0]["targetCents"],1200000)
        self.assertEqual(a["rows"][0]["savedCents"],100000)
        self.assertEqual(a["rows"][0]["monthlyCents"],25000)
        self.assertEqual(self.list("shared")["rows"],[])
        self.assertEqual(self.list("mom")["rows"],[])
        self.assertEqual(self.list("granny")["rows"],[])
        self.assertEqual(self.list("family")["rows"],[])
        self.assertEqual(self.list("mine")["rows"],a["rows"])
        self.assertEqual(stat.S_IMODE(self.dir.stat().st_mode),0o700)
        self.assertEqual(stat.S_IMODE((self.dir/"mine.json").stat().st_mode),0o600)
    def test_add_recurring_and_two_contexts(self):
        a=self.add("mom",kind="expense",title="Utilities",
                   target="0",saved="0",monthly="180.30")
        self.assertEqual(a["rows"][0]["monthlyCents"],18030)
        self.assertEqual(a["rows"][0]["targetCents"],0)
        self.assertEqual(self.list("mine")["rows"],[])
    def test_invalid_values_and_extra_fields(self):
        for title in ("", "Bad\nTitle", "x"*81):
            with self.assertRaises(m.Refusal):
                self.add("mine",title=title)
        for text in ("-10","1e8","15.999","$100"," 1","999999999.00"):
            with self.assertRaises(m.Refusal):
                self.add("mine",target=text)
        with self.assertRaises(m.Refusal):
            self.add("mine",saved="12001")
        with self.assertRaises(m.Refusal):
            self.add("mine",kind="expense",target="1")
        with self.assertRaises(m.Refusal):
            m.run(self.dir,{"action":"list","contextId":"mine","leak":"bad"})
        with self.assertRaises(m.Refusal):
            self.list("../social")
    def test_stale_and_delete_no_cross_context(self):
        a=self.add("mine")
        identifier=a["rows"][0]["id"]
        with self.assertRaises(m.Refusal):
            self.add("mine",rev=0)
        with self.assertRaises(m.Refusal):
            m.run(self.dir,{"action":"delete","contextId":"shared",
                "expectedRevision":0,"id":identifier})
        b=m.run(self.dir,{"action":"delete","contextId":"mine",
            "expectedRevision":1,"id":identifier})
        self.assertEqual(b["rows"],[])
        self.assertEqual(b["revision"],2)
    def test_corruption_refuses_no_overwrite(self):
        self.add("mine")
        path=self.dir/"mine.json"
        path.write_text("INVALID",encoding="utf-8")
        data=path.read_bytes()
        with self.assertRaises(m.Refusal):
            self.list("mine")
        with self.assertRaises(m.Refusal):
            self.add("mine",rev=1)
        self.assertEqual(path.read_bytes(),data)
    def test_symlink_refused(self):
        self.dir.mkdir(mode=0o700)
        target=Path(self.temporary.name)/"foreign.json"
        target.write_text("SENSITIVE")
        (self.dir/"mom.json").symlink_to(target)
        with self.assertRaises(m.Refusal):
            self.list("mom")
        with self.assertRaises(m.Refusal):
            self.add("mom")
        self.assertEqual(target.read_text(),"SENSITIVE")
    def test_unsafe_mode_refused(self):
        self.add("mine")
        (self.dir/"mine.json").chmod(0o644)
        with self.assertRaises(m.Refusal):
            self.list("mine")
        with self.assertRaises(m.Refusal):
            self.add("mine",rev=1)
    def test_duplicate_rows_refused(self):
        a=self.add("mine")
        doc=self.list("mine")
        doc["rows"].append(dict(doc["rows"][0]))
        with self.assertRaises(m.Refusal):
            m.validate(doc,"mine")

if __name__=="__main__":
    unittest.main()
