"""Social PHONE is a companion surface, never an implicit phone content grant."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]


class SocialPhoneMenuTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.selector = (ROOT / "widgets/messanger/AppSelector.qml").read_text()
        cls.controller = (ROOT / "widgets/messanger/MessagingW.qml").read_text()
        cls.pane = (ROOT / "widgets/messanger/PhonePane.qml").read_text()
        cls.router = (ROOT / "services/messaging/SocialMessageRouter.qml").read_text()

    def test_button_and_pane_share_existing_social_window(self):
        self.assertIn('id: phoneFooter', self.selector)
        self.assertIn('label: "PHONE"', self.selector)
        self.assertIn('property bool phoneOpen: false', self.selector)
        self.assertIn('PhonePane {', self.controller)
        self.assertIn('visible: messagingWindow.menuOpen && appSelector.phoneOpen', self.controller)
        self.assertIn('appSelector.phoneOpen = false;', self.controller)
        self.assertNotIn('FloatingWindow {', self.pane)
        self.assertNotIn('PanelWindow {', self.pane)

    def test_phone_surface_only_runs_readonly_probe(self):
        self.assertIn('BlueFerryReadiness.py', self.pane)
        self.assertIn('next.execution !== "READ_ONLY"', self.pane)
        self.assertIn('next.contentAuthorized !== false', self.pane)
        self.assertIn('next.phoneLink !== "UNVERIFIED"', self.pane)
        self.assertNotIn("pair-setup", self.pane)
        self.assertNotIn("sendMessage(", self.pane)
        self.assertNotIn("SocialIdentityStore.", self.pane)
        self.assertNotIn("phoneOpen", self.router)

    def test_closed_or_switched_social_hides_phone(self):
        self.assertIn('appSelector.phoneOpen = false;', self.controller)
        self.assertIn('!appSelector.phoneOpen', self.controller)
        self.assertIn('!appSelector.phoneOpen', self.selector)


if __name__ == "__main__":
    unittest.main()
