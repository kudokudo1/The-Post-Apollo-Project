"""P40 contact detail UX: honest, locked Favorite/Notes/Edit/Email affordances.

Source-only tests. No production grant, real contacts, local storage, user
vault, iPhone provider actions, keyring or desktop installation.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
DETAIL = ROOT / "widgets/messanger/PhoneContactDetail.qml"
PANE = ROOT / "widgets/messanger/PhonePane.qml"


class LockedContactMetadataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.detail = DETAIL.read_text(encoding="utf-8")
        cls.pane = PANE.read_text(encoding="utf-8")

    def part(self, start, end):
        return self.detail.split(start, 1)[1].split(end, 1)[0]

    def test_no_fake_metadata_write_authority_or_optimistic_state(self):
        self.assertIn("readonly property bool personalMetadataWritable: false",
                      self.detail)
        self.assertIn("VERIFIED CONTACT SAVE HOST REQUIRED", self.detail)
        self.assertIn('visible: contact !== null', self.detail)
        for forbidden in (
            "Process {", "XMLHttpRequest", "LocalStorage", "FileView",
            "secret-tool", "PhonePersonalContactVault",
            "PhonePersonalHostGateP36", "PhonePersonalKeyringP36",
            "PhonePersonalSignedTrustP37", "PhonePersonalSignedSourceP39",
            "sendMessage(", "savePersonalApproval(", "requestCallAction(",
            "readOnly: false", "TextEdit {", "TextArea {",
            "onTextChanged:", "onEditingFinished:",
            "favoriteChanged(", "noteSaved(", "Qt.openUrlExternally(",
        ):
            self.assertNotIn(forbidden, self.detail)

    def test_header_edit_is_visible_at_top_right_but_disabled(self):
        header = self.part("id: contactHeader", 'text: detail.contact ?')
        self.assertIn('text: "IPHONE CONTACT // PERSONAL // READ ONLY"', header)
        self.assertIn('label: "EDIT"', header)
        self.assertIn("width: Math.max(0, contactHeader.width - 84)", header)
        self.assertIn("interactive: false", header)
        self.assertIn("available: false", header)
        self.assertIn("accentColor: Colors.orange", header)

    def test_call_message_facetime_email_are_four_actions(self):
        row = self.part("id: contactActions", 'text: "PERSONAL // FAVORITE"')
        for label in ("CALL", "MESSAGE", "FACETIME", "EMAIL"):
            self.assertIn('label: "' + label + '"', row)
        self.assertEqual(row.count("(contactActions.width - 18) / 4"), 4)
        self.assertIn("onTriggered: detail.callRequested()", row)
        self.assertIn("onTriggered: detail.messageRequested()", row)
        self.assertIn("interactive: false // No BlueFerry FaceTime transport.", row)
        self.assertIn("interactive: false // Email routing not connected.", row)
        self.assertIn("available: false", row)
        self.assertIn("EMAIL remains unavailable", self.detail)

    def test_favorite_star_has_magenta_color_and_no_fake_toggle(self):
        favorite = self.part('text: "PERSONAL // FAVORITE"',
                             'text: "PERSONAL // NOTES"')
        self.assertIn('label: "☆ FAVORITE"', favorite)
        self.assertIn("accentColor: Colors.magenta", favorite)
        self.assertIn("interactive: detail.personalMetadataWritable", favorite)
        self.assertIn("available: detail.personalMetadataWritable", favorite)
        self.assertIn("detail.contact !== null", favorite)
        self.assertIn("NOT SAVED // UNAVAILABLE", favorite)
        self.assertIn("detail.personalMetadataStatus", favorite)
        self.assertNotIn("onTriggered:", favorite)
        self.assertNotIn("selected: true", favorite)

    def test_notes_panel_displays_no_private_user_data_and_cannot_save(self):
        notes = self.part('text: "PERSONAL // NOTES"',
                          'text: "SAVED PHONE NUMBERS"')
        for value in (
            "id: localNotesPlaceholder",
            'text: "NOTES UNAVAILABLE',
            "border.color: Colors.magenta",
            'label: "EDIT NOTE"',
            'label: "DELETE NOTE"',
            "accentColor: Colors.red",
            "destructive: true",
            "interactive: false",
            "The iPhone contact provider stays READ ONLY",
        ):
            self.assertIn(value, notes)
        self.assertEqual(notes.count("available: false"), 2)
        self.assertNotIn("onTriggered:", notes)
        self.assertNotIn("TextInput {", notes)
        self.assertNotIn("TextEdit {", notes)
        self.assertNotIn("note: detail.contact", notes)
        self.assertNotIn("phoneNumbers", notes)
        self.assertNotIn("emailAddresses", notes)

    def test_existing_selected_card_guards_and_real_call_paths_remain(self):
        self.assertIn("contact: phonePane.selectedPhoneContactCard", self.pane)
        self.assertIn("onCallRequested: phonePane.openSelectedContactForCall()",
                      self.pane)
        self.assertIn("onMessageRequested: phonePane.openSelectedContactMessages()",
                      self.pane)
        self.assertIn('selectedSection !== "CONTACTS"', self.pane)
        self.assertIn('personalReadStatus !== "LOCAL_SNAPSHOT"', self.pane)
        self.assertIn("onCallNumberRequested: function(number)", self.pane)
        self.assertIn('label: "MAKE CALL"', self.detail)
        self.assertIn('label: "REVIEW OUTGOING CALL"', self.pane)
        self.assertIn('label: "CONFIRM CALL"', self.pane)
        self.assertIn("sendEnabled: false", self.pane)
        self.assertIn('handleStyle: "star"', self.detail)


if __name__ == "__main__":
    unittest.main()
