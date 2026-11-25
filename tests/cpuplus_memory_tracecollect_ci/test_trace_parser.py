import importlib.util
from pathlib import Path
import unittest

spec=importlib.util.spec_from_file_location("collector",Path(__file__).with_name("guest-tracecollect.py"))
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

def fixture():
    return [
        "swapoff-123 [001] .... 1.000001: sys_swapoff(filename: 0x123)",
        "swapoff-123 [001] .... 1.000002: unuse_enter: (try_to_unuse+0x0/0x10)",
        "swapoff-123 [001] .... 1.000003: unuse_return: (try_to_unuse+0x0/0x10) ret=0",
        "swapoff-123 [001] .... 1.000004: sys_swapoff -> 0x0",
    ]

class TraceParser(unittest.TestCase):
    def test_exact_sequence(self):
        self.assertEqual(len(m.parse("\n".join(fixture()),123)),4)
    def test_wrong_actor(self):
        with self.assertRaises(RuntimeError):
            m.parse("\n".join(fixture()).replace("-123","-124",1),123)
    def test_wrong_result(self):
        for old,new in (("ret=0","ret=-4"),("-> 0x0","-> 0x1")):
            with self.assertRaises(RuntimeError):
                m.parse("\n".join(fixture()).replace(old,new),123)
    def test_missing_repeated_reordered(self):
        rows=fixture()
        for altered in (rows[:-1],rows+rows[:1],rows[:1]+rows[2:3]+rows[1:2]+rows[3:]):
            with self.assertRaises(RuntimeError):
                m.parse("\n".join(altered),123)
    def test_same_clock(self):
        with self.assertRaises(RuntimeError):
            m.parse("\n".join(fixture()).replace("1.000003","1.000002"),123)

if __name__=="__main__":
    unittest.main()
