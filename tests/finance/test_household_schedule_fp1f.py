#!/usr/bin/env python3
"""FP1f local scheduling upgrade, edits, exceptions and refusal coverage."""
import importlib.util
import json
from pathlib import Path
import stat
import tempfile
import unittest

path=Path(__file__).resolve().parents[2]/"scripts/finance/household_schedule_store.py"
spec=importlib.util.spec_from_file_location("fp1f_schedule",path)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class ScheduleFP1f(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory()
        self.addCleanup(self.t.cleanup)
        self.directory=Path(self.t.name)/"schedules"
        self.expense="p-"+"a"*32
        self.expense2="p-"+"b"*32
        self.goal="p-"+"c"*32
    def run_cmd(self,action,context="mine",revision=0,**fields):
        return m.run(self.directory,{"action":action,"contextId":context,
            **({} if action=="list" else {"expectedRevision":revision}),**fields})
    def add_bill(self,revision=0):
        return self.run_cmd("add_bill",revision=revision,expenseId=self.expense,dueDay=29)
    def add_skip(self,revision=1,month="2027-02",expense=None):
        return self.run_cmd("add_skip",revision=revision,
            expenseId=expense or self.expense,month=month)
    def test_v1_read_without_write_then_versioned_update(self):
        self.directory.mkdir(mode=0o700)
        id="p-"+"f"*32
        doc={"version":1,"contextId":"mine","revision":4,"rows":[{
            "id":id,"kind":"bill_due","title":"","expenseId":self.expense,
            "dueDay":15,"date":"","amountCents":0,"fundingGoalId":""}]}
        path=self.directory/"mine.json"
        path.write_text(json.dumps(doc)+"\n")
        path.chmod(0o600)
        original=path.read_bytes()
        listed=self.run_cmd("list")
        self.assertEqual(listed["version"],2)
        self.assertEqual(listed["revision"],4)
        self.assertEqual(path.read_bytes(),original)
        updated=self.run_cmd("update_bill",revision=4,
            id=id,expenseId=self.expense,dueDay=28)
        self.assertEqual(updated["rows"][0]["id"],id)
        self.assertEqual(updated["rows"][0]["dueDay"],28)
        self.assertEqual(updated["revision"],5)
        self.assertEqual(json.loads(path.read_text())["version"],2)
        self.assertEqual(stat.S_IMODE(path.stat().st_mode),0o600)
    def test_exception_and_edit_durable(self):
        bill=self.add_bill()
        id=bill["rows"][0]["id"]
        skip=self.add_skip()
        sid=skip["rows"][1]["id"]
        self.assertEqual(skip["rows"][1]["kind"],"bill_skip")
        moved=self.run_cmd("update_skip",revision=2,
            id=sid,expenseId=self.expense,month="2027-03")
        self.assertEqual(moved["rows"][1]["id"],sid)
        self.assertEqual(moved["rows"][1]["date"],"2027-03")
        self.assertEqual(self.run_cmd("list")["rows"],moved["rows"])
        with self.assertRaises(m.Refusal):
            self.add_skip(revision=3,month="2027-03")
        with self.assertRaises(m.Refusal):
            self.run_cmd("delete",revision=3,id=id)
        with self.assertRaises(m.Refusal):
            self.run_cmd("update_bill",revision=3,id=id,
                expenseId=self.expense2,dueDay=10)
        again=self.run_cmd("update_bill",revision=3,id=id,
            expenseId=self.expense,dueDay=31)
        self.assertEqual(again["rows"][0]["dueDay"],31)
        self.assertEqual(self.run_cmd("delete",revision=4,id=sid)["rows"][0]["id"],id)
        self.assertEqual(self.run_cmd("delete",revision=5,id=id)["rows"],[])
    def test_purchase_edit_and_kind_change_refused(self):
        made=self.run_cmd("add_purchase",title="Computer",date="2027-10-12",
            amountText="999.99",fundingGoalId=self.goal)
        id=made["rows"][0]["id"]
        edited=self.run_cmd("update_purchase",revision=1,id=id,title="Laptop",
            date="2027-12-01",amountText="899.50",fundingGoalId="")
        self.assertEqual(edited["rows"][0]["id"],id)
        self.assertEqual(edited["rows"][0]["amountCents"],89950)
        with self.assertRaises(m.Refusal):
            self.run_cmd("update_bill",revision=2,id=id,
                expenseId=self.expense,dueDay=15)
        with self.assertRaises(m.Refusal):
            self.run_cmd("update_purchase",revision=1,id=id,title="Laptop",
                date="2027-12-01",amountText="899.50",fundingGoalId="")
    def test_month_validation_and_no_silent_changes(self):
        bill=self.add_bill()
        before=(self.directory/"mine.json").read_bytes()
        for month in ("2027-13","2027-02-14","2027-00","bad","../social"):
            with self.assertRaises(m.Refusal):
                self.add_skip(month=month)
        with self.assertRaises(m.Refusal):
            self.add_skip(expense=self.expense2)
        with self.assertRaises(m.Refusal):
            self.run_cmd("add_skip",revision=1,expenseId=self.expense,
                month="2027-01",token="forged")
        with self.assertRaises(m.Refusal):
            self.run_cmd("update_bill",revision=1,
                id=bill["rows"][0]["id"],expenseId=self.expense,dueDay=True)
        self.assertEqual((self.directory/"mine.json").read_bytes(),before)
    def test_context_isolation_and_invalid_schema(self):
        self.add_bill()
        with self.assertRaises(m.Refusal):
            self.run_cmd("update_bill",context="mom",revision=0,
                id=self.run_cmd("list")["rows"][0]["id"],
                expenseId=self.expense,dueDay=12)
        path=self.directory/"mine.json"
        doc=json.loads(path.read_text())
        doc["version"]=99
        path.write_text(json.dumps(doc))
        data=path.read_bytes()
        with self.assertRaises(m.Refusal):
            self.run_cmd("list")
        with self.assertRaises(m.Refusal):
            self.add_skip()
        self.assertEqual(path.read_bytes(),data)

if __name__=="__main__":
    unittest.main()
