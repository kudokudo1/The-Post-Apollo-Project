"""Real host timezone and session-scoped Polkit authorization contracts.

All subprocess calls here are mocked. Tests never alter system time, RTC,
timezone, NTP, or authentication settings.
"""
from __future__ import annotations

import importlib.util
import pathlib
import subprocess
import unittest
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parents[2]
HOST_PATH = ROOT / "services/time/TimeHostControl.py"
SPEC = importlib.util.spec_from_file_location("time_host_control_zone_test", HOST_PATH)
host = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(host)

SERVICE = (ROOT / "services/time/TimeSettings.qml").read_text()
PANE = (ROOT / "widgets/TimeSettingsPane.qml").read_text()
TIMEW = (ROOT / "widgets/TimeW.qml").read_text()
CPU = (ROOT / "widgets/CpuPlusW.qml").read_text()
AUTH = (ROOT / "widgets/TimeResyncAuthW.qml").read_text()
SHELL = (ROOT / "shell.qml").read_text()
PICKER = (ROOT / "widgets/TimeZonePicker.qml").read_text()


def proc(args, code=0, stdout="", stderr=""):
    return subprocess.CompletedProcess(args, code, stdout, stderr)


class TimezoneSettingsContracts(unittest.TestCase):
    def test_rejects_untrusted_zone_before_running_any_process(self):
        for value in ("", "../../etc/passwd", "America/New_York;id", "-x",
                      "UTC foo", "Europe//Paris", "Z" * 101):
            with self.subTest(value=value), patch.object(
                    host.subprocess, "run") as runner:
                result = host.set_timezone(value)
            self.assertEqual(result["errorCode"], "ZONE_INVALID")
            runner.assert_not_called()

    def test_requires_zone_from_real_host_catalog(self):
        with patch.object(host.subprocess, "run", return_value=proc(
                [], stdout="UTC\nEurope/London\n")) as runner:
            result = host.set_timezone("Asia/Tokyo")
        self.assertEqual(result["errorCode"], "ZONE_NOT_INSTALLED")
        self.assertEqual(runner.call_count, 1)

    def test_authenticated_timedated_operation_is_verified(self):
        with patch.object(host.subprocess, "run", side_effect=[
                proc([], stdout="UTC\nAmerica/New_York\n"),
                proc(["timedatectl", "set-timezone", "America/New_York"])
                ]) as runner, patch.object(host, "system_properties",
                    side_effect=[{"Timezone": "UTC"},
                                 {"Timezone": "America/New_York"}]):
            result = host.set_timezone("America/New_York")
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["timezone"], "America/New_York")
        self.assertEqual(runner.call_args_list[1].args[0],
                         ["timedatectl", "set-timezone", "America/New_York"])
        self.assertEqual(runner.call_count, 2)

    def test_no_false_success_when_service_did_not_apply_zone(self):
        with patch.object(host.subprocess, "run", side_effect=[
                proc([], stdout="UTC\nEurope/London\n"), proc([])
                ]), patch.object(host, "system_properties",
                    side_effect=[{"Timezone": "UTC"}, {"Timezone": "UTC"}]):
            result = host.set_timezone("Europe/London")
        self.assertEqual(result["errorCode"], "ZONE_VERIFY")
        self.assertEqual(result["status"], "failed")

    def test_denied_auth_does_not_claim_timezone_change(self):
        with patch.object(host.subprocess, "run", side_effect=[
                proc([], stdout="UTC\nEurope/London\n"),
                proc([], code=1, stderr="Interactive authentication required")
                ]), patch.object(host, "system_properties",
                    return_value={"Timezone": "UTC"}):
            result = host.set_timezone("Europe/London")
        self.assertEqual(result["errorCode"], "ZONE_AUTH")
        self.assertEqual(result["status"], "failed")

    def test_clock_reuses_world_filter_and_star_scroller(self):
        self.assertIn("TimeZonePicker {", PANE)
        self.assertIn("TimeSettings.zoneCatalog", PANE)
        self.assertIn("TimeSettings.zoneCountryIndex", PANE)
        self.assertIn('["timedatectl", "list-timezones", "--no-pager"]', SERVICE)
        self.assertIn("WorldZoneSearch.js", SERVICE)
        self.assertIn("NeonScrollBar {", PICKER)
        self.assertIn('handleStyle: "star"', PICKER)
        for zone in ("UTC", "America/New_York", "Europe/London", "Asia/Tokyo"):
            self.assertIn('zone: "' + zone + '"', PANE)
        self.assertIn("onZoneChosen: function(zoneId)", PANE)
        self.assertIn("clockSettingsPane.zoneSearchFocused", TIMEW)

    def test_zone_is_clock_only_with_explicit_confirmation(self):
        self.assertIn("showTimezoneDetails: false", CPU)
        self.assertIn("visible: pane.showTimezoneDetails", PANE)
        self.assertIn("TimeSettings.prepareTimezone(zoneId)", PANE)
        self.assertIn("TimeSettings.requestTimezone()", PANE)
        self.assertIn("TimeSettings.cancelTimezone()", PANE)
        self.assertIn('label: "APPLY ZONE"', PANE)
        self.assertIn("timezoneConfirmRequired", SERVICE)
        self.assertIn("ZoneSearch.contains(zoneCatalog, zoneChoice)", SERVICE)
        self.assertIn("RTC LOCAL=YES", PANE)
        self.assertNotIn("set-timezone", CPU)

    def test_polkit_stays_registered_through_process_and_reports_flow(self):
        self.assertIn("active: TimeSettings.authSessionActive", SHELL)
        self.assertIn("authSessionActive = true", SERVICE)
        self.assertIn("authSessionActive = false", SERVICE)
        self.assertIn("launchTimezoneAfterAgentReady(true)", AUTH)
        self.assertIn("launchResyncAfterAgentReady(true)", AUTH)
        self.assertIn("TimeSettings.authFlowStage", AUTH)
        self.assertIn("TimeSettings.authActionId", AUTH)
        self.assertIn("TimeSettings.authFlowStage", PANE)
        self.assertIn("TextInput.Password", AUTH)
        self.assertNotIn("sudo -S", AUTH + SERVICE + PANE + HOST_PATH.read_text())


if __name__ == "__main__":
    unittest.main()
