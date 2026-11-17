"""FaceTime Audio/Video handoff QML boundary.

Link validation is also executed dynamically by the Node JS test. This
contract deliberately does not assert that native Apple FaceTime call control
or HFP routing exists on Linux.
"""
from __future__ import annotations

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
PANE = (ROOT / "widgets/messanger/PhonePane.qml").read_text()
DETAIL = (ROOT / "widgets/messanger/PhoneContactDetail.qml").read_text()
UI = (ROOT / "widgets/messanger/PhoneFaceTimeHandoff.qml").read_text()
LINKS = (ROOT / "widgets/messanger/PhoneFaceTimeLinks.js").read_text()
CALLS = (ROOT / "services/phone/PhoneCallWorkspace.py").read_text()


class FaceTimeHandoffContract(unittest.TestCase):
    def test_existing_contact_action_split(self):
        self.assertIn('label: "FT AUDIO"', DETAIL)
        self.assertIn('label: "FT VIDEO"', DETAIL)
        self.assertIn('detail.openFaceTimeMode("audio")', DETAIL)
        self.assertIn('detail.openFaceTimeMode("video")', DETAIL)
        self.assertIn('onContactChanged: {', DETAIL)
        self.assertIn('faceTimeMode = "";', DETAIL)
        self.assertIn('PhoneFaceTimeHandoff {', DETAIL)
        self.assertIn('contact: detail.contact', DETAIL)
        self.assertIn('onCloseRequested: detail.faceTimeMode = ""', DETAIL)
        self.assertNotIn('interactive: false // No BlueFerry FaceTime transport.', DETAIL)
        self.assertIn('label: "CALL"', DETAIL)
        self.assertIn('label: "MESSAGE"', DETAIL)
        self.assertIn('label: "EMAIL"', DETAIL)
        self.assertIn('readonly property bool personalMetadataWritable: false'.lower(),
                      DETAIL.lower())

    def test_existing_calls_section_has_link_handoff_not_facetime_provider(self):
        self.assertIn('label: "FT AUDIO"', PANE)
        self.assertIn('label: "FT VIDEO"', PANE)
        self.assertIn('property string callsFaceTimeMode: ""', PANE)
        self.assertIn('onTriggered: phonePane.callsFaceTimeMode = "audio"', PANE)
        self.assertIn('onTriggered: phonePane.callsFaceTimeMode = "video"', PANE)
        self.assertIn('contact: null', PANE)
        self.assertIn('onCloseRequested: phonePane.callsFaceTimeMode = ""', PANE)
        self.assertGreaterEqual(PANE.count('callsFaceTimeMode = "";'), 3)
        self.assertIn('function requestCallAction(action, argument)', PANE)
        self.assertIn('onCallRequested: phonePane.openSelectedContactForCall()', PANE)
        self.assertNotIn('Qt.openUrlExternally(', PANE)
        self.assertIn('faceTimeEnabled !== false', PANE)
        self.assertIn('"facetimeEnabled": False', CALLS.replace(
            '"faceTimeEnabled": False', '"facetimeEnabled": False'))

    def test_only_explicitly_reviewed_apple_https_link_may_launch(self):
        self.assertIn('import "PhoneFaceTimeLinks.js" as FaceTimeLinks', UI)
        self.assertIn('FaceTimeLinks.normalizeInvite(inviteInput.text)', UI)
        self.assertIn('reviewedInvite !== FaceTimeLinks.normalizeInvite(inviteInput.text)', UI)
        self.assertIn('result !== "REVIEW"', UI)
        self.assertIn('Qt.openUrlExternally(selected)', UI)
        self.assertEqual(UI.count('Qt.openUrlExternally('), 1)
        self.assertNotIn('Qt.openUrlExternally(appleDeviceLink.text)', UI)
        self.assertIn('readOnly: true', UI)
        self.assertIn('selectByMouse: true', UI)
        self.assertIn('color: Colors.magenta', UI)
        self.assertIn('color: Colors.orange', UI)
        self.assertIn('onModeChanged: clear()', UI)
        self.assertIn('onContactChanged: clear()', UI)
        self.assertIn('onVisibleChanged: {', UI)
        self.assertIn('NATIVE LINUX FACETIME // NOT CONNECTED', UI)
        self.assertIn('No browser handoff'.upper().split()[0].lower(), UI.lower())

    def test_apple_link_builder_cannot_control_calls(self):
        self.assertIn('facetime-audio:', LINKS)
        self.assertIn('facetime:', LINKS)
        self.assertIn('facetime\\.apple\\.com', LINKS)
        self.assertIn('card.hasAddressDetails !== true', LINKS)
        self.assertIn('Array.isArray(numbers)', LINKS)
        self.assertIn('Array.isArray(emails)', LINKS)
        self.assertNotIn('Qt.openUrlExternally(', LINKS)
        for forbidden in (
            "fetch(", "XMLHttpRequest", "D-Bus", "BlueFerryCallsSource",
            "Dial(", "subprocess", "systemctl", "localStorage",
            "secret-tool", "print(", "console.log(",
        ):
            self.assertNotIn(forbidden, LINKS)


if __name__ == "__main__":
    unittest.main()
