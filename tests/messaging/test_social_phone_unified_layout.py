"""PHONE uses the same conversations shell and horizontal navigation as Social."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[2]
PANE = ROOT / "widgets" / "messanger" / "PhonePane.qml"
LAUNCHER = ROOT / "services" / "phone" / "PhoneNativeSetupLaunch.py"


class UnifiedPhoneLayoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.phone = PANE.read_text()
        cls.launcher = LAUNCHER.read_text()

    def test_real_social_contact_and_chat_components_used(self):
        self.assertIn("    ContactList {", self.phone)
        self.assertIn("    ChatFeed {", self.phone)
        self.assertIn("        conversations: []", self.phone)
        self.assertIn("        conversation: null", self.phone)
        self.assertIn("        messages: []", self.phone)
        self.assertIn("        sendEnabled: false", self.phone)
        self.assertIn('emptyConversationLabel:', self.phone)
        self.assertIn("NO PHONE CHATS YET", self.phone)
        self.assertIn("NO PHONE CONTACTS", self.phone)
        self.assertNotIn("FloatingWindow {", self.phone)
        self.assertNotIn("PanelWindow {", self.phone)

    def test_phone_defaults_to_conversation_world(self):
        self.assertIn('property string selectedSection: "MESSAGES"', self.phone)
        self.assertIn('selectedSection = "MESSAGES";', self.phone)
        self.assertIn('selectedSection = "DEVICE";\n        setupState = "CHECKING";',
                      self.phone)
        self.assertIn('id: sectionToolbar', self.phone)
        self.assertIn('anchors.top: header.bottom', self.phone)
        self.assertIn('id: sectionTabs', self.phone)
        self.assertIn('model: ["DEVICE", "CALLS", "MESSAGES", "CONTACTS"]',
                      self.phone)
        self.assertNotIn("id: sectionRail", self.phone)
        self.assertIn('id: setupOverlay', self.phone)
        self.assertIn('anchors.fill: phoneChatFeed', self.phone)

    def test_one_connect_button_remains_in_header(self):
        self.assertEqual(self.phone.count('id: connectPhoneAction'), 1)
        self.assertIn('label: setupProcess.running ? "CHECKING..." : "CONNECT PHONE"',
                      self.phone)
        self.assertIn('onTriggered: phonePane.startSetup()', self.phone)
        self.assertIn('anchors.right: parent.right', self.phone)
        self.assertIn('label: "SET UP IPHONE"', self.phone)
        self.assertIn('label: "SET UP ANDROID"', self.phone)

    def test_setup_still_requires_explicit_action(self):
        visibility = re.search(
            r'onVisibleChanged: \{(?P<body>.*?)\n    \}',
            self.phone, re.S)
        self.assertIsNotNone(visibility)
        for event in ("startSetup(", "openNativeSetup(", "refreshReadiness("):
            self.assertNotIn(event, visibility.group("body"))
        self.assertIn('setupState !== "CHECKED"', self.phone)
        self.assertIn('nativeSetupProcess.running = true;', self.phone)
        self.assertIn('report.contentAccessEnabled !== false', self.phone)

    def test_no_fake_phone_data_or_unverified_authorization(self):
        self.assertIn('Social has NOT linked a phone', self.phone)
        self.assertIn("Social messages remain locked.", self.phone)
        self.assertIn('Social phone link: NOT VERIFIED', self.phone)
        self.assertIn("Trusted phone link: UNVERIFIED", self.phone)
        self.assertNotIn('sendMessage(', self.phone)
        self.assertNotIn('loadMessages(', self.phone)
        self.assertNotIn('SocialIdentityStore.', self.phone)
        self.assertNotIn('model: [{', self.phone)
        self.assertIn('phonePane.detailsOpen', self.phone)
        self.assertIn('READ-ONLY SETUP PREVIEW', self.phone)

    def test_gui_launcher_has_cli_fallback_not_bluez_mutation(self):
        self.assertIn('"blueferry-quickshell"', self.launcher)
        self.assertIn('[terminal_path, *flags, wizard, "pair-setup"]',
                      self.launcher)
        self.assertIn('if target == "iphone":', self.launcher)
        self.assertNotIn('bluetoothctl pair', self.launcher)
        self.assertNotIn('systemctl start', self.launcher)
        self.assertNotIn('shell=True', self.launcher)


if __name__ == "__main__":
    unittest.main()
