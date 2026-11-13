"""Publisher P1.3 source and permission boundaries, no live desktop claims."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
POLICY = (ROOT / "services/publisher/PublisherTemplatePolicy.js").read_text()
STORE = (ROOT / "services/publisher/PublisherTemplateStore.qml").read_text()
PANE = (ROOT / "widgets/publisher/PublisherTemplatePane.qml").read_text()
PUBLISHER = (ROOT / "widgets/publisher/PublisherPane.qml").read_text()
QMLDIR = (ROOT / "services/publisher/qmldir").read_text()
SOCIAL = (ROOT / "widgets/messanger/MessagingW.qml").read_text()
DRAFT_STORE = (ROOT / "services/publisher/PublisherDraftStore.qml").read_text()
MEDIA_STORE = (ROOT / "services/publisher/PublisherMediaStore.qml").read_text()


class PublisherP13Contracts(unittest.TestCase):
    def test_no_new_social_window_or_provider_authority(self):
        self.assertEqual(SOCIAL.count("FloatingWindow {"), 1)
        self.assertIn('id:"templates", label:"TEMPLATES"', PUBLISHER)
        self.assertIn("PublisherTemplatePane {", PUBLISHER)
        self.assertIn("onGenerated: function(title, body)", PUBLISHER)
        self.assertIn("function composerHasUnsavedChanges()", PUBLISHER)
        self.assertIn('COMPOSE HAS UNSAVED CHANGES', PUBLISHER)
        self.assertIn('publisher.newDraft();', PUBLISHER)
        self.assertIn('publisher.feedback = "TEMPLATE APPLIED // REVIEW FACTS & SAVE"', PUBLISHER)
        for source in (POLICY, STORE, PANE):
            for forbidden in ("QNetworkAccessManager", "Qt.openUrlExternally",
                              "subprocess", "Process {", "sendMessage(",
                              "openProviderWeb(", "shellPath("):
                self.assertNotIn(forbidden, source)
        for source in (STORE, PANE):
            for forbidden in ("FloatingWindow {", "PanelWindow {", "PopupWindow {"):
                self.assertNotIn(forbidden, source)

    def test_separate_fail_closed_single_writer(self):
        self.assertIn(
            "singleton PublisherTemplateStore 1.0 PublisherTemplateStore.qml",
            QMLDIR)
        self.assertIn('Quickshell.dataDir + "/publisher-templates-v1.json"', STORE)
        for required in ("watchChanges: false", "atomicWrites: true",
                         "onSaved:", "onSaveFailed:", "pendingDocument",
                         'storageState = "saving"', 'storageState = "error"',
                         "savedSuccessfully(completedId)", "Policy.parse(raw)"):
            self.assertIn(required, STORE)
        for required in ("UNSUPPORTED_VERSION", "UNKNOWN_FIELDS",
                         "DUPLICATE_TEMPLATE_ID", "REQUIRED_FACT_MISSING",
                         "UNBOUND_PLACEHOLDER", "LOCKED_FACT_NOT_USED",
                         "MALFORMED_PLACEHOLDER", "safeLanguage", "MAX_OUTPUT"):
            self.assertIn(required, POLICY)
        self.assertIn('publisher-drafts-v1.json', DRAFT_STORE)
        self.assertIn('publisher-media-v1.json', MEDIA_STORE)
        self.assertNotIn("PublisherTemplateStore", DRAFT_STORE + MEDIA_STORE)

    def test_preview_cannot_claim_ai_or_publish(self):
        self.assertIn("TemplatePolicy.preview(", PANE)
        self.assertIn("TemplatePolicy.factLines(", PANE)
        self.assertIn("TemplatePolicy.preset(", PANE)
        self.assertIn("function invalidatePreview()", PANE)
        self.assertIn("onTextChanged: templatePane.invalidatePreview()", PANE)
        self.assertIn("function runPreview()", PANE)
        self.assertIn("SAVE TEMPLATE", PANE)
        self.assertIn("USE IN COMPOSE", PANE)
        self.assertIn("templatePane.generated(", PANE)
        self.assertIn("No claims are externally verified, translated, AI rewritten or published.", PANE)
        self.assertIn("Only substitution is locked. Compose remains editable.", PANE)
        self.assertNotIn("autoPublish", PANE)
        self.assertNotIn("upload", STORE.lower())


if __name__ == "__main__":
    unittest.main()
