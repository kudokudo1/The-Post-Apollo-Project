#!/usr/bin/env python3
"""FP1g tests: explicit deferral is versioned and never a bank payment."""
import importlib.util
import json
import stat
import tempfile
import unittest
from pathlib import Path

path=Path(__file__).resolve().parents[2]/"scripts/finance/household_schedule_store.py"
spec=importlib.util.spec_from_file_location("fp1g_schedule",path)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class DeferredBill(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory=Path(self.temp.name)/"schedules"
        self.expense="p-"+"a"*32
        self.other="p-"+"b"*32
    def op(self,action="list",ctx="mine",rev=0,**kw):
        return m.run(self.directory,{"action":action,"contextId":ctx,
            **({} if action=="list" else {"expectedRevision":rev}),**kw})
    def bill(self,rev=0):
        return self.op("add_bill",rev=rev,expenseId=self.expense,dueDay=28)
    def defer(self,rev=1,original="2026-11",target="2026-12-18"):
        return self.op("add_defer",rev=rev,expenseId=self.expense,
            sourceMonth=original,targetDate=target)
    def test_read_v2_unchanged_then_explicit_v3_write(self):
        self.assertEqual(self.op()["version"],2)
        self.assertFalse(self.directory.exists())
        base=self.bill()
        self.assertEqual(base["version"],2)
        path=self.directory/"mine.json"
        prior=path.read_bytes()
        self.assertEqual(self.op()["version"],2)
        self.assertEqual(path.read_bytes(),prior)
        updated=self.defer()
        self.assertEqual(updated["version"],3)
        self.assertEqual(updated["revision"],2)
        self.assertEqual(updated["rows"][0]["id"],base["rows"][0]["id"])
        self.assertEqual(updated["rows"][0]["sourceMonth"],"")
        self.assertEqual(updated["rows"][1]["sourceMonth"],"2026-11")
        self.assertEqual(updated["rows"][1]["date"],"2026-12-18")
        self.assertEqual(json.loads(path.read_text())["version"],3)
        self.assertEqual(stat.S_IMODE(path.stat().st_mode),0o600)
        self.assertEqual(self.op()["rows"],updated["rows"])
        self.assertEqual(self.op(ctx="mom")["rows"],[])
    def test_revision_duplicates_and_expense_custody(self):
        base=self.bill()
        moved=self.defer()
        did=moved["rows"][1]["id"]
        for source,target in [("2026-11","2026-12-20"),("2026-11","2027-02-01")]:
            with self.assertRaises(m.Refusal):self.defer(rev=2,original=source,target=target)
        with self.assertRaises(m.Refusal):
            self.op("add_skip",rev=2,expenseId=self.expense,month="2026-11")
        with self.assertRaises(m.Refusal):
            self.op("update_bill",rev=2,id=base["rows"][0]["id"],
                expenseId=self.other,dueDay=1)
        with self.assertRaises(m.Refusal):
            self.op("delete",rev=2,id=base["rows"][0]["id"])
        changed=self.op("update_defer",rev=2,id=did,
            expenseId=self.expense,sourceMonth="2027-01",targetDate="2027-03-15")
        self.assertEqual(changed["rows"][1]["id"],did)
        self.assertEqual(changed["rows"][1]["sourceMonth"],"2027-01")
        self.assertEqual(changed["rows"][1]["date"],"2027-03-15")
        with self.assertRaises(m.Refusal):self.defer(rev=2)
        removed=self.op("delete",rev=3,id=did)
        self.assertEqual(len(removed["rows"]),1)
        self.assertEqual(self.op("delete",rev=4,id=base["rows"][0]["id"])["rows"],[])
    def test_invalid_move_never_overwrites(self):
        self.bill()
        before=(self.directory/"mine.json").read_bytes()
        cases=[("2026-11","2026-11-30"),("2026-11","2026-10-20"),
               ("2026-11","2027-02-30"),("2026-13","2027-01-01"),
               ("../secrets","2027-01-01"),("2026-11","2026-12-00")]
        for source,target in cases:
            with self.assertRaises(m.Refusal):
                self.defer(original=source,target=target)
        with self.assertRaises(m.Refusal):
            self.op("add_defer",rev=1,expenseId=self.expense,
                sourceMonth="2026-11",targetDate="2027-01-10",unsafe=True)
        with self.assertRaises(m.Refusal):
            self.op("add_defer",rev=1,expenseId=self.other,
                sourceMonth="2026-11",targetDate="2027-01-10")
        self.assertEqual((self.directory/"mine.json").read_bytes(),before)
    def test_v1_legacy_upgrade_only_on_explicit_defer(self):
        self.directory.mkdir(mode=0o700)
        old={"version":1,"contextId":"mine","revision":9,
             "rows":[{"id":"p-"+"d"*32,"kind":"bill_due","title":"",
             "expenseId":self.expense,"dueDay":20,"date":"",
             "amountCents":0,"fundingGoalId":""}]}
        file=self.directory/"mine.json"
        file.write_text(json.dumps(old)+"\n")
        file.chmod(0o600)
        before=file.read_bytes()
        read=self.op()
        self.assertEqual(read["version"],2)
        self.assertEqual(file.read_bytes(),before)
        changed=self.defer(rev=9)
        self.assertEqual(changed["version"],3)
        self.assertEqual(changed["revision"],10)
        self.assertEqual(changed["rows"][0]["dueDay"],20)
        self.assertEqual(changed["rows"][0]["sourceMonth"],"")
    def test_corrupt_new_schema_is_hold(self):
        self.bill()
        self.defer()
        path=self.directory/"mine.json"
        stored=json.loads(path.read_text())
        stored["rows"][1]["sourceMonth"]="2028-15"
        path.write_text(json.dumps(stored))
        corrupt=path.read_bytes()
        with self.assertRaises(m.Refusal):self.op()
        with self.assertRaises(m.Refusal):
            self.op("add_bill",rev=2,expenseId=self.other,dueDay=10)
        self.assertEqual(path.read_bytes(),corrupt)
if __name__=="__main__":
    unittest.main()
