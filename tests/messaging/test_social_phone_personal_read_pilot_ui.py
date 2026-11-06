"""Social PHONE Personal read-only integration after remembered-Personal P21.

The historical P19 terminal/short-lived host remains as a legacy opt-in test
fixture, but PHONE now uses the explicit, remembered per-device preference.
Neither is a signed Identity Center grant or an app sandbox permission.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
PANE = ROOT / "widgets/messanger/PhonePane.qml"
ADAPTER = ROOT / "services/messaging/adapters/BlueFerryAdapter.qml"
REMEMBERED = ROOT / "services/phone/PhoneRememberedRead.py"
LEGACY = ROOT / "services/phone/PhonePersonalReadPilot.py"
ROUTER = ROOT / "services/messaging/SocialMessageRouter.qml"


class PersonalReadPilotUiContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pane = PANE.read_text()
        cls.remembered = REMEMBERED.read_text()
        cls.legacy = LEGACY.read_text()
        cls.adapter = ADAPTER.read_text()

    def test_explicit_first_approval_and_persistent_read_actions(self):
        for marker in (
            '"APPROVE READ"', '"PERMISSION ON"', '"LOAD PERSONAL"', '"REFRESH"',
            'label: "STOP ACCESS"', 'destructive: true',
            'id: personalConsentProcess', 'id: personalReadProcess',
            'id: personalRevokeProcess', 'id: personalStatusProcess',
            'PhoneRememberedRead.py', '"--approve", choice',
            '"--read", personalReadOperation', '"--revoke"', '"--status"',
            'id: personalPermissionOverlay',
            'phonePane.personalPermissionOpen',
            'function savePersonalApproval(choice)',
            'function loadPersonalSnapshot()',
            'function checkPersonalApproval(autoRead, promptIfMissing)',
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, self.pane)
        self.assertNotIn("PhonePersonalReadPilot.py", self.pane)
        self.assertNotIn('"--open-consent"', self.pane)
        self.assertNotIn("CONSENT_TERMINAL_REQUESTED", self.pane)

    def test_read_only_phone_feed_uses_existing_social_components(self):
        for marker in (
            'PhoneAdapters.BlueFerryAdapter {', 'active: phonePane.visible',
            '    ContactList {', '    ChatFeed {',
            'conversations: phonePane.selectedSection === "MESSAGES"',
            'phoneReadAdapter.loadMessages(',
            'messages: phonePane.selectedSection === "MESSAGES"',
            'sendEnabled: false', 'contactCards',
            'id: personalReadFeedback',
            'text: phonePane.personalReadMessage()',
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, self.pane)
        self.assertNotIn("SendToThread(", self.pane)
        self.assertNotIn("sendMessage(", self.pane)
        self.assertNotIn("BlueFerryHostReadPort", self.pane)
        self.assertNotIn("BlueFerryAdapter", ROUTER.read_text())
        self.assertNotIn("Process {", self.adapter)
        self.assertIn("sendText: false", self.adapter)

    def test_status_and_context_wipe_on_revoke_or_identity_change(self):
        for marker in (
            "personalReadGeneration += 1;",
            "phoneReadAdapter.forgetHostView();",
            'phonePane.personalReadStatus = "REVOKE_FAILED";',
            'value.ownerKind !== "PERSONAL"',
            'value.organizationAccess !== false',
            'value.sendingEnabled !== false',
            'value.contextKey !== phoneReadAdapter._contextKey',
            'value.epoch !== phoneReadAdapter._contextEpoch',
            'interval: 8000', '"--status"',
            "!== phonePane.personalReadGeneration",
            "case \"APPROVAL_REQUIRED\":",
            "case \"PROVIDER_UNAVAILABLE\":",
            "case \"READ_UNAVAILABLE\":",
            "case \"STORAGE_UNAVAILABLE\":",
            "case \"BRIDGE_UNAVAILABLE\":",
            "case \"REVOKE_FAILED\":",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, self.pane)
        self.assertNotIn("BlueFerryAdapter", ROUTER.read_text())
        self.assertNotIn("ID_TOKEN", self.remembered)
        self.assertNotIn("tenantId", self.remembered)
        self.assertIn('CONFIRM_TEXT = "ALLOW PERSONAL IPHONE READ"', self.legacy)

    def test_auto_read_only_after_saved_permission_not_auto_grant(self):
        start = self.pane.split("    function startSetup() {", 1)[1].split(
            "\n    function openNativeSetup", 1)[0]
        self.assertNotIn("openPersonalConsent()", start)
        self.assertNotIn("savePersonalApproval(", start)
        self.assertNotIn("loadPersonalSnapshot()", start)
        visible = self.pane.split("    onVisibleChanged: {", 1)[1].split(
            "\n    // The service adapter only displays", 1)[0]
        self.assertIn("checkPersonalApproval(!phonePane.personalNeedsExplicitReload, false)", visible)
        self.assertIn("personalNeedsExplicitReload = true;", self.pane)
        self.assertIn("if (personalApproved && !personalNeedsExplicitReload)", self.pane)
        self.assertIn("personalNeedsExplicitReload = false; // User explicitly requested Personal.", self.pane)
        self.assertNotIn("openPersonalConsent()", visible)
        self.assertNotIn("savePersonalApproval(", visible)
        self.assertNotIn('"--approve"', visible)
        self.assertNotIn("Component.onCompleted: openPersonalConsent()", self.pane)
        self.assertIn("if (personalApproved)", self.pane)
        self.assertIn("phonePane.loadPersonalSnapshot();", self.pane)
        self.assertIn('if (value.state === "APPROVAL_REQUIRED"', self.pane)
        self.assertIn("personalStatusProcess.promptIfMissing", self.pane)

    def test_in_panel_single_permission_and_independent_operations(self):
        for marker in (
            "ALLOW BOTH // REMEMBER",
            "MESSAGES ONLY // REMEMBER",
            "CONTACTS ONLY // REMEMBER",
            'phonePane.savePersonalApproval("b")',
            'phonePane.savePersonalApproval("m")',
            'phonePane.savePersonalApproval("c")',
            "NOT NOW",
            "Other apps running as your Linux user",
            "until you select STOP ACCESS",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, self.pane)
        self.assertIn('"contacts.read"', self.remembered)
        self.assertIn('"messages.read"', self.remembered)
        self.assertNotIn("messages.send", self.remembered)
        self.assertNotIn("org.kde.kdeconnect", self.remembered)


if __name__ == "__main__":
    unittest.main()
