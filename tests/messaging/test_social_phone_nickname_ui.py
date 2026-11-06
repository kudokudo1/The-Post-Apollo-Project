"""PHONE P17 local nickname is never a Bluetooth, user, or content grant."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
PANE = ROOT / "widgets/messanger/PhonePane.qml"
HELPER = ROOT / "services/phone/PhoneNickname.py"


class PhoneNicknameUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ui = PANE.read_text()

    def test_primary_connect_reads_only_current_device_label(self):
        block = self.ui.split("function startSetup() {", 1)[1].split(
            "\n    function openNativeSetup", 1
        )[0]
        self.assertIn("refreshDeviceObservation();", block)
        self.assertIn('id: deviceObservationProcess', self.ui)
        self.assertIn('phonePane.refreshPhoneNickname();', self.ui)
        self.assertIn('PhoneNickname.py', self.ui)
        self.assertIn('"--read", deviceObservation.profileId', self.ui)
        self.assertIn('id: nicknameReadProcess', self.ui)
        self.assertIn('id: nicknameWriteProcess', self.ui)

    def test_editing_explicit_and_only_for_observed_paired_active_profile(self):
        self.assertIn('id: managePhoneNickname', self.ui)
        self.assertIn('label: "SAVE NAME"', self.ui)
        self.assertIn('label: "CLEAR NAME"', self.ui)
        self.assertIn('onTriggered: phonePane.changePhoneNickname("save")', self.ui)
        self.assertIn('onTriggered: phonePane.changePhoneNickname("clear")', self.ui)
        self.assertIn('nicknameEditorOpen', self.ui)
        self.assertIn('deviceObservation.state !== "PAIRED_OFFLINE"', self.ui)
        self.assertIn('deviceObservation.state !== "BLUETOOTH_CONNECTED"', self.ui)
        self.assertIn('next.profileId !== phonePane.deviceObservation.profileId', self.ui)
        self.assertIn('result.profileId !== phonePane.deviceObservation.profileId', self.ui)
        self.assertIn('next.contentAccessEnabled !== false', self.ui)
        self.assertIn('result.contentAccessEnabled !== false', self.ui)
        self.assertIn('next.trustedPhoneLink !== "UNVERIFIED"', self.ui)

    def test_text_input_follows_post_apollo_semantic_colors(self):
        self.assertIn('id: phoneNicknameInput', self.ui)
        self.assertIn('color: Colors.magenta', self.ui)
        self.assertIn('maximumLength: 40', self.ui)
        self.assertIn('color: Colors.orange', self.ui)
        self.assertIn('accentColor: Colors.green', self.ui)
        self.assertIn('destructive: true', self.ui)
        self.assertIn('accentColor: Colors.red', self.ui)
        self.assertIn('"PERSONAL DISPLAY ONLY // Not an account', self.ui)

    def test_still_no_automatic_phone_pairing_or_private_content(self):
        self.assertIn("conversations: []", self.ui)
        self.assertIn("messages: []", self.ui)
        self.assertIn("sendEnabled: false", self.ui)
        self.assertNotIn('bluetoothctl remove', self.ui)
        self.assertNotIn('bluetoothctl pair', self.ui)
        self.assertNotIn('LocalStorage', self.ui)
        self.assertNotIn('phonePane.deviceObservation.contentAccessEnabled = true', self.ui)
        self.assertIn('READ-ONLY SETUP PREVIEW', self.ui)
        self.assertTrue(HELPER.exists())


if __name__ == "__main__":
    unittest.main()
