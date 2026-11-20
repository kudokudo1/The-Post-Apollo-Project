#!/usr/bin/env python3
"""FP1e disposable tests, no real FinanceW files or bank data."""
import importlib.util
import json
from pathlib import Path
import stat
import tempfile
import unittest

module=Path(__file__).resolve().parents[2]/"scripts/finance/household_schedule_store.py"
spec=importlib.util.spec_from_file_location("household_schedule_store",module)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class Schedule(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/"schedules"
        self.expense="p-"+"a"*32
        self.goal="p-"+"b"*32
    def list(self,context="mine"):
        return m.run(self.path,{"action":"list","contextId":context})
    def bill(self,rev=0,context="mine",day=31,expense=None):
        return m.run(self.path,{"action":"add_bill","contextId":context,
            "expectedRevision":rev,"expenseId":self.expense if expense is None else expense,
            "dueDay":day})
    def purchase(self,rev=0,context="mine",date="2027-01-15",
                 title="Laptop",amount="800.75",goal=""):
        return m.run(self.path,{"action":"add_purchase","contextId":context,
            "expectedRevision":rev,"date":date,"title":title,
            "amountText":amount,"fundingGoalId":goal})
    def test_no_create_on_read_and_context_separation(self):
        self.assertEqual(self.list()["rows"],[])
        self.assertFalse(self.path.exists())
        one=self.bill()
        self.assertEqual(one["rows"][0]["amountCents"],0)
        self.assertEqual(one["rows"][0]["dueDay"],31)
        two=self.purchase(rev=1,goal=self.goal)
        self.assertEqual(two["rows"][1]["amountCents"],80075)
        self.assertEqual(two["rows"][1]["fundingGoalId"],self.goal)
        self.assertEqual(self.list()["rows"],two["rows"])
        for other in ("shared","mom","granny","family"):
            self.assertEqual(self.list(other)["rows"],[])
        self.assertEqual(stat.S_IMODE(self.path.stat().st_mode),0o700)
        self.assertEqual(stat.S_IMODE((self.path/"mine.json").stat().st_mode),0o600)
    def test_duplicate_bill_and_stale_refusal(self):
        self.bill()
        with self.assertRaises(m.Refusal):
            self.bill(rev=1)
        with self.assertRaises(m.Refusal):
            self.purchase(rev=0)
        self.assertEqual(self.list()["revision"],1)
    def test_invalid_date_amount_day_and_forged_data(self):
        for day in (0,32,1.0,True):
            with self.assertRaises(m.Refusal):
                self.bill(day=day)
        for date in ("2027-02-30","2027-13-01","2027-01-00","2027-01-01T10:00"):
            with self.assertRaises(m.Refusal):
                self.purchase(date=date)
        for amount in ("0","-1","4e5","2.999","$12","1 000","999999999.99"):
            with self.assertRaises(m.Refusal):
                self.purchase(amount=amount)
        for goal in ("../private","p-"+"a"*31,"N/A"):
            with self.assertRaises(m.Refusal):
                self.purchase(goal=goal)
        with self.assertRaises(m.Refusal):
            m.run(self.path,{"action":"list","contextId":"mine","token":"secret"})
        # A rejected write may create a private directory/lock for serialization,
        # but it must never commit a schedule document.
        self.assertFalse((self.path/"mine.json").exists())
    def test_delete_refuses_other_context(self):
        saved=self.purchase()
        uid=saved["rows"][0]["id"]
        with self.assertRaises(m.Refusal):
            m.run(self.path,{"action":"delete","contextId":"shared",
                "expectedRevision":0,"id":uid})
        removed=m.run(self.path,{"action":"delete","contextId":"mine",
            "expectedRevision":1,"id":uid})
        self.assertEqual(removed["rows"],[])
        self.assertEqual(removed["revision"],2)
    def test_symlink_and_unsafe_permissions_fail_closed(self):
        self.path.mkdir(mode=0o700)
        private=Path(self.temp.name)/"private.json"
        private.write_text("SECRET")
        (self.path/"mine.json").symlink_to(private)
        with self.assertRaises(m.Refusal): self.list()
        with self.assertRaises(m.Refusal): self.purchase()
        self.assertEqual(private.read_text(),"SECRET")
    def test_corrupt_record_refused_without_replacement(self):
        self.purchase()
        path=self.path/"mine.json"
        path.write_text("bad")
        data=path.read_bytes()
        with self.assertRaises(m.Refusal): self.list()
        with self.assertRaises(m.Refusal): self.bill(rev=1)
        self.assertEqual(path.read_bytes(),data)
    def test_unsafe_world_readable_refused(self):
        self.purchase()
        (self.path/"mine.json").chmod(0o644)
        with self.assertRaises(m.Refusal): self.list()
        with self.assertRaises(m.Refusal): self.bill(rev=1)
    def test_invalid_future_schema_rejected(self):
        self.purchase()
        f=self.path/"mine.json"
        doc=json.loads(f.read_text())
        doc["version"]=4
        f.write_text(json.dumps(doc))
        with self.assertRaises(m.Refusal): self.list()

if __name__=="__main__":
    unittest.main()
