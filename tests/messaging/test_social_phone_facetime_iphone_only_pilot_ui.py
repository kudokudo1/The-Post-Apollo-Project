"""iPhone-only FaceTime pilot UI can read capabilities but cannot dial."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
PANEL = (ROOT / "widgets/messanger/PhoneFaceTimeHandoff.qml").read_text()
PANE = (ROOT / "widgets/messanger/PhonePane.qml").read_text()
CONTACT = (ROOT / "widgets/messanger/PhoneContactDetail.qml").read_text()
BACKEND = (ROOT / "services/phone/PhoneFaceTimeIphonePilot.py").read_text()


class FaceTimeIphonePilotUI(unittest.TestCase):
    def test_existing_both_modes_show_one_explicit_preflight_action(self):
        for evidence in (
            'IPHONE-ONLY PILOT // LOCAL CAPABILITY CHECK',
            'CHECK IPHONE SUPPORT',
            'function inspectIphonePilot()',
            'onTriggered: handoff.inspectIphonePilot()',
            'interactive: !iphonePilotProcess.running',
            'iphonePilotProcess.running = true;',
            'Quickshell.shellPath("services/phone/PhoneFaceTimeIphonePilot.py")',
            '"--preflight"', 'id: iphonePilotProcess',
            'property int iphonePilotGeneration: 0',
            'property string iphonePilotState: "NOT_CHECKED"',
            'property var iphonePilotObservation: ({})',
            'onModeChanged: clear()', 'onContactChanged: clear()',
            'onVisibleChanged: {',
        ):
            self.assertIn(evidence, PANEL)
        self.assertNotIn('iphonePilotProcess.running = true;', PANEL.split(
            'function inspectIphonePilot()', 1)[0])
        self.assertIn('if (iphonePilotProcess && iphonePilotProcess.running)', PANEL)
        self.assertIn('iphonePilotProcess.running = false;', PANEL)
        self.assertIn('iphonePilotProcess.generation !== handoff.iphonePilotGeneration', PANEL)

    def test_pilot_denial_requirements_never_expand_dial_authority(self):
        for value in (
            'post-apollo.phone.facetime-iphone-only-preflight.v1',
            'READ_ONLY_EXPLICIT_USER_TEST',
            'outboundIphoneShortcutVerified',
            'outboundPcDispatchAvailable', 'incomingFaceTimeDetected',
            'answerFaceTimeAvailable', 'endFaceTimeAvailable',
            'liveFaceTimeVideoAvailable', 'twoWayFaceTimeAudioVerified',
            'iphoneCompanionAuthenticated', 'faceTimeConnected',
            'canChangeRoute', 'contentAccessEnabled',
            'personalSaveAuthorized', 'result[denied[j]] !== false',
            'No PC FaceTime dial, answer, end or video transport exists.',
        ):
            self.assertIn(value, PANEL)
        self.assertIn(value, PANEL + BACKEND)
        self.assertIn('case "PHONE_CALLS_DISABLED":', PANEL)
        self.assertIn('"PHONE_CALLS_DISABLED"', PANEL)
        self.assertIn('CALLS ON PC IS OFF.', PANEL)
        self.assertIn('"PHONE_CALLS_DISABLED"', (ROOT / "services/phone/PhoneFaceTimeAudioRouteProbe.py").read_text())
        self.assertIn("No phone action will be sent", PANEL)
        self.assertIn("FaceTime incoming call NOT detected", PANEL)
        self.assertIn("select PC/Bluetooth on the iPhone", PANEL)

    def test_v1_and_v2_link_media_and_calls_guards_remain(self):
        self.assertIn('Qt.openUrlExternally(selected)', PANEL)
        self.assertEqual(PANEL.count('Qt.openUrlExternally('), 1)
        self.assertIn('reviewedInvite !== FaceTimeLinks.normalizeInvite(inviteInput.text)', PANEL)
        self.assertIn('facetime-audio:', (ROOT / "widgets/messanger/PhoneFaceTimeLinks.js").read_text())
        self.assertIn('function inspectAudioRoute()', PANEL)
        self.assertIn('Quickshell.shellPath("services/phone/PhoneFaceTimeAudioRouteProbe.py")', PANEL)
        self.assertIn('label: "FT AUDIO"', CONTACT)
        self.assertIn('label: "FT VIDEO"', CONTACT)
        self.assertIn('label: "FT AUDIO"', PANE)
        self.assertIn('label: "FT VIDEO"', PANE)
        self.assertNotIn('Qt.openUrlExternally(appleDeviceLink.text)', PANEL)
        self.assertIn('readonly property bool personalMetadataWritable: false'.lower(),
                      CONTACT.lower())

    def test_no_mutating_command_or_auto_start(self):
        for forbidden in (
            'SetCallsEnabled', 'Calls1.Dial', 'subprocess', 'localStorage',
            'systemctl restart', 'systemctl start',
            'pactl set-card-profile', 'wpctl set-profile',
            'bluetoothctl pair', 'FaceTimeCallControl',
            'Qt.openUrlExternally(appleDeviceLink.text)',
        ):
            self.assertNotIn(forbidden, PANEL + BACKEND)


if __name__ == "__main__":
    unittest.main()
