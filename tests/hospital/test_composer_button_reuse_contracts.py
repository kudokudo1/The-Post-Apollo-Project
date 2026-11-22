"""Hospital composer buttons stay reusable and leave service authority in owners.

These source tests do not activate microphones, send a message, or certify
native Wayland/QML rendering. Existing Hospital acceptance tests run alongside.
"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VOICE = ROOT / "components/VoiceToTextButton.qml"
ASK_SEND = ROOT / "components/AskSendButton.qml"
RECEPTION = ROOT / "widgets/HospitalReceptionistView.qml"
INTERCOM = ROOT / "widgets/HospitalIntercomMenu.qml"
WORKFLOW = ROOT / ".github/workflows/hospital-acceptance.yml"


class HospitalComposerButtonReuseContracts(unittest.TestCase):
    def test_shared_controls_use_existing_action_button_family(self):
        for filename in (VOICE, ASK_SEND):
            with self.subTest(component=filename.name):
                source = filename.read_text()
                self.assertRegex(source, r"(?m)^ActionButton \{")
                self.assertIn("acceptedButtons:", source)
                self.assertIn("Accessible.role: Accessible.Button", source)
                self.assertIn("softGlowEnabled: true", source)
                self.assertIn("wideGlowEnabled: false", source)
                self.assertIn("contentGlowSource:", source) if filename == VOICE else self.assertIn(
                    "contentGlowEnabled: false", source
                )
                for prohibited in (
                    "Process {", "Quickshell.execDetached", "HospitalSpeechInputService",
                    "HospitalLiveDictationService", "HospitalReceptionistService",
                    "HospitalIntercomService", "startRecording(", "stopRecording(",
                    "sendCurrent(", "submitReceptionInput(", "onCompleted:",
                ):
                    self.assertNotIn(prohibited, source)
                self.assertNotIn("layer.effect: DropShadow", source)

    def test_voice_component_exposes_only_state_and_toggle_signal(self):
        voice = VOICE.read_text()
        self.assertIn('property string voiceGlyph: "🗣︎"', voice)
        self.assertIn("signal toggleRequested()", voice)
        self.assertIn("onLeftClicked: toggleRequested()", voice)
        self.assertIn("available: !processing", voice)
        self.assertIn("selected: busy", voice)
        self.assertIn("opacity: busy || backendReady ? 1.0 : 0.48", voice)
        self.assertIn("contentGlowSource: speechGlyph", voice)
        self.assertIn("contentGlowEnabled: glyphGlowEnabled", voice)
        self.assertIn("selectedFillColor: Colors.yellow", voice)
        self.assertIn("selectedBorderColor: Colors.magenta", voice)
        self.assertIn("idleBorderColor: idleAccent", voice)

    def test_ask_send_component_keeps_primary_and_secondary_distinct(self):
        action = ASK_SEND.read_text()
        for required in (
            'property string askLabel: "ASK"',
            'property string sendLabel: "SEND"',
            'property string processingLabel: "..."',
            "property bool allowSecondaryAction: false",
            "signal primaryRequested()",
            "signal secondaryRequested()",
            "onLeftClicked: primaryRequested()",
            "if (allowSecondaryAction)",
            "secondaryRequested();",
            "available: enabledAction",
            "acceptedButtons: allowSecondaryAction",
            "recording ? askSendButton.sendLabel",
            "recording ? recordingAccent : idleAccent",
            "softGlowIdleOpacity: enabledAction ? restingGlowOpacity : 0.12",
        ):
            with self.subTest(required=required):
                self.assertIn(required, action)

    def test_reception_preserves_voice_and_ask_send_semantics(self):
        source = RECEPTION.read_text()
        self.assertEqual(source.count("VoiceToTextButton {"), 1)
        self.assertEqual(source.count("AskSendButton {"), 1)
        self.assertNotRegex(source, r"Rectangle \{\s*id: (?:micButton|sendButton)")
        for required in (
            "id: micButton",
            "id: sendButton",
            "glyphGlowEnabled: true",
            "backendReady: root.speechInputService.backendReady",
            "busy: root.speechInputService.busy",
            "root.speechInputService.stopping",
            "root.speechInputService.transcribing",
            "receptionInput.forceActiveFocus();",
            "root.speechInputService.stopRecording(false);",
            "root.speechInputService.startRecording();",
            "root.speechInputService.stopRecording(true);",
            "root.submitReceptionInput();",
            'askLabel: "ASK"',
            'sendLabel: "SEND"',
            "recordingAccent: Colors.magenta",
            "allowSecondaryAction: false",
            "receptionInput.text.trim().length > 0",
            "onToggleRequested:",
            "onPrimaryRequested:",
        ):
            with self.subTest(required=required):
                self.assertIn(required, source)
        self.assertNotIn("onSecondaryRequested:", source)

    def test_intercom_preserves_ready_gate_and_right_click_path(self):
        source = INTERCOM.read_text()
        self.assertEqual(source.count("VoiceToTextButton {"), 1)
        self.assertEqual(source.count("AskSendButton {"), 1)
        self.assertNotRegex(source, r"Rectangle \{\s*id: (?:micButton|sendButton)")
        for required in (
            "id: micButton",
            "id: sendButton",
            "glyphGlowEnabled: false",
            "backendReady: root.speechInputService.backendReady",
            "busy: root.speechInputService.busy",
            "messageInput.forceActiveFocus();",
            "root.speechInputService.stopRecording(false);",
            "root.speechInputService.startRecording();",
            'String(root.selectedSpecialist.presence || "") === "READY"',
            "root.selectedSpecialist",
            'askLabel: "SEND"',
            'sendLabel: "SEND"',
            "recordingAccent: Colors.omnitrix",
            "allowSecondaryAction: true",
            "onToggleRequested:",
            "onPrimaryRequested: root.sendCurrentVoiceAware()",
            "onSecondaryRequested: root.sendCurrent(true)",
        ):
            with self.subTest(required=required):
                self.assertIn(required, source)

    def test_hospital_workflow_covers_changes_to_shared_components(self):
        workflow = WORKFLOW.read_text()
        self.assertEqual(workflow.count('components/VoiceToTextButton.qml'), 2)
        self.assertEqual(workflow.count('components/AskSendButton.qml'), 2)
        self.assertIn('for test in tests/hospital/test_*contracts.py;', workflow)


if __name__ == "__main__":
    unittest.main()
