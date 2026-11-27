"""Disposable proc/net/dev, sysfs and monotonic-clock fixtures."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import cpuplus_network_io_observer as observer

HEADER = ("Inter-| Receive | Transmit\n"
          " face |bytes packets errs drop fifo frame compressed multicast|bytes packets errs drop fifo colls carrier compressed\n")
BEFORE = (100, 10, 1, 2, 0, 0, 0, 0, 200, 20, 3, 4, 0, 0, 0, 0)
AFTER = (1100, 15, 2, 4, 0, 0, 0, 0, 2200, 27, 3, 5, 0, 0, 0, 0)


class NetworkTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        self.net = root / "net"
        self.devices = root / "devices"
        self.procdev = root / "dev"
        self.net.mkdir()
        self.devices.mkdir()
        self.eth = self.make_interface("eth0", 2, 2, 1)
        self.lo = self.make_interface("lo", 1, 1, 772)
        self.write(BEFORE)

    def make_interface(self, name, index, link, kind):
        path = self.devices / name
        path.mkdir()
        (path / "ifindex").write_text(str(index))
        (path / "iflink").write_text(str(link))
        (path / "type").write_text(str(kind))
        (path / "operstate").write_text("up")
        (self.net / name).symlink_to(path)
        return path

    def write(self, eth, lo=BEFORE):
        self.procdev.write_text(HEADER+"eth0: "+" ".join(map(str, eth))+"\nlo: "+" ".join(map(str, lo))+"\n")

    def run_capture(self, change=None, duration=1, interval=1):
        now = [0]
        def sleep(seconds):
            now[0] += round(seconds * 1e9)
            self.write(AFTER)
            if change:
                change()
        with patch.object(observer.time, "monotonic_ns", side_effect=lambda: now[0]), \
             patch.object(observer.time, "sleep", side_effect=sleep):
            return observer.capture(duration, interval, self.procdev, self.net, self.devices)

    def test_capture_and_idle_interface(self):
        first, second, end = map(json.loads, self.run_capture(duration=3, interval=2).splitlines())
        self.assertEqual(first["interfaces"], [
            ["eth0",2,2,1,"up",1000,5,1,2,2000,7,0,1],
            ["lo",1,1,772,"up",0,0,0,0,0,0,0,0]])
        self.assertEqual(second["interfaces"][0][5:], [0]*8)
        self.assertEqual(second["intervalMs"], 1000)
        self.assertEqual(end["samples"], 2)
        self.assertEqual(end["observedMs"], 3000)
        self.assertEqual(end["calibration"], {"kind":"netio","durationSeconds":3,"intervalMs":2000})

    def test_optional_state(self):
        (self.eth / "operstate").unlink()
        sample, _ = map(json.loads, self.run_capture().splitlines())
        self.assertIsNone(sample["interfaces"][0][4])

    def test_link_state_change_is_observed(self):
        sample, _ = map(json.loads, self.run_capture(
            change=lambda: (self.eth / "operstate").write_text("down")).splitlines())
        self.assertEqual(sample["interfaces"][0][4], "down")

    def test_index_change_refused(self):
        with self.assertRaises(ValueError):
            self.run_capture(change=lambda: (self.eth / "ifindex").write_text("3"))

    def test_counter_reset_refused(self):
        with self.assertRaises(ValueError):
            self.run_capture(change=lambda: self.write((0,)*16))

    def test_coverage_mismatch_refused(self):
        with self.assertRaises(ValueError):
            self.run_capture(change=lambda: (self.net / "lo").unlink())

    def test_duplicate_index_refused(self):
        (self.lo / "ifindex").write_text("2")
        with self.assertRaises(ValueError):
            self.run_capture()

    def test_bad_proc_rows(self):
        for raw in ("", HEADER, HEADER+"eth0: 1 2\n", HEADER+"eth0: "+"-1 "*16,
                    HEADER+"eth0: "+"0 "*16+"\neth0: "+"0 "*16):
            with self.assertRaises(ValueError):
                observer.parse_dev(raw)

    def test_calibration(self):
        for d,i in [(0,1),(31,5),(30,1),(1,2),(1,0),(True,1)]:
            with self.assertRaises(ValueError):
                observer.validate(d,i)

    def test_output_budget(self):
        with patch.object(observer, "MAX_BYTES", 1), self.assertRaises(ValueError):
            self.run_capture()


if __name__ == "__main__":
    unittest.main()
