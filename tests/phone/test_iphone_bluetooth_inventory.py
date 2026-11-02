"""Offline tests for explicit, read-only iPhone Linux prerequisites inventory."""
from __future__ import annotations

from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import subprocess
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "services" / "phone"))
import IphoneBluetoothInventory as inv  # noqa: E402


class InventoryTests(unittest.TestCase):
    def setUp(self):
        self.commands = []
        self.paths = []
        self.listings = []
        self.binaries = {
            "bluetoothctl": "/usr/bin/bluetoothctl",
            "blueferry": "/usr/bin/blueferry",
        }
        self.output = SimpleNamespace(returncode=0, stdout="bluetoothctl: 5.86\n")
        self.sysfs = ["hci0", "hci1", "bluetooth_misc"]

    def which(self, name):
        self.paths.append(name)
        return self.binaries.get(name)

    def run(self, argv, **kwargs):
        self.commands.append((argv, kwargs))
        return self.output

    def listdir(self, path):
        self.listings.append(path)
        return self.sysfs

    def inspect(self, **kwargs):
        return inv.inspect(
            which=self.which, runner=self.run, listdir=self.listdir,
            platform=kwargs.pop("platform", "linux"), **kwargs,
        )

    def assertRestricted(self, result):
        self.assertFalse(result["routeEligible"])
        self.assertFalse(result["contentAccessEnabled"])
        self.assertEqual(result["messaging"], "NOT_VERIFIED")
        self.assertEqual(result["iphonePairing"], "NOT_CHECKED")
        self.assertEqual(result["iphonePermissions"], "NOT_CHECKED")
        self.assertEqual(result["controllerClassicLeSupport"], "NOT_CHECKED")
        self.assertEqual(result["blueferryDaemon"], "NOT_CHECKED")
        self.assertEqual(result["networkRoute"], "NOT_CHECKED")
        self.assertEqual(result["execution"], "OPT_IN_LOCAL_METADATA_ONLY")

    def test_normal_metadata_is_not_message_capability(self):
        out = self.inspect()
        self.assertEqual(out["state"], "LOCAL_METADATA_OBSERVED")
        self.assertEqual(out["bluezVersion"], "5.86")
        self.assertEqual(out["adapterCount"], 2)
        self.assertTrue(out["blueferryExecutableFound"])
        self.assertEqual(out["mapPbapVersionMinimum"], "DOCUMENTED_VERSION_MET")
        self.assertEqual(out["ancsVersionMinimum"], "DOCUMENTED_VERSION_MET")
        self.assertRestricted(out)

    def test_only_command_is_bluetoothctl_version(self):
        self.inspect()
        self.assertEqual(self.commands, [(
            ["/usr/bin/bluetoothctl", "--version"],
            dict(check=False, capture_output=True, text=True, timeout=3),
        )])
        self.assertEqual(self.paths, ["blueferry", "bluetoothctl"])
        self.assertEqual(self.listings, ["/sys/class/bluetooth"])

    def test_default_main_never_inspects_system(self):
        result = io.StringIO()
        with patch.object(inv, "inspect", side_effect=AssertionError("must not run")):
            with redirect_stdout(result):
                exit_code = inv.main([])
        self.assertEqual(exit_code, 2)
        self.assertEqual(json.loads(result.getvalue())["state"], "EXPLICIT_FLAG_REQUIRED")

    def test_wrong_flags_never_inspect(self):
        for flags in [["--probe"], ["--inspect", "--pair"], ["--scan"], ["--inspect", "--inspect"]]:
            with self.subTest(flags=flags):
                with patch.object(inv, "inspect", side_effect=AssertionError("must not run")):
                    with redirect_stdout(io.StringIO()):
                        self.assertEqual(inv.main(flags), 2)

    def test_explicit_flag_emits_only_sanitized_summary(self):
        output = io.StringIO()
        with patch.object(inv, "inspect", return_value=self.inspect()) as inspected:
            with redirect_stdout(output):
                self.assertEqual(inv.main(["--inspect"]), 0)
        inspected.assert_called_once_with()
        self.assertRestricted(json.loads(output.getvalue()))
        self.assertNotIn("/usr/bin", output.getvalue())

    def test_nonlinux_does_no_io(self):
        for platform in ("darwin", "win32", "freebsd"):
            with self.subTest(platform=platform):
                x = self.inspect(platform=platform)
                self.assertEqual(x["state"], "UNSUPPORTED_PLATFORM")
                self.assertEqual(self.commands, [])
                self.assertEqual(self.paths, [])
                self.assertEqual(self.listings, [])
                self.assertRestricted(x)

    def test_missing_bluez_does_not_run_an_alternate_probe(self):
        self.binaries.pop("bluetoothctl")
        x = self.inspect()
        self.assertEqual(x["state"], "BLUEZ_CLI_MISSING")
        self.assertIsNone(x["bluezVersion"])
        self.assertEqual(self.commands, [])
        self.assertRestricted(x)

    def test_missing_blueferry_is_not_an_error_or_daemon_check(self):
        self.binaries.pop("blueferry")
        x = self.inspect()
        self.assertFalse(x["blueferryExecutableFound"])
        self.assertEqual(x["state"], "LOCAL_METADATA_OBSERVED")
        self.assertRestricted(x)

    def test_no_controllers_is_not_pairing_or_map_proof(self):
        self.sysfs = []
        x = self.inspect()
        self.assertEqual(x["adapterCount"], 0)
        self.assertRestricted(x)

    def test_bad_sysfs_does_not_claim_zero_adapters(self):
        for state in (["hci0"] * 2, [f"hci{i}" for i in range(9)],
                      ["hci0"] * 33, None, "hci0"):
            with self.subTest(state=repr(state)[:30]):
                self.sysfs = state
                x = self.inspect()
                self.assertIsNone(x["adapterCount"])
                self.assertEqual(x["state"], "SYSFS_UNAVAILABLE")
                self.assertRestricted(x)

    def test_sysfs_unavailable_still_returns_version(self):
        def failure(path):
            raise PermissionError("private system location")
        x = inv.inspect(which=self.which, runner=self.run, listdir=failure)
        self.assertEqual(x["state"], "SYSFS_UNAVAILABLE")
        self.assertEqual(x["bluezVersion"], "5.86")
        self.assertRestricted(x)
        self.assertNotIn("private", str(x))

    def test_controller_names_are_not_logged_or_returned(self):
        self.sysfs = ["hci0", "private-device-name", "01:23:45:67:89:AB"]
        x = self.inspect()
        self.assertEqual(x["adapterCount"], 1)
        self.assertNotIn("private-device-name", str(x))
        self.assertNotIn("01:23", str(x))

    def test_below_map_minimum_reports_version_only(self):
        self.output.stdout = "5.71"
        x = self.inspect()
        self.assertEqual(x["mapPbapVersionMinimum"], "BELOW_DOCUMENTED_VERSION")
        self.assertEqual(x["ancsVersionMinimum"], "BELOW_DOCUMENTED_VERSION")
        self.assertRestricted(x)

    def test_map_minimum_does_not_imply_ancs_minimum(self):
        self.output.stdout = "5.72"
        x = self.inspect()
        self.assertEqual(x["mapPbapVersionMinimum"], "DOCUMENTED_VERSION_MET")
        self.assertEqual(x["ancsVersionMinimum"], "BELOW_DOCUMENTED_VERSION")
        self.assertRestricted(x)

    def test_ancs_bearer_version_floor(self):
        self.output.stdout = "bluetoothctl 5.86"
        x = self.inspect()
        self.assertEqual(x["ancsVersionMinimum"], "DOCUMENTED_VERSION_MET")
        self.assertRestricted(x)

    def test_patch_version_is_ignored_for_minor_thresholds(self):
        self.output.stdout = "bluetoothctl: 5.87.1"
        x = self.inspect()
        self.assertEqual(x["bluezVersion"], "5.87")
        self.assertRestricted(x)

    def test_invalid_version_output_is_never_echoed(self):
        bad = ("some phone called Alice", "AA:BB:CC:DD:EE:FF 5.86",
               "bluetoothctl 5.86\nuser information", "5.86" * 100,
               "", "abc", "5.86 \x00 private", None, [], "\u03b1 5.86")
        for output in bad:
            with self.subTest(output=str(output)[:20]):
                self.output.stdout = output
                x = self.inspect()
                self.assertEqual(x["state"], "BLUEZ_VERSION_UNAVAILABLE")
                self.assertIsNone(x["bluezVersion"])
                self.assertRestricted(x)
                self.assertNotIn("Alice", str(x))

    def test_nonzero_or_invalid_return_code_is_unavailable(self):
        for code in (1, -1, None, True, "0"):
            with self.subTest(code=code):
                self.output.returncode = code
                x = self.inspect()
                self.assertEqual(x["state"], "BLUEZ_VERSION_UNAVAILABLE")
                self.assertRestricted(x)

    def test_command_timeout_fail_closed(self):
        def timed_out(argv, **kwargs):
            raise subprocess.TimeoutExpired(argv, 3, output=b"private")
        x = inv.inspect(which=self.which, listdir=self.listdir, runner=timed_out)
        self.assertEqual(x["state"], "VERSION_QUERY_TIMEOUT")
        self.assertRestricted(x)
        self.assertNotIn("private", str(x))

    def test_failed_executable_lookup_fails_closed(self):
        def fail(name):
            raise OSError("private path")
        x = inv.inspect(which=fail, runner=self.run, listdir=self.listdir)
        self.assertEqual(x["state"], "INVENTORY_UNAVAILABLE")
        self.assertRestricted(x)
        self.assertEqual(self.commands, [])

    def test_relative_or_malformed_executable_path_is_rejected(self):
        for path in ("bluetoothctl", "--pair", "/tmp/\nprivate", "/x" * 3000, b"/bin/test"):
            with self.subTest(path=str(path)[:18]):
                self.binaries["bluetoothctl"] = path
                x = self.inspect()
                self.assertEqual(x["state"], "INVENTORY_UNAVAILABLE")
                self.assertRestricted(x)
                self.assertEqual(self.commands, [])

    def test_no_full_paths_or_addresses_in_any_output(self):
        for x in (self.inspect(), inv._snapshot("EXPLICIT_FLAG_REQUIRED")):
            serial = json.dumps(x)
            for secret in ("/usr/bin", "/sys/class", "AA:BB", "hci0", "iPhone 16"):
                self.assertNotIn(secret, serial)
            self.assertEqual(set(x), {
                "schema", "execution", "state", "bluezVersion", "adapterCount",
                "blueferryExecutableFound", "mapPbapVersionMinimum",
                "ancsVersionMinimum", "controllerClassicLeSupport", "iphonePairing",
                "iphonePermissions", "blueferryDaemon", "networkRoute", "messaging",
                "routeEligible", "contentAccessEnabled",
            })

    def test_version_parser_exact_shapes(self):
        for stdout, expected in (
            ("5.72", "5.72"), ("bluetoothctl: 5.86\n", "5.86"),
            ("bluetoothctl 5.87.1", "5.87"),
            ("not a version", None), ("5.86 special", None),
        ):
            self.assertEqual(inv.parse_version(stdout, 0), expected)

    def test_zero_system_inspection_in_import_or_empty_cli(self):
        # Import is passive and the default entrypoint only prints a warning.
        with patch.object(inv.shutil, "which", side_effect=AssertionError("lookup")):
            with patch.object(inv.subprocess, "run", side_effect=AssertionError("command")):
                with patch.object(inv.os, "listdir", side_effect=AssertionError("sysfs")):
                    with redirect_stdout(io.StringIO()):
                        self.assertEqual(inv.main([]), 2)


if __name__ == "__main__":
    unittest.main()
