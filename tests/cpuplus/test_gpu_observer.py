"""Bounded GPU reader tests with disposable sysfs trees, no physical GPU needed."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import cpuplus_gpu_observer as gpu


class GpuTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.drm = self.root / "drm"
        self.devices = self.root / "devices"
        self.drm.mkdir()
        self.devices.mkdir()

    def card(self, index, name, metrics=None):
        device = self.devices / name
        device.mkdir()
        card = self.drm / ("card%d" % index)
        card.mkdir()
        (card / "device").symlink_to(device, target_is_directory=True)
        for key, value in (metrics or {}).items():
            (device / key).write_text(str(value))
        return device

    def test_independent_devices_missing_values_and_temperature(self):
        a = self.card(0, "0000:01:00.0", {"gpu_busy_percent": 40,
                      "mem_info_vram_used": 1048576, "mem_info_vram_total": 2097152})
        self.card(1, "0000:02:00.0")
        hw = a / "hwmon" / "hwmon3"
        hw.mkdir(parents=True)
        (hw / "temp1_input").write_text("45500\n")
        rows = [json.loads(line) for line in gpu.capture(1, 1, self.drm, self.devices).splitlines()]
        self.assertEqual(rows[0]["devices"], [
            ["card0", "0000:01:00.0", 40, 1048576, 2097152, 45500],
            ["card1", "0000:02:00.0", None, None, None, None]])
        self.assertEqual(rows[1]["samples"], 1)
        self.assertGreaterEqual(rows[1]["observedMs"], 1000)

    def test_invalid_metrics_are_unavailable(self):
        a = self.card(0, "gpu", {"gpu_busy_percent": 101,
                      "mem_info_vram_used": 3, "mem_info_vram_total": 2})
        self.assertEqual(gpu.metrics(a), [None, None, None, None])
        with self.assertRaisesRegex(ValueError, "no supported"):
            gpu.capture(1, 1, self.drm, self.devices)

    def test_identity_change_refused(self):
        a = self.card(0, "gpu", {"gpu_busy_percent": 20})
        original = gpu.discover(self.drm, self.devices)
        with patch.object(gpu, "discover", side_effect=[original, {}]):
            with self.assertRaisesRegex(ValueError, "identity"):
                gpu.capture(1, 1, self.drm, self.devices)

    def test_bounds_and_duplicate_devices(self):
        with self.assertRaises(ValueError):
            gpu.discover(self.drm, self.devices)
        for duration, interval in [(0,1),(31,5),(30,1),(1,2),(10,6)]:
            with self.assertRaises(ValueError):
                gpu.validate(duration, interval)
        a = self.card(0, "gpu")
        second = self.drm / "card1"
        second.mkdir()
        (second / "device").symlink_to(a)
        with self.assertRaisesRegex(ValueError, "ambiguous"):
            gpu.discover(self.drm, self.devices)


if __name__ == "__main__":
    unittest.main()
