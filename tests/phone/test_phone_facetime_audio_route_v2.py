"""FaceTime Audio candidate, not call presence: pure and actual read-only probes."""
from __future__ import annotations

import importlib
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "phone"))
mod = importlib.import_module("PhoneFaceTimeAudioRouteProbe")
Audio = importlib.import_module("PhoneAudioControls")
SOURCE = ROOT / "services" / "phone" / "PhoneFaceTimeAudioRouteProbe.py"


def provider(**values: object) -> dict:
    data = Audio._output(
        "OBSERVED",
        {
            "preference": "AUTO",
            "route": "PC",
            "calls_enabled": True,
            "calls_state": "READY",
        },
        ofono=True,
        can_adjust=True,
    )
    data.update(values)
    return data


def bluez(*, profile="headset-head-unit", offered=None) -> dict:
    return {
        "name": "bluez_card.XX_YY_ZZ_WW",
        "properties": {"device.api": "bluez5", "device.bus": "bluetooth",
                       "device.description": "PRIVATE_PERSON_DEVICE"},
        "profiles": [{"name": p} for p in (offered or
                    ["a2dp-sink", "headset-head-unit", "headset-head-unit-msbc"])],
        "active_profile": {"name": profile},
        "ports": [{"name": "PRIVATE_AUDIO_PORT"}],
    }


