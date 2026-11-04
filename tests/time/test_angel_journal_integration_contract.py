"""ANGEL M1: TimeW seam, local journal ownership, history/search/filter safety.

Source checks supplement executable pure policy tests and native future UX
testing. No live Quickshell, system time, weather or disk state is touched.
"""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[2]
WINDOW = (ROOT / "widgets/TimeW.qml").read_text(encoding="utf-8")
PANE = (ROOT / "widgets/AngelPane.qml").read_text(encoding="utf-8")
STORE = (ROOT / "services/time/AngelObservationsStore.qml").read_text(encoding="utf-8")
POLICY = (ROOT / "services/time/AngelObservationPolicy.js").read_text(encoding="utf-8")
MODULE = (ROOT / "services/time/qmldir").read_text(encoding="utf-8")
NOTES = (ROOT / "services/hub/ApolloHubNotesStore.qml").read_text(encoding="utf-8")


class AngelJournalContracts(unittest.TestCase):
    def test_placeholder_replaced_without_reordering_other_modes(self):
        self.assertIn('id: "planned", name: "ANGEL"', WINDOW)
        self.assertIn('id: "settings", name: "SETTINGS"', WINDOW)
        self.assertIn("AngelPane {", WINDOW)
        self.assertIn("id: angelPane", WINDOW)
        self.assertIn('visible: timew.selectedMode === "planned"', WINDOW)
        self.assertIn("currentEpochMs: localClock.date.getTime()", WINDOW)
        self.assertNotIn("ANGEL // RESERVED", WINDOW)
        self.assertIn("ANGEL // EXPLICIT JOURNAL // LOCAL ONLY", WINDOW)

    def test_one_native_writer_and_disjoint_notes_tasks_weather(self):
        self.assertIn("singleton AngelObservationsStore 1.0 AngelObservationsStore.qml", MODULE)
        self.assertIn("singleton TimeSettings 1.0 TimeSettings.qml", MODULE)
        self.assertIn('angel-observations-v1.json', STORE)
        self.assertEqual(STORE.count("FileView {"), 1)
        self.assertIn("atomicWrites: true", STORE)
        self.assertIn("watchChanges: false", STORE)
        self.assertIn("blockWrites: false", STORE)
        self.assertIn("onSaved:", STORE)
        self.assertIn("onSaveFailed:", STORE)
        self.assertIn('storageState = "saving"', STORE)
        self.assertIn('feedback = "WRITING // NOT YET SAVED"', STORE)
        self.assertIn('feedback = "SAVED TO LOCAL JOURNAL"', STORE)
        self.assertIn("FileViewError.FileNotFound", STORE)
        self.assertIn("JOURNAL INVALID // DATA PRESERVED ON DISK", STORE)
        self.assertNotIn("FileView {", WINDOW)
        self.assertNotIn("FileView {", PANE)
        for code in (STORE, POLICY, PANE):
            for forbidden in ("apollo-hub-notes-v1.json", "apollo-hub-todo-v1.json",
                              "weather-event-archive-v1.json", "set-local-rtc",
                              "set-ntp", "set-timezone", "pkexec",
                              "Http", "NetworkManager", "chronyd"):
                self.assertNotIn(forbidden, code)
        self.assertIn("apollo-hub-notes-v1.json", NOTES)

    def test_recording_is_explicit_and_preserves_utc_context(self):
        self.assertIn("function recordClock()", PANE)
        self.assertIn("function recordManual()", PANE)
        self.assertIn("onLeftClicked: pane.recordClock()", PANE)
        self.assertIn("onLeftClicked: pane.recordManual()", PANE)
        self.assertIn("function record(digits, capture, observedAtMs)", STORE)
        self.assertIn("return stage(Journal.create(document, digits, capture, observedAtMs))", STORE)
        self.assertIn("Date.now()", PANE)
        self.assertIn("TimeSettings.adjustedEpochMs(observedAtMs)", PANE)
        self.assertIn("displayCalibrationMs: TimeSettings.displayOffsetMs", PANE)
        self.assertIn("utcOffsetMinutes: -localDate.getTimezoneOffset()", PANE)
        self.assertIn("zoneId: zone", PANE)
        self.assertIn("captureMode: mode", PANE)
        self.assertIn("observedAtMs: nowMs", POLICY)
        self.assertIn("displayTime: capture.displayTime", POLICY)
        self.assertNotIn("onCurrentEpochMsChanged: pane.recordClock()", PANE)

    def test_scrollable_history_search_and_overlapping_filter_set(self):
        self.assertIn("id: angelHistoryList", PANE)
        self.assertIn("ListView {", PANE)
        self.assertIn("model: pane.filteredRows", PANE)
        self.assertIn("id: angelSearchInput", PANE)
        self.assertIn("NeonScrollBar {", PANE)
        self.assertIn("handleStyle: \"star\"", PANE)
        self.assertIn("AngelPolicy.filter(AngelObservationsStore.observations", PANE)
        self.assertIn("AngelPolicy.patternTags(modelData.digits)", PANE)
        for pattern in ("repeat", "mirror", "sequence", "add", "subtract", "other"):
            self.assertIn('key: "' + pattern + '"', PANE)
            self.assertIn('case "' + pattern + '":', POLICY)
        self.assertIn("modelData.displayTime", PANE)
        self.assertIn("selectedObservation", PANE)
        self.assertIn("AngelObservationsStore.total", PANE)
        self.assertIn("searchInput", "angelSearchInput")

    def test_history_deletion_is_confirmed_and_red(self):
        self.assertIn('label: "CONFIRM ×"', PANE)
        self.assertIn('label: "DELETE ×"', PANE)
        self.assertIn('accentColor: Colors.red', PANE)
        self.assertIn('destructive: true', PANE)
        self.assertIn("AngelObservationsStore.deleteObservation(", PANE)
        self.assertIn("if (confirmed !== true)", POLICY)
        self.assertIn('reason: "CONFIRM_REQUIRED"', POLICY)
        self.assertIn("writable", STORE)
        self.assertNotIn("FileView {", PANE)

    def test_input_focus_preserves_keyboard_and_no_auto_capture(self):
        self.assertIn("!angelPane.editingText", WINDOW)
        self.assertIn("manualDigitsInput.activeFocus", PANE)
        self.assertIn("angelSearchInput.activeFocus", PANE)
        self.assertIn("RegularExpressionValidator {", PANE)
        self.assertEqual(PANE.count("RegularExpressionValidator {"), 2)
        self.assertIn("Qt.Key_Escape", PANE)
        self.assertNotIn("Timer {", PANE)
        self.assertNotIn("Process {", PANE)
        self.assertNotIn("SystemClock {", PANE)


if __name__ == "__main__":
    unittest.main()
