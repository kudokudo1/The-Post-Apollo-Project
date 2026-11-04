"""Synthetic, offline provider-observation contract tests."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

PATH = (Path(__file__).resolve().parents[2] / "services" / "phone"
        / "PhoneProviderObservation.py")
SPEC = importlib.util.spec_from_file_location("phone_provider_observation", PATH)
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


def blueferry(**changes):
    item = {
        "schema": module.BLUEFERRY_SCHEMA, "execution": "READ_ONLY",
        "blueferryInstalled": True, "bluetoothService": "active",
        "controllerPowered": True, "configurationPresent": True,
        "backendService": "active", "backendObservation": "REPORTED",
        "mapSessionActive": True, "pbapSessionActive": False,
        "phoneLink": "UNVERIFIED", "contentAuthorized": False,
    }
    item.update(changes)
    return item


def kde(**changes):
    item = {
        "schema": module.KDE_SCHEMA, "execution": "DIAGNOSTIC_ONLY",
        "provider": "kdeconnect", "state": "METADATA_REPORTED",
        "reportedPairedReachableCount": 2, "localSmsPluginCount": 1,
        "localContactsPluginCount": 1, "localTelephonyPluginCount": 0,
        "devicePlatform": "UNVERIFIED", "transport": "UNVERIFIED",
        "smsPermission": "NOT_CHECKED", "contactsPermission": "NOT_CHECKED",
        "callAudio": "NOT_CHECKED", "routeEligible": False,
    }
    item.update(changes)
    return item


class ProjectionTests(unittest.TestCase):
    def assert_locked(self, result):
        self.assertEqual(result["schema"], module.SCHEMA)
        self.assertEqual(result["execution"], "PROJECTION_ONLY")
        self.assertIs(result["routeEligible"], False)
        self.assertIs(result["contentAccessEnabled"], False)
        for key in ("trustedPhoneLink", "personBinding", "deviceBinding",
                    "lineBinding", "organizationBinding"):
            self.assertEqual(result[key], "UNVERIFIED")

    def test_two_observations_stay_non_authoritative(self):
        result = module.project(blueferry(), kde())
        self.assert_locked(result)
        self.assertEqual(result["providers"]["BLUEFERRY"], {
            "state": "REPORTED", "mapProfile": "ACTIVE_BACKEND_REPORT",
            "pbapProfile": "INACTIVE_BACKEND_REPORT",
        })
        self.assertEqual(result["providers"]["KDECONNECT"], {
            "state": "METADATA_REPORTED", "pairedReachableReported": 2,
            "smsPluginReported": 1, "contactsPluginReported": 1,
            "telephonyPluginReported": 0, "devicePlatform": "UNVERIFIED",
        })

    def test_blueferry_error_does_not_mask_kde_or_reveal_private_data(self):
        result = module.project(blueferry(message="PRIVATE"), kde())
        self.assert_locked(result)
        self.assertEqual(result["providers"]["BLUEFERRY"]["state"], "UNAVAILABLE")
        self.assertEqual(result["providers"]["KDECONNECT"]["state"], "METADATA_REPORTED")
        self.assertNotIn("PRIVATE", str(result))

    def test_kde_error_does_not_mask_blueferry_or_reveal_private_data(self):
        result = module.project(blueferry(), kde(phoneNumber="PRIVATE"))
        self.assert_locked(result)
        self.assertEqual(result["providers"]["KDECONNECT"]["state"], "UNAVAILABLE")
        self.assertEqual(result["providers"]["BLUEFERRY"]["state"], "REPORTED")
        self.assertNotIn("PRIVATE", str(result))

    def test_blueferry_untrusted_permission_or_status_claims(self):
        cases = (
            {"contentAuthorized": True}, {"contentAuthorized": 0},
            {"phoneLink": "VERIFIED"}, {"execution": "WRITE"},
            {"mapSessionActive": 1}, {"pbapSessionActive": "true"},
            {"backendObservation": "READY"}, {"schema": "other"},
            {"backendService": "inactive"}, {"controllerPowered": "yes"},
            {"bluetoothService": []},
        )
        for change in cases:
            with self.subTest(change=change):
                result = module.project(blueferry(**change), kde())
                self.assert_locked(result)
                self.assertEqual(result["providers"]["BLUEFERRY"]["state"],
                                 "UNAVAILABLE")

    def test_blueferry_nonreported_profiles_remain_unverified(self):
        for state in ("NOT_RUNNING", "NO_OWNER", "UNAVAILABLE"):
            with self.subTest(state=state):
                item = blueferry(
                    backendObservation=state, mapSessionActive=None,
                    pbapSessionActive=None,
                    backendService=("inactive" if state == "NOT_RUNNING"
                                    else "active"))
                result = module.project(item, kde())
                self.assert_locked(result)
                self.assertEqual(result["providers"]["BLUEFERRY"]["state"], state)
                self.assertEqual(result["providers"]["BLUEFERRY"]["mapProfile"],
                                 "UNVERIFIED")
        invalid = module.project(
            blueferry(backendObservation="NO_OWNER", mapSessionActive=True), kde())
        self.assertEqual(invalid["providers"]["BLUEFERRY"]["state"], "UNAVAILABLE")

    def test_kde_plugin_is_not_an_android_permission(self):
        result = module.project(blueferry(), kde(localSmsPluginCount=2))
        self.assert_locked(result)
        self.assertEqual(result["providers"]["KDECONNECT"]["smsPluginReported"], 2)
        self.assertEqual(result["providers"]["KDECONNECT"]["devicePlatform"],
                         "UNVERIFIED")
        self.assertNotIn("ANDROID", str(result))
        self.assertNotIn("GRANTED", str(result))

    def test_claiming_android_device_without_proof_is_rejected(self):
        result = module.project(blueferry(), kde(devicePlatform="ANDROID"))
        self.assert_locked(result)
        self.assertEqual(result["providers"]["KDECONNECT"]["state"], "UNAVAILABLE")

    def test_kde_fake_authorization_transport_or_platform_is_rejected(self):
        cases = (
            {"smsPermission": "GRANTED"}, {"contactsPermission": "GRANTED"},
            {"transport": "NETWORK"}, {"callAudio": "READY"},
            {"routeEligible": True}, {"routeEligible": 0},
            {"execution": "ACTIVE"}, {"provider": "android"},
            {"schema": "other"}, {"state": []},
        )
        for change in cases:
            with self.subTest(change=change):
                result = module.project(blueferry(), kde(**change))
                self.assert_locked(result)
                self.assertEqual(result["providers"]["KDECONNECT"]["state"],
                                 "UNAVAILABLE")

    def test_kde_counts_are_bounded_and_exact_integers(self):
        cases = (
            {"reportedPairedReachableCount": True},
            {"reportedPairedReachableCount": -1},
            {"reportedPairedReachableCount": 5},
            {"localSmsPluginCount": 3},
            {"localContactsPluginCount": 1.0},
            {"localTelephonyPluginCount": "1"},
            {"reportedPairedReachableCount": 0},
        )
        for change in cases:
            with self.subTest(change=change):
                result = module.project(blueferry(), kde(**change))
                self.assertEqual(result["providers"]["KDECONNECT"]["state"],
                                 "UNAVAILABLE")

    def test_kde_nonreported_status_has_no_counts(self):
        states = (
            "BUSCTL_NOT_INSTALLED", "SERVICE_NOT_RUNNING",
            "NO_PAIRED_REACHABLE_DEVICES", "METADATA_UNAVAILABLE",
            "BUS_TIMEOUT", "EXPLICIT_FLAG_REQUIRED",
        )
        for state in states:
            with self.subTest(state=state):
                value = kde(
                    state=state, reportedPairedReachableCount=0,
                    localSmsPluginCount=0, localContactsPluginCount=0,
                    localTelephonyPluginCount=0)
                result = module.project(blueferry(), value)
                self.assert_locked(result)
                self.assertEqual(result["providers"]["KDECONNECT"]["state"], state)
                self.assertIsNone(result["providers"]["KDECONNECT"]
                                  ["pairedReachableReported"])
        invalid = module.project(blueferry(), kde(state="SERVICE_NOT_RUNNING"))
        self.assertEqual(invalid["providers"]["KDECONNECT"]["state"], "UNAVAILABLE")

    def test_malformed_inputs_fail_independently_without_echo(self):
        for bad in (None, {}, [], "SECRET", 1, {"phone": "PRIVATE"}):
            with self.subTest(type=type(bad).__name__):
                result = module.project(bad, bad)
                self.assert_locked(result)
                self.assertEqual(result["providers"]["BLUEFERRY"]["state"],
                                 "UNAVAILABLE")
                self.assertEqual(result["providers"]["KDECONNECT"]["state"],
                                 "UNAVAILABLE")
                self.assertNotIn("SECRET", str(result))
                self.assertNotIn("PRIVATE", str(result))

    def test_no_identifier_or_content_projection(self):
        result = module.project(blueferry(), kde())
        self.assertEqual(set(result), {
            "schema", "execution", "trustedPhoneLink", "personBinding",
            "deviceBinding", "lineBinding", "organizationBinding",
            "routeEligible", "contentAccessEnabled", "providers",
        })
        for secret in ("person-fixture", "device-fixture", "org-fixture",
                       "line-fixture", "session token", "message body"):
            self.assertNotIn(secret, str(result))

    def test_projection_source_does_not_do_host_io(self):
        source = PATH.read_text()
        for forbidden in ("import subprocess", "import dbus", "import socket",
                          "import requests", "os.system(", "Popen(", "open(",
                          "write_text(", "run("):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
