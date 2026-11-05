"""A Calls on PC click explains oFono readiness without mutating the host."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
FILE = ROOT / "services" / "phone" / "PhoneCallPrerequisites.py"
spec = importlib.util.spec_from_file_location("phone_call_prerequisites", FILE)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def check(package="INSTALLED", load="loaded", active="inactive", bus="UNKNOWN"):
    return mod.diagnose(
        package=lambda: package, service=lambda: (load, active),
        bus=lambda: bus,
    )


class CallPrerequisitesTests(unittest.TestCase):
    def locked(self, result):
        self.assertEqual(result["schema"], mod.SCHEMA)
        self.assertEqual(result["execution"], "READ_ONLY_CALL_DIAGNOSIS")
        self.assertEqual(result["trustedPhoneLink"], "UNVERIFIED")
        self.assertIs(result["hfpVerified"], False)
        self.assertIs(result["contentAccessEnabled"], False)
        self.assertEqual(set(result), {
            "schema", "execution", "state", "package", "serviceLoad",
            "serviceActive", "systemBus", "hfpVerified",
            "trustedPhoneLink", "contentAccessEnabled",
        })
        self.assertNotIn("PRIVATE", str(result))

    def test_not_installed_only_when_rpm_and_systemd_both_agree(self):
        x = check(package="NOT_INSTALLED", load="not-found", active="inactive")
        self.locked(x)
        self.assertEqual(x["state"], "PACKAGE_NOT_INSTALLED")
        self.assertEqual(x["package"], "NOT_INSTALLED")
        y = check(package="UNKNOWN", load="not-found", active="inactive")
        self.locked(y)
        self.assertEqual(y["state"], "SERVICE_UNIT_MISSING")

    def test_installed_but_stopped_is_separate_from_failed(self):
        for active, state in (
            ("inactive", "SERVICE_STOPPED"),
            ("failed", "SERVICE_FAILED"),
            ("activating", "SERVICE_STARTING"),
            ("deactivating", "SERVICE_STARTING"),
            ("reloading", "SERVICE_STARTING"),
        ):
            with self.subTest(active=active):
                x = check(active=active)
                self.locked(x)
                self.assertEqual(x["state"], state)

    def test_masked_system_unit_is_not_auto_unmasked(self):
        x = check(load="masked", active="inactive")
        self.locked(x)
        self.assertEqual(x["state"], "SERVICE_MASKED")

    def test_active_system_service_still_needs_bus_and_hfp_checks(self):
        for owner, state in (
            ("NO_OWNER", "DBUS_NAME_MISSING"),
            ("UNKNOWN", "AUDIO_PATH_UNVERIFIED"),
            ("OWNER_PRESENT", "AUDIO_PATH_UNVERIFIED"),
        ):
            with self.subTest(owner=owner):
                x = check(active="active", bus=owner)
                self.locked(x)
                self.assertEqual(x["state"], state)

    def test_unexpected_or_broken_probes_fail_closed(self):
        broken = lambda: (_ for _ in ()).throw(OSError("PRIVATE DEVICE"))
        x = mod.diagnose(package=broken, service=broken, bus=broken)
        self.locked(x)
        self.assertEqual(x["state"], "INSPECTION_UNAVAILABLE")
        self.assertEqual(x["package"], "UNKNOWN")
        self.assertEqual(x["serviceLoad"], "unknown")
        self.assertEqual(x["systemBus"], "UNKNOWN")

        x = mod.diagnose(
            package=lambda: ["PRIVATE"],
            service=lambda: ("PRIVATE", ["PRIVATE"]),
            bus=lambda: ["PRIVATE"],
        )
        self.locked(x)
        self.assertEqual(x["state"], "INSPECTION_UNAVAILABLE")

    def test_non_active_service_never_queries_system_bus(self):
        bus = mock.Mock()
        x = mod.diagnose(
            package=lambda: "INSTALLED",
            service=lambda: ("loaded", "inactive"),
            bus=bus,
        )
        self.locked(x)
        bus.assert_not_called()

    def test_rpm_query_is_read_only_and_redacts_output(self):
        run = mock.Mock(return_value=types.SimpleNamespace(
            stdout="ofono", returncode=0,
        ))
        self.assertEqual(mod.package_state(runner=run), "INSTALLED")
        run.assert_called_once_with(
            ["rpm", "-q", "--qf", "%{NAME}", "ofono"],
            capture_output=True, text=True, timeout=3, check=False,
        )
        self.assertEqual(mod.package_state(
            runner=lambda *a, **k: types.SimpleNamespace(
                stdout="PRIVATE", returncode=0)), "UNKNOWN")
        self.assertEqual(mod.package_state(
            runner=lambda *a, **k: types.SimpleNamespace(
                stdout="package is not installed", returncode=1)), "NOT_INSTALLED")

    def test_systemctl_reads_only_load_and_active_states(self):
        run = mock.Mock(return_value=types.SimpleNamespace(
            stdout="ActiveState=failed\nLoadState=loaded\n",
            returncode=3,
        ))
        self.assertEqual(mod.service_state(runner=run), ("loaded", "failed"))
        run.assert_called_once_with(
            ["systemctl", "show", "ofono.service", "--no-pager",
             "--property=LoadState", "--property=ActiveState"],
            capture_output=True, text=True, timeout=3, check=False,
        )
        self.assertEqual(mod.service_state(runner=lambda *a, **k:
            types.SimpleNamespace(stdout="LoadState=PRIVATE\nActiveState=active")),
            ("unknown", "active"))

    def test_real_dbus_inspection_uses_only_name_has_owner(self):
        bus = mock.Mock()
        bus.name_has_owner.return_value = True
        fake = types.SimpleNamespace(SystemBus=lambda private: bus)
        with mock.patch.dict(sys.modules, {"dbus": fake}):
            self.assertEqual(mod.bus_state(), "OWNER_PRESENT")
        bus.name_has_owner.assert_called_once_with("org.ofono")
        self.assertEqual(bus.method_calls, [mock.call.name_has_owner("org.ofono")])

    def test_requires_explicit_check_action(self):
        with mock.patch.object(mod, "diagnose") as diag, mock.patch("builtins.print"):
            self.assertEqual(mod.main([]), 2)
            diag.assert_not_called()
            self.assertEqual(mod.main(["--check", "--enable"]), 2)
            diag.assert_not_called()
        with mock.patch.object(mod, "diagnose", return_value=check()) as diag:
            with mock.patch("builtins.print") as printed:
                self.assertEqual(mod.main(["--check"]), 0)
                diag.assert_called_once_with()
                self.assertIn("SERVICE_STOPPED", printed.call_args.args[0])

    def test_source_never_starts_services_or_reads_phone_data(self):
        source = FILE.read_text()
        for forbidden in (
            "systemctl start", "systemctl enable", "systemctl restart",
            "dnf install", "bluetoothctl", "subprocess.Popen(",
            "getMessages(", "sendMessage(", "getContacts(",
            "shell=True", "pkexec", "sudo ", "get_object(",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
