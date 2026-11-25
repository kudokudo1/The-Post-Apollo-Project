import importlib.util
from pathlib import Path
import unittest

spec=importlib.util.spec_from_file_location("signal_fixture",Path(__file__).with_name("guest-signalcustody.py"))
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

def rows():
    return ["python-10 [001] .... 1.000001: signal_generate: sig=15 errno=0 code=0 comm=python pid=20 grp=1 res=0",
            "python-20 [002] .... 1.000002: signal_deliver: sig=15 errno=0 code=0 sa_handler=0x1234 sa_flags=0x0"]

class SignalEvidence(unittest.TestCase):
    def test_exact_target_and_emitter(self):
        r=m.parse("\n".join(rows()),10,20,30)
        self.assertEqual([e["emitter_pid"] for e in r],[10,20])
        self.assertEqual([e["target_pid"] for e in r],[20,20])
        self.assertNotIn("0x1234",repr(r))
    def test_sender_is_not_target(self):
        for old,new in (("pid=20","pid=10"),("python-10","python-20"),
                        ("python-20","python-10"),("res=0","res=1"),("sig=15","sig=9")):
            with self.assertRaises(RuntimeError):
                m.parse("\n".join(rows()).replace(old,new,1),10,20,30)
    def test_late_or_missing_delivery(self):
        for r in (rows()[:1],rows()[::-1],rows()+rows()[:1]):
            with self.assertRaises(RuntimeError):
                m.parse("\n".join(r),10,20,30)
    def test_equal_clock_refused(self):
        with self.assertRaises(RuntimeError):
            m.parse("\n".join(rows()).replace("1.000002","1.000001"),10,20,30)
    def test_ambiguous_fields(self):
        with self.assertRaises(RuntimeError):
            m.parse("\n".join(rows()).replace("pid=20","pid=20 pid=20"),10,20,30)
    def test_bad_identity(self):
        for identity in ((10,10,30),(10,20,0),(True,20,30)):
            with self.assertRaises(RuntimeError):
                m.parse("\n".join(rows()),*identity)

if __name__=="__main__":
    unittest.main()
