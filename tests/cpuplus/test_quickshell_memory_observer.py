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
                  Private_Clean=20, Private_Dirty=90, Swap=40, SwapPss=30)
    return "\n".join(f"{k}: {v} kB" for k, v in values.items())


def host_info(available=6000):
    values = dict.fromkeys(observer.HOST_FIELDS, 0)
    values.update(MemTotal=32000, MemAvailable=available, MemFree=1000,
                  AnonPages=15000, Cached=4000, Shmem=500,
                  SReclaimable=400, SUnreclaim=300, SwapTotal=16000, SwapFree=12000)
    return "\n".join(f"{k}: {v} kB" for k, v in values.items())


class ObserverTests(unittest.TestCase):
    def test_host_memory_validation(self):
        self.assertEqual(observer.parse_host_memory(host_info())["MemAvailable"], 6000)
        for text in (host_info(32001), host_info().replace("SwapFree: 12000 kB", "SwapFree: 16001 kB"),
                     host_info().replace("Shmem: 500 kB", ""), host_info() + "\nMemFree: 0 kB",
                     host_info().replace("MemFree: 1000 kB", "MemFree: -1 kB"),
                     host_info().replace("MemFree: 1000 kB", "MemFree: 1000 MB")):
            with self.assertRaises(ValueError):
                observer.parse_host_memory(text)

    def test_host_context_brackets_process_rollup(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "123"
            path.mkdir()
            (path / "stat").write_text(stat())
            (path / "smaps_rollup").write_text(rollup())
            (path.parent / "meminfo").write_text(host_info())
            row = observer.observe(path, os.getuid(), 100)
            self.assertEqual(row["hostObservation"]["beforeKiB"]["MemAvailable"], 6000)
            self.assertEqual(row["hostObservation"]["afterKiB"]["MemAvailable"], 6000)
            self.assertGreaterEqual(row["hostObservation"]["spanMs"], 0)
            before = observer.parse_host_memory(host_info())
            after = observer.parse_host_memory(host_info(2500))
            with patch.object(observer, "host_memory", side_effect=[before, after]) as sample:
                row = observer.observe(path, os.getuid(), 100)
                self.assertEqual(sample.call_count, 2)
                self.assertEqual(row["hostObservation"]["beforeKiB"], before)
                self.assertEqual(row["hostObservation"]["afterKiB"], after)
            (path.parent / "meminfo").write_text("invalid")
            row = observer.observe(path, os.getuid(), 100)
            self.assertIsNone(row["hostObservation"]["beforeKiB"])
            self.assertIsNone(row["hostObservation"]["afterKiB"])
            self.assertEqual(row["memoryKiB"]["Pss"], 150)

    def test_valid_fields_and_zero(self):
        parsed = observer.parse_rollup(rollup())
        self.assertEqual(parsed["Pss"], 150)
        self.assertEqual(parsed["Pss_Shmem"], 0)
        self.assertEqual(parsed["Private_Clean"], 20)
        self.assertEqual(parsed["Private_Dirty"], 90)

    def test_missing_duplicate_malformed(self):
        for text in (rollup().replace("SwapPss: 30 kB", ""),
                     rollup() + "\nPss: 150 kB",
                     rollup().replace("Pss: 150 kB", "Pss: -1 kB"),
                     rollup().replace("Pss: 150 kB", "Pss: 150 MB")):
            with self.subTest(text=text):
                with self.assertRaises(ValueError):
                    observer.parse_rollup(text)

    def test_private_clean_missing_malformed_or_impossible(self):
        for text in (rollup().replace("Private_Clean: 20 kB", ""),
                     rollup() + "\nPrivate_Clean: 20 kB",
                     rollup().replace("Private_Clean: 20 kB", "Private_Clean: -1 kB"),
                     rollup().replace("Private_Clean: 20 kB", "Private_Clean: 20 MB"),
                     rollup().replace("Private_Clean: 20 kB", "Private_Clean: 111 kB")):
            with self.subTest(text=text):
                with self.assertRaises(ValueError):
                    observer.parse_rollup(text)

    def test_private_zero_and_exact_rss_boundary(self):
        zero = rollup().replace("Private_Clean: 20 kB", "Private_Clean: 0 kB")
        self.assertEqual(observer.parse_rollup(zero)["Private_Clean"], 0)
        edge = rollup().replace("Private_Clean: 20 kB", "Private_Clean: 110 kB")
        self.assertEqual(observer.parse_rollup(edge)["Private_Clean"], 110)

    def test_observe(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "123"
            path.mkdir()
            (path / "stat").write_text(stat())
            (path / "smaps_rollup").write_text(rollup())
            row = observer.observe(path, os.getuid(), 100)
            self.assertEqual(row["pssPlusSwapPssKiB"], 180)
            self.assertEqual(row["privateResidentKiB"], 110)
            self.assertEqual(row["memoryKiB"]["Private_Clean"], 20)
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
