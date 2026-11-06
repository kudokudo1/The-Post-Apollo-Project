"""P19 Personal-only local read pilot UI contract; no authenticated org access."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
PANE = ROOT / "widgets/messanger/PhonePane.qml"
ADAPTER = ROOT / "services/messaging/adapters/BlueFerryAdapter.qml"
HOST = ROOT / "services/phone/PhonePersonalReadPilot.py"
ROUTER = ROOT / "services/messaging/SocialMessageRouter.qml"


class PersonalReadPilotUiContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pane = PANE.read_text()
        cls.host = HOST.read_text()
        cls.adapter = ADAPTER.read_text()

    def test_explicit_personal_consent_and_read_actions(self):
        self.assertIn('label: "APPROVE READ"', self.pane)
        self.assertIn('label: "STOP ACCESS"', self.pane)
        self.assertIn("destructive: true", self.pane)
        self.assertIn('"LOAD PERSONAL"', self.pane)
        self.assertIn('label: phonePane.personalReadStatus === "READING"', self.pane)
        self.assertIn('id: personalConsentProcess', self.pane)
        self.assertIn('id: personalReadProcess', self.pane)
        self.assertIn('id: personalRevokeProcess', self.pane)
        self.assertIn('PhonePersonalReadPilot.py', self.pane)
        self.assertIn('"--open-consent"', self.pane)
        self.assertIn('"--client", personalReadOperation', self.pane)
        self.assertIn('"--client", "revoke"', self.pane)
        self.assertIn('CONFIRM_TEXT = "ALLOW PERSONAL IPHONE READ"', self.host)
        self.assertIn("sys.stdin.isatty()", self.host)

    def test_read_only_phone_feed_uses_single_existing_social_components(self):
        self.assertIn('PhoneAdapters.BlueFerryAdapter {', self.pane)
        self.assertIn('active: phonePane.visible', self.pane)
        self.assertIn('    ContactList {', self.pane)
        self.assertIn('    ChatFeed {', self.pane)
        self.assertIn('conversations: phonePane.selectedSection === "MESSAGES"', self.pane)
        self.assertIn('phoneReadAdapter.loadMessages(', self.pane)
        self.assertIn('messages: phonePane.selectedSection === "MESSAGES"', self.pane)
        self.assertIn('sendEnabled: false', self.pane)
        self.assertIn('contactCards', self.pane)
        self.assertNotIn("SendToThread(", self.pane)
        self.assertNotIn("sendMessage(", self.pane)
        self.assertNotIn("BlueFerryHostReadPort", self.pane)
        self.assertNotIn("BlueFerryAdapter", ROUTER.read_text())
        self.assertNotIn('Process {', self.adapter)
        self.assertIn('sendText: false', self.adapter)

    def test_no_secret_or_org_grants_in_ui_and_secure_lifecycle(self):
        for marker in (
            "personalReadGeneration += 1;",
            "phoneReadAdapter.forgetHostView();",
            "phonePane.personalReadStatus = \"ACCESS_STOPPED\";",
            'value.ownerKind !== "PERSONAL"',
            'value.organizationAccess !== false',
            'value.sendingEnabled !== false',
            'value.contextKey !== phoneReadAdapter._contextKey',
            'value.epoch !== phoneReadAdapter._contextEpoch',
            'id: personalStatusProcess',
            'interval: 3000',
            '"--client", "status"',
            "!== phonePane.personalReadGeneration",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, self.pane)
        self.assertNotIn("BlueFerryAdapter", ROUTER.read_text())
        self.assertIn("No texts are sent", self.host)
        self.assertNotIn("ID_TOKEN", self.host)
        self.assertNotIn("tenantId", self.host)

    def test_no_automatic_approval_on_connect_phone_or_visible(self):
        start = self.pane.split("    function startSetup() {", 1)[1].split(
            "\n    function openNativeSetup", 1)[0]
        self.assertNotIn("openPersonalConsent", start)
        self.assertNotIn("loadPersonalSnapshot", start)
        self.assertNotIn("PhonePersonalReadPilot.py", start)
        visible = self.pane.split("    onVisibleChanged: {", 1)[1].split(
            "\n    // This adapter never reads the phone itself.", 1)[0]
        self.assertNotIn("openPersonalConsent()", visible)
        self.assertNotIn("loadPersonalSnapshot()", visible)
        self.assertNotIn('Component.onCompleted: openPersonalConsent()', self.pane)


if __name__ == "__main__":
    unittest.main()
