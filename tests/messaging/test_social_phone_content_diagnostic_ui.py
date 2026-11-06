"""Content-free phone channel readiness is shown in PHONE, not a fake inbox."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
PANE = ROOT / "widgets" / "messanger" / "PhonePane.qml"
SCRIPT = ROOT / "services" / "phone" / "PhoneContentDiagnostic.py"


class PhoneContentDiagnosticUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ui = PANE.read_text(encoding="utf-8")

    def test_one_connect_action_inspects_content_channels(self):
        setup = self.ui.split("    function startSetup() {", 1)[1].split(
            "\n    function openNativeSetup", 1
        )[0]
        self.assertIn("refreshContentDiagnostic();", setup)
        self.assertIn("refreshSavedBridgeState();", setup)
        self.assertIn("refreshDeviceObservation();", setup)
        self.assertIn("id: contentDiagnosticProcess", self.ui)
        self.assertIn("PhoneContentDiagnostic.py", self.ui)
        self.assertIn('"--inspect"', self.ui)

    def test_only_public_metadata_is_accepted(self):
        for phrase in (
            'result.schema !== "post-apollo.phone.content-diagnostic.v0"',
            'result.execution !== "READ_ONLY_PROVIDER_METADATA"',
            'result.socialLink !== "NOT_AUTHORIZED"',
            'result.trustedPhoneLink !== "UNVERIFIED"',
            'result.routeEligible !== false',
            'result.contentAccessEnabled !== false',
            'result.messages.state === "UNVERIFIED"',
            'result.contacts.state === "UNVERIFIED"',
            'count >= 0 && count <= 100000',
        ):
            with self.subTest(marker=phrase):
                self.assertIn(phrase, self.ui)

    def test_message_and_contact_tabs_show_distinct_explanations(self):
        self.assertIn('id: phoneDataHint', self.ui)
        self.assertIn('phonePane.contentDiagnosticText(phonePane.selectedSection)', self.ui)
        self.assertIn('phonePane.contentDiagnosticText("MESSAGES")', self.ui)
        self.assertIn('phonePane.contentDiagnosticText("CONTACTS")', self.ui)
        self.assertIn('MAP session reported active.', self.ui)
        self.assertIn('PBAP session reported active.', self.ui)
        self.assertIn('Social contact access is still NOT LINKED.', self.ui)
        self.assertIn('Social permission are NOT VERIFIED.', self.ui)
        self.assertIn('textFormat: Text.PlainText', self.ui)

    def test_existing_components_are_still_empty_and_send_disabled(self):
        self.assertIn("    ContactList {", self.ui)
        self.assertIn("    ChatFeed {", self.ui)
        self.assertIn("phoneReadAdapter.conversations : []", self.ui)
        self.assertIn("phoneReadAdapter.messages : []", self.ui)
        self.assertIn("sendEnabled: false", self.ui)
        self.assertNotIn('conversations: phonePane.contentDiagnostic', self.ui)
        self.assertNotIn('messages: phonePane.contentDiagnostic', self.ui)
        self.assertNotIn("sendMessage(", self.ui)
        self.assertNotIn("ListThreads(", self.ui)

    def test_observation_is_reset_when_phone_reopens_and_after_setup(self):
        self.assertIn('contentDiagnosticCheck = "NOT CHECKED";', self.ui)
        self.assertIn('contentDiagnostic = ({});', self.ui)
        self.assertIn("phonePane.refreshContentDiagnostic();", self.ui)
        self.assertTrue(SCRIPT.exists())


if __name__ == "__main__":
    unittest.main()
