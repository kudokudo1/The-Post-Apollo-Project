"""P25 Social PHONE CALLS workspace UI contract, source only."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
PANE = ROOT / "widgets/messanger/PhonePane.qml"
BRIDGE = ROOT / "services/phone/PhoneCallWorkspace.py"


class CallWorkspaceUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ui = PANE.read_text()
        cls.bridge = BRIDGE.read_text()

    def test_existing_calls_tab_now_renders_real_call_workspace(self):
        for marker in (
            'model: ["DEVICE", "CALLS", "MESSAGES", "CONTACTS"]',
            'id: phoneCallsWorkspace',
            'visible: phonePane.selectedSection === "CALLS"',
            'id: callsColumn',
            'model: phonePane.callsWorkspaceState === "READY"',
            'phonePane.liveCalls : []',
            'text: modelData.peer',
            'text: "CALLS // IPHONE HANDS-FREE"',
            'phonePane.callsWorkspaceMessage()',
            '? "CHECKING..." : "REFRESH CALLS"',
            'label: "DEVICE / HFP SETUP"',
            'onTriggered: phonePane.startSetup()',
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, self.ui)
        self.assertNotIn('FloatingWindow {', self.ui)
        self.assertNotIn('PanelWindow {', self.ui)

    def test_real_call_actions_not_dummy_buttons(self):
        for marker in (
            'label: "ANSWER"',
            'label: "DECLINE"',
            'label: "HANG UP"',
            'onTriggered: phonePane.requestCallAction("answer", modelData.id)',
            'onTriggered: phonePane.requestCallAction("decline", modelData.id)',
            'onTriggered: phonePane.requestCallAction("hangup", modelData.id)',
            'label: "REVIEW OUTGOING CALL"',
            'phonePane.preparePhoneDial()',
            'label: "CONFIRM CALL"',
            'phonePane.requestCallAction(',
            '"dial", phonePane.callsPendingDial',
            'label: "SWAP ACTIVE / HELD"',
            '"swap", ""',
            'label: "HOLD AND ANSWER"',
            '"hold-answer", ""',
            'label: "SEND TONES"',
            '"tones", callId + "\\t" + callTonesInput.text',
            'id: phoneCallsActionProcess',
            'PhoneCallWorkspace.py',
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, self.ui)
        self.assertIn('destructive: true', self.ui)
        self.assertIn('accentColor: Colors.red', self.ui)

    def test_dial_is_explicit_preview_and_emergencies_phone_only(self):
        self.assertIn('property bool callsConfirmDial: false', self.ui)
        self.assertIn('property string callsPendingDial: ""', self.ui)
        self.assertIn('function preparePhoneDial()', self.ui)
        self.assertIn('function requestCallAction(action, argument)', self.ui)
        self.assertIn('if (action === "dial" && (!callsConfirmDial', self.ui)
        self.assertIn('label: "CANCEL"', self.ui)
        self.assertIn('Use your iPhone for emergency calls.', self.ui)
        self.assertIn('KNOWN_EMERGENCY', self.bridge)
        self.assertIn('DIAL.fullmatch(argument)', self.bridge)
        self.assertNotIn('["python3", "blueferry", "calls", "dial"]', self.ui)

    def test_calls_poll_only_when_tab_open_and_identity_purges(self):
        for marker in (
            'interval: 2500',
            'running: phonePane.visible && phonePane.selectedSection === "CALLS"',
            'phonePane.refreshCallsWorkspace()',
            'callsWorkspaceGeneration += 1;',
            'callsRequireExplicitRefresh = true;',
            'liveCalls = ([]);',
            'if (phoneCallsStatusProcess.running)',
            'phoneCallsStatusProcess.running = false;',
            'if (selectedSection !== "CALLS")',
            'if (visible && selectedSection === "CALLS" && !callsRequireExplicitRefresh)',
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, self.ui)
        self.assertIn('id: phoneCallsStatusProcess', self.ui)
        self.assertIn('response.scope !== "PERSONAL_LOCAL_USER_ONLY"', self.ui)
        self.assertIn('response.organizationGrant !== false', self.ui)

    def test_user_messaging_and_contacts_workspace_unchanged(self):
        for marker in (
            '    ContactList {',
            '    ChatFeed {',
            '    ListView {',
            'id: phoneContactList',
            'id: phoneAddressBook',
            'sendEnabled: false',
            'phoneReadAdapter.conversations : []',
            'phoneReadAdapter.messages : []',
            'emptyConversationLabel:',
            'id: personalReadBar',
            'id: setupOverlay',
            'id: phoneAudioSettings',
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, self.ui)
        self.assertNotIn('FaceTimeEnabled: true', self.ui)
        self.assertNotIn('sendMessage(', self.ui)
        self.assertIn('FaceTime, decline-with-text, starting conferences', self.ui)


if __name__ == "__main__":
    unittest.main()
