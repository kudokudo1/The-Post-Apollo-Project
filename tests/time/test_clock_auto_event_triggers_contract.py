"""Clock AUTO reference event triggers and selected/open styling contracts."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
SERVICE = (ROOT / "services/time/TimeSettings.qml").read_text(encoding="utf-8")
POLICY = (ROOT / "services/time/TimeAutoCheckPolicy.js").read_text(encoding="utf-8")
TIMEW = (ROOT / "widgets/TimeW.qml").read_text(encoding="utf-8")
COMPACT = (ROOT / "widgets/TimeSettingsCompact.qml").read_text(encoding="utf-8")
ACTION = (ROOT / "widgets/TimeActionButton.qml").read_text(encoding="utf-8")


class ClockEventTriggersContracts(unittest.TestCase):
    def test_reload_runs_once_after_durable_preferences_load(self):
        self.assertIn("property bool autoCheckReloadHandled: false", SERVICE)
        self.assertIn("if (!timeSettings.autoCheckReloadHandled)", SERVICE)
        self.assertIn("timeSettings.autoCheckReloadHandled = true;", SERVICE)
        self.assertIn('timeSettings.maybeAutoCheckTime("reload")', SERVICE)
        self.assertIn("timeSettings.maybeAutoCheckTime();", SERVICE)
        self.assertIn("Qt.callLater(function() {", SERVICE)
        self.assertIn("timeSettings.autoCheckStorageState = \"ready\";", SERVICE)

    def test_open_trigger_follows_true_timew_open_event_not_close(self):
        opened = TIMEW.split("onMenuOpenChanged: {", 1)[1].split(
            "onSelectedModeChanged: {", 1
        )[0]
        self.assertIn("if (menuOpen)", opened)
        self.assertIn("TimeSettings.checkOnClockOpened();", opened)
        self.assertLess(opened.index("if (menuOpen)"),
                        opened.index("TimeSettings.checkOnClockOpened();"))
        self.assertIn("autoCheckOpenPendingWhileLoading", SERVICE)
        self.assertIn('return maybeAutoCheckTime("clock-open")', SERVICE)

    def test_triggers_use_only_read_only_measurement_and_master_gate(self):
        portion = SERVICE.split("function setAutoCheckTrigger(name, enabled)", 1)[1].split(
            "function completeAutoReferenceIfReady()", 1
        )[0]
        self.assertIn("AutoCheck.withTrigger(", portion)
        self.assertIn("AutoCheck.canStartAutomaticCheck(active, reason, now,", portion)
        self.assertIn("referenceLastAttemptAtMs)", portion)
        self.assertIn("AutoCheck.isDue(doc, nowMs, lastAutoStartedAtMs)", POLICY)
        self.assertIn("MIN_AUTOMATIC_GAP_MS", POLICY)
        self.assertIn("checkTimeAccuracy()", portion)
        self.assertIn('"measure"', SERVICE)
        for forbidden in ("resyncProcess.exec(", "prepareResync(",
                          "requestResync(", "pkexec", "requestTimezone("):
            self.assertNotIn(forbidden, portion)
        self.assertIn("doc.enabled", POLICY)
        self.assertIn('trigger === "clock-open"', POLICY)
        self.assertIn('trigger === "reload"', POLICY)
        self.assertIn('return trigger === "interval"', POLICY)

    def test_both_trigger_preferences_are_persisted_in_v1_document(self):
        self.assertIn('"/time-auto-check-v1.json"', SERVICE)
        self.assertIn("checkOnReload: true", POLICY)
        self.assertIn("checkOnClockOpen: true", POLICY)
        self.assertIn("function validOptionalTrigger(value)", POLICY)
        self.assertIn("function normalizedTrigger(doc, name)", POLICY)
        self.assertIn("function withTrigger(doc, name, enabled)", POLICY)
        self.assertIn("checkOnReload: normalizedTrigger(", POLICY)
        self.assertIn("checkOnClockOpen: normalizedTrigger(", POLICY)
        self.assertIn("atomicWrites: true", SERVICE)

    def test_compact_sync_has_independent_active_buttons(self):
        sync = COMPACT.split("id: sync", 1)[1].split(
            "id: compactDetailsButton", 1
        )[0]
        self.assertIn("id: autoEventTriggers", sync)
        self.assertIn('label: TimeSettings.autoCheckOnReload', sync)
        self.assertIn('label: TimeSettings.autoCheckOnClockOpen', sync)
        self.assertIn("selected: TimeSettings.autoCheckOnReload", sync)
        self.assertIn("selected: TimeSettings.autoCheckOnClockOpen", sync)
        self.assertIn('setAutoCheckTrigger(\n                    "checkOnReload"', sync)
        self.assertIn('setAutoCheckTrigger(\n                    "checkOnClockOpen"', sync)
        self.assertIn("TimeSettings.autoCheckEnabled", sync)
        self.assertIn('label: "⟳ RESYNC"', sync)

    def test_preview_is_larger_and_selected_clock_format_uses_magenta(self):
        visual = COMPACT.split("id: visual", 1)[1].split("id: sync", 1)[0]
        self.assertIn('text: "PREVIEW // " + compact.calibratedPreview', visual)
        self.assertIn("font.pixelSize: 16", visual)
        self.assertIn("width: parent.width", visual)
        self.assertIn("idleForegroundColor: Colors.cyan", visual)
        self.assertIn("idleForegroundColor: Colors.orange", visual)
        self.assertNotIn("selectedForegroundColor: Colors.cyan", visual)
        self.assertNotIn("selectedForegroundColor: Colors.orange", visual)
        for prop in ("selectedFillColor: Colors.yellow",
                     "selectedForegroundColor: Colors.magenta",
                     "selectedBorderColor: Colors.magenta",
                     "selectedContentGlowColor: Colors.magenta",
                     "selectedSoftGlowColor: Colors.magenta",
                     "selectedWideGlowColor: Colors.magenta"):
            self.assertIn(prop, ACTION)

    def test_clock_submode_open_halation_is_magenta(self):
        sections = [
            ("calcSubModeStrip", "converterPane", 2),
            ("mathTypeStrip", "mathDifferencePane", 2),
            ("toolsSubModeStrip", "alarmPlaceholderPane", 3),
            ("settingsSubModeStrip", "clockSettingsPane", 2),
        ]
        for begin, end, count in sections:
            selection = TIMEW.split("id: " + begin, 1)[1].split(
                "id: " + end, 1
            )[0]
            self.assertEqual(selection.count(
                "perimeterGlowColor: selected ? Colors.magenta : Colors.orange"
            ), count)
            self.assertEqual(selection.count("bordered: true"), count)


if __name__ == "__main__":
    unittest.main()
