"""Sway scroll lock: exact-device, verified and recoverable host actions."""
import importlib.util
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
FILE = ROOT / "services/input/SwayScrollLock.py"
spec = importlib.util.spec_from_file_location("SwayScrollLock", FILE)
control = importlib.util.module_from_spec(spec)
spec.loader.exec_module(control)


class NativeMiddleScrollTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.snapshot = Path(self.tmp.name) / "mouse-scroll-lock-v1.json"
        self.device_id = "1234:5678:USB_Mouse"
        self.method = "none"
        self.lock = "disabled"
        self.button = 0
        self.commands = []
        patcher = patch.object(control, "snapshot_path", return_value=self.snapshot)
        patcher.start()
        self.addCleanup(patcher.stop)
        p2 = patch.object(control.subprocess, "run", side_effect=self.simulate)
        p2.start()
        self.addCleanup(p2.stop)

    def simulate(self, argv, **kwargs):
        self.commands.append(tuple(argv))
        self.assertFalse(kwargs.get("shell", False))
        if argv == ["swaymsg", "-t", "get_inputs"]:
            return SimpleNamespace(returncode=0, stdout=json.dumps([
                {"identifier": self.device_id, "name": "USB Mouse",
                 "type": "pointer", "scroll_method": self.method,
                 "scroll_button_lock": self.lock, "scroll_button": self.button},
                {"identifier": "keyboard", "type": "keyboard"}]))
        if argv[:3] != ["swaymsg", "input", self.device_id]:
            raise AssertionError("unknown command: " + str(argv))
        field, value = argv[3:]
        if field == "scroll_method":
            self.method = value
        elif field == "scroll_button_lock":
            self.lock = value
        elif field == "scroll_button":
            self.button = 274 if value == "BTN_MIDDLE" else (
                0 if value == "disable" else int(value))
        else:
            raise AssertionError("unexpected mutation field")
        return SimpleNamespace(returncode=0, stdout='[{"success":true}]')

    def enable(self):
        return control.enable(self.device_id, "none", "disabled", "0")

    def test_status_is_read_only(self):
        obj = control.inspect()
        self.assertEqual(obj["status"], "ok")
        self.assertFalse(obj["snapshot"])
        self.assertEqual(len(self.commands), 1)
        self.assertEqual(self.commands[0], ("swaymsg", "-t", "get_inputs"))

    def test_enable_then_restore_original_state(self):
        result = self.enable()
        self.assertEqual(result["status"], "enabled")
        self.assertTrue(self.snapshot.exists())
        self.assertTrue(control.active(control.find_device(self.device_id)))
        self.assertEqual(self.button, 274)
        self.assertEqual(self.lock, "enabled")
        self.assertEqual(self.method, "on_button_down")
        self.assertEqual(control.inspect()["active_identifier"], self.device_id)
        restored = control.restore()
        self.assertEqual(restored["status"], "restored")
        self.assertEqual((self.button, self.lock, self.method),
                         (0, "disabled", "none"))
        self.assertFalse(self.snapshot.exists())

    def test_other_scroll_method_restored_exactly(self):
        self.method = "two_finger"
        self.button = 276
        control.enable(self.device_id, "two_finger", "disabled", "276")
        control.restore()
        self.assertEqual((self.method, self.button, self.lock),
                         ("two_finger", 276, "disabled"))

    def test_stale_preflight_refuses_any_write(self):
        with self.assertRaisesRegex(control.LockError, "STALE_DEVICE"):
            control.enable(self.device_id, "on_button_down", "disabled", "0")
        self.assertFalse(self.snapshot.exists())
        self.assertFalse(any(x[1] == "input" for x in self.commands))

    def test_device_exclusivity_and_reentry(self):
        self.enable()
        with self.assertRaisesRegex(control.LockError, "ALREADY_ACTIVE"):
            self.enable()
        self.assertTrue(self.snapshot.exists())

    def test_unexpected_external_change_blocks_restore(self):
        self.enable()
        self.button = 275
        with self.assertRaisesRegex(control.LockError, "DEVICE_CHANGED_EXTERNALLY"):
            control.restore()
        self.assertTrue(self.snapshot.exists())

    def test_later_restore_recovers_partial_enable(self):
        self.enable()
        self.method = "none"  # simulate an interrupted enable sequence
        restored = control.restore()
        self.assertEqual(restored["status"], "restored")
        self.assertFalse(self.snapshot.exists())

    def test_reject_illegal_identifier(self):
        with self.assertRaisesRegex(control.LockError, "INVALID_DEVICE_ID"):
            control.enable("type:pointer; exec arbitrary", "none","disabled","0")
        self.assertFalse(self.snapshot.exists())

    def test_unowned_snapshot_blocks_all_changes(self):
        self.snapshot.write_text("not json")
        with self.assertRaises(control.LockError):
            self.enable()
        self.assertEqual(self.snapshot.read_text(), "not json")
        self.assertFalse(any(x[1] == "input" for x in self.commands))

    def test_unverified_reply_leaves_snapshot_recoverable(self):
        def reject(argv, **kwargs):
            if "-t" in argv:
                return self.simulate(argv, **kwargs)
            self.commands.append(tuple(argv))
            return SimpleNamespace(returncode=0,
                                   stdout='[{"success":false}]')
        with patch.object(control.subprocess, "run", side_effect=reject):
            with self.assertRaisesRegex(control.LockError, "SWAY_REJECTED_SETTING"):
                self.enable()
        self.assertTrue(self.snapshot.exists())

    def test_no_autoscroll_claims_or_privilege_escalation(self):
        text = FILE.read_text()
        for forbidden in ("shell=True", "pkexec", "sudo", "ydotool",
                          "EVIOCGRAB", "/dev/uinput", "wlr_virtual_pointer"):
            self.assertNotIn(forbidden, text)
        self.assertEqual(control.main(["invalid"]), 2)


if __name__ == "__main__":
    unittest.main()
