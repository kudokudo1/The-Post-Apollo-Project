"""Clock settings subviews, dock format, and Tools alarm placeholder contracts.

No Linux time, alarms, user configuration, or Polkit commands are executed.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
TIMEW = (ROOT / "widgets/TimeW.qml").read_text(encoding="utf-8")
PANE = (ROOT / "widgets/TimeSettingsPane.qml").read_text(encoding="utf-8")
SHELL = (ROOT / "shell.qml").read_text(encoding="utf-8")
DOCK = (ROOT / "modules/Clock.qml").read_text(encoding="utf-8")
CPU = (ROOT / "widgets/CpuPlusW.qml").read_text(encoding="utf-8")


class ClockSettingsSubmodesContracts(unittest.TestCase):
    def test_settings_tabs_reuse_peer_mode_strip_style_outside_scroll(self):
        self.assertIn('property string settingsView: "visual"', TIMEW)
        self.assertIn('id: settingsSubModeStrip', TIMEW)
        self.assertIn('labelText: "VISUAL TIME"', TIMEW)
        self.assertIn('labelText: "SYNC"', TIMEW)
        self.assertIn('selected: timew.settingsView === "visual"', TIMEW)
        self.assertIn('selected: timew.settingsView === "sync"', TIMEW)
        self.assertIn('onTriggered: timew.settingsView = "visual"', TIMEW)
        self.assertIn('onTriggered: timew.settingsView = "sync"', TIMEW)
        self.assertIn('bordered: false', TIMEW)
        self.assertIn('textOnly: true', TIMEW)
        self.assertLess(TIMEW.index('id: settingsSubModeStrip'),
                        TIMEW.index('id: clockSettingsPane'))
        self.assertIn('settingsSection: timew.settingsView', TIMEW)
        self.assertIn('height: 505 - settingsSubModeStrip.height - parent.spacing', TIMEW)

    def test_shared_cpu_pane_keeps_all_sections(self):
        self.assertIn('property string settingsSection: "all"', PANE)
        self.assertIn('visible: pane.settingsSection !== "sync"', PANE)
        self.assertIn('visible: pane.settingsSection !== "visual"', PANE)
        self.assertIn('id: visualSettingsContent', PANE)
        self.assertIn('id: syncSettingsContent', PANE)
        self.assertIn('id: settingsTimeBasicsPane', CPU)
        self.assertNotIn('settingsSection:', CPU)
        self.assertIn('onSettingsSectionChanged:', PANE)
        self.assertIn('scroll.contentY = 0;', PANE)
        self.assertIn('zonePickerExpanded = false;', PANE)
        self.assertLess(PANE.index('id: visualSettingsContent'),
                        PANE.index('SYSTEM TIMEZONE // CHANGE'))
        self.assertLess(PANE.index('SYSTEM TIMEZONE // CHANGE'),
                        PANE.index('id: syncSettingsContent'))
        self.assertLess(PANE.index('id: syncSettingsContent'),
                        PANE.index('id: autoCheckDial'))
        self.assertLess(PANE.index('id: autoCheckDial'),
                        PANE.index('CONFIRM RESYNC'))

    def test_dock_format_switch_uses_real_clock_owner(self):
        self.assertIn('property var dockClock: null', TIMEW)
        self.assertIn('dockClock: clockDock', SHELL)
        self.assertIn('timeWindow: timewWindow', SHELL)
        self.assertIn('property bool is24Hour: false', DOCK)
        self.assertIn('clockArea.is24Hour = !clockArea.is24Hour;', DOCK)
        self.assertIn('signal dockFormatRequested(bool use24)', PANE)
        self.assertIn('text: "DOCK // FORMAT"', PANE)
        self.assertIn('label: "12H"', PANE)
        self.assertIn('label: "24H"', PANE)
        self.assertIn('selected: !pane.dock24Hour', PANE)
        self.assertIn('selected: pane.dock24Hour', PANE)
        self.assertIn('pane.dockFormatRequested(false)', PANE)
        self.assertIn('pane.dockFormatRequested(true)', PANE)
        self.assertIn('dock24Hour: timew.dockClock ? timew.dockClock.is24Hour : false', TIMEW)
        self.assertIn('timew.dockClock.is24Hour = use24;', TIMEW)
        self.assertNotIn('TimeSettings.requestTimezone()', TIMEW.split(
            'id: clockSettingsPane', 1)[1].split('AngelPane {', 1)[0])

    def test_sync_dial_and_one_shot_resync_are_grouped_safely(self):
        self.assertIn('id: resyncDialButton', PANE)
        self.assertIn('id: resyncLaunch', PANE)  # CPU++ existing owner preserved
        self.assertIn('visible: pane.settingsSection !== "all"', PANE)
        self.assertIn('visible: pane.settingsSection === "all"', PANE)
        self.assertIn('showResyncTrigger: true', TIMEW)
        self.assertIn('label: "⟳ RESYNC"', PANE)
        self.assertIn('onLeftClicked: TimeSettings.prepareResync()', PANE)
        self.assertIn('onLeftClicked: TimeSettings.requestResync()', PANE)
        self.assertIn('onLeftClicked: TimeSettings.cancelResync()', PANE)
        self.assertIn('TimeSettings.setAutoCheckEnabled(', PANE)
        self.assertIn('TimeSettings.setAutoCheckIntervalHours(', PANE)
        self.assertIn('TimeSettings.checkTimeAccuracy()', PANE)
        dial = PANE.split('id: autoCheckDial', 1)[1].split(
            'text: "LAST CHECK // "', 1)[0]
        self.assertIn('id: resyncDialButton', dial)
        self.assertIn('"AUTO CHECK ON" : "AUTO CHECK OFF"', PANE)

    def test_tools_alarm_is_label_only_not_a_scheduling_service(self):
        self.assertIn('id: toolsSubModeStrip', TIMEW)
        self.assertIn('labelText: "STOPWATCH"', TIMEW)
        self.assertIn('labelText: "COUNTDOWN"', TIMEW)
        self.assertIn('labelText: "ALARM"', TIMEW)
        self.assertIn('onTriggered: timew.toolsView = "alarm"', TIMEW)
        alarm = TIMEW.split('id: alarmPlaceholderPane', 1)[1].split(
            'id: stopwatchPane', 1)[0]
        self.assertIn('ALARM // PLANNED', alarm)
        self.assertIn('ALARM CONTROLS // NOT IMPLEMENTED', alarm)
        self.assertNotIn('Timer {', alarm)
        self.assertNotIn('Process {', alarm)
        self.assertNotIn('onTriggered:', alarm)
        self.assertNotIn('onLeftClicked:', alarm)
        self.assertNotIn('notify-send', alarm)
        self.assertIn('height: 34', TIMEW.split('id: toolsSubModeStrip', 1)[1].split(
            'id: alarmPlaceholderPane', 1)[0])


if __name__ == "__main__":
    unittest.main()
