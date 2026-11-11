"""P32: anchored contact/message search and magenta alphabetical sections."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
PANE = ROOT / "widgets/messanger/PhonePane.qml"
DIRECTORY = ROOT / "widgets/messanger/PhoneDirectorySearch.js"


class PhoneFixedSearchSections(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pane = PANE.read_text(encoding="utf-8")
        cls.directory = DIRECTORY.read_text(encoding="utf-8")

    def test_search_is_fixed_above_both_scroll_lists(self):
        code = self.pane.split("id: phoneListSearchBar", 1)[1].split(
            "    ContactList {", 1)[0]
        for marker in (
            "anchors.top: personalReadBar.bottom",
            'selectedSection === "MESSAGES"',
            'selectedSection === "CONTACTS"',
            'id: phoneContactsSearch', 'id: phoneMessagesSearch',
            'text: phonePane.contactSearchQuery',
            'text: phonePane.messageSearchQuery',
            'color: Colors.magenta',
            'color: Colors.orange',
            'maximumLength: 128',
            'selectByMouse: true',
            'FILTERING LOADED CONTACTS',
            'SEARCH LOADED CONTACTS',
            'FILTERING CONVERSATIONS',
            'SEARCH CONVERSATIONS',
        ):
            self.assertIn(marker, code)
        self.assertIn("anchors.top: phoneListSearchBar.bottom", self.pane)
        self.assertIn("anchors.fill: phoneContactList", self.pane)
        self.assertNotIn("ListView {", code)  # no scrolling ancestor of input
        self.assertNotIn("Flickable {", code)

    def test_search_only_uses_existing_local_authorized_snapshot(self):
        start = self.pane.split("readonly property var filteredPhoneConversations:", 1)[1]
        content = start.split("Component.onCompleted:", 1)[0]
        for marker in (
            "personalApproved", "personalNeedsExplicitReload",
            'personalReadStatus !== "LOCAL_SNAPSHOT"', "!phoneReadAdapter.active",
            "DirectorySearch.filterConversations(",
            "phoneReadAdapter.conversations, messageSearchQuery",
            "DirectorySearch.filterContacts(",
            "phoneReadAdapter.contactCards, contactSearchQuery",
            "DirectorySearch.contactDirectoryRows(filteredPhoneContacts)",
        ):
            self.assertIn(marker, content)
        for forbidden in (
            "Process {", "sendMessage(", "savePersonalApproval(",
            "unlockBlueFerryStorage(", "refreshMessagesTabOnRepeat(",
            "openPersonalConsent(", "PhoneRememberedRead.py", "network",
        ):
            self.assertNotIn(forbidden, content)
        self.assertIn("sendEnabled: false", self.pane)
        self.assertIn("conversations: phonePane.selectedSection", self.pane)
        self.assertIn("? phonePane.filteredPhoneConversations : []", self.pane)
        self.assertIn("model: phonePane.contactDirectoryRows", self.pane)
        self.assertIn("no global search claim", self.pane.lower())

    def test_alphabet_headers_have_magenta_letters_and_divider(self):
        section = self.pane.split("id: phoneAddressBook", 1)[1].split(
            "// The separate PHONE address book", 1)[0]
        self.assertIn('modelData.kind === "heading"', section)
        self.assertIn("height: isHeading ? 36 : 64", section)
        self.assertIn("directoryRow.modelData.letter", section)
        self.assertGreaterEqual(section.count("color: Colors.magenta"), 2)
        self.assertIn("height: 2", section)
        self.assertIn("readonly property var card: directoryRow.isHeading", section)
        self.assertIn("String(addressBookRow.card.id)", section)
        self.assertIn('personalReadStatus === "LOCAL_SNAPSHOT"', section)
        self.assertIn("visible: !directoryRow.isHeading", section)

    def test_search_and_selection_do_not_leave_stale_results(self):
        self.assertIn("phonePane.selectedPhoneContactId = \"\";", self.pane)
        self.assertIn("phoneContactList.clearSelection();", self.pane)
        hide = self.pane.split("onVisibleChanged: {", 1)[1].split(
            "function callsWorkspaceMessage()", 1)[0]
        self.assertIn('contactSearchQuery = "";', hide)
        self.assertIn('messageSearchQuery = "";', hide)
        identity = self.pane.split("onActiveSocialIdentityIdChanged: {", 1)[1].split(
            "property string probeStatus:", 1)[0]
        self.assertIn('contactSearchQuery = "";', identity)
        self.assertIn('messageSearchQuery = "";', identity)
        self.assertIn("NO MATCHES IN LOADED CONTACTS", self.pane)
        self.assertIn("NO MATCHES IN LOADED CONVERSATIONS", self.pane)

    def test_directory_helpers_are_pure_and_snapshot_limited(self):
        for marker in (
            "function filterConversations(", "function filterContacts(",
            "function sectionLetter(", "function contactDirectoryRows(",
            'return /^[A-Z]$/.test(first) ? first : "#";',
            'kind: "heading"', 'kind: "contact"', "entries.sort(",
        ):
            self.assertIn(marker, self.directory)
        for forbidden in (
            "XMLHttpRequest", "fetch(", "dbus", "FileView", "Process {",
            "writeFile(", "LocalStorage", "Qt.openUrlExternally",
            "sendMessage(", "savePersonalApproval(",
        ):
            self.assertNotIn(forbidden, self.directory)


if __name__ == "__main__":
    unittest.main()
