#!/usr/bin/env python3
"""Surgery input/header/worker colors + genuine incremental local dictation."""
from pathlib import Path
root = Path(__file__).resolve().parents[2]
manager = (root / "widgets/HospitalWorkforceManagerView.qml").read_text()
host = (root / "widgets/HospitalW.qml").read_text()
live = (root / "services/hospital/HospitalLiveDictationService.qml").read_text()
script = (root / "scripts/hospital-live-dictation.py").read_text()
session = (root / "scripts/hospital_whisper_session.py").read_text()
reception_voice = (root / "services/hospital/HospitalSpeechInputService.qml").read_text()
sandbox = (root / "scripts/hospital-whisper-sandbox.py").read_text()
stt = (root / "scripts/hospital-reception-stt.sh").read_text()
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
      "Mic preserves open-state yellow fill and magenta active styling")
check('readonly property bool stopInProgress: voiceActive' in manager
      and 'root.speechInputService.stopping' in manager
      and 'root.speechInputService.transcribing' in manager
      and manager.count('managerArea.stopInProgress ? Colors.red') >= 3
      and 'spread: managerArea.stopInProgress ? 5 : 4' in manager
      and 'STOPPING // FINALIZING DICTATION // NO SUBMISSION' in manager
      and 'MIC CLOSED // TRANSCRIBING // NO SUBMISSION' in manager,
      "Manual STOP and auto-stop show a yellow-red finishing state until child exit")
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
check('liveEngine.vadActive = vadActive' in frontdesk
      and frontdesk.count('liveEngine.vadActive = false') >= 3,
      "Front-desk VAD applies only to its own capture, not the next Manage job")
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

check('property bool safetyHold: true' in live
      and 'if (safetyHold)' in live
      and 'VOICE SAFETY HOLD' in live
      and 'svc.lastError || "MIC UNAVAILABLE' in manager,
      "Standalone microphones remain held unless owning Hospital host opts in")
check('MODEL_GUARD = Path(__file__).with_name' in script
      and 'str(MODEL_GUARD)' in script
      and 'os.killpg(process.pid, signal.SIGKILL)' in script
      and 'preexec_fn=' in script,
      "Live recognizer always uses external child guard and group timeout")
check('MAX_VIRTUAL_BYTES = 3 * 1024 * 1024 * 1024' in sandbox
      and 'MAX_CPU_SECONDS = 12' in sandbox
      and 'MAX_CORES = 2' in sandbox
      and 'os.sched_setaffinity' in sandbox
      and 'resource.RLIMIT_AS' in sandbox
      and 'resource.RLIMIT_CPU' in sandbox
      and 'resource.RLIMIT_CORE' in sandbox
      and 'POST_APOLLO_STT_SAFE_MODE' in sandbox,
      "Model CPU, memory, core dumps and CPU affinity are constrained")
check('safe_args=(-ng -t 2)' in stt
      and 'POST_APOLLO_STT_SAFE_MODE' in stt
      and 'exec "$backend" "${safe_args[@]}"' in stt,
      "Whisper disables GPU and caps threads only inside guarded live mode")

check('property string lastStage: "SAFETY_HOLD"' in live
      and 'if (safetyHold)' in live
      and 'data.kind === "stage"' in live
      and 'HOSPITAL_VOICE_STAGE // ' in live
      and 'FIRST_MODEL_STARTED' in live
      and 'MODEL_TIMEOUT' in live
      and 'console.warn("HOSPITAL_VOICE_STAGE // " + code)' in live,
      "Stage-only lifecycle diagnostics are allowlisted, with the mic still held")
check('send("stage", detail="RECORDER_STARTED")' in script
      and 'send("stage", detail="FIRST_AUDIO_QUEUED")' in script
      and 'send("stage", detail="FIRST_MODEL_STARTED")' in script
      and 'send("stage", detail="FIRST_MODEL_ENDED")' in script
      and 'send("stage", detail="FIRST_TEXT_READY")' in script
      and '"MODEL_TIMEOUT" if isinstance(error, subprocess.TimeoutExpired)' in script
      and 'send("stage", detail="RECORDING_COMPLETED")' in script,
      "The Python recorder emits bounded non-content milestones around first inference")

check('property bool safetyHold: true' in live
      and 'safetyHold: false' in host
      and 'pilotOneChunk: false' in host
      and 'pilotLiveChunks: 6' in host
      and 'property bool pilotLiveChunks' not in live
      and 'property int pilotLiveChunks: 0' in live
      and 'command.push("--pilot-live-chunks"' in live
      and 'pilotWatchdog.restart()' in live
      and 'id: pilotWatchdog' in live
      and 'interval: root.pilotLiveChunks > 0 ? 45000 : 20000' in live,
      "Bounded incremental mic is opt-in only through HospitalW")
