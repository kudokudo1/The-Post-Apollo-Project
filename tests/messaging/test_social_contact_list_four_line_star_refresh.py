"""P30: shared native contact previews and consent-preserving PHONE tab refresh."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[2]
LIST = ROOT / "widgets/messanger/ContactList.qml"
PHONE = ROOT / "widgets/messanger/PhonePane.qml"
MESSAGING = ROOT / "widgets/messanger/MessagingW.qml"
SCROLL = ROOT / "components/NeonScrollBar.qml"


class ContactListFourLineStarRefreshTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contact = LIST.read_text(encoding="utf-8")
        cls.phone = PHONE.read_text(encoding="utf-8")
        cls.messaging = MESSAGING.read_text(encoding="utf-8")
        cls.scroll = SCROLL.read_text(encoding="utf-8")

    def test_shared_list_reused_by_phone_and_other_social_services(self):
        self.assertIn('    ContactList {', self.phone)
        self.assertIn('        ContactList {', self.messaging)
        self.assertIn("property bool phonePreviewMode: true", self.contact)
        self.assertIn("phonePreviewMode: true", self.phone)
        self.assertIn("height: contactRoot.phonePreviewMode ? 116 : 66", self.contact)
        self.assertIn("maximumLineCount: contactRoot.phonePreviewMode ? 4 : 2147483647",
                      self.contact)
        self.assertIn("height: contactRoot.phonePreviewMode ? 64 : implicitHeight",
                      self.contact)
        self.assertIn("spacing: 7", self.contact)

    def test_contact_colors_are_orange_and_message_cyan_with_selected_contrast(self):
        name = self.contact.split("id: contactName", 1)[1].split(
            "id: contactPreview", 1)[0]
        preview = self.contact.split("id: contactPreview", 1)[1].split(
            "id: contactMouse", 1)[0]
        self.assertIn("Colors.black : Colors.orange", name)
        self.assertIn("Colors.black : Colors.cyan", preview)
        self.assertIn("opacity: 1.0", preview)
        self.assertIn("textFormat: contactRoot.phonePreviewMode ? Text.PlainText", preview)
        self.assertIn('String(modelData.lastMessage || "").replace(/\\s+/g, " ").trim()',
                      preview)
        self.assertIn("clip: contactRoot.phonePreviewMode", name)
        self.assertIn("clip: contactRoot.phonePreviewMode", preview)
        self.assertIn("elide: Text.ElideRight", preview)
        address_book = self.phone.split("id: phoneAddressBook", 1)[1].split(
            "id: emptyPhoneContacts", 1)[0]
        self.assertIn("color: Colors.orange", address_book)
        self.assertIn("color: Colors.cyan", address_book)

    def test_star_scrollbar_reuses_shared_component_only_in_contact_list(self):
        self.assertIn('handleStyle: "star"', self.contact)
        self.assertIn("accountForContentOrigin: true", self.contact)
        self.assertIn('property string handleStyle: "bar"', self.scroll)
        self.assertIn('String(root.handleStyle || "").toLowerCase() === "star"', self.scroll)
        self.assertIn("visible: conversationList.visible && scrollable", self.contact)
        address_book = self.phone.split("id: phoneAddressBook", 1)[1].split(
            "id: emptyPhoneContacts", 1)[0]
        self.assertIn('flickable: phoneAddressBook', address_book)
        self.assertIn('geometryMode: "viewport"', address_book)
        self.assertIn('handleStyle: "star"', address_book)
        self.assertIn("accountForContentOrigin: true", address_book)

    def test_messages_tab_first_open_switch_and_repeat_click_are_covered(self):
        tabs = self.phone.split('id: sectionTabs', 1)[1].split(
            'id: personalReadBar', 1)[0]
        self.assertIn('model: ["DEVICE", "CALLS", "MESSAGES", "CONTACTS"]', tabs)
        self.assertIn('modelData === "MESSAGES"', tabs)
        self.assertIn('phonePane.selectedSection === "MESSAGES"', tabs)
        self.assertIn('phonePane.refreshMessagesTabOnRepeat();', tabs)
        self.assertIn('phonePane.selectedSection = modelData;', tabs)
        section = self.phone.split("onSelectedSectionChanged: {", 1)[1].split(
            "onStageHoleXChanged:", 1)[0]
        self.assertIn('selectedSection === "MESSAGES"', section)
        self.assertIn("loadPersonalSnapshot();", section)
        self.assertIn("checkPersonalApproval(false, false);", section)
        opened = self.phone.split("onVisibleChanged: {", 1)[1].split(
            "function callsWorkspaceMessage()", 1)[0]
        self.assertIn('selectedSection = "MESSAGES";', opened)
        self.assertIn("checkPersonalApproval(!phonePane.personalNeedsExplicitReload, false)",
                      opened)

    def test_repeat_click_cannot_bypass_consent_or_start_concurrent_reads(self):
        action = self.phone.split("function refreshMessagesTabOnRepeat()", 1)[1].split(
            "onSelectedSectionChanged:", 1)[0]
        for required in (
            "!visible", "!personalReadUiReady",
            'selectedSection !== "MESSAGES"', "personalPermissionOpen",
            "personalRevokeProcess.running",
            "personalReadProcess.running", "personalStatusProcess.running",
            "personalApproved && !personalNeedsExplicitReload",
            "loadPersonalSnapshot();",
            "checkPersonalApproval(!personalNeedsExplicitReload, false);",
        ):
            self.assertIn(required, action)
        for forbidden in (
            "savePersonalApproval", "openPersonalConsent", "unlockBlueFerryStorage",
            "startSetup(", "PhoneRememberedRead.py", "personalApproved = true",
            "phoneReadAdapter.beginHostView", "revokePersonalAccess",
            "sendMessage(",
        ):
            self.assertNotIn(forbidden, action)
        self.assertIn('sendEnabled: false', self.phone)


if __name__ == "__main__":
    unittest.main()
