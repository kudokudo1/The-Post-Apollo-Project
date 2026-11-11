"""P31 Personal contact details, selection, and explicit action boundaries."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[2]
PHONE = ROOT / "widgets/messanger/PhonePane.qml"
DETAIL = ROOT / "widgets/messanger/PhoneContactDetail.qml"
PROJECTION = ROOT / "services/messaging/adapters/BlueFerryProjectionView.js"


class PhoneContactDetailsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.phone = PHONE.read_text(encoding="utf-8")
        cls.detail = DETAIL.read_text(encoding="utf-8")
        cls.projection = PROJECTION.read_text(encoding="utf-8")

    def extract(self, start: str, end: str) -> str:
        return self.phone.split(start, 1)[1].split(end, 1)[0]

    def test_selection_is_by_current_opaque_id_with_consent_and_snapshot_guards(self):
        part = self.extract("readonly property var selectedPhoneContactCard: {",
                            "Component.onCompleted:")
        for value in (
            'selectedSection !== "CONTACTS"', "!personalApproved",
            "personalNeedsExplicitReload", 'personalReadStatus !== "LOCAL_SNAPSHOT"',
            "!phoneReadAdapter.active", 'selectedPhoneContactId === ""',
            "phoneReadAdapter.contactCards", "String(cards[i].id) === selectedPhoneContactId",
            "return null;",
        ):
            self.assertIn(value, part)
        address_book = self.extract("id: phoneAddressBook", "// The separate PHONE address book")
        for value in (
            "selectedPhoneContactId", "required property var modelData", "MouseArea {",
            "onClicked:", 'personalReadStatus === "LOCAL_SNAPSHOT"',
            "!phonePane.personalNeedsExplicitReload", "String(modelData.id)",
            "maximumLineCount: 1", "clip: true",
            "Colors.orange", "Colors.cyan",
        ):
            self.assertIn(value, address_book)

    def test_no_stale_contact_after_revoke_identity_switch_or_close(self):
        changed = self.extract("onActiveSocialIdentityIdChanged: {", "property string probeStatus:")
        self.assertIn('selectedPhoneContactId = "";', changed)
        changed = self.extract("onSelectedSectionChanged: {", "onStageHoleXChanged:")
        self.assertIn('if (selectedSection !== "CONTACTS")', changed)
        self.assertIn('selectedPhoneContactId = "";', changed)
        closed = self.extract("onVisibleChanged: {", "function callsWorkspaceMessage()")
        self.assertGreaterEqual(closed.count('selectedPhoneContactId = "";'), 2)
        revoked = self.extract("function revokePersonalAccess()", "function clearPersonalView()")
        self.assertIn('selectedPhoneContactId = "";', revoked)
        cleared = self.extract("function clearPersonalView()", "function phoneStorageMessage()")
        self.assertIn('selectedPhoneContactId = "";', cleared)

    def test_contact_detail_reuses_only_projection_fields_not_private_lookups(self):
        for field in (
            "displayNameInProfile", "organization", "primary", "phoneCount",
            "emailCount", "hasPhoto",
        ):
            self.assertIn("contact." + field, self.detail)
            self.assertIn(field + ":", self.projection)
        for forbidden in (
            "Process {", "XMLHttpRequest", "LocalStorage", "file://",
            "Clipboard", "SendToThread", "fetch(", "openUrl(", "faceTime://",
            "facetime://", "sip:", "sms:", "tel:",
        ):
            self.assertNotIn(forbidden, self.detail)
        self.assertIn("text: detail.contact && detail.contact.hasPhoto", self.detail)
        self.assertIn("PHOTO REPORTED", self.detail)

    def test_three_buttons_are_visible_and_real_actions_have_honest_limits(self):
        self.assertIn('label: "CALL"', self.detail)
        self.assertIn('label: "MESSAGE"', self.detail)
        self.assertIn('label: "FACETIME"', self.detail)
        self.assertIn("interactive: detail.contact !== null && detail.canPrepareCall",
                      self.detail)
        self.assertIn("onTriggered: detail.callRequested()", self.detail)
        self.assertIn("onTriggered: detail.messageRequested()", self.detail)
        self.assertIn("interactive: false // No BlueFerry FaceTime transport.", self.detail)
        self.assertIn("PHONE cannot safely link a contact card to a thread", self.detail)
        self.assertIn("FACETIME unavailable", self.detail)
        self.assertIn("PhoneContactDetail {", self.phone)
        self.assertIn("onCallRequested: phonePane.openSelectedContactForCall()", self.phone)
        self.assertIn("onMessageRequested: phonePane.openSelectedContactMessages()", self.phone)

    def test_call_prefills_existing_confirmation_workspace_not_auto_dial(self):
        actions = self.extract("function contactPrimaryDialNumber(card)",
                               "function refreshCallsWorkspace()")
        self.assertIn('typeof card.primary !== "string"', actions)
        self.assertIn("normalized", actions)
        self.assertIn('/^[+]?[0-9]{3,18}$/.test(normalized)', actions)
        self.assertIn('selectedSection = "CALLS";', actions)
        self.assertIn("phoneDialInput.text = number;", actions)
        self.assertIn("callsConfirmDial = false;", actions)
        self.assertIn('selectedSection !== "CONTACTS"', actions)
        self.assertNotIn("requestCallAction(", actions)
        self.assertNotIn("preparePhoneDial()", actions)
        self.assertIn('label: "REVIEW OUTGOING CALL"', self.phone)
        self.assertIn('label: "CONFIRM CALL"', self.phone)

    def test_message_navigates_without_untrusted_contact_thread_matching_or_sending(self):
        actions = self.extract("function openSelectedContactMessages()",
                               "function refreshCallsWorkspace()")
        self.assertIn('selectedSection = "MESSAGES";', actions)
        self.assertIn('selectedPhoneContactCard === null', actions)
        for forbidden in (
            "sendMessage(", "sendRequested(", "phoneReadAdapter.loadMessages(",
            "savePersonalApproval(", "PhoneRememberedRead.py",
            "phoneReadAdapter.conversations", "contact.primary",
        ):
            self.assertNotIn(forbidden, actions)
        self.assertIn("sendEnabled: false", self.phone)

    def test_detail_panel_does_not_replace_existing_chat_feed_or_call_workspace(self):
        part = self.extract("PhoneContactDetail {", "// Informative, content-free status")
        self.assertIn("anchors.fill: phoneChatFeed", part)
        self.assertIn("contact: phonePane.selectedPhoneContactCard", part)
        self.assertIn("canPrepareCall: phonePane.contactPrimaryDialNumber(contact)", part)
        self.assertIn("    ChatFeed {", self.phone)
        self.assertIn("id: phoneCallsWorkspace", self.phone)
        self.assertIn("id: personalPermissionOverlay", self.phone)


if __name__ == "__main__":
    unittest.main()
