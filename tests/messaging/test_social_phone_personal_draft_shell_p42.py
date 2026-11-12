"""P42 editable PHONE draft shell is NOT installed/wired to live contact UI.

Verifies neutral preview-only state, explicit non-saving behavior and styling.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
SHELL = ROOT / "widgets/messanger/PhonePersonalDraftEditor.qml"
DETAIL = ROOT / "widgets/messanger/PhoneContactDetail.qml"
PANE = ROOT / "widgets/messanger/PhonePane.qml"

class PersonalDraftShellTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = SHELL.read_text()
        cls.detail = DETAIL.read_text()
        cls.pane = PANE.read_text()

    def test_isolated_only_no_public_save_grant(self):
        self.assertNotIn("PhonePersonalDraftEditor", self.detail)
        self.assertNotIn("PhonePersonalDraftEditor", self.pane)
        self.assertIn("property bool previewEnabled: false", self.source)
        self.assertIn("readonly property bool secureSaveAuthorized: false", self.source)
        self.assertIn("available: editor.secureSaveAuthorized", self.source)
        self.assertIn("interactive: false // No native, verified one-use save host.", self.source)
        self.assertIn("PREVIEW ONLY // NOTHING IS SAVED OR SENT TO IPHONE", self.source)
        self.assertIn("SAVE REQUIRES VERIFIED PHONE HOST + C5 HUMAN CONSENT", self.source)
        self.assertNotIn("onTriggered: editor.save", self.source)

    def test_complete_native_controls_and_styles_exist(self):
        for part in (
            "☆ FAVORITE ON", "FAVORITE OFF", "NOTE // PRIVATE DRAFT",
            "TextEdit {", "color: Colors.magenta",
            "color: Colors.orange", "label: \"SAVE\"",
            "label: \"CLEAR DRAFT\"", "label: \"CANCEL\"",
            "accentColor: Colors.red", "destructive: true",
            "onContactChanged: resetForSelection()",
            "onPreviewEnabledChanged: resetForSelection()",
            "Component.onDestruction: discardDraft()",
            "editor.cancelRequested()",
        ):
            with self.subTest(part=part):
                self.assertIn(part, self.source)
        self.assertIn("DraftState.withFavorite", self.source)
        self.assertIn("DraftState.withNote", self.source)
        self.assertIn("DraftState.summary", self.source)

    def test_no_runtime_storage_or_provider_connection(self):
        for banned in (
            "Process {", "XMLHttpRequest", "LocalStorage",
            "FileView", "secret-tool", "PhonePersonalHostGateP36",
            "PhonePersonalContactVault", "writeFile", "sendMessage(",
            "Qt.openUrlExternally", "P37", "P41a",
            "onCallRequested:", "onMessageRequested:",
        ):
            with self.subTest(banned=banned):
                self.assertNotIn(banned, self.source)

if __name__ == "__main__":
    unittest.main()
