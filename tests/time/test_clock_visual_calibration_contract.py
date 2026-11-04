"""Clock visual semantics, rapid calibration, and opt-in reference checks.

External clock commands are mocked. No system time, NTP, RTC, timezone, or
local config is changed by this test suite.
"""
from __future__ import annotations

import importlib.util
import pathlib
import subprocess
import unittest
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parents[2]
HOST_PATH = ROOT / "services/time/TimeHostControl.py"
SPEC = importlib.util.spec_from_file_location("clock_display_host", HOST_PATH)
host = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(host)

CLOCK = (ROOT / "modules/Clock.qml").read_text()
TIMEW = (ROOT / "widgets/TimeW.qml").read_text()
PANE = (ROOT / "widgets/TimeSettingsPane.qml").read_text()
SERVICE = (ROOT / "services/time/TimeSettings.qml").read_text()
ACTION = (ROOT / "widgets/TimeActionButton.qml").read_text()
PICKER = (ROOT / "widgets/TimeZonePicker.qml").read_text()
AUTH = (ROOT / "widgets/TimeResyncAuthW.qml").read_text()


def result(code, stdout="", stderr=""):
    return subprocess.CompletedProcess([], code, stdout, stderr)


class ClockVisualCalibrationTests(unittest.TestCase):
    def test_settings_is_last_and_next_is_angel(self):
        order = TIMEW.split("readonly property var modes: [", 1)[1].split("]", 1)[0]
        self.assertLess(order.index('id: "planned", name: "ANGEL"'),
                        order.index('id: "settings", name: "SETTINGS"'))
        self.assertTrue(order.rstrip().endswith('{ id: "settings", name: "SETTINGS" }'))
        self.assertIn("timew.chooseMode(timew.modes.length - 1)", TIMEW)
        self.assertIn("ANGEL // RESERVED", TIMEW)

    def test_selected_mode_uses_open_clock_style(self):
        self.assertIn("selectedFillColor: Colors.yellow", TIMEW)
        self.assertIn("selectedPrimaryColor: Colors.magenta", TIMEW)
        self.assertIn("perimeterGlowColor: timew.selectedModeIndex === index", TIMEW)

    def test_zone_selection_open_state_and_white_identity(self):
        self.assertIn('zone: "UTC"', PANE)
        self.assertIn('zone: "America/New_York"', PANE)
        self.assertIn('zone: "Europe/London"', PANE)
        self.assertIn('zone: "Asia/Tokyo"', PANE)
        self.assertIn("actionRole: \"time\"", PANE)
        self.assertIn("TimeSettings.timezoneConfirmRequired", PANE)
        self.assertIn("TimeSettings.hostInfo.timezone === modelData.zone", PANE)
        self.assertIn("openSelectedZone: true", PANE)
        self.assertIn("zoneAccentColor: Colors.white", PANE)
        self.assertIn("selected: picker.openSelectedZone", PICKER)
        self.assertIn("selectedForegroundColor: Colors.magenta", PICKER)
        self.assertIn('zoneChoice = "";', SERVICE)

    def test_zone_result_delegate_has_single_accent_binding(self):
        # Repeated QML property assignments make the entire widget type
        # unavailable at load time, cascading through CPU++ and shell.qml.
        delegate = PICKER.split("delegate: ActionButton {", 1)[1].split(
            "\n            }", 1)[0]
        self.assertEqual(delegate.count("accentColor:"), 1)
        self.assertIn("accentColor: picker.openSelectedZone", delegate)
        self.assertNotIn("accentColor: Colors.white", delegate)
        self.assertIn("selectedFillColor: Colors.yellow", delegate)

    def test_time_yellow_cancel_red_with_independent_glows(self):
        self.assertIn('actionRole === "sync" ? Colors.yellow', ACTION)
        self.assertIn('actionRole === "cancel" ? Colors.red', ACTION)
        self.assertIn("selectedFillColor: Colors.yellow", ACTION)
        self.assertIn("selectedContentGlowColor: Colors.magenta", ACTION)
        self.assertIn("idleSoftGlowColor: roleColor", ACTION)
        self.assertIn("pressedContentGlowColor: roleColor", ACTION)
        self.assertIn("wideGlowEnabled: true", ACTION)
        self.assertIn("accentColor: Colors.yellow", TIMEW)
        self.assertIn('label: "CONFIRM RESYNC"', PANE)
        self.assertIn('actionRole: "sync"', PANE)
        self.assertIn('actionRole: "cancel"', PANE)
        self.assertIn('actionRole: "cancel"', AUTH)

    def test_rapid_calibration_queues_last_value_with_single_writer(self):
        self.assertIn('storageState === "saving"', SERVICE)
        self.assertIn("property var queuedDocument: null", SERVICE)
        self.assertIn("queuedDocument !== null ?", SERVICE)
        self.assertIn("if (pendingDocument !== null)", SERVICE)
        self.assertIn("queuedDocument = next.document", SERVICE)
        self.assertIn("beginOffsetWrite(next.document)", SERVICE)
        self.assertIn("timeSettings.beginOffsetWrite(queued)", SERVICE)
        self.assertIn("timeSettings.document = saved", SERVICE)
        self.assertIn("timeSettings.queuedDocument = null", SERVICE)
        self.assertIn('atomicWrites: true', SERVICE)
        self.assertNotIn("settingsFile.setText(", SERVICE.split("function persistOffset(ms)", 1)[1].split("function adjustDisplayMs",1)[0])

    def test_underline_spans_time_cluster_not_icon_and_uses_evidence(self):
        self.assertIn("width: clockReadout.width", CLOCK)
        self.assertIn("x: clockRow.x + clockReadout.x", CLOCK)
        self.assertIn("color: Colors.yellow", CLOCK)
        self.assertIn("TimeSettings.dockTimeUnderlined(clock.date.getTime())", CLOCK)
        self.assertIn("displayDeviationActive", SERVICE)
        self.assertIn("hasFreshReference(nowEpochMs)", SERVICE)
        self.assertIn("referenceWarningThresholdMs: 1000", SERVICE)
        self.assertIn("referenceMaxAgeMs: 15 * 60 * 1000", SERVICE)
        self.assertNotIn('ntpSynchronized === "no"', SERVICE.split("function dockTimeUnderlined", 1)[1].split("function checkTimeAccuracy", 1)[0])

    def test_reference_check_is_explicit_and_opt_in(self):
        self.assertIn('label: "CHECK TIME"', PANE)
        self.assertIn("TimeSettings.checkTimeAccuracy()", PANE)
        self.assertIn('"measure"', SERVICE)
        self.assertIn("CHECK TIME CONTACTS", PANE)
        self.assertIn("NO LINE DOES NOT GUARANTEE ACCURACY", PANE)
        self.assertIn('["systemctl", "is-active", "chronyd.service"]', HOST_PATH.read_text())
        self.assertIn('[chronyd, "-Q", "-t", "15"]', HOST_PATH.read_text())

    def test_measurement_when_chronyd_inactive(self):
        sample = ("2026-11-03 System clock wrong by -3500.007655 "
                  "seconds (ignored)\nCould not open drift.tmp: Permission denied")
        with patch.object(host.os.path, "isfile", return_value=True), patch.object(
                host.subprocess, "run", side_effect=[
                    result(3, stdout="inactive\n"),
                    result(1, stderr=sample),
                ]) as run:
            data = host.measure_clock()
        self.assertEqual(data["status"], "measured")
        self.assertEqual(data["offsetMs"], -3500008)
        self.assertEqual(run.call_args_list[1].args[0],
                         [host.CHRONYD_PATHS[0], "-Q", "-t", "15"])
        self.assertEqual(run.call_count, 2)

    def test_measurement_when_daemon_active_reads_tracking_without_new_daemon(self):
        # An active Chrony instance uses its existing recent source estimate.
        # The measurement must not launch another chronyd or change the clock.
        from datetime import datetime, timezone
        tracking = (
            "Reference ID : CB00710F (source)\n"
            "Stratum : 3\n"
            "Ref time (UTC) : Wed Nov 04 05:00:00 2026\n"
            "System time : 0.050000000 seconds slow of NTP time\n"
            "Root delay : 0.020000 seconds\n"
            "Root dispersion : 0.010000 seconds\n"
            "Leap status : Normal\n")
        with patch.object(host.os.path, "isfile", return_value=True), patch.object(
                host.subprocess, "run", side_effect=[
                    result(0, stdout="active\n"),
                    result(0, stdout=tracking),
                ]) as run, patch.object(host, "parse_tracking_measurement",
                    wraps=host.parse_tracking_measurement) as parse:
            # Fix sample age deterministically without launching host commands.
            with patch.object(host.datetime, "datetime", wraps=datetime) as dt:
                dt.now.return_value = datetime(2026, 11, 4, 5, 1, tzinfo=timezone.utc)
                data = host.measure_clock()
        self.assertEqual(data["source"], "CHRONY_TRACKING")
        self.assertEqual(data["offsetMs"], -50)
        self.assertEqual(run.call_count, 2)
        self.assertEqual(run.call_args_list[1].args[0],
                         [host.CHRONYC, "tracking"])

    def test_measurement_requires_actual_sample_not_command_success(self):
        with patch.object(host.os.path, "isfile", return_value=True), patch.object(
                host.subprocess, "run", side_effect=[
                    result(3, stdout="inactive\n"),
                    result(0, stdout="chronyd completed"),
                ]):
            data = host.measure_clock()
        self.assertEqual(data["errorCode"], "REFERENCE_NO_SAMPLE")
        self.assertEqual(data["status"], "unavailable")


if __name__ == "__main__":
    unittest.main()
