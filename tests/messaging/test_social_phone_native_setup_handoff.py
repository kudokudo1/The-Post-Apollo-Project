"""Social PHONE: user-initiated native setup handoff, no silent pairing."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[2]
PANE = (ROOT / "widgets" / "messanger" / "PhonePane.qml")


class NativeSetupUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ui = PANE.read_text()

    def test_existing_phone_pane_keeps_only_one_main_setup_action(self):
        self.assertIn('id: connectPhoneAction', self.ui)
        self.assertIn('label: setupProcess.running ? "CHECKING..." : "CONNECT PHONE"', self.ui)
        self.assertEqual(self.ui.count('id: connectPhoneAction'), 1)
        self.assertIn('label: "SET UP IPHONE"', self.ui)
        self.assertIn('label: "SET UP ANDROID"', self.ui)
        self.assertIn('onTriggered: phonePane.openNativeSetup("iphone")', self.ui)
        self.assertIn('onTriggered: phonePane.openNativeSetup("android")', self.ui)
        self.assertIn('label: phonePane.detailsOpen ? "HIDE DETAILS" : "DETAILS"', self.ui)
        self.assertNotIn("FloatingWindow {", self.ui)
        self.assertNotIn("PanelWindow {", self.ui)

    def test_setup_choices_are_not_primary_security_controls(self):
        self.assertIn('&& phonePane.setupState === "CHECKED"', self.ui)
        self.assertIn('interactive: !nativeSetupProcess.running', self.ui)
        self.assertNotIn('model: ["DEVICE", "CALLS", "MESSAGES", "CONTACTS", "PERMISSIONS"]',
                         self.ui)
        self.assertIn('model: ["DEVICE", "CALLS", "MESSAGES", "CONTACTS"]', self.ui)
        self.assertNotIn("SocialIdentityStore.", self.ui)

    def test_native_app_opens_only_from_specific_user_choice(self):
        action = re.search(r'function openNativeSetup\(target\) \{(?P<body>.*?)\n    \}',
                           self.ui, re.S)
        self.assertIsNotNone(action)
        self.assertIn('setupState !== "CHECKED"', action.group("body"))
        self.assertIn('target !== "iphone" && target !== "android"', action.group("body"))
        self.assertIn("PhoneNativeSetupLaunch.py", action.group("body"))
        self.assertIn('"--open", target', action.group("body"))
        self.assertIn('nativeSetupProcess.running = true;', action.group("body"))
        auto = re.search(r'onVisibleChanged: \{(?P<body>.*?)\n    \}', self.ui, re.S)
        self.assertIsNotNone(auto)
        self.assertNotIn('openNativeSetup(', auto.group("body"))
        self.assertNotIn('startSetup()', auto.group("body"))
        self.assertNotIn('refreshReadiness()', auto.group("body"))

    def test_untrusted_native_process_output_cannot_activate_phone(self):
        self.assertIn('result.schema !== "post-apollo.phone.native-setup-launch.v0"', self.ui)
        self.assertIn('result.execution !== "USER_INITIATED_NATIVE_SETUP"', self.ui)
        self.assertIn('result.target !== phonePane.nativeSetupTarget', self.ui)
        self.assertIn('result.trustedPhoneLink !== "UNVERIFIED"', self.ui)
        self.assertIn('result.routeEligible !== false', self.ui)
        self.assertIn('result.contentAccessEnabled !== false', self.ui)
        self.assertIn('phonePane.nativeSetupStatus !== "OPENING"', self.ui)
        self.assertIn('Social messages remain locked.', self.ui)
        self.assertNotIn("sendMessage(", self.ui)
        self.assertNotIn("requestPairing(", self.ui)
        self.assertNotIn("blueferry pair-setup", self.ui)

    def test_existing_readonly_probe_and_connection_guard_remain(self):
        self.assertIn('PhoneSetupReadiness.py', self.ui)
        self.assertIn('next.contentAuthorized !== false', self.ui)
        self.assertIn('report.contentAccessEnabled !== false', self.ui)
        self.assertIn('report.trustedPhoneLink !== "UNVERIFIED"', self.ui)
        self.assertIn('READ-ONLY SETUP PREVIEW', self.ui)


if __name__ == "__main__":
    unittest.main()
