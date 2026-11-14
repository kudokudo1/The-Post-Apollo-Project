"""P44 native review presentation uses exactly the same ordered P44 plan.

Source checks do not authenticate C5 or native Fedora. SAVE remains hard false.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
EDITOR = ROOT / "widgets/messanger/PhonePersonalDraftEditor.qml"
DETAIL = ROOT / "widgets/messanger/PhoneContactDetail.qml"
P44 = ROOT / "widgets/messanger/PhonePersonalSavePlanP44.js"


class NativeTransactionReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.editor = EDITOR.read_text()
        cls.detail = DETAIL.read_text()
        cls.plan = P44.read_text()

    def test_review_displays_one_or_two_separate_approvals_without_note(self):
        for part in (
            'import "PhonePersonalSavePlanP44.js" as SavePlan',
            "readonly property var reviewPlan:",
            "SavePlan.planDraft(pending, currentContactId())",
            'editor.reviewPlan.status === "UNTRUSTED_REVIEW_ONLY"',
            "editor.reviewPlan.operations.length === 2",
            "2 SEPARATE HUMAN APPROVALS REQUIRED // NOT SAVED",
            "1 HUMAN APPROVAL REQUIRED // NOT SAVED",
            "REVIEW // NO VALID CHANGE TO SAVE",
        ):
            with self.subTest(part=part):
                self.assertIn(part, self.editor)
        self.assertNotIn('text: editor.pending.note', self.editor)
        self.assertNotIn('text: editor.reviewPlan.operations[', self.editor)

    def test_no_authority_from_client_plan_or_ui(self):
        self.assertIn("readonly property bool secureSaveAuthorized: false",
                      self.editor)
        self.assertIn("available: editor.secureSaveAuthorized", self.editor)
        self.assertIn("interactive: false", self.editor)
        self.assertIn("readonly property bool personalMetadataWritable: false",
                      self.detail)
        self.assertIn('onTriggered: detail.openDraftPreview()', self.detail)
        self.assertIn("PhonePersonalDraftEditor {", self.detail)
        self.assertNotIn("onSaveRequested:", self.detail)
        for banned in (
            "Process {", "XMLHttpRequest", "LocalStorage",
            "FileView", "secret-tool", "Vault.commit(",
            "Qt.openUrlExternally", "sendMessage(", "approved: true",
        ):
            self.assertNotIn(banned, self.editor)
            self.assertNotIn(banned, self.plan)

    def test_cancel_does_not_keep_old_draft(self):
        for part in (
            "onContactChanged: resetForSelection()",
            "onPreviewEnabledChanged: resetForSelection()",
            "Component.onDestruction: discardDraft()",
            'noteDraft.text = "";',
            "editor.discardDraft();",
            "editor.cancelRequested();",
        ):
            self.assertIn(part, self.editor)


if __name__ == "__main__":
    unittest.main()
