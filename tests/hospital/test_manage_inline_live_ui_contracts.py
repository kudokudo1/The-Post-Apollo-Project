#!/usr/bin/env python3
"""Surgery input/header/worker colors + genuine incremental local dictation."""
from pathlib import Path
root = Path(__file__).resolve().parents[2]
manager = (root / "widgets/HospitalWorkforceManagerView.qml").read_text()
host = (root / "widgets/HospitalW.qml").read_text()
live = (root / "services/hospital/HospitalLiveDictationService.qml").read_text()
script = (root / "scripts/hospital-live-dictation.py").read_text()
text = (root / "services/hospital/HospitalDictationTextPolicy.js").read_text()
issues = []
def check(ok, label):
    if not ok: issues.append(label)

check('HospitalLiveDictationService {' in host
      and 'id: workforceSpeechInputService' in host
      and host.count('HospitalSpeechInputService {') >= 2,
      "Only Manage uses live stream, Reception and Intercom retain their recorder")
check('stdout: SplitParser {' in live
      and 'onRead: function(data)' in live
      and 'signal liveTextReady(string text)' in live
      and 'signal liveFinished()' in live,
      "Must receive incremental lines before the recording process exits")
check('stdinEnabled: true' in live
      and 'liveProcess.write("STOP\\n")' in live
      and 'scriptPath, whisperHelper' in live
      and 'liveProcess.running = false' in live,
      "Own and stop the local Python/PipeWire child without UI submission")
check('pw-record' in script and 'whisper-cli' in script
      and 'subprocess.Popen(' in script
      and 'subprocess.run(command' in script
      and 'print(packet(kind' in script,
      "A real local stream and short Whisper chunks, not a fake animation")
check('"partial"' in script and '"done"' in script
      and 'CHUNK_SECONDS = 4' in script
      and 'MAX_QUEUE = 8' in script
      and 'MAX_SECONDS = 90' in script,
      "Partial/final protocol has bounded audio, inference and queue")
check('BLANK_AUDIO' in script and 'if not is_speech(raw):' not in script
      and 'not is_speech(raw)' in script,
      "Silence and blank-audio placeholders are discarded")
check('BLANK_AUDIO' in text
      and 'if (!spoken' in text,
      "Defensive placeholder filtering before text insertion")
check('onLiveTextReady(text)' in manager
      and 'root.acceptLivePhrase(text)' in manager
      and 'onLiveFinished()' in manager
      and 'root.finishLiveDictation()' in manager,
      "Live phrases go directly into selected editor, no separate submit")
check('root.dictationOriginalText = field.value' in manager
      and 'field.value = root.dictationOriginalText' in manager
      and 'readOnly: managerArea.voiceActive' in manager,
      "CANCEL reverts only current voice session and locks edit during dictation")
check('function acceptLivePhrase(text)' in manager
      and 'DictationTextPolicy.appendTranscription(' in manager
      and 'voiceMaxLength' in manager
      and 'root.speechInputService.stopRecording(false)' in manager,
      "Guard live text length and never auto submit")
check('id: editorFrame' in manager
      and 'anchors.right: parent.right' in manager
      and 'anchors.top: parent.top' in manager
      and 'id: micAction' in manager
      and 'label: "CANCEL"' in manager,
      "MIC/STOP and CANCEL live INSIDE each prompt rectangle")
check('managerArea.voiceActive || micMouse.containsMouse' in manager
      and '? Colors.yellow : Colors.dark' in manager
      and '? Colors.magenta : Colors.omnitrix' in manager,
      "Mic uses open-state yellow fill, magenta border/icon/glow")
check('component ManagerCaption: Row {' in manager
      and '.replace(/\\s*\\/+\\s*/g, " // ")' in manager
      and 'font.pixelSize: 10' in manager
      and 'color: modelData.indexOf("/") >= 0 ? Colors.white : Colors.blue' in manager
      and 'color: Colors.cyan' in manager,
      "Slightly larger blue headers, white double slashes, shared cyan glow")
check('height: editHeight + 18' in manager
      and 'height: 12' in manager,
      "Keep fixed header height and no expanded gap between prompt boxes")
check('id: workerNameLabel' in manager
      and 'color: Colors.orange' in manager
      and 'id: workerSepOne' in manager
      and 'id: workerSepTwo' in manager
      and 'text: " // "' in manager
      and 'color: Colors.white' in manager
      and 'color: Colors.orange' in manager,
      "Worker names orange, white slash delimiters with orange glow")
for forbidden in ('OPENAI_API_KEY', 'session-create', 'room-bind',
                  'git checkout', 'git push', 'fetch(', 'requests.post('):
    check(forbidden not in script + live, "Voice process cannot launch or mutate: "+forbidden)
if issues:
    print("HOSPITAL MANAGE LIVE INLINE // FAIL")
    for issue in issues: print(" - " + issue)
    raise SystemExit(1)
print("HOSPITAL MANAGE LIVE INLINE // PASS // inline open mic, live chunks, blank suppression, color grammar")
