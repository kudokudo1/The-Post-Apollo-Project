"""One Connect Phone action in Social, without implicit pairing or grants."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[2]
PANE = ROOT / "widgets" / "messanger" / "PhonePane.qml"
SCRIPT = ROOT / "services" / "phone" / "PhoneSetupReadiness.py"


class PhoneConnectUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ui = PANE.read_text()
        cls.script = SCRIPT.read_text()

    def test_one_primary_connect_action_inside_existing_pane(self):
        self.assertIn('id: connectPhoneAction', self.ui)
        self.assertIn('label: setupProcess.running ? "CHECKING..." : "CONNECT PHONE"', self.ui)
        self.assertIn('onTriggered: phonePane.startSetup()', self.ui)
        self.assertIn('text: "PHONE // CONNECT"', self.ui)
        self.assertNotIn("FloatingWindow {", self.ui)
        self.assertNotIn("PanelWindow {", self.ui)
        self.assertIn('model: ["DEVICE", "CALLS", "MESSAGES", "CONTACTS"]', self.ui)
        self.assertNotIn('model: ["DEVICE", "CALLS", "MESSAGES", "CONTACTS", "PERMISSIONS"]', self.ui)

    def test_setup_diagnostic_is_explicit_only_not_on_menu_open(self):
        match = re.search(
            r'function startSetup\(\) \{(?P<body>.*?)\n    \}', self.ui, re.S)
        self.assertIsNotNone(match)
        self.assertIn("PhoneSetupReadiness.py", match.group("body"))
        self.assertIn('"--check"', match.group("body"))
        self.assertIn('setupProcess.running = true;', match.group("body"))
        visibility = re.search(
            r'onVisibleChanged: \{(?P<body>.*?)\n    \}', self.ui, re.S)
        self.assertIsNotNone(visibility)
        self.assertNotIn('startSetup()', visibility.group("body"))
        self.assertNotIn('refreshReadiness()', visibility.group("body"))
        self.assertNotIn('KdeConnectDbusProbe.py', self.ui)
        self.assertEqual(self.ui.count('"--check"'), 1)

    def test_projections_require_false_grants_and_unverified_link(self):
        self.assertIn('report.execution !== "READ_ONLY_CHECK"', self.ui)
        self.assertIn('report.trustedPhoneLink !== "UNVERIFIED"', self.ui)
        self.assertIn('report.routeEligible !== false', self.ui)
        self.assertIn('report.contentAccessEnabled !== false', self.ui)
        self.assertIn('phonePane.setupState !== "CHECKING"', self.ui)
        self.assertIn('phonePane.setupState === "CHECKING" && exitCode !== 0', self.ui)
        self.assertIn('Social has NOT linked a phone', self.ui)
        self.assertIn('Social phone link: NOT VERIFIED', self.ui)
        self.assertNotIn('sendMessage(', self.ui)
        self.assertNotIn('pair-setup', self.ui)
        self.assertNotIn('SocialIdentityStore.', self.ui)

    def test_details_are_collapsed_and_old_diagnostic_stays_read_only(self):
        self.assertIn('property bool detailsOpen: false', self.ui)
        self.assertIn('label: phonePane.detailsOpen ? "HIDE DETAILS" : "DETAILS"', self.ui)
        self.assertIn('&& phonePane.detailsOpen', self.ui)
        self.assertIn('phonePane.refreshReadiness();', self.ui)
        self.assertIn('BlueFerryReadiness.py', self.ui)
        self.assertIn('next.contentAuthorized !== false', self.ui)
        self.assertIn('next.phoneLink !== "UNVERIFIED"', self.ui)
        self.assertIn('READ-ONLY SETUP PREVIEW', self.ui)

    def test_no_phone_settings_mutation_in_setup_command(self):
        self.assertIn('from BlueFerryReadiness import readiness', self.script)
        self.assertIn('from KdeConnectDbusProbe import probe', self.script)
        self.assertIn('from PhoneProviderObservation import project', self.script)
        for forbidden in ("systemctl start", "pair-setup", "bluetoothctl pair",
                          "getMessages(", "sendMessage(", "subprocess.run("):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, self.script)


if __name__ == "__main__":
    unittest.main()
