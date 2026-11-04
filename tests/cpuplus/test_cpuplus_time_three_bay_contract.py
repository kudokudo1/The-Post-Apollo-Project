"""CPU++ Settings / Time M1 three-bay reuse and isolation contracts.

No host clock, timezone, RTC, NTP, local files or Quickshell runtime changed.
The existing Clock-owned time service and guarded authorization remain unique.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
CPU = (ROOT / "widgets/CpuPlusW.qml").read_text(encoding="utf-8")
CLOCK_PANE = (ROOT / "widgets/TimeSettingsPane.qml").read_text(encoding="utf-8")
ACTIVE = (ROOT / "widgets/cpuplus/CpuPlusSettingsTimeActivePane.qml").read_text(
    encoding="utf-8")
ADVANCED = (ROOT / "widgets/cpuplus/CpuPlusSettingsTimeAdvancedPane.qml").read_text(
    encoding="utf-8")
LOCATION = (ROOT / "widgets/cpuplus/CpuPlusSettingsLocationPane.qml").read_text(
    encoding="utf-8")
SERVICE = (ROOT / "services/time/TimeSettings.qml").read_text(encoding="utf-8")


class CpuPlusTimeThreeBayContracts(unittest.TestCase):
    def test_layout_places_time_basic_active_advanced_in_correct_bays(self):
        left = CPU.split("id: sharedInstrumentPane", 1)[1].split(
            "id: targetPane", 1)[0]
        middle = CPU.split("id: targetPane", 1)[1].split(
            "id: actuatorPane", 1)[0]
        right = CPU.split("id: actuatorPane", 1)[1]

        self.assertIn("TimeSettingsPane {", left)
        self.assertIn("id: settingsTimeBasicsPane", left)
        self.assertIn("anchors.top: sharedStateHeader.bottom", left)
        self.assertIn("CpuPlusSettingsTimeActivePane {", middle)
        self.assertIn("id: settingsTimeActivePane", middle)
        self.assertIn("anchors.top: targetSubModeStrip.bottom", middle)
        self.assertIn("CpuPlusSettingsTimeAdvancedPane {", right)
        self.assertIn("id: settingsTimeAdvancedPane", right)
        self.assertIn("anchors.top: actuatorHeader.bottom", right)

    def test_basic_reuses_same_clock_ui_and_confirms_system_changes(self):
        self.assertEqual(CPU.count("TimeSettingsPane {"), 1)
        self.assertIn("showTimezoneDetails: true", CPU)
        self.assertIn("showResyncTrigger: true", CPU)
        self.assertIn("showHostDiagnostics: false", CPU)
        self.assertIn("showResyncDiagnostics: false", CPU)
        self.assertIn("showReferenceExplanation: false", CPU)
        self.assertIn("TimeSettings.prepareTimezone(zoneId)", CLOCK_PANE)
        self.assertIn("TimeSettings.requestTimezone()", CLOCK_PANE)
        self.assertIn("TimeSettings.requestResync()", CLOCK_PANE)
        self.assertIn("TimeSettings.checkTimeAccuracy()", CLOCK_PANE)
        self.assertIn("visible: pane.showHostDiagnostics", CLOCK_PANE)
        self.assertIn("pane.showResyncDiagnostics", CLOCK_PANE)
        self.assertIn("visible: pane.showReferenceExplanation", CLOCK_PANE)
        self.assertIn("property bool showHostDiagnostics: true", CLOCK_PANE)
        self.assertIn("property bool showResyncDiagnostics: true", CLOCK_PANE)

    def test_hidden_diagnostics_row_has_one_qml_height_assignment(self):
        # A duplicate height or accent binding can make all of shell.qml fail
        # to load. This explicitly guards the previously broken class.
        head = CLOCK_PANE.split("id: resyncDiagnoseButton", 1)[0]
        start = head.rfind("            Row {")
        self.assertGreaterEqual(start, 0)
        row = head[start:]
        self.assertEqual(sum(
            1 for line in row.splitlines()
            if line.strip().startswith("height:")
        ), 1)

    def test_center_live_status_does_not_claim_unverified_accuracy(self):
        self.assertIn("SystemClock {", ACTIVE)
        self.assertIn("precision: SystemClock.Seconds", ACTIVE)
        self.assertIn("TimeSettings.adjustedEpochMs", ACTIVE)
        self.assertIn("TimeSettings.hasFreshReference", ACTIVE)
        self.assertIn("TimeSettings.dockZoneOffsetMismatch", ACTIVE)
        self.assertIn("NOT RECENTLY VERIFIED", ACTIVE)
        self.assertIn("PROFILE SAVING NOT YET ENABLED", ACTIVE)
        self.assertIn("TimeSettings.zoneChoice", ACTIVE)
        self.assertIn("TimeSettings.hostInfo.timezone", ACTIVE)

    def test_right_is_readonly_diagnostics_not_unapproved_actuation(self):
        self.assertIn("TimeSettings.refreshHostStatus()", ADVANCED)
        self.assertIn("TimeSettings.diagnoseResync()", ADVANCED)
        self.assertIn("TimeSettings.hostInfo.ntpEnabled", ADVANCED)
        self.assertIn("TimeSettings.hostInfo.rtcLocal", ADVANCED)
        self.assertIn("TimeSettings.authFlowStage", ADVANCED)
        self.assertIn("NOT YET ENABLED", ADVANCED)
        for forbidden in ("set-local-rtc", "set-timezone", "set-ntp",
                          "TimeSettings.requestResync()", "TimeSettings.requestTimezone()",
                          "FileView {", "pkexec", "sudo"):
            self.assertNotIn(forbidden, ADVANCED)

    def test_location_and_shared_monitor_bays_are_untouched(self):
        self.assertIn("CpuPlusSettingsLocationPane {", CPU)
        self.assertIn("id: settingsLocationPane", CPU)
        self.assertIn("registry: PlaceRegistry", CPU)
        self.assertIn('settingsSubMode === "LOCATION"', CPU)
        self.assertIn("ThermalMonitorView {", CPU)
        self.assertIn("SystemMonitorView {", CPU)
        self.assertIn("settingsLocationPane.editingText", CPU)
        self.assertNotIn("TimeSettings.", LOCATION)
        self.assertIn("showTimezoneDetails: true", CPU)
        self.assertIn("visible: !(cpuPlusWindow.selectedModeIndex === 4", CPU)

    def test_focus_guard_keeps_timezone_search_editable(self):
        self.assertIn("settingsTimeBasicsPane.zoneSearchFocused", CPU)
        self.assertIn('settingsSubMode === "TIME"', CPU)
        self.assertIn("onSettingsSubModeChanged:", CPU)
        self.assertIn("TimeSettings.cancelResync()", CPU)

    def test_no_new_time_writer_or_background_time_polling(self):
        self.assertIn('import qs.services.time', CPU)
        self.assertIn("time-settings-v1.json", SERVICE)
        self.assertIn("atomicWrites: true", SERVICE)
        for piece in (ACTIVE, ADVANCED, CPU):
            self.assertNotIn("FileView {", piece)
            self.assertNotIn("TimeHostControl.py", piece)
            self.assertNotIn("set-local-rtc", piece)
        self.assertNotIn("FileView {", CLOCK_PANE)
        self.assertNotIn("SystemClock {", ADVANCED)


if __name__ == "__main__":
    unittest.main()
