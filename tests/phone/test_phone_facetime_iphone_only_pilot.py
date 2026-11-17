"""iPhone-only FaceTime pilot: no private reads, no false call authority."""
from __future__ import annotations

import importlib
import io
from contextlib import redirect_stdout
from pathlib import Path
import sys
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "phone"))
pilot = importlib.import_module("PhoneFaceTimeIphonePilot")
Audio = importlib.import_module("PhoneAudioControls")
Route = importlib.import_module("PhoneFaceTimeAudioRouteProbe")
SOURCE = (ROOT / "services/phone/PhoneFaceTimeIphonePilot.py").read_text()


def provider(**extra):
    data = Audio._output(
        "OBSERVED", {
            "preference": "AUTO", "route": "PC",
            "calls_enabled": False, "calls_state": "UNKNOWN",
        }, can_adjust=True, ofono=True)
    data.update(extra)
    return data


def audio(**extra):
    data = Route._response(
        "HFP_SYSTEM_PROFILE_ACTIVE", system=True, offered=True, active=True
    )
    data.update(extra)
    return data


def raw_status(**extra):
    data = {
        "api_version": 2, "daemon": True, "map": True, "pbap": False,
        "calls_enabled": False, "notification_muted_app_count": 2,
        "phone": "PRIVATE_DEVICE", "contacts": ["PRIVATE_CONTACT"],
    }
    data.update(extra)
    return data


