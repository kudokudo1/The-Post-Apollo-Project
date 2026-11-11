"""P29: bounded two-line Social PHONE message preview; shared list unchanged."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
PANE = ROOT / "widgets" / "messanger" / "PhonePane.qml"
LIST = ROOT / "widgets" / "messanger" / "ContactList.qml"


class PhoneTwoLinePreviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.phone = PANE.read_text(encoding="utf-8")
        cls.contact = LIST.read_text(encoding="utf-8")
        cls.phone_list = cls.phone.split("    ContactList {", 1)[1].split("\n    }", 1)[0]
        cls.delegate = cls.contact.split("        delegate: Rectangle {", 1)[1]

    def test_two_line_preview_is_phone_only_opt_in(self):
        self.assertIn("property bool phonePreviewMode: false", self.contact)
        self.assertIn("phonePreviewMode: true", self.phone_list)
        self.assertEqual(self.phone.count("phonePreviewMode: true"), 1)
        self.assertEqual(self.contact.count("property bool phonePreviewMode: false"), 1)

    def test_phone_preview_two_wrapped_lines_clipped_with_ellipsis(self):
        self.assertIn("maximumLineCount: contactRoot.phonePreviewMode ? 2 : 2147483647",
                      self.delegate)
        self.assertIn("Text.WrapAtWordBoundaryOrAnywhere : Text.NoWrap",
                      self.delegate)
        self.assertIn("height: contactRoot.phonePreviewMode ? 36 : implicitHeight",
                      self.delegate)
        self.assertIn("clip: contactRoot.phonePreviewMode", self.delegate)
        self.assertIn("elide: Text.ElideRight", self.delegate)
        self.assertIn("textFormat: contactRoot.phonePreviewMode ? Text.PlainText : Text.AutoText",
                      self.delegate)

    def test_name_is_bounded_to_one_line(self):
        header = self.delegate.split("id: contactName", 1)[1].split(
            "id: contactPreview", 1)[0]
        self.assertIn("maximumLineCount: contactRoot.phonePreviewMode ? 1 : 2147483647",
                      header)
        self.assertIn("height: contactRoot.phonePreviewMode ? 22 : implicitHeight", header)
        self.assertIn("clip: contactRoot.phonePreviewMode", header)
        self.assertIn("wrapMode: Text.NoWrap", header)

    def test_phone_rows_have_space_and_other_social_rows_keep_66(self):
        self.assertIn("height: contactRoot.phonePreviewMode ? 90 : 66", self.delegate)
        # Two-line preview ends 9 px before bottom; name starts at y=10.
        self.assertGreater(90 - 36 - 9, 10 + 22)
        self.assertIn("spacing: 7", self.contact)
        self.assertIn("clip: false", self.delegate)  # preserve hover glow

    def test_preview_collapses_provider_newlines_without_mutating_messages(self):
        self.assertIn('String(modelData.lastMessage || "").replace(/\\s+/g, " ").trim()',
                      self.delegate)
        self.assertIn('(modelData.lastMessage ? modelData.lastMessage : "")',
                      self.delegate)  # legacy provider behavior outside PHONE
        self.assertIn("phoneReadAdapter.conversations", self.phone_list)
        self.assertIn("phoneReadAdapter.loadMessages", self.phone_list)
        self.assertIn("sendEnabled: false", self.phone)
        self.assertIn("width: Math.min(200, Math.max(135, phonePane.width * 0.30))",
                      self.phone)


if __name__ == "__main__":
    unittest.main()