class FaceTimeAudioRouteTests(unittest.TestCase):
    def assert_locked(self, result):
        self.assertEqual(set(result), {
            "schema", "execution", "state", "phoneBackendObserved",
            "cellularHfpReadyReported", "systemAudioObserved",
            "systemHfpProfileOffered", "systemHfpProfileActive",
            "faceTimeAudioVerified", "faceTimeConnected",
            "faceTimeCallControl", "microphoneVerified", "speakerVerified",
            "canChangeRoute", "providerAuthenticated", "personalDataAccess",
        })
        self.assertEqual(result["schema"], mod.SCHEMA)
        self.assertEqual(result["execution"], "READ_ONLY_USER_INITIATED")
        for field in (
            "faceTimeAudioVerified", "faceTimeConnected",
            "faceTimeCallControl", "microphoneVerified", "speakerVerified",
            "canChangeRoute", "providerAuthenticated", "personalDataAccess",
        ):
            self.assertIs(result[field], False, field)
        for private in ("PRIVATE_PERSON", "XX_YY", "bluez_card", "phoneNumbers",
                        "remote", "phonebook", "contacts", "facetime.apple.com/join"):
            self.assertNotIn(private, str(result))

    def test_active_profile_is_only_system_hfp_not_facetime_identity(self):
        data = mod.inspect(provider=provider, cards=lambda: (True, True))
        self.assert_locked(data)
        self.assertEqual(data["state"], "HFP_SYSTEM_PROFILE_ACTIVE")
        self.assertIs(data["systemHfpProfileActive"], True)
        self.assertIs(data["cellularHfpReadyReported"], True)

    def test_offered_but_inactive_profile_still_not_connected(self):
        data = mod.inspect(provider=provider, cards=lambda: (True, False))
        self.assert_locked(data)
        self.assertEqual(data["state"], "HFP_PROFILE_AVAILABLE_ONLY")
        self.assertIs(data["systemHfpProfileActive"], False)

    def test_cellular_ready_does_not_mean_hfp_profile_exists(self):
        data = mod.inspect(provider=provider, cards=lambda: (False, False))
        self.assert_locked(data)
        self.assertEqual(data["state"], "HFP_PROFILE_NOT_OBSERVED")

    def test_a2dp_headset_never_counts_as_hfp(self):
        audio = mod.project_audio_cards([bluez(profile="a2dp-sink", offered=["a2dp-sink"])])
        self.assertEqual(audio, (False, False))
        hfp = mod.project_audio_cards([bluez(profile="a2dp-sink")])
        self.assertEqual(hfp, (True, False))
        hfp = mod.project_audio_cards([bluez(profile="headset-head-unit-msbc")])
        self.assertEqual(hfp, (True, True))

    def test_non_bluez_card_cannot_satisfy_hfp(self):
        card = bluez()
        card["name"] = "alsa_card.pci-0000_00_1f.3"
        self.assertEqual(mod.project_audio_cards([card]), (False, False))
        card = bluez()
        card["properties"] = {"device.api": "alsa"}
        self.assertEqual(mod.project_audio_cards([card]), (False, False))

    def test_reject_malformed_cards_without_exposing_raw_backend_output(self):
        for value in (
            {}, "PRIVATE", None, True, list(range(33)),
            [{"name": "bluez_card.X", "properties": None}],
            [{"name": "bluez_card.X" * 20, "properties": {}}],
            [{"name": "bluez_card.X", "properties": {"device.api":"bluez5"},
              "profiles": ["hfp"] * 65}],
            [{"name": "bluez_card.X", "properties": {"device.api":"bluez5"},
              "profiles": "headset-head-unit"}],
        ):
            with self.subTest(value=str(value)[:55]):
                self.assertIsNone(mod.project_audio_cards(value))
        for bad in (None, {}, "invalid", (False,), (True, False, True),
                    (True, 1), (False, True)):
            with self.subTest(bad=bad):
                result = mod.inspect(provider=provider, cards=lambda: bad)
                self.assert_locked(result)
                self.assertEqual(result["state"], "AUDIO_INSPECTION_UNAVAILABLE")

    def test_unknown_provider_and_hfp_profile_never_authenticates(self):
        for status in (
            {}, provider(result="BRIDGE_UNAVAILABLE"),
            provider(faceTimeEnabled=True),  # extra provider fields not trusted
            provider(trustedPhoneLink="VERIFIED"),
            provider(contentAccessEnabled=True),
            provider(callsState="UNKNOWN"),
            provider(callsEnabled="true"),
            provider(ofonoActive="yes"),
        ):
            with self.subTest(status=str(status)[:55]):
                result = mod.inspect(provider=lambda: status, cards=lambda: (True, True))
                self.assert_locked(result)
                if status.get("result") != "OBSERVED" or \
                        status.get("trustedPhoneLink") != "UNVERIFIED" or \
                        status.get("contentAccessEnabled") is not False or \
                        type(status.get("ofonoActive")) is not bool:
                    self.assertEqual(result["state"], "PHONE_BRIDGE_UNAVAILABLE")
                elif status.get("callsState") == "UNKNOWN" or \
                        type(status.get("callsEnabled")) is not bool:
                    self.assertEqual(result["state"], "PHONE_CALL_STATUS_UNREPORTED")
                    self.assertIs(result["phoneBackendObserved"], True)
                    self.assertIs(result["cellularHfpReadyReported"], False)
        # An unrelated FaceTime field in BlueFerry status MUST NOT let us
        # claim provider-integrated FaceTime call state.
        self.assertIs(mod.inspect(provider=lambda:provider(faceTimeEnabled=True),
                                  cards=lambda:(True, True))["faceTimeConnected"], False)

    def test_real_getstatus_partial_call_state_is_not_a_dead_daemon(self):
        # Operator observed a valid D-Bus GetStatus: api_version=2,
        # daemon=true, phone_audio_route is str, calls_state is NOT str.
        # Feed those raw fields through the ACTUAL PhoneAudioControls parser.
        for raw_state in (None, False, 0, [], "new-future-call-enum"):
            raw = {
                "api_version": 2, "daemon": True,
                "phone_audio_preference": "pc",
                "phone_audio_route": "pc",
                "calls_enabled": True, "calls_state": raw_state,
            }
            projected = Audio._project(raw)
            self.assertIsNotNone(projected)
            self.assertEqual(projected["calls_state"], "UNKNOWN")
            observed = Audio._output(
                "OBSERVED", projected, can_adjust=True, ofono=True)
            result = mod.inspect(
                provider=lambda: observed, cards=lambda: (True, True))
            self.assert_locked(result)
            self.assertEqual(result["state"], "PHONE_CALL_STATUS_UNREPORTED")
            self.assertIs(result["phoneBackendObserved"], True)
            self.assertIs(result["cellularHfpReadyReported"], False)
            self.assertIs(result["systemHfpProfileActive"], True)
            # HFP profile active does NOT license FaceTime to connect.
            self.assertIs(result["faceTimeAudioVerified"], False)

        for raw in (
            {"api_version": 2, "daemon": True,
             "phone_audio_route": "pc", "calls_enabled": True},
            {"api_version": 2, "daemon": True,
             "phone_audio_route": "pc", "calls_state": "ready"},
        ):
            projected = Audio._project(raw)
            observed = Audio._output(
                "OBSERVED", projected, can_adjust=True, ofono=True)
            result = mod.inspect(
                provider=lambda: observed, cards=lambda: (False, False))
            self.assert_locked(result)
            self.assertEqual(result["state"], "PHONE_CALL_STATUS_UNREPORTED")
            self.assertIs(result["phoneBackendObserved"], True)
            self.assertIs(result["cellularHfpReadyReported"], False)

    def test_ready_report_requires_true_hfp_cellular_and_ofono(self):
        for change in (
            {"callsEnabled": False},
            {"callsState": "CONNECTING"},
            {"callsState": "BLUEZ_CONFLICT"},
            {"ofonoActive": False},
        ):
            data = mod.inspect(provider=lambda: provider(**change),
                               cards=lambda: (True, True))
            self.assert_locked(data)
            self.assertEqual(data["state"], "PHONE_CALLS_NOT_READY")
            self.assertIs(data["cellularHfpReadyReported"], False)

    def test_pactl_invocation_is_fixed_readonly_and_does_not_expose_device(self):
        run = Mock(return_value=Mock(
            stdout=json.dumps([bluez(profile="headset-head-unit")]),
            returncode=0, stderr="PRIVATE_SYSTEM_DATA",
        ))
        result = mod._pactl_cards(find=lambda _: "/usr/bin/pactl", run=run)
        self.assertEqual(result, (True, True))
        run.assert_called_once()
        args, kwargs = run.call_args
        self.assertEqual(args, (["/usr/bin/pactl", "-f", "json", "list", "cards"],))
        self.assertEqual(kwargs["timeout"], 4)
        self.assertEqual(kwargs["env"]["PULSE_NO_AUTOSPAWN"], "1")
        self.assertEqual(kwargs["env"]["LC_ALL"], "C")
        self.assertFalse(kwargs["check"])
        self.assertTrue(kwargs["capture_output"])
        self.assertTrue(kwargs["text"])
        self.assertNotIn("PRIVATE_SYSTEM_DATA", str(result))
        self.assertNotIn("PRIVATE_PERSON_DEVICE", str(result))

    def test_pactl_missing_bad_output_timeout_and_oversized_fail_closed(self):
        self.assertIsNone(mod._pactl_cards(find=lambda _: None))
        self.assertIsNone(mod._pactl_cards(find=lambda _: "pactl"))
        for response in (
            Mock(stdout="untrusted", returncode=0),
            Mock(stdout="PRIVATE", returncode=1),
            Mock(stdout=" " * 140000, returncode=0),
            Mock(stdout='{"bad":"data"}', returncode=0),
        ):
            self.assertIsNone(mod._pactl_cards(find=lambda _: "/usr/bin/pactl",
                                               run=lambda *a, **kw: response))
        self.assertIsNone(mod._pactl_cards(
            find=lambda _: "/usr/bin/pactl",
            run=Mock(side_effect=TimeoutError("private"))))
        # A transport timeout is refused; never switch to a mutating remedy.

    def test_strict_cli_and_source_no_writers(self):
        self.assertEqual(mod.main(["invalid"]), 2)
        with patch.object(mod, "inspect", return_value=mod._response(
            "HFP_SYSTEM_PROFILE_ACTIVE", system=True, offered=True, active=True
        )):
            self.assertEqual(mod.main(["--status"]), 0)
        code = SOURCE.read_text()
        for forbidden in (
            "pactl set-", "set-card-profile", "blueferry audio",
            "systemctl restart", "systemctl start", "wpctl set-",
            "subprocess.Popen(", "shell=True", "secret-tool",
            "PhonePersonalContactVault", "PhonePersonalSave",
            "FaceTimeLink", "PhoneCallWorkspace",
        ):
            self.assertNotIn(forbidden, code)


if __name__ == "__main__":
    unittest.main()
