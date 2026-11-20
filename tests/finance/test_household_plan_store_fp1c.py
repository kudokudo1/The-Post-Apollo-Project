#!/usr/bin/env python3
"""FP1c: v1->v2 compatible household plans, tested only with temp files."""
import importlib.util
import json
import stat
import tempfile
import unittest
from pathlib import Path

path=Path(__file__).resolve().parents[2]/"scripts/finance/household_plan_store.py"
spec=importlib.util.spec_from_file_location("fp1c_household",path)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class Planning(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory()
        self.addCleanup(self.t.cleanup)
        self.directory=Path(self.t.name)/"household-plans"
    def list(self,ctx="mine"):
        return m.run(self.directory,{"action":"list","contextId":ctx})
    def create(self,kind="goal",ctx="mine",revision=0,deadline="",title="Car",
               target="6000",saved="200",monthly="100"):
        return m.run(self.directory,{"action":"add","contextId":ctx,
            "expectedRevision":revision,"kind":kind,"title":title,
            "targetText":target,"savedText":saved,"monthlyText":monthly,
            "deadlineMonth":deadline})
    def update(self,id,kind="goal",ctx="mine",revision=1,
               deadline="2027-11",title="New car",target="8000",
               saved="300",monthly="200"):
        return m.run(self.directory,{"action":"update","contextId":ctx,
            "expectedRevision":revision,"id":id,"kind":kind,"title":title,
            "targetText":target,"savedText":saved,"monthlyText":monthly,
            "deadlineMonth":deadline})
    def test_income_expense_goal_contexts_and_updates(self):
        goal=self.create(deadline="2028-06")
        self.assertEqual(goal["version"],2)
        ident=goal["rows"][0]["id"]
        changed=self.update(ident)
        self.assertEqual(changed["rows"][0]["id"],ident)
        self.assertEqual(changed["rows"][0]["deadlineMonth"],"2027-11")
        self.assertEqual(changed["rows"][0]["monthlyCents"],20000)
        self.assertEqual(self.list()["rows"],changed["rows"])
        income=self.create("income","mom",0,"","Paycheck","0","0","3000.20")
        self.assertEqual(income["rows"][0]["monthlyCents"],300020)
        expense=self.create("expense","shared",0,"","Rent","0","0","800")
        self.assertEqual(expense["rows"][0]["kind"],"expense")
        self.assertEqual(self.list("granny")["rows"],[])
        self.assertEqual(self.list("family")["rows"],[])
    def test_invalid_updates_refuse_without_mutating(self):
        goal=self.create()
        before=(self.directory/"mine.json").read_bytes()
        ident=goal["rows"][0]["id"]
        with self.assertRaises(m.Refusal):
            self.update(ident,revision=0)
        with self.assertRaises(m.Refusal):
            self.update(ident,kind="expense",target="0",saved="0")
        with self.assertRaises(m.Refusal):
            self.update(ident,deadline="2027-00")
        with self.assertRaises(m.Refusal):
            self.update("p-"+"f"*32)
        with self.assertRaises(m.Refusal):
            self.update(ident,ctx="mom",revision=0)
        self.assertEqual(before,(self.directory/"mine.json").read_bytes())
    def test_read_only_v1_projection_then_upgraded_write(self):
        self.directory.mkdir(mode=0o700)
        ident="p-"+"d"*32
        original={"version":1,"contextId":"mine","revision":4,
            "rows":[{"id":ident,"kind":"goal","title":"Emergency",
                "targetCents":200000,"savedCents":50000,"monthlyCents":10000}]}
        path=self.directory/"mine.json"
        path.write_text(json.dumps(original)+"\n",encoding="utf-8")
        path.chmod(0o600)
        before=path.read_bytes()
        viewed=self.list()
        self.assertEqual(viewed["version"],2)
        self.assertEqual(viewed["rows"][0]["deadlineMonth"],"")
        self.assertEqual(path.read_bytes(),before)
        changed=self.update(ident,revision=4,deadline="2028-10",
            title="Emergency",target="3000",saved="500",monthly="120")
        self.assertEqual(changed["revision"],5)
        self.assertEqual(json.loads(path.read_text())["version"],2)
        self.assertEqual(stat.S_IMODE(path.stat().st_mode),0o600)
    def test_unsupported_schema_is_not_overwritten(self):
        self.directory.mkdir(mode=0o700)
        path=self.directory/"mine.json"
        path.write_text('{"version":999,"contextId":"mine","revision":0,"rows":[]}')
        path.chmod(0o600)
        before=path.read_bytes()
        with self.assertRaises(m.Refusal):
            self.list()
        with self.assertRaises(m.Refusal):
            self.create()
        self.assertEqual(path.read_bytes(),before)
    def test_extra_fields_and_income_deadline_refused(self):
        income=self.create("income",target="0",saved="0",monthly="500")
        ident=income["rows"][0]["id"]
        with self.assertRaises(m.Refusal):
            self.update(ident,kind="income",revision=1,target="0",saved="0",
                monthly="700",deadline="2027-10")
        with self.assertRaises(m.Refusal):
            m.run(self.directory,{"action":"update","contextId":"mine",
                "expectedRevision":1,"id":ident,"kind":"income",
                "title":"Pay","targetText":"0","savedText":"0",
                "monthlyText":"700","deadlineMonth":"","token":"forged"})
        self.assertEqual(self.list()["rows"][0]["monthlyCents"],50000)

if __name__=="__main__":
    unittest.main()
