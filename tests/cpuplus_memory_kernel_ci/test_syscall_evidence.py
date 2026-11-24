import importlib.util
from pathlib import Path
import struct
import unittest

spec = importlib.util.spec_from_file_location("kernel_fixture", Path(__file__).with_name("guest-kernel-custody.py"))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class SyscallEvidence(unittest.TestCase):
    def sample(self, op=1, arch=m.AUDIT_ARCH_X86_64, nr=m.SYS_SWAPOFF):
        raw = bytearray(128)
        raw[0] = op
        struct.pack_into("<I", raw, 4, arch)
        struct.pack_into("<Q", raw, 24, nr)
        return bytes(raw)

    def test_exact_entry(self):
        self.assertTrue(m.decode_swapoff_entry(self.sample(), 80))

    def test_other_syscall_or_exit_not_entry(self):
        self.assertFalse(m.decode_swapoff_entry(self.sample(nr=167), 80))
        self.assertFalse(m.decode_swapoff_entry(self.sample(op=2), 33))

    def test_wrong_architecture_refused(self):
        with self.assertRaisesRegex(RuntimeError, "architecture"):
            m.decode_swapoff_entry(self.sample(arch=0x40000003), 80)

    def test_bad_length_refused(self):
        for length in (0, 129, 31, True):
            with self.subTest(length=length), self.assertRaises(RuntimeError):
                m.decode_swapoff_entry(self.sample(), length)

if __name__ == "__main__":
    unittest.main()
