"""PHONE audio controls are in the Social Device menu, never terminal-only."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[2]
PHONE = ROOT / "widgets" / "messanger" / "PhonePane.qml"
HELPER = ROOT / "services" / "phone" / "PhoneAudioControls.py"


class PhoneAudioUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.qml = PHONE.read_text()
        cls.backend = HELPER.read_text()

    def test_existing_phone_menu_contains_both_audio_controls(self):
        self.assertIn('id: phoneAudioSettings', self.qml)
        self.assertIn('text: "IPHONE AUDIO"', self.qml)
        self.assertIn('id: mediaRouteChoices', self.qml)
        self.assertIn('{ title: "IPHONE", route: "phone" }', self.qml)
        self.assertIn('{ title: "COMPUTER", route: "pc" }', self.qml)
        self.assertIn('{ title: "AUTO", route: "auto" }', self.qml)
        self.assertIn('onTriggered: phonePane.changePhoneAudio("media", modelData.route)', self.qml)
        self.assertIn('? "CALLS ON PC: ON" : "CALLS ON PC: OFF"', self.qml)
        self.assertIn('"calls", phonePane.phoneAudioStatus.callsEnabled === true', self.qml)
        self.assertIn('For calls only, choose IPHONE above and enable CALLS ON PC', self.qml)

    def test_one_primary_connect_button_and_same_social_pane(self):
        self.assertEqual(self.qml.count('id: connectPhoneAction'), 1)
        self.assertIn('    ContactList {', self.qml)
        self.assertIn('    ChatFeed {', self.qml)
        self.assertIn('conversations: []', self.qml)
        self.assertIn('messages: []', self.qml)
        self.assertIn('sendEnabled: false', self.qml)
        self.assertIn('model: ["DEVICE", "CALLS", "MESSAGES", "CONTACTS"]', self.qml)
        self.assertNotIn('FloatingWindow {', self.qml)
        self.assertNotIn('PanelWindow {', self.qml)

    def test_changes_require_user_press_and_active_saved_bridge(self):
        body = re.search(r'function changePhoneAudio\(family, selection\) \{(.*?)\n    \}',
                         self.qml, re.S)
        self.assertIsNotNone(body)
        content = body.group(1)
        self.assertIn('setupState !== "CHECKED"', content)
        self.assertIn('phoneAudioStatus.canAdjust !== true', content)
        self.assertIn('phoneAudioStatus.ofonoActive !== true', content)
        self.assertIn('"--set", family, selection', content)
        self.assertIn('audioActionProcess.running = true;', content)
        self.assertIn('PhoneAudioControls.py', self.qml)
        self.assertIn('"--status"', self.qml)
        visible = re.search(r'onVisibleChanged: \{(.*?)\n    \}', self.qml, re.S)
        self.assertIsNotNone(visible)
        self.assertNotIn('changePhoneAudio(', visible.group(1))
        self.assertNotIn('refreshPhoneAudioControls(', visible.group(1))

    def test_call_on_state_never_claims_hfp_ready(self):
        self.assertIn('Call preference on. HFP status:', self.qml)
        self.assertIn('Actual call audio depends on oFono', self.qml)
        self.assertIn('not ready on this desktop.', self.qml)
        self.assertIn('First media change may briefly interrupt', self.qml)
        self.assertIn('r.trustedPhoneLink !== "UNVERIFIED"', self.qml)
        self.assertIn('r.contentAccessEnabled !== false', self.qml)
        self.assertIn('"PREFERENCE_SAVED"', self.qml)
        self.assertIn('No change made.', self.qml)

    def test_audio_controls_do_not_steal_staged_terminal_space(self):
        self.assertIn('id: phoneAudioSettings', self.qml)
        self.assertIn('visible: phonePane.setupState === "CHECKED" && !phonePane.stageWanted', self.qml)
        self.assertIn('phoneChatFeed.x + 10', self.qml)
        self.assertIn('stageHoleY:', self.qml)
        self.assertIn('WeatherStage.StationChassisCutout {', self.qml)
        self.assertIn('onTriggered: phonePane.closeStagedSetup()', self.qml)

    def test_per_provider_storage_no_system_settings_or_autorun(self):
        self.assertIn('phone_audio_preference', self.backend)
        self.assertIn('calls_enabled', self.backend)
        self.assertNotIn('subprocess.Popen(', self.backend)
        self.assertNotIn('systemctl restart', self.backend)
        self.assertNotIn('bluez5.roles', self.backend)
        self.assertNotIn('localStorage', self.qml)
        self.assertNotIn('sendMessage(', self.qml)
        self.assertNotIn('Bluetooth settings', self.backend)


if __name__ == "__main__":
    unittest.main()
