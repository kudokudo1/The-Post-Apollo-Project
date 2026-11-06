"""Device identity is observed, never inferred from an audio route or a label."""
from __future__ import annotations

import importlib
from pathlib import Path
import sys
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "phone"))
module = importlib.import_module("PhoneDeviceObservation")
ID = "123e4567-e89b-42d3-a456-426614174000"
MAC = "AA:BB:CC:DD:EE:FF"


def report(**changes):
    value = {"api_version": 2, "daemon": True, "phone_profile_id": ID,
             "map": True, "pbap": False}
    value.update(changes)
    return value


class ObservationTests(unittest.TestCase):
    def inspect(self, *, status=None, config=(ID, MAC), device=None):
        if status is None:
            status = report()
        if device is None:
            device = {"paired": True, "connected": True, "alias": "Work iPhone"}
        return module.observe(backend=lambda: status, binding=lambda: config,
                              bluez=lambda address: (
                                  self.assertEqual(address, MAC) or device))

    def check_locked(self, value):
        self.assertEqual(value["schema"], module.SCHEMA)
        self.assertEqual(value["execution"], "READ_ONLY_DEVICE_OBSERVATION")
        self.assertEqual(value["trustedPhoneLink"], "UNVERIFIED")
        self.assertIs(value["contentAccessEnabled"], False)
        self.assertEqual(set(value), {
            "schema", "execution", "state", "profileId", "displayName",
            "bluetoothLink", "trustedPhoneLink", "contentAccessEnabled",
        })
        self.assertNotIn(MAC, str(value))

    def test_exact_profile_and_paired_bluez_link(self):
        v = self.inspect()
        self.check_locked(v)
        self.assertEqual(v["state"], "BLUETOOTH_CONNECTED")
        self.assertEqual(v["bluetoothLink"], "CONNECTED")
        self.assertEqual(v["profileId"], ID)
        self.assertEqual(v["displayName"], "Work iPhone")

    def test_paired_but_not_connected_and_unknown_link_are_distinct(self):
        v = self.inspect(device={"paired": True, "connected": False,
                                 "alias": "My iPhone"})
        self.check_locked(v)
        self.assertEqual(v["state"], "PAIRED_OFFLINE")
        self.assertEqual(v["bluetoothLink"], "PAIRED_OFFLINE")
        unknown = self.inspect(device={"paired": False, "connected": True,
                                       "alias": "Untrusted iPhone"})
        self.check_locked(unknown)
        self.assertEqual(unknown["state"], "PROFILE_ONLY")
        self.assertEqual(unknown["bluetoothLink"], "UNVERIFIED")
        self.assertEqual(unknown["displayName"], "iPhone")

    def test_profile_mismatch_never_claims_a_named_device(self):
        with self.subTest("profile mismatch"):
            v = self.inspect(config=("f23e4567-e89b-42d3-a456-426614174000", MAC))
            self.check_locked(v)
            self.assertEqual(v["state"], "PROFILE_ONLY")
            self.assertEqual(v["displayName"], "iPhone")
        with self.subTest("no config"):
            v = self.inspect(config=None)
            self.check_locked(v)
            self.assertEqual(v["state"], "PROFILE_ONLY")

    def test_backend_without_valid_opaque_profile_never_selects_a_phone(self):
        for status in (None, {}, report(phone_profile_id=None),
                       report(phone_profile_id=MAC), report(map="true"),
                       report(api_version=3), report(daemon=False)):
            with self.subTest(status=status):
                v = module.observe(backend=lambda: status,
                                   binding=mock.Mock(side_effect=AssertionError),
                                   bluez=mock.Mock(side_effect=AssertionError))
                self.check_locked(v)
                self.assertEqual(v["state"], "UNAVAILABLE")
                self.assertEqual(v["profileId"], "")

    def test_untrusted_alias_is_not_rendered_and_no_grants_created(self):
        for name in ("", "\nEvil", "<script>" * 12, "A" * 100):
            with self.subTest(name=name):
                v = self.inspect(device={"paired": True, "connected": True,
                                         "alias": name})
                self.check_locked(v)
                self.assertEqual(v["displayName"], "iPhone")
        source = (ROOT / "services/phone/PhoneDeviceObservation.py").read_text()
        for forbidden in ("bluetoothctl pair", "bluetoothctl remove",
                          "Pair(", "Disconnect(", "Connect(", "StartDiscovery(",
                          "ListThreads(", "ListContacts(", "SendMessage(",
                          "subprocess.Popen(", "contacts-sync"):
            self.assertNotIn(forbidden, source)

    def test_read_errors_and_wrong_flags_fail_closed(self):
        for device in ({"paired": "yes", "connected": True, "alias": "X"},
                       {"paired": True, "connected": "true", "alias": "X"}):
            v = self.inspect(device=device)
            self.check_locked(v)
            self.assertEqual(v["state"], "PROFILE_ONLY")
        for reader in (
            lambda: (_ for _ in ()).throw(ValueError("private data")),
            lambda: (_ for _ in ()).throw(OSError("private data")),
        ):
            v = module.observe(backend=reader)
            self.check_locked(v)
            self.assertEqual(v["state"], "UNAVAILABLE")

    def test_explicit_check_only(self):
        with mock.patch.object(module, "observe", return_value={"schema":module.SCHEMA}) as reader:
            with mock.patch("builtins.print"):
                self.assertEqual(module.main([]), 2)
                reader.assert_not_called()
                self.assertEqual(module.main(["--inspect"]), 0)
                reader.assert_called_once_with()

    def test_source_keeps_mac_private_and_os_config_read_only(self):
        source = (ROOT / "services/phone/PhoneDeviceObservation.py").read_text()
        self.assertIn('os.O_RDONLY', source)
        self.assertIn('O_NOFOLLOW', source)
        self.assertIn('owner = str(bus.get_name_owner(SERVICE))', source)
        self.assertIn('bus.name_has_owner("org.bluez")', source)
        self.assertNotIn('"deviceMac":', source)
        self.assertNotIn('"address":', source)
        self.assertNotIn("print(status)", source)


if __name__ == "__main__":
    unittest.main()
