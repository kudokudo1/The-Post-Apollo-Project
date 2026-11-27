"""Host CPU observer tests, including real read-only Linux smoke."""
import json
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import cpuplus_host_cpu_observer as observer


class HostCpuTests(unittest.TestCase):
    def test_guest_not_double_counted(self):
        a = observer.parse_stat("cpu 10 2 3 20 1 4 5 6 8 9\ncpu0 10 2 3 20 1 4 5 6 8 9\n")
        b = observer.parse_stat("cpu 20 3 5 30 3 5 6 7 18 19\ncpu0 20 3 5 30 3 5 6 7 18 19\n")
        self.assertEqual(observer.delta(a[-1], b[-1]), [28, 16, 2])

    def test_bad_counters_and_topology(self):
        for value in ["cpu 1 2", "cpu 1 2 3 4 5 6 7 8", "cpu -1 2 3 4 5 6 7 8\ncpu0 1 2 3 4 5 6 7 8",
                      "cpu 1 2 3 4 5 6 7 8\ncpu0 1 2 3 4 5 6 7 8\ncpu0 1 2 3 4 5 6 7 8"]:
            with self.assertRaises(ValueError):
                observer.parse_stat(value)
        with self.assertRaises(ValueError):
            observer.delta((1,)*8, (1,)*8)
        with self.assertRaises(ValueError):
            observer.delta((2,)*8, (3,3,3,3,1,3,3,3))

    def test_calibration(self):
        for duration, interval in [(0,1),(31,5),(30,1),(1,2),(10,6),(1,0)]:
            with self.assertRaises(ValueError):
                observer.validate(duration,interval)
        for duration, interval in [(1,1),(10,1),(30,3),(13,2)]:
            observer.validate(duration,interval)

    def test_optional_unavailable_not_zero(self):
        with patch.object(observer, "bounded_text", side_effect=OSError):
            self.assertIsNone(observer.optional_pressure())
            self.assertIsNone(observer.optional_frequency(0))

    def test_real_capture(self):
        # Hosted CI uses a small Linux guest; an oversized host is refused.
        result = subprocess.run([sys.executable,"-B",str(ROOT/"scripts/cpuplus_host_cpu_observer.py"),
                                 "--workshop","--duration","1","--interval","1"],
                                text=True,capture_output=True,timeout=8,check=True)
        self.assertLessEqual(len(result.stdout.encode("ascii")),observer.MAX_BYTES)
        sample,end = map(json.loads,result.stdout.splitlines())
        self.assertEqual(sample["event"],"hostcpu")
        self.assertEqual(end["samples"],1)
        self.assertEqual(end["observedMs"],sample["elapsedMs"])
        self.assertGreaterEqual(end["observedMs"],1000)
        self.assertTrue(sample["cores"])
        self.assertEqual(end["calibration"],{"kind":"hostcpu","durationSeconds":1,"intervalMs":1000})
        self.assertEqual(sample["intervalMs"],sample["elapsedMs"])
        self.assertLessEqual(sample["aggregate"][1]+sample["aggregate"][2],sample["aggregate"][0])
        for cpu,total,busy,wait,freq in sample["cores"]:
            self.assertGreater(total,0)
            self.assertLessEqual(busy+wait,total)
            self.assertTrue(freq is None or freq>0)


if __name__ == "__main__":
    unittest.main()
