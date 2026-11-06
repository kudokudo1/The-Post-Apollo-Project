"""Synthetic, content-free checks for iPhone MAP/PBAP status diagnostics."""
from __future__ import annotations

import importlib
from pathlib import Path
import sys
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "phone"))
module = importlib.import_module("PhoneContentDiagnostic")
PROFILE = "123e4567-e89b-42d3-a456-426614174000"
OTHER = "223e4567-e89b-42d3-a456-426614174000"


def device(**changes):
    result = {
        "schema": "post-apollo.phone.device-observation.v0",
        "execution": "READ_ONLY_DEVICE_OBSERVATION",
        "state": "BLUETOOTH_CONNECTED",
        "profileId": PROFILE,
        "displayName": "iPhone",
        "bluetoothLink": "CONNECTED",
        "trustedPhoneLink": "UNVERIFIED",
        "contentAccessEnabled": False,
    }
    result.update(changes)
    return result


def status(**changes):
    result = {
        "daemon": True, "api_version": 2,
        "phone_profile_id": PROFILE,
        "map": True, "pbap": True,
        "contact_card_count": 7,
        "privateInformation": "PRIVATE NUMBER AND CONTENT",
    }
    result.update(changes)
    return result


class ContentDiagnosticTests(unittest.TestCase):
    def check(self, *, obs=None, backend=None):
        if obs is None:
            obs = device()
        if backend is None:
            backend = status()
        return module.inspect(device_reader=lambda: obs,
                              status_reader=lambda: backend)

    def locked(self, result):
        self.assertEqual(result["schema"], module.SCHEMA)
        self.assertEqual(result["execution"], "READ_ONLY_PROVIDER_METADATA")
        self.assertEqual(result["trustedPhoneLink"], "UNVERIFIED")
        self.assertEqual(result["socialLink"], "NOT_AUTHORIZED")
        self.assertIs(result["routeEligible"], False)
        self.assertIs(result["contentAccessEnabled"], False)
        self.assertEqual(set(result), {
            "schema", "execution", "state", "deviceState", "messages",
            "contacts", "socialLink", "trustedPhoneLink", "routeEligible",
            "contentAccessEnabled",
        })
        self.assertEqual(set(result["messages"]), {"state"})
        self.assertEqual(set(result["contacts"]), {"state", "cachedCount"})
        self.assertNotIn(PROFILE, str(result))
        self.assertNotIn("PRIVATE", str(result))
        self.assertNotIn("iPhone", str(result))
        self.assertNotIn("mac", str(result).lower())

    def test_matching_profile_reports_only_map_pbap_and_bounded_count(self):
        value = self.check()
        self.locked(value)
        self.assertEqual(value["state"], "BACKEND_REPORTED")
        self.assertEqual(value["deviceState"], "BLUETOOTH_CONNECTED")
        self.assertEqual(value["messages"]["state"], "MAP_ACTIVE_BACKEND_REPORT")
        self.assertEqual(value["contacts"]["state"], "PBAP_ACTIVE_BACKEND_REPORT")
        self.assertEqual(value["contacts"]["cachedCount"], 7)

    def test_audio_link_does_not_imply_message_or_contacts_profiles(self):
        result = self.check(backend=status(map=False, pbap=False))
        self.locked(result)
        self.assertEqual(result["messages"]["state"], "MAP_INACTIVE_BACKEND_REPORT")
        self.assertEqual(result["contacts"]["state"], "PBAP_INACTIVE_BACKEND_REPORT")
        self.assertEqual(result["contacts"]["cachedCount"], 7)
        self.assertEqual(result["socialLink"], "NOT_AUTHORIZED")

    def test_no_contacts_cached_is_distinct_from_no_contact_support(self):
        zero = self.check(backend=status(contact_card_count=0))
        missing = self.check(backend=status(contact_card_count=None))
        invalid = self.check(backend=status(contact_card_count="0"))
        for result in (zero, missing, invalid):
            self.locked(result)
        self.assertEqual(zero["contacts"]["cachedCount"], 0)
        self.assertIsNone(missing["contacts"]["cachedCount"])
        self.assertIsNone(invalid["contacts"]["cachedCount"])

    def test_offline_pairing_does_not_call_backend(self):
        reader = mock.Mock(side_effect=AssertionError("must not read backend"))
        value = module.inspect(
            device_reader=lambda: device(state="PAIRED_OFFLINE",
                                         bluetoothLink="PAIRED_OFFLINE"),
            status_reader=reader,
        )
        reader.assert_not_called()
        self.locked(value)
        self.assertEqual(value["state"], "DEVICE_OFFLINE")
        self.assertEqual(value["deviceState"], "PAIRED_OFFLINE")
        self.assertEqual(value["messages"]["state"], "UNVERIFIED")

    def test_fake_device_or_cross_profile_never_returns_metadata(self):
        invalid = (
            {}, None, device(state="PROFILE_ONLY"),
            device(trustedPhoneLink="VERIFIED"),
            device(contentAccessEnabled=True),
            device(profileId="INVALID"),
            device(bluetoothLink="PAIRED_OFFLINE"),
            device(execution="WRONG"),
        )
        for obs in invalid:
            with self.subTest(obs=obs):
                result = self.check(obs=obs)
                self.locked(result)
                self.assertEqual(result["state"], "UNAVAILABLE")
                self.assertIsNone(result["contacts"]["cachedCount"])
        for report in (
            status(phone_profile_id=OTHER), status(api_version=3),
            status(map="true"), status(pbap=1),
            status(daemon=False), status(phone_profile_id=None),
            None, {},
        ):
            with self.subTest(report=report):
                result = self.check(backend=report)
                self.locked(result)
                self.assertEqual(result["state"], "UNAVAILABLE")

    def test_backend_errors_do_not_leak_private_data(self):
        result = module.inspect(
            device_reader=lambda: device(),
            status_reader=mock.Mock(side_effect=RuntimeError("PRIVATE PHONE DATA")),
        )
        self.locked(result)
        self.assertEqual(result["state"], "UNAVAILABLE")

    def test_explicit_user_action_only(self):
        with mock.patch.object(module, "inspect",
                               return_value=module._fallback()) as reader:
            with mock.patch("builtins.print"):
                self.assertEqual(module.main([]), 2)
                reader.assert_not_called()
                self.assertEqual(module.main(["--inspect"]), 0)
                reader.assert_called_once()

    def test_no_message_contact_queries_or_changes(self):
        script = (ROOT / "services/phone/PhoneContentDiagnostic.py").read_text()
        for forbidden in (
            "ListThreads(", "ListContacts(", "ListContactCards(",
            "GetContact(", "SendToThread(", "subprocess.Popen(", "bluetoothctl",
            "systemctl start", "os.unlink(", "os.replace(", "print(status)",
        ):
            self.assertNotIn(forbidden, script)


if __name__ == "__main__":
    unittest.main()
