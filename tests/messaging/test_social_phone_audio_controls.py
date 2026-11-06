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
        self.assertIn('For calls only, choose IPHONE above and select CALLS ON PC.', self.qml)

    def test_one_primary_connect_button_and_same_social_pane(self):
        self.assertEqual(self.qml.count('id: connectPhoneAction'), 1)
        self.assertIn('    ContactList {', self.qml)
        self.assertIn('    ChatFeed {', self.qml)
        self.assertIn('phoneReadAdapter.conversations : []', self.qml)
        self.assertIn('phoneReadAdapter.messages : []', self.qml)
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
        self.assertIn('Tap the call control for the missing hands-free requirement.', self.qml)
        self.assertIn('First media change may briefly interrupt', self.qml)
        self.assertIn('r.trustedPhoneLink !== "UNVERIFIED"', self.qml)
        self.assertIn('r.contentAccessEnabled !== false', self.qml)
        self.assertIn('"PREFERENCE_SAVED"', self.qml)
        self.assertIn('No change made.', self.qml)

    def test_calls_off_stays_clickable_without_ofono_and_shows_explanation(self):
        # The operator's screenshot had a visually present but completely
        # disabled CALLS ON PC: OFF because oFono was not active.
        action_label = self.qml.index('label: phonePane.phoneAudioStatus.callsEnabled === true')
        button_start = self.qml.rfind('ActionButton {', 0, action_label)
        button_end = self.qml.index('onTriggered: phonePane.changePhoneAudio(', action_label)
        self.assertGreaterEqual(button_start, 0)
        button = self.qml[button_start:button_end]
        self.assertIn('interactive: !audioActionProcess.running', button)
        self.assertIn('&& !audioStatusProcess.running', button)
        self.assertIn('&& !phonePane.stageWanted', button)
        # Missing capabilities are handled by the click, not a dead button.
        self.assertNotIn('&& phonePane.phoneAudioStatus.ofonoActive === true', button)
        self.assertNotIn('&& phonePane.phoneAudioStatus.callsEnabled !== null', button)
        self.assertNotIn('&& phonePane.phoneAudioStatus.canAdjust === true', button)

        handler_start = self.qml.index('function changePhoneAudio(family, selection)')
        handler_end = self.qml.index('function phoneAudioResultText()', handler_start)
        action = self.qml[handler_start:handler_end]
        self.assertIn('phoneAudioResult = "CALLS_PREREQUISITES_MISSING";', action)
        self.assertIn('phoneAudioResult = "CALLS_UNSUPPORTED";', action)
        self.assertIn('phoneAudioResult = "CALLS_STATUS_UNAVAILABLE";', action)
        self.assertIn('phoneAudioStatus.ofonoActive !== true', action)
        self.assertIn('phoneAudioStatus.canAdjust !== true', action)
        self.assertIn('typeof phoneAudioStatus.callsEnabled !== "boolean"', action)
        self.assertIn('No audio changes were made.', self.qml)
        self.assertIn('Tap the call control for the missing hands-free requirement.', self.qml)

    def test_calls_button_runs_readonly_reason_check_instead_of_host_install(self):
        self.assertIn('id: callPrerequisiteProcess', self.qml)
        self.assertIn('PhoneCallPrerequisites.py', self.qml)
        self.assertIn('function diagnoseCallPrerequisites()', self.qml)
        self.assertIn('diagnoseCallPrerequisites();', self.qml)
        self.assertIn('phoneAudioResult = "CALLS_DIAGNOSING";', self.qml)
        self.assertIn('r.execution !== "READ_ONLY_CALL_DIAGNOSIS"', self.qml)
        self.assertIn('r.hfpVerified !== false', self.qml)
        self.assertIn('r.trustedPhoneLink !== "UNVERIFIED"', self.qml)
        self.assertIn('r.contentAccessEnabled !== false', self.qml)
        self.assertIn('oFono is not installed on this Fedora system.', self.qml)
        self.assertIn('oFono is installed as a service but is stopped.', self.qml)
        self.assertIn('The oFono service exists but failed to start.', self.qml)
        self.assertIn('oFono appears active. Hands-free routing', self.qml)
        self.assertIn('phoneAudioResult === "CALLS_DIAGNOSING"', self.qml)
        self.assertIn('callPrerequisiteCheck = "NOT CHECKED";', self.qml)
        self.assertIn('&& !callPrerequisiteProcess.running', self.qml)
        start = self.qml.index('onVisibleChanged: {')
        end = self.qml.index('\n    }', start)
        block = self.qml[start:end]
        self.assertNotIn('diagnoseCallPrerequisites(', block)
        self.assertNotIn('PhoneCallPrerequisites.py', block)
        self.assertNotIn('systemctl start', self.qml)
        self.assertNotIn('dnf install', self.qml)

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
