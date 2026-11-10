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
      "All three menus use a single host-owned live dictation engine")
check('stdout: SplitParser {' in live
      and 'onRead: function(data)' in live
      and 'signal liveTextReady(string text)' in live
      and 'signal liveFinished()' in live,
      "Must receive incremental lines before the recording process exits")
check('stdinEnabled: true' in live
      and 'liveProcess.write("STOP\\n")' in live
      and 'scriptPath, whisperHelper' in live
      and 'liveProcess.write("CANCEL\\n")' in live
      and 'cancelWatchdog.restart()' in live
      and 'liveProcess.running = false' in live,
      "Own and stop the local Python/PipeWire child without UI submission")
check('pw-record' in script and 'whisper-cli' in script
      and 'subprocess.Popen(' in script
      and 'start_new_session=True' in script
      and 'on_start=model_started' in script
      and 'print(packet(kind' in script,
      "A real local stream and short Whisper chunks, not a fake animation")
check('"partial"' in script and '"done"' in script
      and 'CHUNK_SECONDS = 4' in script
      and 'MAX_QUEUE = 2' in script
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
      and 'anchors.verticalCenter: parent.verticalCenter' in manager
      and 'anchors.rightMargin: 7' in manager
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
      and 'id: staffWorkerName' in manager
      and 'id: staffSepOne' in manager
      and 'id: staffSepTwo' in manager
      and 'text: " // "' in manager
      and 'color: Colors.white' in manager
      and 'color: Colors.orange' in manager,
      "Worker names orange, white slash delimiters with orange glow")
for forbidden in ('OPENAI_API_KEY', 'session-create', 'room-bind',
                  'git checkout', 'git push', 'fetch(', 'requests.post('):
    check(forbidden not in script + live, "Voice process cannot launch or mutate: "+forbidden)
# Cross-surface repair: preserve a single live local speech transport while
# keeping explicit SEND/ASK actions separate from streaming text insertion.
frontdesk = (root / "services/hospital/HospitalSpeechInputService.qml").read_text()
reception = (root / "widgets/HospitalReceptionistView.qml").read_text()
intercom = (root / "widgets/HospitalIntercomMenu.qml").read_text()
check(host.count('liveStreaming: true') == 2
      and 'otherVoiceBusy: intercomSpeechInputService.busy' in host
      and 'otherVoiceBusy: speechInputService.busy' in host,
      "Reception and Intercom opt in to live speech with mutual microphone exclusion")
check('property var liveEngine: null' in frontdesk
      and 'liveEngine.startRecording()' in frontdesk
      and 'liveEngine.stopRecording(false)' in frontdesk
      and 'target: root.liveEngine' in frontdesk
      and 'liveEngine: workforceSpeechInputService' in host
      and host.count('liveEngine: workforceSpeechInputService') == 2
      and 'signal liveTextReady(string text)' in frontdesk
      and 'signal transcriptionFinished(bool submitRequested)' in frontdesk,
      "Front desks forward live text from the same Manage worker, no nested mic")
check('maxPackets: 48' in host and 'chunkSeconds: 2' in host
      and 'property int maxPackets: 30' in live
      and 'packetCount > maxPackets' in live,
      "Shorter 2-second chunks retain the 90-second front-desk bound")
check('onLiveTextReady(text)' in reception
      and 'root.acceptVoiceTranscript(text, false);' in reception
      and 'onTranscriptionFinished(submitRequested)' in reception
      and 'root.submitReceptionInput();' in reception
      and 'onVisibleChanged:' in reception,
      "Reception shows phrases live, does not auto-send and cancels on hide")
check('onLiveTextReady(text)' in intercom
      and 'root.acceptVoiceTranscript(text, false);' in intercom
      and 'onTranscriptionFinished(submitRequested)' in intercom
      and 'root.sendCurrent();' in intercom,
      "Intercom shows phrases before STOP without silently dispatching")
check('color: Colors.magenta' in intercom
      and 'cursorDelegate: Rectangle {' in intercom
      and 'color: Colors.orange' in intercom
      and 'rightMargin: 6' in intercom
      and 'rightMargin: 4' in intercom,
      "Intercom has magenta operator text/orange cursor and separated controls")
mic_section = manager.split('id: micAction', 1)[-1].split('id: cancelAction', 1)[0]
cancel_section = manager.split('id: cancelAction', 1)[-1].split('label: "CANCEL"', 1)[0]
check('anchors.rightMargin: 7' in mic_section
      and 'anchors.verticalCenter: parent.verticalCenter' in mic_section
      and 'anchors.verticalCenter: parent.verticalCenter' in cancel_section,
      "Embedded Manager microphone/CANCEL controls remain vertically centered, shifted 5px left")
check('parser.add_argument("--vad"' in script
      and 'parser.add_argument("--chunk-seconds"' in script
      and 'if vad:' in script and 'heard_speech' in script,
      "Local stream retains optional silence auto-stop and configurable 2-second chunks")

check('firstChunkMs: 1400' in host
      and 'first_chunk_ms' in script
      and 'first_target' in script
      and 'first_chunk_sent = first_chunk_sent or sent' in script,
      "All Hospital microphones queue the opening speech segment earlier")
check('def model_started(process)' in script
      and 'def halt_model()' in script
      and 'os.killpg(current.pid, signal.SIGTERM)' in script
      and 'if command == "CANCEL":' in script
      and 'tail += bytes(minimum - len(tail))' in script,
      "Model teardown and subsecond speech tail remain bounded under cancellation")
check('voiceSelected: root.speechInputService.busy' in reception
      and 'color: micButton.voiceSelected ? Colors.yellow' in reception
      and 'color: micButton.voiceSelected ? Colors.magenta' in reception
      and 'voiceSelected: root.speechInputService.busy' in intercom
      and 'color: micButton.voiceSelected ? Colors.yellow' in intercom
      and 'color: micButton.voiceSelected ? Colors.magenta' in intercom,
      "Front desk microphones use canonical active/open selection colors")

if issues:
    print("HOSPITAL MANAGE LIVE INLINE // FAIL")
    for issue in issues: print(" - " + issue)
    raise SystemExit(1)
print("HOSPITAL MANAGE LIVE INLINE // PASS // inline open mic, live chunks, blank suppression, color grammar")
