"""Saved BlueFerry setup/status may be inspected, never linked or authorized."""
from __future__ import annotations

import importlib
from pathlib import Path
import sys
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "phone"))
module = importlib.import_module("PhoneSavedBridgeState")
SCRIPT = ROOT / "services/phone/PhoneSavedBridgeState.py"


def upstream(**changes):
    r = {
        "schema": "post-apollo.social.phone-readiness.v0",
        "execution": "READ_ONLY",
        "blueferryInstalled": True,
        "bluetoothService": "active",
        "controllerPowered": True,
        "configurationPresent": True,
        "backendService": "active",
        "backendObservation": "REPORTED",
        "mapSessionActive": True,
        "pbapSessionActive": False,
        "phoneLink": "UNVERIFIED",
        "contentAuthorized": False,
    }
    r.update(changes)
    return r


class SavedStateTests(unittest.TestCase):
    def locked(self, result):
        self.assertEqual(result["schema"], module.SCHEMA)
        self.assertEqual(result["execution"], "READ_ONLY_LOCAL_LIFECYCLE")
        self.assertEqual(result["trustedPhoneLink"], "UNVERIFIED")
        self.assertIs(result["contentAccessEnabled"], False)
        self.assertEqual(set(result), {
            "schema", "execution", "state", "configurationPresent",
            "backendService", "startup", "messageProfile", "contactsProfile",
            "trustedPhoneLink", "contentAccessEnabled",
        })

    def test_configured_daemon_shows_backend_report_not_social_authority(self):
        result = module.inspect(
            probe=lambda: upstream(), startup=lambda: "enabled")
        self.locked(result)
        self.assertEqual(result["state"], "BACKEND_REPORTED")
        self.assertEqual(result["startup"], "enabled")
        self.assertTrue(result["configurationPresent"])
        self.assertEqual(result["messageProfile"], "ACTIVE_BACKEND_REPORT")
        self.assertEqual(result["contactsProfile"], "INACTIVE_BACKEND_REPORT")
        self.assertNotIn("CONNECTED", str(result))
        self.assertNotIn("PRIVATE", str(result))

    def test_configured_but_daemon_inactive_keeps_config(self):
        result = module.inspect(
            probe=lambda: upstream(
                backendService="inactive", backendObservation="NOT_RUNNING",
                mapSessionActive=None, pbapSessionActive=None),
            startup=lambda: "disabled")
        self.locked(result)
        self.assertEqual(result["state"], "CONFIGURATION_PRESENT_BACKEND_INACTIVE")
        self.assertTrue(result["configurationPresent"])
        self.assertEqual(result["backendService"], "inactive")
        self.assertEqual(result["startup"], "disabled")
        self.assertEqual(result["messageProfile"], "UNVERIFIED")

    def test_no_config_cannot_be_assumed_saved_pairing(self):
        result = module.inspect(
            probe=lambda: upstream(
                configurationPresent=False, backendService="inactive",
                backendObservation="NOT_RUNNING", mapSessionActive=None,
                pbapSessionActive=None),
            startup=lambda: "enabled")
        self.locked(result)
        self.assertEqual(result["state"], "NO_LOCAL_CONFIGURATION")
        self.assertFalse(result["configurationPresent"])

    def test_active_daemon_without_status_is_not_link_proof(self):
        result = module.inspect(
            probe=lambda: upstream(
                backendObservation="NO_OWNER", mapSessionActive=None,
                pbapSessionActive=None), startup=lambda: "static")
        self.locked(result)
        self.assertEqual(result["state"], "CONFIGURATION_PRESENT_BACKEND_UNVERIFIED")
        self.assertEqual(result["messageProfile"], "UNVERIFIED")
        self.assertEqual(result["contactsProfile"], "UNVERIFIED")

    def test_invalid_source_or_forged_grant_fails_closed(self):
        for observation in (
            None, {}, upstream(phoneLink="CONNECTED"),
            upstream(contentAuthorized=True),
            upstream(mapSessionActive="yes"),
            upstream(backendService="active", backendObservation="NOT_RUNNING",
                     mapSessionActive=True, pbapSessionActive=True),
        ):
            with self.subTest(observation=observation):
                s = mock.Mock()
                result = module.inspect(probe=lambda: observation, startup=s)
                self.locked(result)
                self.assertEqual(result["state"], "UNAVAILABLE")
                self.assertIsNone(result["configurationPresent"])
                s.assert_not_called()

    def test_startup_probe_reads_only_one_systemd_property(self):
        runner = mock.Mock(return_value=mock.Mock(stdout="enabled\n"))
        self.assertEqual(module.startup_state(runner=runner), "enabled")
        runner.assert_called_once_with(
            ["systemctl", "--user", "is-enabled", "blueferry.service"],
            capture_output=True, text=True, timeout=3, check=False,
        )
        for value in ("", "enabled somehow", "PRIVATE PHONENUMBER", "nope"):
            with self.subTest(value=value):
                self.assertEqual(
                    module.startup_state(
                        runner=lambda *a, **k: mock.Mock(stdout=value)),
                    "unknown")

    def test_missing_or_exceptional_tools_do_not_leak_private_error(self):
        s = module.inspect(probe=lambda: upstream(),
                           startup=lambda: (_ for _ in ()).throw(
                               ValueError("PRIVATE MAC ADDRESS")))
        self.locked(s)
        self.assertEqual(s["startup"], "unknown")
        self.assertNotIn("PRIVATE", str(s))
        self.assertEqual(
            module.startup_state(
                runner=mock.Mock(side_effect=OSError("PRIVATE MAC"))),
            "unknown")

    def test_requires_explicit_flag(self):
        with mock.patch.object(module, "inspect") as action, mock.patch("builtins.print"):
            self.assertEqual(module.main([]), 2)
            action.assert_not_called()
            self.assertEqual(module.main(["--inspect"]), 0)
            action.assert_called_once_with()

    def test_no_device_database_or_phone_mutation(self):
        source = SCRIPT.read_text()
        for forbidden in (
            "bluetoothctl pair", "bluetoothctl remove", "systemctl start",
            "systemctl enable", "pair-setup", "sendMessage(", "contacts-sync",
            "requests.", "subprocess.Popen(",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
