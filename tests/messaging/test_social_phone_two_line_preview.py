"""P29/P30: bounded previews preserved and expanded to all native Social lists."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
PANE = ROOT / "widgets" / "messanger" / "PhonePane.qml"
LIST = ROOT / "widgets" / "messanger" / "ContactList.qml"


class SharedContactPreviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.phone = PANE.read_text(encoding="utf-8")
        cls.contact = LIST.read_text(encoding="utf-8")
        cls.phone_list = cls.phone.split("    ContactList {", 1)[1].split("\n    }", 1)[0]
        cls.delegate = cls.contact.split("        delegate: Rectangle {", 1)[1]

    def test_four_line_preview_is_shared_default_and_phone_remains_opted_in(self):
        self.assertIn("property bool phonePreviewMode: true", self.contact)
        self.assertIn("phonePreviewMode: true", self.phone_list)
        self.assertEqual(self.phone.count("phonePreviewMode: true"), 1)
        self.assertEqual(self.contact.count("property bool phonePreviewMode: true"), 1)

    def test_all_previews_have_four_wrapped_lines_clipped_with_ellipsis(self):
        self.assertIn("maximumLineCount: contactRoot.phonePreviewMode ? 4 : 2147483647",
                      self.delegate)
        self.assertIn("Text.WrapAtWordBoundaryOrAnywhere : Text.NoWrap",
                      self.delegate)
        self.assertIn("height: contactRoot.phonePreviewMode ? 64 : implicitHeight",
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

    def test_four_line_rows_contain_both_name_and_snippet(self):
        self.assertIn("height: contactRoot.phonePreviewMode ? 116 : 66", self.delegate)
        # Four-line excerpt ends 9 px before bottom; name starts at y=10.
        self.assertGreater(116 - 64 - 9, 10 + 22)
        self.assertIn("spacing: 7", self.contact)
        self.assertIn("clip: false", self.delegate)  # preserve hover glow

    def test_all_previews_collapse_provider_newlines_without_mutating_messages(self):
        self.assertIn('String(modelData.lastMessage || "").replace(/\\s+/g, " ").trim()',
                      self.delegate)
        self.assertIn('(modelData.lastMessage ? modelData.lastMessage : "")',
                      self.delegate)  # explicit legacy opt-out only
        self.assertIn("phoneReadAdapter.conversations", self.phone_list)
        self.assertIn("phoneReadAdapter.loadMessages", self.phone_list)
        self.assertIn("sendEnabled: false", self.phone)
        self.assertIn("width: Math.min(200, Math.max(135, phonePane.width * 0.30))",
                      self.phone)


if __name__ == "__main__":
    unittest.main()
