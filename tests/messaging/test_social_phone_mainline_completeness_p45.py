"""P45 asserts previously side-branch-merged P44 actually exists in mainline.

This catches a GitHub merged flag that only means the feature branch moved,
not that the main application contains the dependent source.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
P44 = (
    ".github/workflows/social-phone-p44-transaction-rehearsal.yml",
    "MODEL/contracts/social-phone-p44-transaction-rehearsal-v0.md",
    "services/phone/PhonePersonalSaveOrchestratorP44.py",
    "tests/messaging/test_social_phone_save_plan_p44.cjs",
    "tests/messaging/test_social_phone_transaction_review_p44.py",
    "tests/phone/test_phone_personal_save_orchestrator_p44.py",
    "widgets/messanger/PhonePersonalSavePlanP44.js",
)
EDITOR = ROOT / "widgets/messanger/PhonePersonalDraftEditor.qml"
DETAIL = ROOT / "widgets/messanger/PhoneContactDetail.qml"
KEY = ROOT / "services/phone/PhonePersonalProtectedKeyP45.py"


class MainlineContractTests(unittest.TestCase):
    def test_all_original_p44_files_exist_on_checkout(self):
        for path in P44:
            with self.subTest(path=path):
                source = ROOT / path
                self.assertTrue(source.is_file(), path)
                self.assertTrue(source.read_text().strip(), path)

    def test_p44_review_and_p45_locked_feedback_really_wired(self):
        editor = EDITOR.read_text()
        detail = DETAIL.read_text()
        for part in (
            'import "PhonePersonalSavePlanP44.js" as SavePlan',
            'import "PhonePersonalSaveFeedbackP45.js" as SaveFeedback',
            "SavePlan.planDraft(pending, currentContactId())",
            'SaveFeedback.classify({status: "HOST_UNAVAILABLE"}).text',
            "2 SEPARATE HUMAN APPROVALS REQUIRED // NOT SAVED",
            "1 HUMAN APPROVAL REQUIRED // NOT SAVED",
            "readonly property bool secureSaveAuthorized: false",
            "interactive: false // No native, verified one-use save host.",
        ):
            with self.subTest(part=part):
                self.assertIn(part, editor)
        self.assertIn("PhonePersonalDraftEditor {", detail)
        self.assertIn("readonly property bool personalMetadataWritable: false", detail)
        self.assertIn('onTriggered: detail.openDraftPreview()', detail)
        self.assertNotIn("PhonePersonalProtectedKeyP45", editor)
        self.assertNotIn("PhonePersonalProtectedKeyP45", detail)

    def test_no_production_secret_service_run_from_ui(self):
        editor = EDITOR.read_text()
        key = KEY.read_text()
        self.assertIn("post-apollo-phone-personal-protected-v1", key)
        self.assertIn("lookup", key)
        for code in (
            "secret-tool", "subprocess", "Vault.commit(",
            "Qt.openUrlExternally", "Process {", "FileView",
        ):
            self.assertNotIn(code, editor)
        for code in ('"store"', '"clear"', '"unlock"', "def main("):
            self.assertNotIn(code, key)


if __name__ == "__main__":
    unittest.main()
