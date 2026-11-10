#!/usr/bin/env python3
"""Hospital long-form mic must remain local, explicit and non-submitting."""
from pathlib import Path
root = Path(__file__).resolve().parents[2]
host = (root / "widgets/HospitalW.qml").read_text()
manager = (root / "widgets/HospitalWorkforceManagerView.qml").read_text()
voice = (root / "services/hospital/HospitalSpeechInputService.qml").read_text()
policy = (root / "services/hospital/HospitalDictationTextPolicy.js").read_text()
issues = []
def check(ok, message):
    if not ok:
        issues.append(message)

check(host.count('HospitalSpeechInputService {') >= 3
      and 'id: workforceSpeechInputService' in host
      and 'audioFileName: "hospital-workforce-dictation.wav"' in host
      and 'speechInputService: workforceSpeechInputService' in host,
      "Use existing local Whisper recorder with a unique Surgery audio file")
check('otherVoiceBusy: speechInputService.busy' in host
      and '|| intercomSpeechInputService.busy' in host
      and 'workforceSpeechInputService.cancel();' in host,
      "Refuse concurrent Reception/Intercom recording and cancel on Hospital close")
check('import "../services/hospital/HospitalDictationTextPolicy.js" as DictationTextPolicy' in manager
      and 'DictationTextPolicy.appendTranscription(' in manager,
      "Reuse bounded plain-text insertion policy, not a second transcriber")
for key, alias in [
    ("intake","intakeBriefField"),
    ("goal","jobGoalField"),
    ("constraints","jobConstraintsField"),
    ("done","jobDoneField"),
    ("checklist","jobChecklistField"),
]:
    check('voiceKey: "intake"' in manager if key=="intake" else
          'voiceKey:"'+key+'"' in manager,
          key+" must enable microphone")
    check('if (key === "'+key+'") return '+alias+';' in manager,
          key+" must route transcript back only to its selected text editor")
check('component ManagerArea: Column {' in manager
      and 'property string voiceKey: ""' in manager
      and 'HospitalActionButton {' in manager
      and 'label: "CANCEL"' in manager
      and '"STOP"' in manager
      and ': "MIC"' in manager,
      "Share MIC, STOP and CANCEL controls across multiline fields")
check('svc.startRecording()' in manager
      and 'svc.stopRecording(false)' in manager
      and 'root.speechInputService.cancel()' in manager,
      "Recording requires explicit action, stop never sends")
check('onTranscriptionReady(text, submitRequested)' in manager
      and 'root.acceptDictation(text);' in manager
      and 'submitRequested' in manager
      and 'field.value = result.text;' in manager
      and 'field.focusEditorAtEnd()' in manager,
      "Only insert text, never submit an AI/Room/Worker/Job request")
check('onModeChanged:' in manager
      and 'cancelDictation()' in manager
      and 'onActiveChanged:' in manager
      and 'if (!active)' in manager,
      "Abandon recording on section change, menu collapse or close")
check('root.dictationMode = root.mode' in manager
      and 'startedMode !== root.mode' in manager
      and 'root.voiceAreaForKey(key)' in manager,
      "Prevent a late transcript from entering a different section or field")
check('onTextChanged: managerArea.edited()' in manager
      and 'textFormat: TextEdit.PlainText' in manager
      and 'const result = DictationTextPolicy.appendTranscription(' in manager,
      "Dictation must preserve and extend current plain text")
check('Quickshell.shellPath("scripts/hospital-reception-stt.sh")' in voice
      and 'Quickshell.shellPath("scripts/hospital-voice-record.py")' in voice
      and 'transcriptionReady(' in voice,
      "Reuse proven local Whisper and PipeWire backend")
check('submitted:false' in policy
      and 'saved:false' in policy
      and 'launched:false' in policy,
      "Speech transcription grants no execution or data-write authority")
for forbidden in ('exec(', 'session-attach', 'session-create', 'room-bind',
                  'gh auth', 'OPENAI_API_KEY', 'fetch('):
    check(forbidden not in policy,
          "Text merge policy must never invoke API or commands: "+forbidden)
if issues:
    print("HOSPITAL SURGERY MULTILINE DICTATION // FAIL")
    for issue in issues: print(" - "+issue)
    raise SystemExit(1)
print("HOSPITAL SURGERY MULTILINE DICTATION // PASS // five text editors, local mic, no submit")
