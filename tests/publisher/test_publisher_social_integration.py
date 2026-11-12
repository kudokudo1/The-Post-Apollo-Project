"""Static P1 SocialW integration contract, without live Wayland claims."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
selector = (ROOT / "widgets/messanger/AppSelector.qml").read_text()
host = (ROOT / "widgets/messanger/MessagingW.qml").read_text()
pane = (ROOT / "widgets/publisher/PublisherPane.qml").read_text()
store = (ROOT / "services/publisher/PublisherDraftStore.qml").read_text()
policy = (ROOT / "services/publisher/PublisherDraftPolicy.js").read_text()
qmldir = (ROOT / "services/publisher/qmldir").read_text()


class PublisherP1Contracts(unittest.TestCase):
    def test_existing_social_window_stays_single(self):
        self.assertEqual(host.count("FloatingWindow {"), 1)
        self.assertIn("PublisherUi.PublisherPane {", host)
        self.assertIn('import "../publisher" as PublisherUi', host)
        self.assertIn("visible: messagingWindow.menuOpen && appSelector.publisherOpen", host)
        self.assertIn("z: 8", host)
        for source in (pane, store):
            for forbidden in ("FloatingWindow {", "PanelWindow {", "PopupWindow {",
                              "Process {", "sendMessage(", "login(", "logout("):
                self.assertNotIn(forbidden, source)

    def test_companion_ui_not_provider_app(self):
        self.assertIn("property bool publisherOpen: false", selector)
        self.assertIn('id: publisherFooter', selector)
        self.assertIn('label: "PUBLISHER"', selector)
        self.assertIn("appSelector.publisherOpen = next;", selector)
        self.assertIn("appSelector.publisherOpen = false;", host)
        self.assertIn("&& !appSelector.publisherOpen", host)
        self.assertIn("if (appSelector.publisherOpen)", host)
        self.assertIn("socialWindow.requestActivate();", host)
        self.assertIn('label: "PHONE"', selector)
        self.assertIn('label: "USER // SETTINGS"', selector)
        self.assertNotIn('name: "PUBLISHER"', selector)  # no service index
        self.assertIn("appSelector.appActivated(buttonContainer.modelData.serviceIndex);", selector)

    def test_draft_writer_and_future_states(self):
        self.assertIn("singleton PublisherDraftStore 1.0 PublisherDraftStore.qml", qmldir)
        self.assertIn('Quickshell.dataDir + "/publisher-drafts-v1.json"', store)
        for expected in ("watchChanges: false", "atomicWrites: true",
                         "onSaved:", "onSaveFailed:", "pendingDocument",
                         'storageState = "saving"', 'storageState = "error"',
                         "savedSuccessfully(savedId)"):
            self.assertIn(expected, store)
        self.assertIn("FileViewError.FileNotFound", store)
        self.assertIn("Policy.parse(raw)", store)
        self.assertIn("UNSUPPORTED_VERSION", policy)
        self.assertIn("DUPLICATE_DRAFT_ID", policy)
        self.assertIn("UNKNOWN_FIELDS", policy)
        self.assertIn("NO SCHEDULE, QUEUE, UPLOAD OR POSTING AUTHORITY.", pane)
        self.assertIn("LOCAL SAVE ACKNOWLEDGED", pane)
        self.assertNotIn("Qt.openUrlExternally", pane)


if __name__ == "__main__":
    unittest.main()
