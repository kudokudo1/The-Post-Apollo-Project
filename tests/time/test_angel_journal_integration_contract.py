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
        self.assertIn("const localDate = new Date(observedAtMs)", PANE)
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

    def test_saved_date_is_visible_without_rewriting_angel_journal(self):
        # The v1 source already saves a true UTC instant and the captured
        # offset. Date formatting must be read-only and stable across moves.
        self.assertIn('function observedDate(row)', POLICY)
        self.assertIn('row.observedAtMs + row.utcOffsetMinutes * 60000', POLICY)
        self.assertIn('date.toISOString().slice(0, 10)', POLICY)
        self.assertIn('AngelPolicy.observedDate(modelData)', PANE)
        self.assertIn('AngelPolicy.observedDate(pane.selectedObservation)', PANE)
        self.assertIn('\\nDATE // ', PANE)
        self.assertIn('modelData.displayTime', PANE)
        self.assertIn('id: angelHistoryList', PANE)
        self.assertIn('new Date(pane.selectedObservation.observedAtMs)', PANE)
        self.assertEqual(STORE.count('FileView {'), 1)
        self.assertIn('angel-observations-v1.json', STORE)
        self.assertIn('var VERSION = 1;', POLICY)
        self.assertNotIn('property string observationDate', STORE)
        self.assertNotIn('function recordDate', STORE)

    def test_err_filter_combines_other_with_explicit_per_entry_review(self):
        self.assertIn('key: "err", label: "ERR"', PANE)
        self.assertIn('case "err":', POLICY)
        self.assertIn('kind === "err"', POLICY)
        self.assertIn('row.errMarked === true', POLICY)
        self.assertIn('matchesFilter(row.digits, "other")', POLICY)
        self.assertIn('function toggleErr(document, id)', POLICY)
        self.assertIn('function toggleErrObservation(id)', STORE)
        self.assertIn('Journal.toggleErr(document, id)', STORE)
        self.assertIn('id: errMarkButton', PANE)
        self.assertIn('"CLEAR ERR" : "MARK ERR"', PANE)
        self.assertIn('AngelObservationsStore.toggleErrObservation(pane.selectedId)', PANE)
        self.assertIn('label: (observationEntry.isMarkedErr ? "ERR* // " : "")', PANE)
        self.assertIn('OTHER = NO PATTERN // ERR = OTHER + USER-MARKED', PANE)
        self.assertIn('row.errMarked === undefined', POLICY)
        self.assertIn('errMarked: row.errMarked === true', POLICY)
        self.assertIn('errMarked: false', POLICY)
        self.assertIn('atomicWrites: true', STORE)
        self.assertEqual(STORE.count("FileView {"), 1)
        self.assertNotIn("FileView {", PANE)

    def test_semantic_filter_and_entry_colors_are_consistent(self):
        # ERR is an explicit per-sighting review; other unmatched rows
        # do not become red. Favorites take magenta; otherwise the first
        # structural pattern determines the row identity.
        filters = PANE.split("id: angelPatternFilters", 1)[1].split(
            "id: angelHistoryArea", 1)[0]
        entries = PANE.split("delegate: Item {", 1)[1].split(
            "onLeftClicked: {", 1)[0]
        self.assertIn('case "favorite": return Colors.magenta;', PANE)
        self.assertIn('case "mirror": return Colors.yellow;', PANE)
        self.assertIn('case "add": return Colors.cyan;', PANE)
        self.assertIn('case "subtract": return Colors.blue;', PANE)
        self.assertIn('case "multiply": return Colors.omnitrix;', PANE)
        self.assertIn('case "divide": return Colors.green;', PANE)
        self.assertIn('case "sequence": return Colors.orange;', PANE)
        self.assertIn('case "err": return Colors.red;', PANE)
        self.assertIn('default: return Colors.white;', PANE)
        self.assertIn('return filterInk(key);', PANE)
        self.assertNotIn('key === "sequence" ? Colors.yellow', PANE)
        self.assertIn("function visiblePattern(digits)", PANE)
        self.assertIn("patterns.indexOf(activeFilter) >= 0", PANE)
        self.assertIn("pane.visiblePattern(modelData.digits)", entries)
        self.assertIn("readonly property color ink: pane.filterInk(modelData.key)", filters)
        self.assertIn("idleBorderColor: edge", filters)
        self.assertIn("selected: pane.activeFilter === modelData.key", filters)
        self.assertIn("highlightWhenSelected: true", filters)
        self.assertIn("selectedForegroundColor: Colors.magenta", filters)
        self.assertIn("selectedContentGlowColor: Colors.magenta", filters)

        self.assertIn("readonly property bool isMarkedErr:", entries)
        self.assertIn("modelData.errMarked === true", entries)
        self.assertIn("isMarkedErr ? Colors.red", entries)
        self.assertIn("isFavoriteNumber ? Colors.magenta", entries)
        self.assertIn("pane.filterInk(pattern)", entries)
        self.assertIn("pane.filterEdge(pattern)", entries)
        self.assertIn("accentColor: observationEntry.entryInk", entries)
        self.assertIn("idleBorderColor: observationEntry.entryEdge", entries)
        self.assertIn("selected: pane.selectedId === modelData.id", entries)
        self.assertIn("highlightWhenSelected: true", entries)
        self.assertIn("selectedForegroundColor: Colors.magenta", entries)
        self.assertIn("selectedContentGlowColor: Colors.magenta", entries)
        self.assertNotIn("matchesFilter(", entries)
        self.assertNotIn("activeFilter ===", entries)

    def test_angel_selected_open_yellow_fill_with_magenta_glow(self):
        local_button = (ROOT / "widgets/AngelActionButton.qml").read_text(
            encoding="utf-8")
        meaning = (ROOT / "widgets/AngelMeaningPane.qml").read_text(
            encoding="utf-8")
        self.assertIn("ActionButton {", local_button)
        self.assertIn("readonly property color fixedFillColor: Colors.black",
                      local_button)
        self.assertIn("readonly property color activeFillColor: Colors.yellow",
                      local_button)
        self.assertIn("property bool highlightWhenSelected: false",
                      local_button)
        for state in ("idle", "hover", "pressed", "keyboardSelected"):
            self.assertIn(state + "FillColor: fixedFillColor", local_button)
        self.assertIn("selectedFillColor: activeFillColor", local_button)
        self.assertIn(
            "color: highlightWhenSelected && selected ? activeFillColor : fixedFillColor",
            local_button)
        self.assertIn("selectedForegroundColor: Colors.magenta", local_button)
        self.assertIn("selectedBorderColor: Colors.magenta", local_button)
        self.assertIn("selectedContentGlowColor: Colors.magenta", local_button)
        # Filled rectangular shadows caused the earlier visual failure.
        self.assertIn("softGlowEnabled: false", local_button)
        self.assertIn("wideGlowEnabled: false", local_button)
        self.assertIn("contentGlowEnabled: true", local_button)
        self.assertNotIn("RectangularShadow {", local_button)
        # Only active view/filter/history/note use the yellow selection fill.
        self.assertEqual(PANE.count("highlightWhenSelected: true"), 5)
        self.assertNotIn("highlightWhenSelected: true", meaning)
        for control in ("favoriteObservation", "errMarkButton"):
            block = PANE.split("id: " + control, 1)[1].split(
                "onLeftClicked:", 1)[0]
            self.assertNotIn("highlightWhenSelected: true", block)
        for content in (PANE, meaning):
            self.assertNotIn("FillColor:", content)
        self.assertEqual(PANE.count("AngelActionButton {"), 13)
        self.assertEqual(meaning.count("AngelActionButton {"), 2)
        self.assertIn("x: 0", PANE.split("id: favoriteObservation", 1)[1]
                      .split("id: noteObservation", 1)[0])
        self.assertIn("x: favoriteObservation.width + 4", PANE)
        self.assertIn("x: observationSelect.x + observationSelect.width + 4",
                      PANE)

    def test_counter_words_and_slashes_are_white(self):
        header = PANE.split('text: "HISTORY //"', 1)[1].split(
            'id: angelSearchInput', 1)[0]
        self.assertIn("color: Colors.white", header)
        self.assertIn("text: String(pane.filteredRows.length)", header)
        self.assertIn("color: Colors.magenta", header)
        self.assertIn('text: "SHOWN //"', header)
        self.assertIn("text: String(AngelObservationsStore.total)", header)
        self.assertIn("color: Colors.orange", header)
        self.assertIn('text: "SAVED"', header)

    def test_favorite_and_note_seams_use_existing_owners(self):
        self.assertIn("import qs.services.favorites", PANE)
        self.assertIn("FavoritesDefaultStore.toggleFavorite(", PANE)
        self.assertIn("FavoritesDefaultStore.favoriteKeys", PANE)
        self.assertIn('key: "favorite", label: "FAV"', PANE)
        self.assertIn('key: "multiply", label: "MUL"', PANE)
        self.assertIn('key: "divide", label: "DIV"', PANE)
        self.assertIn("function editObservationNote(row)", PANE)
        self.assertIn("function saveObservationNote(id, note)", STORE)
        self.assertIn("Journal.setNote(document, id, note)", STORE)
        self.assertIn('id: noteObservation', PANE)
        self.assertIn('id: noteField', PANE)
        self.assertIn('id: noteEditor', PANE)
        self.assertIn("AngelPolicy.MAX_NOTE_LENGTH", PANE)
        self.assertIn('text: "HISTORY //"', PANE)
        self.assertIn("Colors.magenta", PANE)
        self.assertIn("Colors.orange", PANE)
        err_button = PANE.split("id: errMarkButton", 1)[1].split(
            "id: deleteButton", 1)[0]
        self.assertIn("accentColor: Colors.red", err_button)

    def test_history_deletion_is_confirmed_and_red(self):
        self.assertIn('"CONFIRM ×" : "DELETE ×"', PANE)
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
