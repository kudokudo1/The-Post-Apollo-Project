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

class ProbeDiagnostic(unittest.TestCase):
    def test_documented_command_record(self):
        raw="[ 12.123456] trace_fprobe: error: Failed to find symbol\n  Command: f:pa_cpu_mem_ci/unuse_enter try_to_unuse\n             ^\n"
        d=m.probe_diagnostic(raw,"f:pa_cpu_mem_ci/unuse_enter try_to_unuse")
        self.assertEqual(d["category"],"SYMBOL_NOT_FOUND")
        self.assertEqual(d["location"],"trace_fprobe")
    def test_stale_error_not_attributed(self):
        raw="[ 1.1] probe: error: Failed to find symbol\n  Command: fixed\n[ 2.2] probe: error: Invalid argument\n  Command: other\n"
        self.assertEqual(m.probe_diagnostic(raw,"fixed")["category"],"LAST_COMMAND_MISMATCH")
    def test_unknown_reason_and_redaction(self):
        raw="[ 1.1] probe: error: Unexpected 0xffff888012345678 at 123456789012345\n  Command: fixed\n"
        d=m.probe_diagnostic(raw,"fixed")
        self.assertEqual(d["category"],"KERNEL_DIAGNOSTIC")
        self.assertNotIn("ffff8880",d["message"])
        self.assertNotIn("123456789012345",d["message"])
    def test_missing_or_unrecognized_header(self):
        self.assertEqual(m.probe_diagnostic("","fixed")["category"],"NO_COMMAND_RECORD")
        self.assertEqual(m.probe_diagnostic("bad header\n Command: fixed","fixed")["category"],"ERROR_HEADER_UNRECOGNIZED")

if __name__=="__main__":
    unittest.main()
