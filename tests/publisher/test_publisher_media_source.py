"""P1.2 static integration boundaries, not a live Quickshell visual test."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
pane = (ROOT / "widgets/publisher/PublisherPane.qml").read_text()
library = (ROOT / "widgets/publisher/PublisherMediaLibraryPane.qml").read_text()
picker = (ROOT / "widgets/publisher/PublisherMediaPicker.qml").read_text()
video = (ROOT / "widgets/publisher/PublisherVideoPreview.qml").read_text()
store = (ROOT / "services/publisher/PublisherMediaStore.qml").read_text()
policy = (ROOT / "services/publisher/PublisherMediaPolicy.js").read_text()
probe = (ROOT / "services/publisher/PublisherMediaProbe.py").read_text()
qmldir = (ROOT / "services/publisher/qmldir").read_text()
social = (ROOT / "widgets/messanger/MessagingW.qml").read_text()


class PublisherMediaSourceContracts(unittest.TestCase):
    def test_maintains_existing_social_single_window(self):
        self.assertEqual(social.count("FloatingWindow {"), 1)
        self.assertIn('id: publisherPane', social)
        self.assertIn("visible: messagingWindow.menuOpen && appSelector.publisherOpen",
                      social)
        self.assertIn('id:"media", label:"MEDIA"', pane)
        self.assertIn("PublisherMediaLibraryPane {", pane)
        self.assertIn("PublisherMediaStore.snapshot.links.filter(", pane)
        self.assertIn('onTriggered: publisher.activeSection = "media"', pane)
        self.assertNotIn("Process {", pane)
        self.assertNotIn("FloatingWindow {", library)
        self.assertNotIn("PanelWindow {", library)

    def test_picker_and_probe_are_deliberate_and_local(self):
        self.assertIn("import QtQuick.Dialogs", picker)
        self.assertIn("FileDialog.OpenFile", picker)
        self.assertIn("FileDialog.ReadOnly", picker)
        self.assertIn("onAccepted: picker.fileSelected", picker)
        self.assertIn("active: false", library)
        self.assertIn('source: "PublisherMediaPicker.qml"', library)
        self.assertIn("PublisherMediaProbe.py", library)
        self.assertIn('"python3", "-I", "-B"', library)
        self.assertIn("onStreamFinished:", library)
        self.assertIn("onExited:", library)
        self.assertIn('operation === "verify"', library)
        self.assertIn('result.stamp !== item.stamp', library)
        self.assertIn("verifiedPreview = true;", library)
        for banned in ("QNetworkAccessManager", "requests.post(", "urllib.request",
                       "shutil.copy", "shutil.move", "os.unlink(", "os.remove("):
            self.assertNotIn(banned, probe)

    def test_reference_storage_and_links_never_touch_original_file(self):
        self.assertIn("singleton PublisherMediaStore 1.0 PublisherMediaStore.qml", qmldir)
        self.assertIn('Quickshell.dataDir + "/publisher-media-v1.json"', store)
        for required in ("atomicWrites: true", "watchChanges: false",
                         "onSaved:", "onSaveFailed:", "pendingDocument",
                         "Policy.register(", "Policy.attach(", "Policy.detach(",
                         "operationFinished(", 'storageState = "error"'):
            self.assertIn(required, store)
        for required in ("TOO_MANY_ATTACHMENTS", "UNKNOWN_MEDIA",
                         "SOURCE_CHANGED_REVIEW_REQUIRED", "UNSUPPORTED_VERSION",
                         "INVALID_MEDIA_LINK", "UNKNOWN_FIELDS"):
            self.assertIn(required, policy)
        self.assertIn("savedDraftExists", library)
        self.assertIn("verifiedPreview", library)
        self.assertIn("CONFIRM UNLINK", library)
        self.assertIn("ORIGINAL FILE PRESERVED", library)
        for text in (library, pane, store, picker, video):
            self.assertNotIn("Qt.openUrlExternally", text)

    def test_optional_video_decoder_does_not_autoplay(self):
        self.assertIn("import QtMultimedia", video)
        self.assertIn("MediaPlayer {", video)
        self.assertIn("VideoOutput {", video)
        self.assertIn("AudioOutput { muted: true }", video)
        self.assertIn("onTriggered:", video)
        self.assertNotIn("autoPlay: true", video)
        self.assertIn('source: "PublisherVideoPreview.qml"', library)
        self.assertIn("videoPreview.status === Loader.Error", library)


if __name__ == "__main__":
    unittest.main()
