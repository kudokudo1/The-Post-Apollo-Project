"""One-action phone setup must remain explicit, redacted and non-connecting."""
import importlib
import sys
from pathlib import Path
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "phone"))
phone = importlib.import_module("PhoneSetupReadiness")
source = importlib.import_module("PhoneProviderObservation")


def blueferry(**updates):
    item = {
        "schema": source.BLUEFERRY_SCHEMA, "execution": "READ_ONLY",
        "blueferryInstalled": True, "bluetoothService": "active",
        "controllerPowered": True, "configurationPresent": True,
        "backendService": "active", "backendObservation": "REPORTED",
        "mapSessionActive": True, "pbapSessionActive": False,
        "phoneLink": "UNVERIFIED", "contentAuthorized": False,
    }
    item.update(updates)
    return item


def kde(**updates):
    item = {
        "schema": source.KDE_SCHEMA, "execution": "DIAGNOSTIC_ONLY",
        "provider": "kdeconnect", "state": "METADATA_REPORTED",
        "reportedPairedReachableCount": 1, "localSmsPluginCount": 1,
        "localContactsPluginCount": 0, "localTelephonyPluginCount": 0,
        "devicePlatform": "UNVERIFIED", "transport": "UNVERIFIED",
        "smsPermission": "NOT_CHECKED", "contactsPermission": "NOT_CHECKED",
        "callAudio": "NOT_CHECKED", "routeEligible": False,
    }
    item.update(updates)
    return item


class PhoneSetupTests(unittest.TestCase):
    def locked(self, result):
        self.assertEqual(result["schema"], phone.SCHEMA)
        self.assertEqual(result["execution"], "READ_ONLY_CHECK")
        self.assertEqual(result["trustedPhoneLink"], "UNVERIFIED")
        self.assertIs(result["routeEligible"], False)
        self.assertIs(result["contentAccessEnabled"], False)

    def test_one_click_reads_each_provider_once_and_never_grants_access(self):
        b, k = mock.Mock(return_value=blueferry()), mock.Mock(return_value=kde())
        result = phone.check(blueferry_reader=b, kdeconnect_reader=k)
        b.assert_called_once_with()
        k.assert_called_once_with()
        self.locked(result)
        self.assertEqual(result["status"], "BRIDGE_REPORTED")
        self.assertEqual(result["providers"]["BLUEFERRY"]["mapProfile"],
                         "ACTIVE_BACKEND_REPORT")
        self.assertEqual(result["providers"]["KDECONNECT"]["smsPluginReported"], 1)
        self.assertNotIn("CONNECTED", str(result))
        self.assertNotIn("GRANTED", str(result))

    def test_no_available_backends_is_not_a_connection(self):
        result = phone.check(
            blueferry_reader=lambda: blueferry(
                backendService="inactive", backendObservation="NOT_RUNNING",
                mapSessionActive=None, pbapSessionActive=None),
            kdeconnect_reader=lambda: kde(
                state="NO_PAIRED_REACHABLE_DEVICES",
                reportedPairedReachableCount=0, localSmsPluginCount=0),
        )
        self.locked(result)
        self.assertEqual(result["status"], "NO_BRIDGE_REPORTED")

    def test_error_from_one_source_does_not_hide_other_source(self):
        def fails():
            raise RuntimeError("PRIVATE PHONE TOKEN")
        result = phone.check(blueferry_reader=fails,
                             kdeconnect_reader=lambda: kde())
        self.locked(result)
        self.assertEqual(result["providers"]["BLUEFERRY"]["state"], "UNAVAILABLE")
        self.assertEqual(result["providers"]["KDECONNECT"]["state"], "METADATA_REPORTED")
        self.assertNotIn("PRIVATE", str(result))

    def test_both_probes_fail_closed_without_private_error(self):
        def fails():
            raise ValueError("MESSAGE BODY")
        result = phone.check(blueferry_reader=fails, kdeconnect_reader=fails)
        self.locked(result)
        self.assertEqual(result["status"], "NO_BRIDGE_REPORTED")
        self.assertNotIn("MESSAGE BODY", str(result))
        self.assertEqual(result["providers"]["BLUEFERRY"]["state"], "UNAVAILABLE")
        self.assertEqual(result["providers"]["KDECONNECT"]["state"], "UNAVAILABLE")

    def test_unsupported_claims_cannot_become_verified_device(self):
        result = phone.check(
            blueferry_reader=lambda: blueferry(contentAuthorized=True),
            kdeconnect_reader=lambda: kde(smsPermission="GRANTED"),
        )
        self.locked(result)
        self.assertEqual(result["status"], "NO_BRIDGE_REPORTED")
        self.assertEqual(result["providers"]["BLUEFERRY"]["state"], "UNAVAILABLE")
        self.assertEqual(result["providers"]["KDECONNECT"]["state"], "UNAVAILABLE")

    def test_missing_explicit_flag_does_not_call_any_probe(self):
        with mock.patch.object(phone, "check") as check, mock.patch("builtins.print") as print_:
            self.assertEqual(phone.main([]), 2)
            check.assert_not_called()
            self.assertIn("EXPLICIT_ACTION_REQUIRED", print_.call_args.args[0])

    def test_explicit_flag_calls_once_and_projects_only_result(self):
        with mock.patch.object(phone, "check", return_value={
            "schema": phone.SCHEMA, "status": "NO_BRIDGE_REPORTED"
        }) as check, mock.patch("builtins.print") as print_:
            self.assertEqual(phone.main(["--check"]), 0)
            check.assert_called_once_with()
            self.assertIn("NO_BRIDGE_REPORTED", print_.call_args.args[0])

    def test_source_does_not_pair_modify_services_or_read_content(self):
        code = (ROOT / "services" / "phone" / "PhoneSetupReadiness.py").read_text()
        for forbidden in ("pair-setup", "systemctl start", "bluetoothctl pair",
                          "sendMessage(", "getMessages(", "os.system(", "Popen("):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, code)


if __name__ == "__main__":
    unittest.main()
