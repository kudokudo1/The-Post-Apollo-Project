"""Origin availability is read-only inventory, never trusted cursor coordinates."""
from __future__ import annotations
import json
import math
import os
from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import patch
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services/input"))
import AutoscrollOriginProbe as probe


def outputs():
    return [
        {"name": "DP-2", "active": True,
         "rect": {"x": -1920, "y": 0, "width": 1920, "height": 1080},
         "scale": 1.0},
        {"name": "HDMI-A-1", "active": True,
         "rect": {"x": 0, "y": 0, "width": 2560, "height": 1440},
         "scale": 1.25},
        {"name": "eDP-1", "active": False, "rect": {}, "scale": None}
    ]


class OriginInventoryTests(unittest.TestCase):
    def test_negative_monitor_coordinates_and_inactive_outputs(self):
        parsed = probe.parse_outputs(json.dumps(outputs()))
        self.assertEqual(len(parsed), 2)
        self.assertEqual(parsed[0]["x"], -1920)
        self.assertEqual(parsed[1]["scale"], 1.25)
        self.assertEqual(parsed[1]["width"], 2560)

    def test_duplicate_and_malformed_outputs_fail_closed(self):
        data = outputs()
        for bad in (
            [],
            [{"name": "DP-2", "active": True,
              "rect": {"x": 0, "y": 0, "width": 0, "height": 500},
              "scale": 1.0}],
            [data[0], data[0]],
            [dict(data[0], scale=float("nan"))],
            [dict(data[0], name="../untrusted")],
            [dict(data[0], rect={"x": 0.3, "y": 0,
                                  "width": 1920, "height": 1080})],
        ):
            with self.subTest(data=bad):
                with self.assertRaises(probe.ProbeError):
                    probe.parse_outputs(json.dumps(bad))

    def test_seat_and_capabilities_do_not_claim_pointer_target(self):
        self.assertTrue(probe.parse_seats('[{"name":"seat0","focus":0}]'))
        self.assertFalse(probe.parse_seats("[]"))
        self.assertFalse(probe.parse_seats(
            '[{"name":"seat0"},{"name":"seat1"}]'))
        check = probe.parse_protocols(
            "interface: 'zwlr_layer_shell_v1'\n"
            "interface: 'zwlr_virtual_pointer_manager_v1'\n")
        self.assertTrue(check["zwlr_layer_shell_v1"])
        self.assertTrue(check["zwlr_virtual_pointer_manager_v1"])
        empty = probe.parse_protocols("interface: 'wl_compositor'\n")
        self.assertFalse(empty["zwlr_layer_shell_v1"])

    def test_complete_readonly_inventory_leaves_runtime_off(self):
        calls = []
        def cmd(argv, timeout=2.5):
            calls.append(argv)
            if argv == ["swaymsg", "-t", "get_outputs"]:
                return json.dumps(outputs())
            if argv == ["swaymsg", "-t", "get_seats"]:
                return '[{"name":"seat0","focus":31}]'
            if argv == ["wayland-info"]:
                return ("zwlr_layer_shell_v1\n"
                        "zwlr_virtual_pointer_manager_v1\n")
            raise AssertionError("unexpected command")
        with patch.dict(os.environ, {"SWAYSOCK": "/tmp/fake-sway",
                                     "WAYLAND_DISPLAY": "wayland-test"}),patch.object(
            probe, "run_readonly", side_effect=cmd),patch.object(
            probe, "stop_socket_available", return_value=False):
            reply = probe.inspect()
        self.assertEqual(reply["status"], "inventory_only")
        self.assertEqual(len(reply["outputs"]), 2)
        self.assertTrue(reply["protocols"]["zwlr_layer_shell_v1"])
        self.assertTrue(reply["single_seat"])
        self.assertFalse(reply["pointer_origin_verified"])
        self.assertFalse(reply["pointer_target_verified"])
        self.assertFalse(reply["escape_binding_verified"])
        self.assertFalse(reply["runtime_enabled"])
        self.assertFalse(reply["overlay_allowed"])
        self.assertEqual(calls, [
            ["swaymsg", "-t", "get_outputs"],
            ["swaymsg", "-t", "get_seats"],
            ["wayland-info"],
        ])

    def test_no_sway_socket_never_touches_compositor(self):
        with patch.dict(os.environ, {"SWAYSOCK": ""}),patch.object(
            probe, "run_readonly",
            side_effect=AssertionError("must not run")):
            reply = probe.inspect()
        self.assertEqual(reply["status"], "no_sway_socket")
        self.assertFalse(reply["pointer_origin_verified"])
        self.assertFalse(reply["runtime_enabled"])

    def test_wayland_info_missing_is_not_success(self):
        def mock_run(cmd, timeout=2.5):
            if cmd == ["swaymsg", "-t", "get_outputs"]:
                return json.dumps(outputs())
            if cmd == ["swaymsg", "-t", "get_seats"]:
                return '[{"name":"seat0"}]'
            raise probe.ProbeError("READ_ONLY_COMMAND_UNAVAILABLE")
        with patch.dict(os.environ, {"SWAYSOCK": "/tmp/fake"}),patch.object(
            probe, "run_readonly", side_effect=mock_run):
            result = probe.inspect()
        self.assertEqual(result["wayland_info"], "unavailable")
        self.assertFalse(result["protocols"]["zwlr_layer_shell_v1"])
        self.assertFalse(result["runtime_enabled"])

    def test_source_never_grabs_mouse_or_injects_virtual_input(self):
        text=(ROOT/"services/input/AutoscrollOriginProbe.py").read_text()
        for forbidden in ("UInput", "InputDevice(", ".grab(", "sudo ",
                          "pkexec", "ydotool", "wayland-virtual",
                          "os.system(", "shell=True"):
            self.assertNotIn(forbidden, text)
        self.assertEqual(probe.main(["--unknown"]), 2)


if __name__ == "__main__":
    unittest.main()
