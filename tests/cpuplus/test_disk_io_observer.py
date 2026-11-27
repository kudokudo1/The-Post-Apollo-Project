"""Disposable sysfs and timing tests for the disk I/O observer."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import cpuplus_disk_io_observer as observer


class DiskIoTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.block = root / "block"
        self.devices = root / "devices"
        self.block.mkdir()
        self.devices.mkdir()
        self.disk = self.make_disk("sda", "8:0")
        self.before = (10, 1, 20, 30, 40, 2, 50, 60, 3, 70, 80)
        self.after = (12, 2, 28, 34, 43, 2, 54, 66, 1, 77, 90)
        self.write(self.disk, self.before)

    def make_disk(self, name, dev):
        parent = self.devices / "pci0" / name
        disk = parent / "block" / name
        disk.mkdir(parents=True)
        (disk / "device").symlink_to(parent, target_is_directory=True)
        (disk / "dev").write_text(dev)
        (disk / "diskseq").write_text("42")
        (self.block / name).symlink_to(disk, target_is_directory=True)
        return disk

    def write(self, disk, values):
        (disk / "stat").write_text(" ".join(map(str, values)))

    def test_scope_and_identity(self):
        partition = self.disk / "sda1"
        partition.mkdir()
        (partition / "partition").write_text("1")
        loop = self.devices / "virtual" / "block" / "loop0"
        loop.mkdir(parents=True)
        (self.block / "loop0").symlink_to(loop, target_is_directory=True)
        pin, rows = observer.snapshot(self.block, self.devices)
        self.assertEqual(list(rows), ["sda"])
        self.assertEqual(pin["sda"][1:4], (8, 0, 42))
        self.assertEqual(rows["sda"], self.before)
        (self.disk / "diskseq").write_text("43")
        self.assertNotEqual(pin, observer.discover(self.block, self.devices))

    def test_missing_diskseq_is_explicit(self):
        (self.disk / "diskseq").unlink()
        self.assertIsNone(observer.discover(self.block, self.devices)["sda"][3])

    def test_duplicate_device_number_refused(self):
        self.make_disk("sdb", "8:0")
        with self.assertRaises(ValueError):
            observer.discover(self.block, self.devices)

    def test_no_device_refused(self):
        (self.block / "sda").unlink()
        with self.assertRaises(ValueError):
            observer.discover(self.block, self.devices)

    def test_metrics(self):
        self.assertEqual(observer.delta(self.before, self.after),
                         [2, 4096, 4, 3, 2048, 6, 7, 10, 1])
        self.assertEqual(observer.delta(self.before, self.before),
                         [0, 0, 0, 0, 0, 0, 0, 0, 3])

    def test_bad_stats_and_reset(self):
        for text in ["", "1 2", " ".join(["-1"] * 11),
                     " ".join(["18446744073709551616"] * 11)]:
            with self.subTest(text=text), self.assertRaises(ValueError):
                observer.parse_stat(text)
        with self.assertRaises(ValueError):
            observer.delta(self.after, self.before)
        large = list(self.before)
        large[2] += observer.MAX_SAFE // 512 + 1
        with self.assertRaises(ValueError):
            observer.delta(self.before, large)

    def test_calibration(self):
        for duration, interval in [(0,1),(31,5),(30,1),(1,2),(10,6),(1,0),(True,1)]:
            with self.assertRaises(ValueError):
                observer.validate(duration, interval)
        for duration, interval in [(1,1),(10,1),(30,3),(13,2)]:
            observer.validate(duration, interval)

    def run_capture(self, duration=1, interval=1, replace=False):
        now = [0]
        def sleep(seconds):
            now[0] += round(seconds * 1e9)
            self.write(self.disk, self.after)
            if replace:
                (self.disk / "diskseq").write_text("44")
        with patch.object(observer.time, "monotonic_ns", side_effect=lambda: now[0]), \
             patch.object(observer.time, "sleep", side_effect=sleep):
            return observer.capture(duration, interval, self.block, self.devices)

    def test_capture_receipt_and_idle_interval(self):
        text = self.run_capture(3, 2)
        first, second, terminal = map(json.loads, text.splitlines())
        self.assertEqual(first["schema"], observer.SCHEMA)
        self.assertEqual(first["devices"], [["sda",8,0,42,2,4096,4,3,2048,6,7,10,1]])
        self.assertEqual(first["intervalMs"], 2000)
        self.assertEqual(second["intervalMs"], 1000)
        self.assertEqual(second["devices"][0][4:], [0,0,0,0,0,0,0,0,1])
        self.assertEqual(terminal["samples"], 2)
        self.assertEqual(terminal["observedMs"], 3000)
        self.assertEqual(terminal["calibration"],
                         {"kind":"diskio","durationSeconds":3,"intervalMs":2000})
        self.assertLessEqual(len(text.encode("ascii")), observer.MAX_BYTES)

    def test_topology_change_refuses_capture(self):
        with self.assertRaises(ValueError):
            self.run_capture(replace=True)

    def test_report_budget_refuses_capture(self):
        with patch.object(observer, "MAX_BYTES", 1), self.assertRaises(ValueError):
            self.run_capture()


if __name__ == "__main__":
    unittest.main()
