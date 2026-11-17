"""PHONE FaceTime Audio V2 user-initiated route evidence and NO native call."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
PANEL = (ROOT / "widgets/messanger/PhoneFaceTimeHandoff.qml").read_text()
PANE = (ROOT / "widgets/messanger/PhonePane.qml").read_text()
CONTACT = (ROOT / "widgets/messanger/PhoneContactDetail.qml").read_text()
PROBE = (ROOT / "services/phone/PhoneFaceTimeAudioRouteProbe.py").read_text()
LINKS = (ROOT / "widgets/messanger/PhoneFaceTimeLinks.js").read_text()


class FaceTimeRouteUI(unittest.TestCase):
    def test_explicit_click_and_fixed_status_only_host_command(self):
        for s in ('import Quickshell', 'import Quickshell.Io',
                  'property string audioRouteState: "NOT_CHECKED"',
                  'property int audioRouteGeneration: 0',
                  'function inspectAudioRoute()',
                  'mode !== "audio"',
                  'audioRouteProcess.running',
                  'onTriggered: handoff.inspectAudioRoute()',
                  '"python3"',
                  'Quickshell.shellPath("services/phone/PhoneFaceTimeAudioRouteProbe.py")',
                  '"--status"',
                  'label: audioRouteProcess.running ? "CHECKING AUDIO..." : "CHECK AUDIO ROUTE"'):
            self.assertIn(s, PANEL)
        self.assertNotIn("audioRouteProcess.running = true;", PANEL.split(
            'function inspectAudioRoute()', 1)[0])
        self.assertIn('running = true;', PANEL)
        self.assertIn('interactive: !audioRouteProcess.running', PANEL)
        self.assertIn('visible: handoff.mode === "audio"', PANEL)
        self.assertIn("No device settings changed.", PANEL)

    def test_full_host_schema_checks_and_no_connection_elevation(self):
        for value in (
            'post-apollo.phone.facetime-audio-route.v1',
            'READ_ONLY_USER_INITIATED',
            'observed.faceTimeAudioVerified !== false',
            'observed.faceTimeConnected !== false',
            'observed.faceTimeCallControl !== false',
            'observed.microphoneVerified !== false',
            'observed.speakerVerified !== false',
            'observed.canChangeRoute !== false',
            'observed.providerAuthenticated !== false',
            'observed.personalDataAccess !== false',
            'audioRouteProcess.generation !== handoff.audioRouteGeneration',
            'handoff.audioRouteObservation = ({})',
            'audioRouteGeneration += 1',
            'audioRouteState = "NOT_CHECKED"',
            'if (audioRouteProcess && audioRouteProcess.running)',
            'audioRouteProcess.running = false',
            'onModeChanged: clear()',
            'onContactChanged: clear()',
        ):
            self.assertIn(value, PANEL)
        self.assertIn('may belong to another device', PANEL)
        self.assertIn('FaceTime, microphone and speaker are NOT verified', PANEL)
        self.assertIn('Start FaceTime Audio on the iPhone', PANEL)
        self.assertIn('select the available PC/Bluetooth audio endpoint', PANEL)
        self.assertIn('PHONE cannot observe which iPhone app', PANEL)
        self.assertIn('faceTimeAudioVerified": False', PROBE)
        self.assertIn('faceTimeConnected": False', PROBE)
        self.assertIn('canChangeRoute": False', PROBE)

    def test_does_not_weaken_original_face_time_link_or_call_controls(self):
        self.assertIn('Qt.openUrlExternally(selected)', PANEL)
        self.assertEqual(PANEL.count('Qt.openUrlExternally('), 1)
        self.assertIn('reviewedInvite !== FaceTimeLinks.normalizeInvite(inviteInput.text)', PANEL)
        self.assertIn('readonly property bool personalMetadataWritable: false'.lower(),
                      CONTACT.lower())
        self.assertIn('label: "FT AUDIO"', CONTACT)
        self.assertIn('label: "FT VIDEO"', CONTACT)
        self.assertIn('label: "FT AUDIO"', PANE)
        self.assertIn('label: "FT VIDEO"', PANE)
        self.assertIn('function requestCallAction(action, argument)', PANE)
        self.assertIn("facetime-audio:", LINKS)
        self.assertNotIn('Qt.openUrlExternally(appleDeviceLink.text)', PANEL)
        self.assertNotIn('facetime-audio:', PROBE)
        self.assertNotIn('FaceTimeLink', PROBE)

    def test_no_profile_mutation_or_personal_authorization(self):
        for forbidden in (
            'systemctl start', 'systemctl restart', 'bluetoothctl pair',
            'pactl set-card-profile', 'wpctl set-profile',
            'PhonePersonalContactVault', 'PhonePersonalSaveOrchestrator',
            'C5OneUseConsentVerified', 'FaceTimeCallControl',
            'secret-tool', 'RequestDial(', 'AudioControl.apply(',
        ):
            self.assertNotIn(forbidden, PANEL + PROBE)


if __name__ == "__main__":
    unittest.main()