check('parser.add_argument("--pilot-one-chunk"' in script
      and 'parser.add_argument("--pilot-live-chunks"' in script
      and 'pilot_one_chunk=args.pilot_one_chunk' in script
      and 'pilot_live_chunks=args.pilot_live_chunks' in script
      and 'live_chunk_ceiling = max(0, min(8, int(pilot_live_chunks)))' in script
      and 'if live_chunk_ceiling and accepted_chunks >= live_chunk_ceiling:' in script
      and 'accepted_chunks < live_chunk_ceiling' in script
      and 'not pilot_one_chunk' in script,
      "Live trial limits model launches and no tail inference exceeds budget")
check('send("stage", detail="CAPTURE_STOPPED")' in script
      and 'send("stage", detail="MODEL_BACKPRESSURE")' in script
      and 'signal captureStopped()' in live
      and 'captureStopped();' in live
      and 'function onCaptureStopped()' in
          (root / "services/hospital/HospitalSpeechInputService.qml").read_text()
      and 'voiceState = "transcribing";' in live,
      "Auto-closed mic is visible as processing while buffered partials continue")

# Quality backend is opt-in from HospitalW, private and child-resource-limited.
session = (root / "scripts/hospital_whisper_session.py").read_text()
check('preferPersistentModel: true' in host
      and 'property bool preferPersistentModel: false' in live
      and 'command.push("--prefer-persistent")' in live
      and 'MODEL_SESSION_READY' in live
      and 'MODEL_SESSION_UNAVAILABLE' in live
      and 'prefer_persistent=args.prefer_persistent' in script,
      "Persistent session is optional, with stage-only availability reporting")
check('socket.AF_UNIX' in session
      and 'MAX_RESPONSE_BYTES = 65536' in session
      and 'start_new_session=True' in session
      and 'MODEL_GUARD), "--session"' in session
      and 'MAX_SESSION_CPU_SECONDS = 48' in sandbox
      and 'MAX_VIRTUAL_BYTES = 3 * 1024 * 1024 * 1024' in sandbox
      and 'exec "$server" -m "$model" --host "$socket_path"' in stt
      and '-ng -t 2 -p 1' in stt,
      "One private local CPU-only guarded model is reused, never a TCP listener")
check('OVERLAP_BYTES = RATE * FRAME_BYTES * 3 // 4' in script
      and 'trim_repeated_prefix(' in script
      and 'overlap = previous_pcm_tail' in script
      and 'session.transcribe(overlap + chunk,' in script
      and 'prompt=previous_text[-160:]' in script
      and 'phrase = transcribe_chunk(stt_helper, chunk' in script,
      "Bounded overlapping windows and de-duplication preserve guarded CLI fallback")

check('help_text" == *"--no-gpu"*' in stt
      and 'help_text" == *"--no-context"*' not in stt
      and ' -ng -t 2 -p 1 -l en -nt' in stt
      and ' -nt -nc' not in stt
      and 'private_server_compatible || exit 3' in stt,
      "Private whisper-server launch accepts documented upstream flags, never unsupported -nc")

check('capture_reason = ["CAPTURE_SOURCE_ENDED"]' in script
      and 'capture_reason[0] = "CAPTURE_USER_STOP"' in script
      and 'capture_reason[0] = "CAPTURE_CHUNK_LIMIT"' in script
      and 'send("stage", detail="CAPTURE_LIMIT_NEAR")' in script
      and 'send("stage", detail=capture_reason[0])' in script
      and 'send("stage", detail="CAPTURE_STOPPED")' in script,
      "Fixed non-content capture stop reasons distinguish user STOP from safety limit")
check('property string captureStopReason: ""' in live
      and 'property bool audioDropped: false' in live
      and 'property bool safetyLimitSoon: false' in live
      and 'captureStopReason = code;' in live
      and 'audioDropped = true;' in live
      and 'safetyLimitSoon = true;' in live
      and 'CAPTURE_CHUNK_LIMIT' in live,
      "Stage-only reasons latch in the held voice owner until next recording")
check('SAFETY AUTO-STOP // FINISHING LAST CHUNK' in manager
      and 'SAFETY STOP // CHUNK LIMIT // TAP MIC TO CONTINUE' in manager
      and 'AUDIO SKIPPED // MODEL TOO SLOW // REVIEW MISSING WORDS' in manager
      and 'SAFETY LIMIT SOON // FINISH PHRASE' in manager,
      "Manage surfaces early cutoff and dropped audio, never silent truncation")