class IphonePilotTests(unittest.TestCase):
    def check_locked(self, value):
        self.assertEqual(set(value), {
            "schema", "execution", "blueferryResponding",
            "cellularCallsPreference", "iphoneDataLinkSelfReported",
            "notificationAppInventoryAdvertised", "localHfpOffered",
            "localHfpActive", "outboundIphoneShortcutVerified",
            "outboundPcDispatchAvailable", "incomingFaceTimeDetected",
            "answerFaceTimeAvailable", "endFaceTimeAvailable",
            "liveFaceTimeVideoAvailable", "twoWayFaceTimeAudioVerified",
            "iphoneCompanionAuthenticated", "faceTimeConnected",
            "canChangeRoute", "contentAccessEnabled", "personalSaveAuthorized",
        })
        self.assertEqual(value["schema"], pilot.SCHEMA)
        self.assertEqual(value["execution"], pilot.EXECUTION)
        for field in (
            "outboundIphoneShortcutVerified", "outboundPcDispatchAvailable",
            "incomingFaceTimeDetected", "answerFaceTimeAvailable",
            "endFaceTimeAvailable", "liveFaceTimeVideoAvailable",
            "twoWayFaceTimeAudioVerified", "iphoneCompanionAuthenticated",
            "faceTimeConnected", "canChangeRoute",
            "contentAccessEnabled", "personalSaveAuthorized",
        ):
            self.assertIs(value[field], False, field)
        for secret in ("PRIVATE_CONTACT", "PRIVATE_DEVICE",
                       "phoneNumbers", "message", "caller", "mac", "profileId"):
            self.assertNotIn(secret, str(value))

    def test_actual_disabled_blueferry_status_is_observed_not_broken(self):
        data = pilot.inspect(provider=provider, raw_status=raw_status, route=audio)
        self.check_locked(data)
        self.assertIs(data["blueferryResponding"], True)
        self.assertEqual(data["cellularCallsPreference"], "OFF")
        self.assertIs(data["iphoneDataLinkSelfReported"], True)
        self.assertIs(data["notificationAppInventoryAdvertised"], True)
        self.assertIs(data["localHfpActive"], True)
        self.assertIs(data["incomingFaceTimeDetected"], False)
        self.assertIs(data["twoWayFaceTimeAudioVerified"], False)

    def test_real_raw_disabled_calls_contract_flows_through_existing_projection(self):
        raw = raw_status()
        self.assertNotIn("calls_state", raw)
        projected = Audio._project(raw)
        self.assertIsNotNone(projected)
        self.assertEqual(projected["calls_state"], "UNKNOWN")
        report = Audio._output("OBSERVED", projected, can_adjust=True, ofono=True)
        value = pilot.inspect(
            provider=lambda: report, raw_status=lambda: raw, route=audio)
        self.check_locked(value)
        self.assertEqual(value["cellularCallsPreference"], "OFF")

    def test_provider_unreachable_does_not_read_extra_status(self):
        raw = mock.Mock()
        for provider_data in (
            {}, Audio._output("BRIDGE_UNAVAILABLE"),
            provider(result="BRIDGE_UNAVAILABLE"),
            provider(trustedPhoneLink="VERIFIED"),
            provider(contentAccessEnabled=True),
            provider(ofonoActive="true"),
        ):
            with self.subTest(provider=str(provider_data)[:100]):
                result = pilot.inspect(
                    provider=lambda: provider_data, raw_status=raw, route=audio)
                self.check_locked(result)
                self.assertIs(result["blueferryResponding"], False)
                self.assertEqual(result["cellularCallsPreference"], "UNKNOWN")
        raw.assert_not_called()

    def test_on_unknown_and_spoofed_status_never_grants_facetime(self):
        for values, expected in (
            ({"callsEnabled": True, "callsState": "READY"}, "ON"),
            ({"callsEnabled": True, "callsState": "UNKNOWN"}, "ON"),
            ({"callsEnabled": None}, "UNKNOWN"),
            ({"callsEnabled": "true"}, "UNKNOWN"),
            ({"callsEnabled": False, "callsState": "READY"}, "OFF"),
        ):
            with self.subTest(values=values):
                result = pilot.inspect(
                    provider=lambda: provider(**values),
                    raw_status=raw_status, route=audio)
                self.check_locked(result)
                self.assertEqual(result["cellularCallsPreference"], expected)
                self.assertIs(result["faceTimeConnected"], False)

    def test_app_inventory_is_capability_marker_not_call_detection(self):
        for cap, expected in ((None, False), (True, False), ("2", False),
                              (-1, False), (3, True), (0, True)):
            with self.subTest(cap=cap):
                result = pilot.inspect(
                    provider=provider,
                    raw_status=lambda: raw_status(notification_muted_app_count=cap),
                    route=audio)
                self.check_locked(result)
                self.assertIs(result["notificationAppInventoryAdvertised"], expected)
                self.assertIs(result["incomingFaceTimeDetected"], False)

    def test_invalid_raw_dbus_payload_fails_closed(self):
        for raw in (None, "PRIVATE", [], {}, raw_status(api_version=1),
                    raw_status(daemon=False),
                    raw_status(api_version=True), raw_status(map="yes", pbap="no")):
            with self.subTest(raw=str(raw)[:70]):
                result = pilot.inspect(
                    provider=provider, raw_status=lambda: raw, route=audio)
                self.check_locked(result)
                if isinstance(raw, dict) and raw.get("api_version") == 2 \
                        and raw.get("daemon") is True:
                    self.assertFalse(result["iphoneDataLinkSelfReported"])
                else:
                    self.assertFalse(result["notificationAppInventoryAdvertised"])

    def test_hfp_candidate_is_never_an_active_facetime_call(self):
        for route, offered, active in (
            (audio(), True, True),
            (audio(systemHfpProfileActive=False), True, False),
            (audio(systemHfpProfileActive=False,
                   systemHfpProfileOffered=False), False, False),
            (audio(faceTimeConnected=True), False, False),
            (audio(faceTimeCallControl=True), False, False),
            (audio(providerAuthenticated=True), False, False),
            ({}, False, False),
            (None, False, False),
            (audio(systemAudioObserved=False), False, False),
        ):
            with self.subTest(route=str(route)[:80]):
                output = pilot.inspect(
                    provider=provider, raw_status=raw_status,
                    route=lambda: route)
                self.check_locked(output)
                self.assertIs(output["localHfpOffered"], offered)
                self.assertIs(output["localHfpActive"], active)

    def test_failures_are_bounded_and_never_print_private_payload(self):
        boom = mock.Mock(side_effect=RuntimeError("PRIVATE_IDENTIFIERS"))
        for key in ("provider", "raw_status", "route"):
            callbacks = {
                "provider": provider, "raw_status": raw_status, "route": audio
            }
            callbacks[key] = boom
            value = pilot.inspect(**callbacks)
            self.check_locked(value)
            self.assertNotIn("PRIVATE_IDENTIFIERS", str(value))

    def test_cli_is_preflight_only_no_launch(self):
        stream = io.StringIO()
        with redirect_stdout(stream):
            self.assertEqual(pilot.main(["--send-call"]), 2)
        self.assertIn("EXPLICIT_ACTION_REQUIRED", stream.getvalue())
        with mock.patch.object(pilot, "inspect", return_value=pilot.inspect(
            provider=provider, raw_status=raw_status, route=audio)):
            stream = io.StringIO()
            with redirect_stdout(stream):
                self.assertEqual(pilot.main(["--preflight"]), 0)
            self.assertIn('"outboundPcDispatchAvailable": false', stream.getvalue())

        for prohibited in (
            "ListNotifications(", "ListNotificationApps(", "SetCallsEnabled",
            "OpenNotification", "Dial(", "Answer(", "Hangup(",
            "subprocess.Popen", "subprocess.run", "systemctl", "pactl set-",
            "socket", "requests", "urllib", "BluetoothConnect",
            "PhonePersonalSave", "localStorage", "secret-tool",
            "faceTimeConnected\": True",
        ):
            self.assertNotIn(prohibited, SOURCE)


if __name__ == "__main__":
    unittest.main()
