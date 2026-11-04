"""ANGEL M2 source lens integration contracts, no live HTTP or local writes."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
JOURNAL = (ROOT / "widgets/AngelPane.qml").read_text()
MEANING = (ROOT / "widgets/AngelMeaningPane.qml").read_text()
POLICY = (ROOT / "services/time/AngelInterpretationPolicy.js").read_text()
SOURCE = (ROOT / "services/time/AngelSourceLookup.py").read_text()
STORE = (ROOT / "services/time/AngelObservationsStore.qml").read_text()
TIMEW = (ROOT / "widgets/TimeW.qml").read_text()


class AngelInterpretationIntegration(unittest.TestCase):
    def test_journal_and_meaning_are_separate_explicit_modes(self):
        self.assertIn('property string activeView: "journal"', JOURNAL)
        self.assertIn('id: angelViewStrip', JOURNAL)
        self.assertIn('label: "JOURNAL"', JOURNAL)
        self.assertIn('label: "MEANING"', JOURNAL)
        self.assertIn('onLeftClicked: pane.showMeaning()', JOURNAL)
        self.assertIn('function showMeaning()', JOURNAL)
        self.assertIn('pane.meaningSelection = chosen;', JOURNAL)
        self.assertIn('id: angelMeaningPane', JOURNAL)
        self.assertIn('visible: pane.activeView === "meaning"', JOURNAL)
        self.assertIn('visible: pane.activeView === "journal"', JOURNAL)
        self.assertIn('initialDigits: pane.meaningSelection', JOURNAL)
        self.assertIn('!angelPane.editingText', TIMEW)
        self.assertIn('|| angelMeaningPane.editingText', JOURNAL)
        self.assertIn('id: angelHistoryList', JOURNAL)
        self.assertIn('id: errMarkButton', JOURNAL)
        self.assertIn('id: deleteButton', JOURNAL)

    def test_request_requires_click_and_explicit_preflight(self):
        self.assertIn('id: sourceButton', MEANING)
        self.assertIn('label: sourceProcess.running ? "FETCHING..." : "FETCH SOURCE"', MEANING)
        self.assertIn('onLeftClicked: meaning.requestSource()', MEANING)
        self.assertIn('onAccepted: meaning.requestSource()', MEANING)
        self.assertIn('function requestSource()', MEANING)
        self.assertIn('if (!Interpret.lookupEligible(requested) || sourceProcess.running)', MEANING)
        self.assertIn('sourceProcess.exec([', MEANING)
        self.assertIn('Quickshell.shellPath("services/time/AngelSourceLookup.py")', MEANING)
        self.assertIn('Process {', MEANING)
        self.assertIn('running: false', MEANING)
        self.assertNotIn('Timer {', MEANING)
        self.assertNotIn('Component.onCompleted: meaning.requestSource()', MEANING)
        self.assertNotIn('onInitialDigitsChanged: requestSource()', MEANING)
        self.assertNotIn('Process {', JOURNAL)

    def test_lookup_is_quoted_and_separate_from_journal_writer(self):
        self.assertIn('SOURCE_ROOT', POLICY)
        self.assertIn('https://www.astrology.com/numerology/angel-numbers/', POLICY)
        self.assertIn('var PROVIDER = "Astrology.com"', POLICY)
        self.assertIn('digits.length <= 4', POLICY)
        self.assertIn('MAX_DIGITS = 8', POLICY)
        self.assertIn('urllib.request', SOURCE)
        self.assertIn('SamePublisherRedirect', SOURCE)
        self.assertIn('MAX_BYTES = 512000', SOURCE)
        self.assertIn('TIMEOUT = 9', SOURCE)
        self.assertIn('WORD_LIMIT = 20', SOURCE)
        self.assertIn('SOURCE_NOT_VERIFIED', SOURCE)
        self.assertIn("class ShortSectionParser(HTMLParser)", SOURCE)
        self.assertIn('extract_reference(page, digits)', SOURCE)
        self.assertNotIn('FileView {', MEANING)
        self.assertNotIn('FileView {', SOURCE)
        self.assertNotIn('Process {', STORE)
        self.assertIn('angel-observations-v1.json', STORE)

    def test_meaning_is_not_equated_to_verifiable_cosmic_event(self):
        self.assertIn('meaning.patternTags.join(" + ")', MEANING)
        self.assertIn('Interpret.arithmeticReduction(digits)', MEANING)
        self.assertIn('No universal angel-number interpretation is inferred', MEANING)
        self.assertIn('Published meanings are beliefs or traditions', MEANING)
        self.assertIn('No automatic searches and no stored meanings', MEANING)
        self.assertIn('NO BROWSER REDIRECT', MEANING)
        self.assertIn('sourceResult = null', MEANING)
        self.assertIn('requestDigits !== digits', MEANING)
        self.assertIn('Interpret.interpretResponse(raw, requestDigits)', MEANING)
        self.assertNotIn('WeatherEventArchive', MEANING)
        self.assertNotIn('CelestialVisualService', MEANING)


if __name__ == "__main__":
    unittest.main()
