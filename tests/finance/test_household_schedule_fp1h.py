#!/usr/bin/env python3
"""FP1h: disposable v4 cadence storage, migration and refusal tests."""
import importlib.util
import json
import stat
import tempfile
import unittest
from pathlib import Path

path=Path(__file__).resolve().parents[2]/"scripts/finance/household_schedule_store.py"
spec=importlib.util.spec_from_file_location("fp1h_schedule",path)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class Cadence(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.directory=Path(self.tmp.name)/"schedules"
        self.expense="p-"+"a"*32
        self.second="p-"+"b"*32
    def op(self,action="list",revision=0,context="mine",**fields):
        command={"action":action,"contextId":context}
        if action!="list": command["expectedRevision"]=revision
        command.update(fields)
        return m.run(self.directory,command)
    def bill(self,revision=0,expense=None):
        return self.op("add_bill",revision=revision,
                       expenseId=expense or self.expense,dueDay=31)
    def cadence(self,revision=1,expense=None,months=3,anchor="2026-11"):
        return self.op("add_cadence",revision=revision,
                       expenseId=expense or self.expense,
                       intervalMonths=months,anchorMonth=anchor)

    def test_v2_read_unchanged_and_explicit_quarterly_migration(self):
        self.assertEqual(self.op()["version"],2)
        self.assertFalse(self.directory.exists())
        bill=self.bill()
        path=self.directory/"mine.json"
        data=path.read_bytes()
        self.assertEqual(self.op()["version"],2)
        self.assertEqual(path.read_bytes(),data)
        doc=self.cadence()
        self.assertEqual(doc["version"],4)
        self.assertEqual(doc["revision"],2)
        self.assertEqual(doc["rows"][0]["id"],bill["rows"][0]["id"])
        self.assertEqual(doc["rows"][0]["sourceMonth"],"")
        self.assertEqual(doc["rows"][1]["intervalMonths"],3)
        self.assertEqual(doc["rows"][1]["anchorMonth"],"2026-11")
        self.assertEqual(json.loads(path.read_text())["version"],4)
        self.assertEqual(stat.S_IMODE(path.stat().st_mode),0o600)
        self.assertEqual(stat.S_IMODE(self.directory.stat().st_mode),0o700)
        self.assertEqual(self.op()["rows"],doc["rows"])
        self.assertEqual(self.op(context="granny")["rows"],[])

    def test_v3_existing_deferral_remains_compatible(self):
        self.bill()
        initial=self.op("add_defer",revision=1,expenseId=self.expense,
                        sourceMonth="2027-02",targetDate="2027-03-10")
        self.assertEqual(initial["version"],3)
        previous=(self.directory/"mine.json").read_bytes()
        self.assertEqual(self.op()["version"],3)
        self.assertEqual((self.directory/"mine.json").read_bytes(),previous)
        scheduled=self.cadence(revision=2)
        self.assertEqual(scheduled["version"],4)
        self.assertEqual(scheduled["rows"][1]["sourceMonth"],"2027-02")
        self.assertEqual(scheduled["rows"][2]["intervalMonths"],3)
        deferred=self.op("add_defer",revision=3,expenseId=self.expense,
                         sourceMonth="2027-05",targetDate="2027-06-10")
        self.assertEqual(deferred["version"],4)
        self.assertEqual(deferred["rows"][-1]["sourceMonth"],"2027-05")

    def test_legacy_v1_no_read_rewrite(self):
        self.directory.mkdir(mode=0o700)
        old={"version":1,"contextId":"mine","revision":7,"rows":[{
            "id":"p-"+"c"*32,"kind":"bill_due","title":"","expenseId":self.expense,
            "dueDay":31,"date":"","amountCents":0,"fundingGoalId":""}]}
        file=self.directory/"mine.json"
        file.write_text(json.dumps(old)+"\n")
        file.chmod(0o600)
        before=file.read_bytes()
        self.assertEqual(self.op()["version"],2)
        self.assertEqual(file.read_bytes(),before)
        upgraded=self.cadence(revision=7,months=12,anchor="2027-03")
        self.assertEqual(upgraded["version"],4)
        self.assertEqual(upgraded["rows"][0]["sourceMonth"],"")
        self.assertEqual(upgraded["rows"][1]["intervalMonths"],12)

    def test_invalid_frequency_and_conflicting_occurrences_are_refused(self):
        self.bill()
        baseline=(self.directory/"mine.json").read_bytes()
        for months in (0,1,2,6,13,True,3.0,"3"):
            with self.assertRaises(m.Refusal):
                self.cadence(months=months)
        for anchor in ("2026-13","2026-00","bad","2026-11-01","../secrets"):
            with self.assertRaises(m.Refusal):
                self.cadence(anchor=anchor)
        with self.assertRaises(m.Refusal):
            self.cadence(expense=self.second)
        self.assertEqual((self.directory/"mine.json").read_bytes(),baseline)
        saved=self.cadence()
        cadence_id=saved["rows"][1]["id"]
        with self.assertRaises(m.Refusal):
            self.cadence(revision=2,anchor="2027-02")
        with self.assertRaises(m.Refusal):
            self.op("add_skip",revision=2,expenseId=self.expense,month="2026-12")
        with self.assertRaises(m.Refusal):
            self.op("add_defer",revision=2,expenseId=self.expense,
                    sourceMonth="2026-12",targetDate="2027-01-17")
        with self.assertRaises(m.Refusal):
            self.op("update_bill",revision=2,id=saved["rows"][0]["id"],
                    expenseId=self.second,dueDay=15)
        with self.assertRaises(m.Refusal):
            self.op("delete",revision=2,id=saved["rows"][0]["id"])
        accepted=self.op("add_skip",revision=2,expenseId=self.expense,month="2027-02")
        with self.assertRaises(m.Refusal):
            self.op("update_cadence",revision=3,id=cadence_id,
                    expenseId=self.expense,intervalMonths=12,
                    anchorMonth="2026-11")
        self.assertEqual(self.op()["rows"],accepted["rows"])

    def test_safe_reversal_and_v4_subsequent_operations(self):
        saved=self.bill()
        current=self.cadence()
        cadence_id=current["rows"][1]["id"]
        changed=self.op("update_cadence",revision=2,id=cadence_id,
            expenseId=self.expense,intervalMonths=12,anchorMonth="2027-01")
        self.assertEqual(changed["rows"][1]["id"],cadence_id)
        self.assertEqual(changed["rows"][1]["intervalMonths"],12)
        self.assertEqual(changed["rows"][1]["anchorMonth"],"2027-01")
        deleted=self.op("delete",revision=3,id=cadence_id)
        self.assertEqual(deleted["version"],4)
        self.assertEqual(len(deleted["rows"]),1)
        self.assertEqual(deleted["rows"][0]["id"],saved["rows"][0]["id"])
        extra=self.bill(revision=4,expense=self.second)
        self.assertEqual(extra["version"],4)
        self.assertEqual(extra["rows"][-1]["sourceMonth"],"")
        self.assertEqual(self.op("delete",revision=5,id=saved["rows"][0]["id"])["version"],4)

    def test_orphan_duplicate_and_unknown_schema_holds(self):
        self.bill()
        doc=self.cadence()
        f=self.directory/"mine.json"
        current=json.loads(f.read_text())
        current["rows"].append({**current["rows"][1],"id":"p-"+"d"*32})
        f.write_text(json.dumps(current))
        before=f.read_bytes()
        with self.assertRaises(m.Refusal): self.op()
        with self.assertRaises(m.Refusal):
            self.op("add_bill",revision=2,expenseId=self.second,dueDay=15)
        self.assertEqual(f.read_bytes(),before)
        current["rows"].pop()
        current["version"]=5
        f.write_text(json.dumps(current))
        with self.assertRaises(m.Refusal): self.op()

if __name__=="__main__":
    unittest.main()
