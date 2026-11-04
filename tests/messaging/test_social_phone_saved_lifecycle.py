"""Social PHONE should recognize existing BlueFerry state without new pairing."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[2]
PANE = ROOT / "widgets/messanger/PhonePane.qml"
SCRIPT = ROOT / "services/phone/PhoneSavedBridgeState.py"
LAUNCH = ROOT / "services/phone/PhoneNativeSetupLaunch.py"


class SavedBlueFerryUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ui = PANE.read_text()
        cls.saved = SCRIPT.read_text()
        cls.launch = LAUNCH.read_text()

    def test_same_primary_action_checks_saved_local_state(self):
        self.assertEqual(self.ui.count("id: connectPhoneAction"), 1)
        self.assertIn('label: setupProcess.running ? "CHECKING..." : "CONNECT PHONE"',
                      self.ui)
        block = re.search(r'function startSetup\(\) \{(.*?)\n    \}', self.ui, re.S)
        self.assertIsNotNone(block)
        self.assertIn("refreshSavedBridgeState();", block.group(1))
        self.assertIn('PhoneSetupReadiness.py', block.group(1))
        self.assertIn('PhoneSavedBridgeState.py', self.ui)
        self.assertIn('"--inspect"', self.ui)
        self.assertIn('id: savedBridgeProcess', self.ui)

    def test_config_present_differs_from_active_backend_and_social_authorization(self):
        self.assertIn('CONFIGURATION_PRESENT_BACKEND_INACTIVE', self.ui)
        self.assertIn('CONFIGURATION_PRESENT_BACKEND_UNVERIFIED', self.ui)
        self.assertIn('BACKEND_REPORTED', self.ui)
        self.assertIn('NO_LOCAL_CONFIGURATION', self.ui)
        self.assertIn('BlueFerry configuration exists, but its background service is not active.', self.ui)
        self.assertIn('Saved BlueFerry config file:', self.ui)
        self.assertIn('Starts with session:', self.ui)
        self.assertIn('next.trustedPhoneLink !== "UNVERIFIED"', self.ui)
        self.assertIn('next.contentAccessEnabled !== false', self.ui)
        self.assertIn('Social phone link: NOT VERIFIED', self.ui)
        self.assertIn('sendEnabled: false', self.ui)

    def test_existing_config_offers_existing_client_instead_of_repeat_wizard(self):
        self.assertIn('? "OPEN IPHONE" : "SET UP IPHONE"', self.ui)
        self.assertIn('onTriggered: phonePane.openNativeSetup("iphone")', self.ui)
        self.assertIn('client_command = "tui" if existing_config else "pair-setup"',
                      self.launch)
        self.assertIn('configured: Callable[[], bool]', self.launch)
        self.assertIn('stage_candidate=terminal == "foot"', self.launch)
        self.assertNotIn('bluetoothctl remove', self.launch)
        self.assertNotIn('systemctl start', self.launch)

    def test_stage_exit_refreshes_bridge_status_not_unlinks_phone(self):
        self.assertIn('result.state === "ACTOR_NOT_FOUND"', self.ui)
        self.assertIn('phonePane.stageState === "ALIGNED"', self.ui)
        self.assertIn('phonePane.stageState = "FINISHED"', self.ui)
        self.assertIn('phonePane.refreshSavedBridgeState();', self.ui)
        self.assertIn('BlueFerry client closed.', self.ui)
        self.assertNotIn('bluetoothctl remove', self.ui)
        self.assertNotIn('blueferry reconnect', self.ui)

    def test_no_new_device_storage_or_permission_grant(self):
        self.assertIn('    ContactList {', self.ui)
        self.assertIn('    ChatFeed {', self.ui)
        self.assertIn('conversations: []', self.ui)
        self.assertIn('messages: []', self.ui)
        self.assertIn('READ-ONLY SETUP PREVIEW', self.ui)
        for forbidden in ("FileView {", "LocalStorage", "SQLite", "sendMessage(",
                          "contacts-sync", "blueferry calls enable"):
            self.assertNotIn(forbidden, self.ui)
        self.assertIn('READ_ONLY_LOCAL_LIFECYCLE', self.ui)


if __name__ == "__main__":
    unittest.main()