check('def timing_packet(metric: str, milliseconds: int)' in script
      and 'TIMING_FIELDS = frozenset(' in script
      and '"AUDIO_READY", "MODEL_STARTUP", "QUEUE_WAIT"' in script
      and '"INFERENCE", "FIRST_TEXT"' in script
      and 'clips.put((raw, time.monotonic()), timeout=0.1)' in script
      and 'send_timing("AUDIO_READY", started_at)' in script
      and 'send_timing("QUEUE_WAIT", enqueued_at)' in script
      and 'send_timing("MODEL_STARTUP", model_loading_at)' in script
      and 'send_timing("INFERENCE", decoding_at)' in script
      and 'send_timing("FIRST_TEXT", started_at)' in script,
      "Capture/queue/model/decode timings are fixed-code integer receipts only")
check('property int firstTextMs: -1' in live
      and 'property int peakInferenceMs: -1' in live
      and 'property int peakQueueWaitMs: -1' in live
      and 'if (data.kind === "timing")' in live
      and 'Number.isInteger(ms)' in live
      and 'ms > 45000' in live
      and 'console.warn("HOSPITAL_VOICE_TIMING // " + metric' in live
      and 'root.speechInputService.timingSummary' in manager,
      "Hospital validates bounded timing and shows summary after normal dictation")

check('WARMUP_MIN_BYTES = RATE * FRAME_BYTES * 3 // 10' in script
      and 'model_warmup_requested = threading.Event()' in script
      and 'if (prefer_persistent and pilot_live_chunks > 0' in script
      and 'and is_speech(bytes(pending))' in script
      and 'model_warmup_requested.set()' in script
      and 'if model_warmup_requested.is_set() and not attempted_session:' in script
      and 'start_persistent_once(early=True)' in script
      and 'MODEL_EARLY_START' in live,
      "One guarded persistent model can preload only after speech, before first chunk")
check('clips = queue.Queue(maxsize=MAX_QUEUE)' in script
      and 'MAX_QUEUE = 2' in script
      and 'pilot_live_chunks: int = 0, prefer_persistent: bool = False' in script
      and 'pilotOneChunk: false' in host
      and 'pilotLiveChunks: 6' in host
      and 'property bool safetyHold: true' in live
      and 'interval: root.pilotLiveChunks > 0 ? 45000 : 20000' in live,
      "Startup overlap changes no CPU/RAM caps, queue depth, model count or watchdog")

check('PAUSE_MIN_BYTES = RATE * FRAME_BYTES * 6 // 5' in script
      and 'def quiet_pcm_frame(pcm: bytes' in script
      and 'persistent_model_ready = threading.Event()' in script
      and 'persistent_model_ready.set()' in script
      and 'recognition_idle = threading.Event()' in script
      and 'recognition_idle.is_set()' in script
      and 'clips.empty()' in script
      and 'recognition_idle.clear()' in script
      and 'recognition_idle.set()' in script
      and 'quiet_run_ms >= pause_gap_ms' in script
      and 'not full_chunk and first_chunk_sent' in script
      and 'speech_pause_ms: int = 0' in script
      and 'send("stage", detail="PAUSE_CHUNK_READY")' in script,
      "Only already-loaded persistent Whisper uses short natural pause chunks")
check('property int speechPauseMs: 0' in live
      and 'speechPauseMs: 450' in host
      and 'command.push("--speech-pause-ms"' in live
      and 'PAUSE_CHUNK_READY' in live
      and 'if (preferPersistentModel && pilotLiveChunks > 0)' in live
      and 'pilotLiveChunks: 6' in host
      and 'chunkSeconds: 2' in host
      and 'firstChunkMs: 1400' in host,
      "Pause-aware partials opt in only from guarded Hospital owner, max cadence unchanged")

check('def clear_pause_at_end(pcm: bytes' in script
      and 'threshold: float = 350.0' in script
      and 'quiet_pcm_frame(ending[pos:pos + frame_bytes], threshold)' in script
      and 'previous_chunk_ended_quietly = False' in script
      and 'if (speech_pause_ms > 0 and previous_chunk_ended_quietly' in script
      and 'overlap = b""' in script
      and 'send("stage", detail="SILENT_OVERLAP_SKIPPED")' in script
      and 'previous_chunk_ended_quietly = (' in script
      and 'speech_pause_ms > 0 and clear_pause_at_end(chunk)' in script
      and 'prompt=previous_text[-160:]' in script
      and 'OVERLAP_BYTES = RATE * FRAME_BYTES * 3 // 4' in script,
      "Overlap removed only after sustained strict quiet, never during continuous speech")
