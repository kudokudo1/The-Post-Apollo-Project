"""Fake-sysfs coverage for the read-only, privilege-free LED proxy."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
HELPER = ROOT / "services/input/KeyboardLedProbe.py"
spec = importlib.util.spec_from_file_location("KeyboardLedProbe", HELPER)
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


class LedProbeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def add(self, label, content="1\n"):
        entry = self.root / label
        entry.mkdir(parents=True)
        (entry / "brightness").write_text(content)
        return entry

    def test_absent_is_not_off(self):
        result = probe.sample(self.root)
        self.assertEqual(result["num"]["status"], "absent")
        self.assertIsNone(result["num"]["value"])
        self.assertEqual(result["caps"]["status"], "absent")

    def test_on_off_and_bounded_multiple_consistent(self):
        self.add("input3::numlock", "1\n")
        self.add("input2::numlock", "255\n")
        self.add("input5::capslock", "0\n")
        result = probe.sample(self.root)
        self.assertEqual(result["source"], "linux-led-brightness-proxy")
        self.assertEqual(result["num"], {
            "status": "observed", "value": "on", "count": 2})
        self.assertEqual(result["caps"], {
            "status": "observed", "value": "off", "count": 1})

    def test_conflicting_leds_fail_closed(self):
        self.add("input1::numlock", "1\n")
        self.add("input2::numlock", "0\n")
        state = probe.sample(self.root)["num"]
        self.assertEqual(state["status"], "conflict")
        self.assertIsNone(state["value"])

    def test_unreadable_led_fails_closed(self):
        self.add("input1::capslock", "garbage")
        self.add("input2::capslock", "1\n")
        state = probe.sample(self.root)["caps"]
        self.assertEqual(state["status"], "unreadable")
        self.assertIsNone(state["value"])

    def test_ignores_unrelated_leds(self):
        self.add("input3::scrolllock", "1")
        self.add("asus::kbd_backlight", "255")
        self.add("inputbad::capslock", "1")
        self.assertEqual(probe.sample(self.root)["caps"]["status"], "absent")

    def test_oversize_brightness_is_unknown(self):
        self.add("input1::capslock", "9" * 100)
        self.assertEqual(probe.sample(self.root)["caps"]["status"], "unreadable")

    def test_too_many_entries_denies_and_no_device_names(self):
        for index in range(65):
            self.add("indicator-" + str(index), "1")
        response = probe.sample(self.root)
        self.assertEqual(response["status"], "too_many_entries")
        self.assertNotIn("indicator-", str(response))

    def test_never_reads_key_events_or_writes(self):
        src = HELPER.read_text()
        for forbidden in ("/dev/input", "swaymsg", "subprocess",
                          "os.system", "os.open", "write_text", "unlink",
                          "chmod", "EVIOCGKEY"):
            self.assertNotIn(forbidden, src)
        self.assertEqual(probe.main(["other"]), 2)


if __name__ == "__main__":
    unittest.main()
