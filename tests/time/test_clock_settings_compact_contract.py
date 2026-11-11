"""Clock compact settings: no routine scrolling, preserved owners and controls."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
PANE = (ROOT / "widgets/TimeSettingsPane.qml").read_text()
COMPACT = (ROOT / "widgets/TimeSettingsCompact.qml").read_text()
TIMEW = (ROOT / "widgets/TimeW.qml").read_text()
CPU = (ROOT / "widgets/CpuPlusW.qml").read_text()


class ClockCompactSettingsContracts(unittest.TestCase):
    def test_only_clock_uses_fixed_layout_cpu_keeps_scrolling_full_pane(self):
        self.assertIn('property string settingsSection: "all"', PANE)
        self.assertIn('TimeSettingsCompact {', PANE)
        self.assertIn('id: compactSettings', PANE)
        self.assertIn('visible: pane.settingsSection !== "all"', PANE)
        self.assertIn('visible: pane.settingsSection === "all"', PANE)
        self.assertIn('settingsSection: pane.settingsSection', PANE)
        self.assertIn('settingsSection: timew.settingsView', TIMEW)
        self.assertIn('id: settingsTimeBasicsPane', CPU)
        self.assertNotIn('settingsSection:', CPU)
        # The main pages are fixed. Only the explicit DETAILS overlay
        # has an internal scroller for long diagnostic receipts.
        self.assertEqual(COMPACT.count('Flickable {'), 1)
        self.assertLess(COMPACT.index('id: sync'),
                        COMPACT.index('id: detailsScroll'))
        self.assertIn('id: detailsOverlay', COMPACT)
        self.assertIn('visible: compact.detailsOpen', COMPACT)
        self.assertIn('onLeftClicked: compact.detailsOpen = true', COMPACT)
        self.assertIn('onLeftClicked: compact.detailsOpen = false', COMPACT)
        self.assertNotIn('ScrollBar {', COMPACT)
        self.assertIn('id: visual', COMPACT)
        self.assertIn('id: sync', COMPACT)
        self.assertIn('anchors.top: parent.top', COMPACT)
        self.assertIn('visible: compact.settingsSection === "visual"', COMPACT)
        self.assertIn('visible: compact.settingsSection === "sync"', COMPACT)
        self.assertIn('systemZonePicker.searchFocused || compactSettings.zoneSearchFocused', PANE)

    def test_visual_keeps_dock_format_display_offset_and_confirmed_zone(self):
        visual = COMPACT.split('id: visual', 1)[1].split('id: sync', 1)[0]
        self.assertIn('label: "12H"', visual)
        self.assertIn('label: "24H"', visual)
        self.assertIn('Colors.cyan', visual)
        self.assertIn('Colors.orange', visual)
        self.assertIn('selectedForegroundColor: Colors.cyan', visual)
        self.assertIn('selectedForegroundColor: Colors.orange', visual)
        self.assertIn('selected: !compact.dock24Hour', visual)
        self.assertIn('selected: compact.dock24Hour', visual)
        self.assertIn('compact.dockFormatRequested(false)', visual)
        self.assertIn('compact.dockFormatRequested(true)', visual)
        self.assertIn('TimeSettings.adjustDisplayMs(modelData.delta)', visual)
        self.assertIn('TimeSettings.resetDisplay()', visual)
        self.assertIn('TimeSettings.prepareTimezone(modelData.zone)', visual)
        self.assertIn('TimeSettings.prepareTimezone(zoneId)', visual)
        self.assertIn('TimeSettings.requestTimezone()', visual)
        self.assertIn('TimeSettings.cancelTimezone()', visual)
        self.assertIn('id: compactZonePicker', visual)
        self.assertIn('z: 30', visual)
        self.assertIn('visible: TimeSettings.timezoneConfirmRequired', visual)
        self.assertIn('TimeSettings.hostInfo.dstActive', visual)
        self.assertIn('TimeSettings.timezoneMessage', visual)
        self.assertIn('TimeSettings.errorCode', visual)

    def test_sync_four_actions_adjacent_to_dial_with_auth_boundary(self):
        sync = COMPACT.split('id: sync', 1)[1]
        dial = sync.split('id: syncIntervalDial', 1)[1].split(
            'text: "LAST // "', 1
        )[0]
        for label in ('"AUTO ON" : "AUTO OFF"', 'label: "⟳ RESYNC"',
                      'label: "DIAGNOSE"', 'label: "CHECK TIME"'):
            self.assertIn(label, dial)
        for call in (
            'TimeSettings.setAutoCheckEnabled(',
            'TimeSettings.setAutoCheckIntervalHours(',
            'TimeSettings.prepareResync()',
            'TimeSettings.diagnoseResync()',
            'TimeSettings.checkTimeAccuracy()',
            'TimeSettings.requestResync()',
            'TimeSettings.cancelResync()',
        ):
            self.assertIn(call, sync)
        self.assertIn('visible: TimeSettings.resyncConfirmRequired', sync)
        self.assertIn('TimeSettings.autoCheckResult', sync)
        self.assertIn('TimeSettings.resyncMessage', sync)
        self.assertIn('TimeSettings.diagnosticMessage', sync)
        self.assertIn('TimeSettings.referenceMessage', sync)
        self.assertIn('TimeSettings.diagnosticDetail', COMPACT)
        self.assertIn('TimeSettings.resyncAuthPath', COMPACT)
        self.assertIn('TimeSettings.authFlowStage', COMPACT)
        self.assertIn('TimeSettings.timezoneMessage', COMPACT)
        self.assertIn('TimeSettings.resyncErrorCode', sync)
        self.assertIn('TimeSettings.autoCheckErrorCode', sync)
        self.assertIn('numericDetentInterval: 6', sync)
        self.assertIn('maximumValue: 168', sync)
        self.assertIn('snapContinuousToStep: true', sync)
        self.assertNotIn('resyncProcess.exec(', sync)
        self.assertNotIn('pkexec', sync)
        self.assertNotIn('Process {', sync)

    def test_every_timew_secondary_modebutton_is_bordered(self):
        for start, end, expected in (
            ('id: calcSubModeStrip', 'id: converterPane', 2),
            ('id: mathTypeStrip', 'id: mathDifferencePane', 2),
            ('id: toolsSubModeStrip', 'id: alarmPlaceholderPane', 3),
            ('id: settingsSubModeStrip', 'id: clockSettingsPane', 2),
        ):
            region = TIMEW.split(start, 1)[1].split(end, 1)[0]
            self.assertEqual(region.count('ModeButton {'), expected, start)
            self.assertEqual(region.count('bordered: true'), expected, start)
            self.assertNotIn('bordered: false', region)


if __name__ == "__main__":
    unittest.main()
