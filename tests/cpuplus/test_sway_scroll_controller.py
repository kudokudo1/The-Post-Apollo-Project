"""Fake Sway IPC contract: read, apply, verify, refuse, and rollback evidence."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from unittest import TestCase, main, mock
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "services/input/SwayScrollControl.py"
spec = importlib.util.spec_from_file_location("SwayScrollControl", SRC)
control = importlib.util.module_from_spec(spec)
spec.loader.exec_module(control)


class SwayScrollTests(TestCase):
    def setUp(self):
        self.factor = 1.0
        self.calls = []
        self.input_id = "1234:5678:USB_Mouse"
        self.device = {
            "identifier": self.input_id, "name": "USB Mouse",
            "type": "pointer", "scroll_factor": 1
        }
        self.patcher = mock.patch.object(control.subprocess, "run",
                                         side_effect=self.execute)
        self.patcher.start()
        self.addCleanup(self.patcher.stop)

    def execute(self, argv, **kwargs):
        self.calls.append(tuple(argv))
        self.assertFalse(kwargs.get("shell", False))
        self.assertLessEqual(kwargs["timeout"], 4)
        if argv == ["swaymsg", "-t", "get_inputs"]:
            device = dict(self.device, scroll_factor=self.factor)
            data = [device, {"identifier": "other", "type": "keyboard"}]
            return SimpleNamespace(returncode=0, stdout=json.dumps(data))
        if argv[:3] == ["swaymsg", "input", self.input_id]:
            if argv[3] != "scroll_factor":
                raise AssertionError("Unexpected field")
            self.factor = float(argv[4])
            return SimpleNamespace(returncode=0, stdout='[{"success":true}]')
        raise AssertionError("Unexpected command " + str(argv))

    def test_discovery_returns_real_scroll_factor(self):
        result = control.inspect()
        self.assertEqual(result["scope"], "live_sway_only")
        self.assertEqual(len(result["devices"]), 1)
        self.assertEqual(result["devices"][0]["factor"], 1.0)
        self.assertEqual(result["devices"][0]["identifier"], self.input_id)

    def test_apply_and_undo_with_expected_factor(self):
        first = control.apply(self.input_id, "2.0", "1.0")
        self.assertEqual(first["status"], "applied")
        self.assertEqual(first["before"], 1.0)
        self.assertEqual(first["factor"], 2.0)
        self.assertEqual(self.factor, 2.0)
        after = control.apply(self.input_id, "1.0", "2.0")
        self.assertEqual(after["factor"], 1.0)
        self.assertEqual(self.factor, 1.0)
        self.assertTrue(any(x[:3] == ("swaymsg", "input", self.input_id)
                            for x in self.calls))

    def test_stale_factor_cannot_overwrite_other_worker(self):
        self.factor = 2.0
        with self.assertRaisesRegex(control.ScrollControlError,
                                    "STALE_DEVICE_FACTOR"):
            control.apply(self.input_id, "3.0", "1.0")
        self.assertEqual(self.factor, 2.0)
        self.assertFalse(any(x[1] == "input" for x in self.calls))

    def test_invalid_and_suspicious_inputs_never_reach_sway_command(self):
        for identifier, factor, expected in [
            ("type:pointer; reload", "2.0", "1.0"),
            (self.input_id, "nan", "1.0"),
            (self.input_id, "inf", "1.0"),
            (self.input_id, "0", "1.0"),
            (self.input_id, "999", "1.0"),
            (self.input_id, "1.1", "1.0"),
            (self.input_id, "2.0", "infinity")
        ]:
            with self.assertRaises(control.ScrollControlError):
                control.apply(identifier, factor, expected)
        self.assertFalse(any(x[1] == "input" for x in self.calls))

    def test_noop_never_runs_input_command(self):
        result = control.apply(self.input_id, "1.0", "1.0")
        self.assertEqual(result["status"], "unchanged")
        self.assertFalse(any(x[1] == "input" for x in self.calls))

    def test_sway_rejection_blocks_success(self):
        def reject(argv, **kwargs):
            if "-t" in argv:
                return self.execute(argv, **kwargs)
            self.calls.append(tuple(argv))
            return SimpleNamespace(returncode=0, stdout='[{"success":false}]')
        with mock.patch.object(control.subprocess, "run", side_effect=reject):
            with self.assertRaisesRegex(control.ScrollControlError,
                                        "SWAY_REJECTED_CHANGE"):
                control.apply(self.input_id, "2.0", "1.0")

    def test_unverified_changes_never_claim_success(self):
        def no_change(argv, **kwargs):
            if "-t" in argv:
                return self.execute(argv, **kwargs)
            self.calls.append(tuple(argv))
            return SimpleNamespace(returncode=0, stdout='[{"success":true}]')
        with mock.patch.object(control.subprocess, "run", side_effect=no_change):
            with self.assertRaisesRegex(control.ScrollControlError,
                                        "CHANGE_NOT_VERIFIED"):
                control.apply(self.input_id, "2.0", "1.0")
        self.assertEqual(self.factor, 1.0)

    def test_no_devices_or_out_of_range_previous_are_refused(self):
        self.factor = 12.0
        result = control.inspect()
        self.assertEqual(result["devices"], [])
        with self.assertRaisesRegex(control.ScrollControlError,
                                    "DEVICE_NOT_FOUND"):
            control.apply(self.input_id, "1.0", "1.0")

    def test_no_files_no_privilege_escalation(self):
        text = SRC.read_text()
        for forbidden in ("pkexec", "sudo", "os.system", "shell=True",
                          "write_text(", "atomic_write(", "swaymsg reload"):
            self.assertNotIn(forbidden, text)
        self.assertEqual(control.main(["wrong"]), 2)


if __name__ == "__main__":
    main()
