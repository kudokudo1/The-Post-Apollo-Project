"""P43 integrated PHONE editor and strictly untrusted native ingress tests."""
from __future__ import annotations

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "phone"))
import PhonePersonalEditIngressP43 as Ingress

DETAIL = ROOT / "widgets/messanger/PhoneContactDetail.qml"
EDITOR = ROOT / "widgets/messanger/PhonePersonalDraftEditor.qml"
PANE = ROOT / "widgets/messanger/PhonePane.qml"


def intent(action, **changes):
    return dict(schema=Ingress.SCHEMA, action=action,
                selectedContactId="123e4567:epoch-19:row-7", **changes)


class HostIngressTests(unittest.TestCase):
    def test_normalizes_all_actions_and_private_data_remains_ephemeral(self):
        valid = (
            (intent("LINK"), "LINK", None, None),
            (intent("UNLINK"), "UNLINK", None, None),
            (intent("FAVORITE", favorite=True), "FAVORITE", True, None),
            (intent("FAVORITE", favorite=False), "FAVORITE", False, None),
            (intent("NOTE", note="synthetic private note 😀"),
             "NOTE", None, "synthetic private note 😀"),
            (intent("NOTE", note=""), "NOTE", None, ""),
        )
        for payload, action, favorite, note in valid:
            with self.subTest(action=action, payload=list(payload)):
                result = Ingress.parse_untrusted_editor_intent(payload)
                self.assertEqual(result.action, action)
                self.assertEqual(result.favorite, favorite)
                self.assertEqual(result.note, note)
                self.assertEqual(result.selected_contact_id,
                                 payload["selectedContactId"])
                self.assertEqual(repr(result),
                                 "<StagedEditorIntent UNSAVED_UNTRUSTED>")
                self.assertNotIn("synthetic private note", repr(result))
                self.assertFalse(hasattr(result, "save"))
                self.assertFalse(hasattr(result, "approved"))

    def test_rejects_auth_claims_malformed_intents_and_cross_action_values(self):
        invalid = (
            intent("LINK", trusted=True),
            intent("FAVORITE", favorite=1),
            intent("FAVORITE", favorite=True, note="x"),
            intent("FAVORITE", favorite=None),
            intent("NOTE"),
            intent("NOTE", note=None),
            intent("NOTE", note=0),
            intent("NOTE", note="x" * 4097),
            intent("NOTE", note="null\x00injected"),
            intent("NOTE", note="\ud800"),
            intent("UNLINK", note=""),
            intent("SAVE"),
            {**intent("LINK"), "productionEnabled": True},
            {**intent("LINK"), "hostVerified": True},
            {**intent("LINK"), "consentReceipt": "fake"},
            {**intent("LINK"), "expectedRevision": 0},
            {**intent("LINK"), "profileId": "user-supplied"},
            {**intent("LINK"), "nonce": "user-supplied"},
            {**intent("LINK"), "selectedContactId": ""},
            {**intent("LINK"), "selectedContactId": "bad\nselected"},
            {**intent("LINK"), "selectedContactId": "../bad"},
            {**intent("LINK"), "selectedContactId": "x" * 257},
            {**intent("LINK"), "selectedContactId": None},
            {**intent("LINK"), "schema": "bogus"},
        )
        for value in invalid:
            with self.subTest(keys=list(value)):
                with self.assertRaisesRegex(
                    Ingress.EditorIntentRefused, "^PHONE_EDITOR_INTENT_REFUSED$"
                ):
                    Ingress.parse_untrusted_editor_intent(value)
        for value in (None, "LINK", [], True):
            with self.assertRaises(Ingress.EditorIntentRefused):
                Ingress.parse_untrusted_editor_intent(value)

    def test_no_save_keyring_or_public_host_entry_point(self):
        source = (ROOT / "services/phone/PhonePersonalEditIngressP43.py").read_text()
        for banned in (
            "def main(", "if __name__ ==", "import os", "import dbus",
            "socket.", "subprocess.", "secret-tool", "print(",
            "Vault.commit(", "open(", "FileView", "http",
        ):
            self.assertNotIn(banned, source)
        self.assertIn("Identity.MAX_NOTE", source)
        self.assertIn("repr=False", source)


class LiveMountedDraftTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.detail = DETAIL.read_text()
        cls.editor = EDITOR.read_text()
        cls.pane = PANE.read_text()

    def test_edit_control_opens_real_component_but_not_a_vault_save(self):
        self.assertIn('label: "EDIT"', self.detail)
        self.assertIn('onTriggered: detail.openDraftPreview()', self.detail)
        self.assertIn('PhonePersonalDraftEditor {', self.detail)
        self.assertIn('previewEnabled: detail.draftPreviewOpen', self.detail)
        self.assertIn('contact: detail.draftPreviewOpen', self.detail)
        self.assertIn('onCancelRequested: detail.closeDraftPreview()', self.detail)
        self.assertIn('readonly property bool personalMetadataWritable: false',
                      self.detail)
        self.assertIn('readonly property bool secureSaveAuthorized: false',
                      self.editor)
        self.assertIn('interactive: false // No native, verified one-use save host.',
                      self.editor)
        self.assertIn('PREVIEW ONLY // NOTHING IS SAVED OR SENT TO IPHONE',
                      self.editor)
        self.assertNotIn("onSaveRequested:", self.detail)
        self.assertNotIn("PhonePersonalEditIngressP43", self.detail)

    def test_draft_is_revoked_on_current_card_or_view_loss(self):
        for needle in (
            'property bool draftPreviewOpen: false',
            'onContactChanged: closeDraftPreview()',
            'onVisibleChanged: {',
            'if (!visible)',
            'closeDraftPreview();',
            'contact !== null && visible',
            'typeof contact.id === "string"',
            'contact.id.length <= 256',
            'previewEnabled: detail.draftPreviewOpen',
            'contact: detail.draftPreviewOpen && detail.canOpenDraftPreview',
        ):
            with self.subTest(needle=needle):
                self.assertIn(needle, self.detail)
        for needle in (
            "selectedPhoneContactId = \"\";",
            'personalReadStatus !== "LOCAL_SNAPSHOT"',
            "!personalApproved",
            "!visible",
        ):
            self.assertIn(needle, self.pane)
        for needle in (
            "onContactChanged: resetForSelection()",
            "onPreviewEnabledChanged: resetForSelection()",
            "Component.onDestruction: discardDraft()",
            'noteDraft.text = "";',
        ):
            self.assertIn(needle, self.editor)

    def test_phone_dial_message_and_favorite_remain_original(self):
        for needle in (
            "onCallRequested: phonePane.openSelectedContactForCall()",
            "onMessageRequested: phonePane.openSelectedContactMessages()",
            "onCallNumberRequested: function(number)",
        ):
            self.assertIn(needle, self.pane)
        for needle in (
            'label: "☆ FAVORITE"',
            "available: detail.personalMetadataWritable",
            'text: "NOT SAVED // UNAVAILABLE"',
            'label: "EDIT NOTE"',
            'label: "DELETE NOTE"',
        ):
            self.assertIn(needle, self.detail)
        for banned in (
            "PhonePersonalContactVault", "PhonePersonalKeyringP36",
            "Qt.openUrlExternally", "savePersonalApproval(",
            "FileView", "secret-tool", "Process {", "XMLHttpRequest",
        ):
            self.assertNotIn(banned, self.detail)


if __name__ == "__main__":
    unittest.main()
