"""Explicit in-menu iPhone sound routing. No global defaults or pairing."""
from pathlib import Path
import importlib
import sys
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "phone"))
audio = importlib.import_module("PhoneAudioControls")
SOURCE = ROOT / "services" / "phone" / "PhoneAudioControls.py"


def status(**updates):
    value = {
        "api_version": 2, "daemon": True,
        "phone_audio_preference": "auto",
        "phone_audio_route": "pc",
        "calls_enabled": False, "calls_state": "disabled",
        "phone": "PRIVATE DEVICE", "contacts": ["PRIVATE"], "messages": ["PRIVATE"],
    }
    value.update(updates)
    return value


def before(**updates):
    result = audio._output("OBSERVED", {
        "preference": "AUTO", "route": "PC",
        "calls_enabled": False, "calls_state": "DISABLED",
    }, can_adjust=True, ofono=True)
    result.update(updates)
    return result


class AudioControlTests(unittest.TestCase):
    def locked(self, result):
        self.assertEqual(result["schema"], audio.SCHEMA)
        self.assertEqual(result["trustedPhoneLink"], "UNVERIFIED")
        self.assertIs(result["contentAccessEnabled"], False)
        self.assertEqual(set(result), {
            "schema", "execution", "result", "mediaPreference",
            "mediaRoute", "callsEnabled", "callsState", "canAdjust",
            "ofonoActive", "trustedPhoneLink", "contentAccessEnabled",
        })
        for secret in ("PRIVATE", "DEVICE", "contacts", "messages"):
            self.assertNotIn(secret, str(result))

    def test_status_sanitizes_provider_data(self):
        result = audio.inspect(
            config=lambda: True, service=lambda: "active",
            status=lambda: status(), ofono=lambda: True)
        self.locked(result)
        self.assertEqual(result["result"], "OBSERVED")
        self.assertTrue(result["canAdjust"])
        self.assertTrue(result["ofonoActive"])
        self.assertEqual(result["mediaPreference"], "AUTO")
        self.assertEqual(result["mediaRoute"], "PC")
        self.assertIs(result["callsEnabled"], False)
        self.assertEqual(result["callsState"], "DISABLED")

    def test_no_local_config_or_inactive_backend_never_returns_action_permission(self):
        for config, service in ((False, "active"), (True, "inactive")):
            with self.subTest(config=config, service=service):
                status_reader, ofono = mock.Mock(), mock.Mock()
                result = audio.inspect(
                    config=lambda: config, service=lambda: service,
                    status=status_reader, ofono=ofono)
                self.locked(result)
                self.assertEqual(result["result"], "BRIDGE_UNAVAILABLE")
                self.assertFalse(result["canAdjust"])
                status_reader.assert_not_called()
                ofono.assert_not_called()

    def test_invalid_status_and_old_backend_fail_closed(self):
        for invalid in (
            None, {}, status(api_version=1), status(daemon=False),
            status(phone_audio_preference=["unsafe"], calls_enabled="yes"),
        ):
            with self.subTest(invalid=invalid):
                result = audio.inspect(
                    config=lambda: True, service=lambda: "active",
                    status=lambda: invalid, ofono=lambda: True)
                self.locked(result)
                if type(invalid) is dict and invalid.get("api_version") == 2 and invalid.get("daemon") is True:
                    self.assertEqual(result["result"], "OBSERVED")
                    self.assertEqual(result["mediaPreference"], "UNKNOWN")
                    self.assertIsNone(result["callsEnabled"])
                else:
                    self.assertEqual(result["result"], "BRIDGE_UNAVAILABLE")

    def test_media_choice_changes_only_iphone_route_after_click(self):
        states = [before(), before(mediaPreference="PHONE", mediaRoute="PHONE")]
        probe = mock.Mock(side_effect=states)
        runner = mock.Mock(return_value=mock.Mock(returncode=0, stdout="PRIVATE PHONE", stderr=""))
        result = audio.apply(
            "media", "phone", probe=probe,
            find=lambda x: "/usr/bin/blueferry", run=runner)
        self.locked(result)
        self.assertEqual(result["result"], "PREFERENCE_SAVED")
        self.assertEqual(result["mediaPreference"], "PHONE")
        self.assertEqual(probe.call_count, 2)
        runner.assert_called_once_with(
            ["/usr/bin/blueferry", "audio", "phone"],
            capture_output=True, text=True, timeout=20, check=False,
        )

    def test_auto_mode_does_not_become_global_install_default(self):
        result = audio.apply(
            "media", "auto",
            probe=mock.Mock(side_effect=[
                before(mediaPreference="PHONE"),
                before(mediaPreference="AUTO"),
            ]),
            find=lambda _: "/usr/bin/blueferry",
            run=lambda *a, **k: mock.Mock(returncode=0),
        )
        self.locked(result)
        self.assertEqual(result["result"], "PREFERENCE_SAVED")
        self.assertEqual(result["mediaPreference"], "AUTO")

    def test_call_enable_blocked_without_ofono_before_any_mutation(self):
        launcher = mock.Mock()
        res = audio.apply(
            "calls", "enable",
            probe=lambda: before(ofonoActive=False),
            find=mock.Mock(), run=launcher)
        self.locked(res)
        self.assertEqual(res["result"], "CALLS_PREREQUISITES_MISSING")
        self.assertFalse(res["ofonoActive"])
        launcher.assert_not_called()

    def test_calls_enabled_preference_is_distinct_from_hfp_ready(self):
        action = audio.apply(
            "calls", "enable",
            probe=mock.Mock(side_effect=[
                before(), before(callsEnabled=True, callsState="SEARCHING")]),
            find=lambda _: "/usr/bin/blueferry",
            run=lambda *a, **k: mock.Mock(returncode=0),
        )
        self.locked(action)
        self.assertEqual(action["result"], "PREFERENCE_SAVED")
        self.assertIs(action["callsEnabled"], True)
        self.assertEqual(action["callsState"], "SEARCHING")
        self.assertNotIn("CONNECTED", str(action))

    def test_disable_calls_allowed_without_ofono(self):
        runner = mock.Mock(return_value=mock.Mock(returncode=0))
        res = audio.apply(
            "calls", "disable",
            probe=mock.Mock(side_effect=[
                before(callsEnabled=True, ofonoActive=False),
                before(callsEnabled=False, ofonoActive=False)]),
            find=lambda _: "/usr/bin/blueferry",
            run=runner)
        self.locked(res)
        self.assertEqual(res["result"], "PREFERENCE_SAVED")
        runner.assert_called_once()
        self.assertEqual(runner.call_args.args[0],
                         ["/usr/bin/blueferry", "calls", "disable"])

    def test_forged_or_invalid_action_never_executes(self):
        finder, runner = mock.Mock(), mock.Mock()
        for family, selection in (
            ("media", "remove"), ("media", "phone; rm -rf /"),
            ("calls", "dial"), ("calls", "all"), ("system", "restart"),
            (None, "phone"), ("media", None)):
            with self.subTest(action=(family, selection)):
                result = audio.apply(family, selection,
                                     probe=lambda: before(), find=finder, run=runner)
                self.locked(result)
                self.assertEqual(result["result"], "REFUSED")
        finder.assert_not_called()
        runner.assert_not_called()

    def test_no_bridge_or_forged_grant_blocks_change(self):
        for initial in (
            before(canAdjust=False),
            before(trustedPhoneLink="CONNECTED"),
            before(contentAccessEnabled=True),
            before(result="BRIDGE_UNAVAILABLE"),
        ):
            with self.subTest(initial=initial):
                runner = mock.Mock()
                result = audio.apply("media", "phone", probe=lambda: initial, run=runner)
                self.locked(result)
                self.assertEqual(result["result"], "BRIDGE_UNAVAILABLE")
                runner.assert_not_called()

    def test_missing_binary_or_backend_error_no_claim_of_success(self):
        r1 = audio.apply(
            "media", "pc", probe=lambda: before(), find=lambda _: None)
        self.locked(r1)
        self.assertEqual(r1["result"], "CLIENT_UNAVAILABLE")
        r2 = audio.apply(
            "media", "pc", probe=lambda: before(),
            find=lambda _: "/usr/bin/blueferry",
            run=lambda *a, **k: (_ for _ in ()).throw(
                OSError("PRIVATE DATA")))
        self.locked(r2)
        self.assertEqual(r2["result"], "CHANGE_FAILED")

    def test_failed_post_action_verification_not_success(self):
        result = audio.apply(
            "media", "phone",
            probe=mock.Mock(side_effect=[
                before(mediaPreference="AUTO"),
                before(mediaPreference="AUTO")]),
            find=lambda _: "/usr/bin/blueferry",
            run=lambda *a, **k: mock.Mock(returncode=0))
        self.locked(result)
        self.assertEqual(result["result"], "NOT_CONFIRMED")

    def test_probe_exception_never_executes(self):
        runner = mock.Mock()
        result = audio.apply(
            "media", "pc",
            probe=lambda: (_ for _ in ()).throw(
                ValueError("PRIVATE PHONE")), run=runner)
        self.locked(result)
        self.assertEqual(result["result"], "BRIDGE_UNAVAILABLE")
        runner.assert_not_called()

    def test_cli_requires_explicit_flags(self):
        with mock.patch.object(audio, "inspect") as inspect, mock.patch.object(audio, "apply") as apply, mock.patch("builtins.print"):
            self.assertEqual(audio.main([]), 2)
            inspect.assert_not_called()
            apply.assert_not_called()

    def test_no_host_mutation_outside_requested_provider_action(self):
        src = SOURCE.read_text()
        for forbidden in (
            "bluetoothctl remove", "systemctl restart",
            "systemctl enable", "blueferry pair-setup",
            "subprocess.Popen(", "shell=True", "sudo ", "pkexec",
            "connectDevice(", "sendMessage(", "getMessages(",
        ):
            with self.subTest(text=forbidden):
                self.assertNotIn(forbidden, src)


if __name__ == "__main__":
    unittest.main()
