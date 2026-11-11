"""Static styling contract for affirmative Personal PHONE call controls.

Does not instantiate Quickshell, contact providers, BlueFerry, HFP, or dial calls.
"""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[2]
CONTACT_DETAIL = ROOT / "widgets/messanger/PhoneContactDetail.qml"
PHONE_PANE = ROOT / "widgets/messanger/PhonePane.qml"


def action_accent(source: str, label: str) -> str:
    pattern = re.compile(
        r'\blabel:\s*"' + re.escape(label) +
        r'"(?:(?!\bActionButton\s*\{)[\s\S])*?\baccentColor:\s*Colors\.(\w+)',
    )
    colors = pattern.findall(source)
    if len(colors) != 1:
        raise AssertionError(f"Expected exactly one {label!r} ActionButton accent, got {colors!r}")
    return colors[0]


class PhoneCallActionColorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contact = CONTACT_DETAIL.read_text(encoding="utf-8")
        cls.phone = PHONE_PANE.read_text(encoding="utf-8")

    def test_contact_call_actions_are_green(self):
        for label in ("CALL", "MAKE CALL"):
            with self.subTest(label=label):
                self.assertEqual(action_accent(self.contact, label), "green")

    def test_outgoing_and_answer_actions_are_green(self):
        for label in ("ANSWER", "REVIEW OUTGOING CALL", "CONFIRM CALL", "HOLD AND ANSWER"):
            with self.subTest(label=label):
                self.assertEqual(action_accent(self.phone, label), "green")

    def test_non_call_semantics_unchanged(self):
        for source, label, expected in (
            (self.contact, "MESSAGE", "cyan"),
            (self.contact, "FACETIME", "orange"),
            (self.contact, "EMAIL", "magenta"),
            (self.phone, "DECLINE", "red"),
            (self.phone, "HANG UP", "red"),
            (self.phone, "REFRESH CALLS", "cyan"),
        ):
            # REFRESH CALLS has a conditional progress label; check its style in place.
            if label == "REFRESH CALLS":
                self.assertIn('accentColor: Colors.cyan', source[source.index('"REFRESH CALLS"'):source.index('"REFRESH CALLS"') + 120])
                continue
            with self.subTest(label=label):
                self.assertEqual(action_accent(source, label), expected)

    def test_shared_palette_preserved(self):
        self.assertIn('readonly property color green: "#9ECE6A"',
                      (ROOT / "components/Colors.qml").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
