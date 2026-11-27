"""Disposable procfs/sysfs and clock fixtures for the swap observer."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import cpuplus_swap_io_observer as observer

HEADER = "Filename Type Size Used Priority\n"
ROW = "/dev/zram0 partition 8192 4096 100\n"
MEM = "MemTotal: 16384 kB\nMemAvailable: 2048 kB\nSwapTotal: 8192 kB\nSwapFree: 4096 kB\n"


def psi(some=100000, full=20000):
    return f"some avg10=2.50 avg60=1.00 avg300=0.00 total={some}\nfull avg10=0.10 avg60=0.00 avg300=0.00 total={full}\n"


class SwapTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.proc = Path(tmp.name) / "proc"
        self.block = Path(tmp.name) / "block"
        (self.proc / "pressure").mkdir(parents=True)
        (self.block / "zram0").mkdir(parents=True)
        (self.proc / "swaps").write_text(HEADER+ROW)
        (self.proc / "meminfo").write_text(MEM)
        (self.proc / "vmstat").write_text("pswpin 100\npswpout 200\n")
        (self.proc / "pressure/memory").write_text(psi())
        (self.block / "zram0/mm_stat").write_text("4194304 1048576 1572864 0 0 0 0 0\n")

    def run_capture(self, change=None, page=4096, duration=1, interval=1):
        now = [0]
        def sleep(seconds):
            now[0] += round(seconds*1e9)
            (self.proc / "vmstat").write_text("pswpin 102\npswpout 203\n")
            (self.proc / "pressure/memory").write_text(psi(110000, 21000))
            if change:
                change()
        with patch.object(observer.time, "monotonic_ns", side_effect=lambda: now[0]), \
             patch.object(observer.time, "sleep", side_effect=sleep):
            return observer.capture(duration, interval, self.proc, self.block, page)

    def test_capture_and_page_units(self):
        for page in (4096, 65536):
            (self.proc / "vmstat").write_text("pswpin 100\npswpout 200\n")
            (self.proc / "pressure/memory").write_text(psi())
            text = self.run_capture(page=page, duration=3, interval=2)
            first, second, end = map(json.loads, text.splitlines())
            self.assertEqual(first["swapBytes"], [2*page, 3*page])
            self.assertEqual(first["memoryKiB"], [16384, 2048, 8192, 4096])
            self.assertEqual(first["pressure"], [2.5, .1, 10000, 1000])
            self.assertEqual(first["zram"], [["zram0",4194304,1048576,1572864]])
            self.assertEqual(second["swapBytes"], [0,0])
            self.assertEqual(second["intervalMs"], 1000)
            self.assertEqual(end["pageSize"], page)
            self.assertEqual(end["samples"], 2)
            self.assertEqual(end["observedMs"], 3000)
            self.assertEqual(end["calibration"], {"kind":"swapio","durationSeconds":3,"intervalMs":2000})
            self.assertLessEqual(len(text), observer.MAX_BYTES)

    def test_unavailable_optional_sources(self):
        (self.block / "zram0/mm_stat").unlink()
        def missing():
            (self.proc / "pressure/memory").unlink(missing_ok=True)
        row, _ = map(json.loads, self.run_capture(change=missing).splitlines())
        self.assertIsNone(row["pressure"])
        self.assertEqual(row["zram"], [["zram0",None,None,None]])

    def test_no_active_swap(self):
        (self.proc / "swaps").write_text(HEADER)
        (self.proc / "meminfo").write_text(MEM.replace("8192 kB","0 kB").replace("4096 kB","0 kB"))
        row, _ = map(json.loads, self.run_capture().splitlines())
        self.assertEqual(row["memoryKiB"][2:], [0,0])
        self.assertEqual(row["zram"], [])

    def test_topology_change(self):
        with self.assertRaises(ValueError):
            self.run_capture(change=lambda: (self.proc / "swaps").write_text(HEADER))

    def test_counter_reset(self):
        with self.assertRaises(ValueError):
            self.run_capture(change=lambda: (self.proc / "vmstat").write_text("pswpin 1\npswpout 203\n"))

    def test_psi_counter_reset(self):
        with self.assertRaises(ValueError):
            self.run_capture(change=lambda: (self.proc / "pressure/memory").write_text(psi(1,1)))

    def test_required_fields_and_duplicates(self):
        for raw in ("pswpin 1\n", "pswpin -1\npswpout 2\n", "pswpin 1\npswpin 2\npswpout 3\n"):
            with self.assertRaises(ValueError):
                observer.fields(raw, ("pswpin","pswpout"))
        with self.assertRaises(ValueError):
            observer.parse_swaps(HEADER+ROW+ROW)
        with self.assertRaises(ValueError):
            observer.parse_meminfo(MEM.replace("4096 kB","9000 kB"))

    def test_calibration(self):
        for d,i,p in [(0,1,4096),(31,5,4096),(30,1,4096),(1,2,4096),(1,1,3000),(True,1,4096)]:
            with self.assertRaises(ValueError):
                observer.validate(d,i,p)

    def test_output_budget(self):
        with patch.object(observer,"MAX_BYTES",1), self.assertRaises(ValueError):
            self.run_capture()

    def test_paths_not_disclosed(self):
        (self.proc / "swaps").write_text(HEADER+"/private/name file 8192 4096 -2\n")
        self.assertNotIn("/private/name",self.run_capture())


if __name__ == "__main__":
    unittest.main()