check('SILENT_OVERLAP_SKIPPED' in live
      and 'speechPauseMs: 450' in host
      and 'property int speechPauseMs: 0' in live
      and 'pilotLiveChunks: 6' in host
      and 'MAX_QUEUE = 2' in script,
      "Silence-aware compute saving inherits guarded pause opt-in and CPU limits")

check('DECODER_MODES = frozenset(("STANDARD", "FAST"))' in session
      and 'if decoder_mode == "FAST":' in session
      and 'fields.append(("best_of", "1"))' in session
      and 'decoder_mode: str = "STANDARD"' in session
      and 'if decoder_mode not in DECODER_MODES:' in session,
      "Standard retains former request; Fast explicitly selects one greedy candidate")
check('decoder_trial: str = "standard"' in script
      and 'parser.add_argument("--decoder-trial", choices=("standard", "fast")' in script
      and 'fast_trial = (decoder_trial == "fast" and prefer_persistent' in script
      and 'and pilot_live_chunks > 0 and not pilot_one_chunk)' in script
      and 'decoder_mode=("FAST" if fast_trial' in script
      and 'send("stage", detail="DECODER_FAST_ACTIVE")' in script
      and 'send("stage", detail="DECODER_FAST_FALLBACK")' in script,
      "Fast decoder only in bounded persistent AF_UNIX session; CLI fallback is truthful")
check('function startRecording(requestedDecoderMode)' in live
      and 'requestedDecoderMode === "FAST"' in live
      and 'decoderModeUsed = fastRequested ? "FAST PENDING" : "STANDARD"' in live
      and 'command.push("--decoder-trial", "fast")' in live
      and 'DECODER_FAST_ACTIVE|DECODER_FAST_FALLBACK' in live
      and 'return decoderModeUsed + " // AUDIO "' in live
      and 'liveEngine.startRecording()' in reception_voice,
      "One-shot A/B mode, Reception and Intercom continue Standard by default")
check('property string decoderMode: "STANDARD"' in manager
      and 'function selectDecoderMode(value)' in manager
      and 'svc.startRecording(root.decoderMode)' in manager
      and 'label: "VOICE // STANDARD"' in manager
      and 'label: "VOICE // FAST TRIAL"' in manager
      and '!root.speechInputService.busy && !root.otherVoiceBusy' in manager
      and 'root.mode === "SETUP" || root.mode === "JOB"' in manager
      and 'pilotLiveChunks: 6' in host
      and 'MAX_QUEUE = 2' in script,
      "Surgery opt-in A/B UI is locked while busy; original voice safety limits remain")

# One guarded responsive early-flush trial is separate from the existing
# fast decoder choice. No extra model jobs, shorter total capture, or
# cross-surface reuse of the Surgery-only experiment is permitted.
check('label: "VOICE // RESPONSIVE TRIAL"' in manager
      and 'root.selectDecoderMode("RESPONSIVE")' in manager
      and 'value !== "RESPONSIVE"' in manager
      and 'responsiveRequested = requestedDecoderMode === "RESPONSIVE"' in live
      and 'command.push("--responsive-partial-trial")' in live
      and 'RESPONSIVE_TRIAL_ACTIVE|RESPONSIVE_TRIAL_FALLBACK' in live
      and 'RESPONSIVE_CHUNK_READY|RESPONSIVE_CATCHUP_CHUNK' in live
      and 'decoderModeUsed = "RESPONSIVE"' in live
      and 'responsive_partial_trial: bool = False' in script
      and 'responsive_trial = (responsive_partial_trial' in script
      and 'not responsive_used' in script
      and 'recognition_idle.is_set()' in script
      and 'clips.empty()' in script
      and 'responsive_catchup_bytes = target - PAUSE_MIN_BYTES' in script
      and 'responsive_catchup_bytes = 0' in script
      and 'pilotLiveChunks: 6' in host
      and 'MAX_QUEUE = 2' in script
      and 'liveEngine.startRecording()' in reception_voice,
      "One idle partial rebalances 1.2s + 2.8s without extra jobs or shared mode")

if issues:
    print("HOSPITAL MANAGE LIVE INLINE // FAIL")
    for issue in issues: print(" - " + issue)
    raise SystemExit(1)
print("HOSPITAL MANAGE LIVE INLINE // PASS // inline open mic, live chunks, blank suppression, color grammar")
