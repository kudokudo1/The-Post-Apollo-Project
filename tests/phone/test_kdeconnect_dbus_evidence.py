"""Synthetic KDE Connect desktop D-Bus evidence tests. No bus/device access."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "phone"))
import KdeConnectDbusEvidence as evidence  # noqa: E402


def report(*, supported=None, loaded=None, providers=None, **changes):
    value = {
        "schema": evidence.SCHEMA, "isPaired": True, "isReachable": True,
        "deviceType": "phone",
        "supportedPlugins": list(supported or []),
        "loadedPlugins": list(loaded or []),
        "activeProviderNames": list(providers or []),
    }
    value.update(changes)
    return value


class DbusEvidenceTests(unittest.TestCase):
    def test_sms_local_plugin_not_equivalent_to_sms_permission(self):
        x = evidence.assess(report(
            supported=["kdeconnect_sms"], loaded=["kdeconnect_sms"]))
        self.assertEqual(x["state"], "PAIRED_REACHABLE_REPORTED")
        self.assertEqual(x["sms"], "LOCAL_PLUGIN_LOADED")
        self.assertEqual(x["smsPermission"], "NOT_CHECKED")
        self.assertFalse(x["routeEligible"])

    def test_contacts_local_plugin_not_equivalent_to_phone_contacts(self):
        x = evidence.assess(report(
            supported=["kdeconnect_contacts"], loaded=["kdeconnect_contacts"]))
        self.assertEqual(x["contacts"], "LOCAL_PLUGIN_LOADED")
        self.assertEqual(x["contactsPermission"], "NOT_CHECKED")
        self.assertFalse(x["routeEligible"])

    def test_telephony_event_not_equivalent_to_call_audio(self):
        x = evidence.assess(report(
            supported=["kdeconnect_telephony"], loaded=["kdeconnect_telephony"]))
        self.assertEqual(x["telephonyEvents"], "LOCAL_PLUGIN_LOADED")
        self.assertEqual(x["callAudio"], "NOT_CHECKED")
        self.assertFalse(x["routeEligible"])

    def test_all_local_plugins_loaded_still_cannot_route(self):
        plugins = list(evidence.PLUGINS.values())
        x = evidence.assess(report(
            supported=plugins, loaded=plugins, providers=["LanLinkProvider"]))
        self.assertEqual([x["sms"], x["contacts"], x["telephonyEvents"]],
                         ["LOCAL_PLUGIN_LOADED"] * 3)
        self.assertEqual(x["transport"], "UNVERIFIED")
        self.assertEqual(x["devicePlatform"], "UNVERIFIED")
        self.assertFalse(x["routeEligible"])

    def test_supported_but_not_loaded_is_not_available(self):
        x = evidence.assess(report(supported=["kdeconnect_sms"]))
        self.assertEqual(x["sms"], "SUPPORTED_NOT_LOADED")
        self.assertEqual(x["contacts"], "NOT_ADVERTISED")

    def test_not_advertised_plugin_remains_unavailable(self):
        x = evidence.assess(report())
        self.assertEqual(x["sms"], "NOT_ADVERTISED")
        self.assertEqual(x["contacts"], "NOT_ADVERTISED")
        self.assertEqual(x["telephonyEvents"], "NOT_ADVERTISED")

    def test_unpaired_device_never_reports_plugin_ready(self):
        x = evidence.assess(report(isPaired=False, supported=["kdeconnect_sms"]))
        self.assertEqual(x["state"], "NOT_PAIRED")
        self.assertEqual(x["sms"], "NOT_EVALUATED")
        self.assertFalse(x["routeEligible"])

    def test_unreachable_device_never_reports_plugin_ready(self):
        x = evidence.assess(report(isReachable=False, supported=["kdeconnect_sms"]))
        self.assertEqual(x["state"], "NOT_REACHABLE")
        self.assertEqual(x["sms"], "NOT_EVALUATED")

    def test_loaded_plugin_when_unpaired_is_inconsistent(self):
        x = evidence.assess(report(
            isPaired=False, supported=["kdeconnect_sms"], loaded=["kdeconnect_sms"]))
        self.assertEqual(x["state"], "INCONSISTENT_REPORT")
        self.assertEqual(x["sms"], "NOT_EVALUATED")

    def test_loaded_plugin_not_supported_is_inconsistent(self):
        x = evidence.assess(report(loaded=["kdeconnect_sms"]))
        self.assertEqual(x["state"], "INCONSISTENT_REPORT")
        self.assertEqual(x["sms"], "NOT_EVALUATED")

    def test_link_provider_when_unreachable_is_inconsistent(self):
        x = evidence.assess(report(isReachable=False, providers=["LanLinkProvider"]))
        self.assertEqual(x["state"], "INCONSISTENT_REPORT")
        self.assertEqual(x["transport"], "UNVERIFIED")

    def test_no_network_inference_from_provider_name(self):
        for name in ["LanLinkProvider", "BluetoothLinkProvider", "unknown_provider"]:
            with self.subTest(name=name):
                x = evidence.assess(report(providers=[name]))
                self.assertEqual(x["transport"], "UNVERIFIED")
                self.assertFalse(x["routeEligible"])
                self.assertEqual(x["reportedActiveLinkCount"], 1)

    def test_phone_type_does_not_prove_android(self):
        for device_type in ["phone", "tablet", "desktop"]:
            with self.subTest(device_type=device_type):
                x = evidence.assess(report(deviceType=device_type))
                self.assertEqual(x["devicePlatform"], "UNVERIFIED")
                self.assertEqual(x["reportedPhoneType"], device_type == "phone")

    def test_extra_fields_rejected_including_secret_metadata(self):
        for changes in [{"phoneNumber": "dummy"}, {"deviceId": "private"}, {"contact": "name"}]:
            with self.subTest(changes=changes):
                with self.assertRaises(ValueError):
                    evidence.assess(report(**changes))

    def test_missing_fields_and_bad_schema_rejected(self):
        sample = report()
        del sample["loadedPlugins"]
        with self.assertRaises(ValueError):
            evidence.assess(sample)
        with self.assertRaises(ValueError):
            evidence.assess(report(schema="other"))
        with self.assertRaises(ValueError):
            evidence.assess([])

    def test_no_truthy_bool_substitution(self):
        for key in ["isPaired", "isReachable"]:
            for wrong in [1, 0, "true", None]:
                with self.subTest(key=key, wrong=wrong):
                    with self.assertRaises(ValueError):
                        evidence.assess(report(**{key: wrong}))

    def test_invalid_names_or_duplicate_plugins_rejected(self):
        variants = [
            {"loaded": ["kdeconnect_sms", "kdeconnect_sms"]},
            {"supported": ["sms with spaces"]},
            {"providers": ["provider\nsecret"]},
            {"supported": ["a" * 81]},
            {"loaded": ["kdeconnect_sms"] * 65},
            {"providers": [f"provider{i}" for i in range(9)]},
        ]
        for variant in variants:
            with self.subTest(variant=str(variant)[:70]):
                with self.assertRaises(ValueError):
                    evidence.assess(report(**variant))

    def test_non_list_collections_rejected(self):
        for change in [
            {"supportedPlugins": {"kdeconnect_sms"}},
            {"loadedPlugins": "kdeconnect_sms"},
            {"activeProviderNames": None},
        ]:
            with self.subTest(change=change):
                with self.assertRaises(ValueError):
                    evidence.assess(report(**change))

    def test_result_redacts_names_and_never_echoes_plugin_ids(self):
        x = evidence.assess(report(
            supported=["kdeconnect_sms", "kdeconnect_contacts"],
            loaded=["kdeconnect_sms"],
            providers=["privateLinkProvider"]))
        self.assertEqual(set(x), {
            "schema", "provider", "execution", "state",
            "reportedPhoneType", "reportedActiveLinkCount", "transport",
            "devicePlatform", "sms", "contacts", "telephonyEvents",
            "smsPermission", "contactsPermission", "callAudio", "routeEligible",
        })
        self.assertEqual(x["execution"], "ASSESS_ONLY")
        self.assertNotIn("privateLinkProvider", str(x))
        self.assertNotIn("kdeconnect_sms", str(x))

    def test_immutable_output_policy_even_when_reachable(self):
        x = evidence.assess(report(supported=list(evidence.PLUGINS.values()),
                                  loaded=list(evidence.PLUGINS.values())))
        self.assertFalse(x["routeEligible"])
        self.assertEqual(x["smsPermission"], "NOT_CHECKED")
        self.assertEqual(x["contactsPermission"], "NOT_CHECKED")
        self.assertEqual(x["callAudio"], "NOT_CHECKED")


if __name__ == "__main__":
    unittest.main()
