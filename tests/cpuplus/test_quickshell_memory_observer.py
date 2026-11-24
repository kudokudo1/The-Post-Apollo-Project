import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import cpuplus_quickshell_memory_observer as observer


def stat(start=100, name="quickshell"):
    fields = ["0"] * 20
    fields[0] = "S"
    fields[11] = "20"
    fields[12] = "5"
    fields[19] = str(start)
    return "123 (" + name + ") " + " ".join(fields)


def rollup():
    values = dict.fromkeys(observer.FIELDS, 0)
    values.update(Rss=200, Pss=150, Pss_Anon=100, Pss_File=50,
                  Private_Dirty=90, Swap=40, SwapPss=30)
    return "\n".join(f"{k}: {v} kB" for k, v in values.items())


class ObserverTests(unittest.TestCase):
    def test_valid_fields_and_zero(self):
        parsed = observer.parse_rollup(rollup())
        self.assertEqual(parsed["Pss"], 150)
        self.assertEqual(parsed["Pss_Shmem"], 0)

    def test_missing_duplicate_malformed(self):
        for text in (rollup().replace("SwapPss: 30 kB", ""),
                     rollup() + "\nPss: 150 kB",
                     rollup().replace("Pss: 150 kB", "Pss: -1 kB"),
                     rollup().replace("Pss: 150 kB", "Pss: 150 MB")):
            with self.subTest(text=text):
                with self.assertRaises(ValueError):
                    observer.parse_rollup(text)

    def test_observe(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "123"
            path.mkdir()
            (path / "stat").write_text(stat())
            (path / "smaps_rollup").write_text(rollup())
            row = observer.observe(path, os.getuid(), 100)
            self.assertEqual(row["pssPlusSwapPssKiB"], 180)
            self.assertEqual(row["cpuTicks"], 25)
            self.assertEqual(row["startTicks"], 100)
            with self.assertRaises(ValueError):
                observer.observe(path, os.getuid() + 1, 100)
            with self.assertRaises(ValueError):
                observer.observe(path, os.getuid(), 101)
            (path / "stat").write_text(stat(name="other"))
            with self.assertRaises(ValueError):
                observer.observe(path, os.getuid(), 100)

    def test_identity_change_during_read(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "123"
            path.mkdir()
            (path / "smaps_rollup").write_text(rollup())
            with patch.object(observer, "identity", side_effect=[
                {"start": 100, "ticks": 25}, {"start": 101, "ticks": 0}
            ]):
                with self.assertRaises(ValueError):
                    observer.observe(path, os.getuid(), 100)

    def test_unavailable_rollup(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "123"
            path.mkdir()
            (path / "stat").write_text(stat())
            with self.assertRaises(OSError):
                observer.observe(path, os.getuid(), 100)


if __name__ == "__main__":
    unittest.main()
