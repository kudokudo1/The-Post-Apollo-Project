"""CPU++ TIME settings adapter contract: shared Clock-owned configuration.

No host clock mutation or duplicate time persistence lives in CPU++.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
CPU = (ROOT / "widgets/CpuPlusW.qml").read_text(encoding="utf-8")
PANE = (ROOT / "widgets/TimeSettingsPane.qml").read_text(encoding="utf-8")
TIME_SETTINGS = (ROOT / "services/time/TimeSettings.qml").read_text(encoding="utf-8")
CLOCK = (ROOT / "widgets/TimeW.qml").read_text(encoding="utf-8")
LOCATION = (ROOT / "widgets/cpuplus/CpuPlusSettingsLocationPane.qml").read_text(encoding="utf-8")


class CpuPlusTimeSettingsContracts(unittest.TestCase):
    def test_both_settings_submodes_remain_available(self):
        self.assertIn('property string settingsSubMode: "LOCATION"', CPU)
        self.assertIn('{ name: "LOCATION", key: "LOCATION"', CPU)
        self.assertIn('{ name: "TIME", key: "TIME"', CPU)
        self.assertIn("selectSettingsSubMode(modelData.key)", CPU)
        self.assertIn('settingsSubMode === "LOCATION"', CPU)
        self.assertIn('settingsSubMode === "TIME"', CPU)
        self.assertIn("CpuPlusSettingsLocationPane {", CPU)
        self.assertIn("registry: PlaceRegistry", CPU)
        self.assertIn("settingsLocationPane.editingText", CPU)

    def test_cpu_mode_uses_shared_view_and_persistence(self):
        self.assertIn("import qs.services.time", CPU)
        self.assertIn("TimeSettingsPane {", CPU)
        self.assertIn("TimeSettings.displayOffsetLabel", CPU)
        self.assertIn("showClockPreview: false", CPU)
        self.assertIn("showTimezoneDetails: false", CPU)
        self.assertIn("showResyncTrigger: true", CPU)
        self.assertIn("panelVisible: visible && cpuPlusWindow.menuOpen", CPU)
        self.assertIn("time-settings-v1.json", TIME_SETTINGS)
        self.assertIn("atomicWrites: true", TIME_SETTINGS)

    def test_time_ui_excludes_clock_only_functions(self):
        self.assertNotIn("SystemClock {", CPU)
        self.assertNotIn("FileView {", CPU)
        self.assertNotIn("TimeHostControl.py", CPU)
        self.assertNotIn("set-timezone", CPU)
        self.assertIn("TIME // SETTINGS", CPU)
        self.assertIn("HOST // DAYLIGHT SAVING", PANE)
        self.assertIn("visible: pane.showTimezoneDetails", PANE)
        self.assertIn("visible: pane.showClockPreview", PANE)

    def test_both_views_use_one_guarded_resync_controller(self):
        self.assertIn("TimeSettings.prepareResync()", CLOCK)
        self.assertIn("TimeSettings.prepareResync()", PANE)
        self.assertIn("TimeSettings.resyncConfirmRequired", PANE)
        self.assertIn('label: "CONFIRM RESYNC"', PANE)
        self.assertIn("TimeSettings.requestResync()", PANE)
        self.assertIn("TimeSettings.cancelResync()", PANE)
        self.assertIn("resyncConfirmRequired", TIME_SETTINGS)

    def test_dst_is_system_observation_only(self):
        self.assertIn("TimeSettings.hostInfo.dstActive", PANE)
        self.assertIn("TimeSettings.hostInfo.rtcLocal", PANE)
        self.assertIn("TimeSettings.hostInfo.ntpEnabled", PANE)
        # Zone mutation is Clock-owned and intentionally not exposed in CPU++.
        self.assertNotIn("set-timezone", CPU)
        self.assertIn('"set-timezone", zoneChoice', TIME_SETTINGS)
        self.assertNotIn("set-ntp", TIME_SETTINGS)
        self.assertNotIn("TimeSettings.", LOCATION)


if __name__ == "__main__":
    unittest.main()
