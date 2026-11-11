import QtQuick
import Quickshell
import Quickshell.Io

// Shared local live dictation engine for Surgery Manage, Reception and Intercom.
// One host-owned recorder; source-level hold remains until crash clearance.
// No form submit, cloud request or durable audio.
Scope {
    id: root
    property string voiceState: "checking"
    property bool backendReady: false
    // Incident hold: operator reported a full PC crash from Surgery Manage
    // live dictation. Do not enable real microphones merely because CI passes.
    // Explicit operator + host verification is required before setting false.
    property bool safetyHold: true
    property string lastError: ""
    property string lastTranscript: ""
    // Short lifecycle code only, never spoken words or audio. A few stage
    // receipts permit post-crash correlation without reproducing speech.
    property string lastStage: "SAFETY_HOLD"
    property int recordingElapsedSeconds: 0
    property double recordingStartedAt: 0
    property bool liveStreaming: true
    // Legacy standalone default; HospitalW sets 2-second chunks for all menus.
    property int chunkSeconds: 4
    property int firstChunkMs: 1400
    property bool vadActive: false
    property int vadSpeechThreshold: 600
    property int vadSilenceMs: 2200
    property int vadMinimumSpeechMs: 250
    property bool wasCancelled: false
    property bool doneSeen: false
    property int packetCount: 0
    property int maxPackets: 30
    readonly property bool recording: voiceState === "recording"
    readonly property bool stopping: voiceState === "stopping"
    readonly property bool transcribing: voiceState === "transcribing"
    readonly property bool busy: recording || stopping || transcribing
    readonly property string recordingElapsedLabel: {
        const duration = Math.max(0, recordingElapsedSeconds);
        const mins = Math.floor(duration / 60);
        const secs = duration % 60;
        return (mins < 10 ? "0" : "") + mins + ":"
            + (secs < 10 ? "0" : "") + secs;
    }
    readonly property string scriptPath:
        Quickshell.shellPath("scripts/hospital-live-dictation.py")
    readonly property string whisperHelper:
        Quickshell.shellPath("scripts/hospital-reception-stt.sh")

    signal liveTextReady(string text)
    signal liveFinished()
    signal voiceError(string message)

    function probe() {
        if (probeProcess.running)
            return false;
        voiceState = "checking";
        probeProcess.exec(["bash", "-lc",
            'command -v pw-record >/dev/null 2>&1 && test -f "$1" && bash "$2" --check',
            "hospital-live-dictation-check", scriptPath, whisperHelper]);
        return true;
    }

    function startRecording() {
        if (safetyHold) {
            lastStage = "SAFETY_HOLD";
            lastError = "VOICE SAFETY HOLD // HOST CRASH NOT YET CLEARED";
            voiceError(lastError);
            return false;
        }
        if (busy || liveProcess.running)
            return false;
        if (!backendReady) {
            lastError = "LOCAL LIVE DICTATION UNAVAILABLE // CHECK PIPEWIRE + WHISPER";
            voiceError(lastError);
            return false;
        }
        wasCancelled = false;
        doneSeen = false;
        packetCount = 0;
        lastError = "";
        lastTranscript = "";
        lastStage = "REQUESTED";
        recordingStartedAt = Date.now();
        recordingElapsedSeconds = 0;
        voiceState = "recording";
        const command = ["python3", scriptPath, whisperHelper,
            "--chunk-seconds", String(Math.max(2, Math.min(4, chunkSeconds))),
            "--first-chunk-ms", String(Math.max(1000,
                Math.min(chunkSeconds * 1000, firstChunkMs)))];
        if (vadActive) {
            command.push("--vad", "--threshold", String(vadSpeechThreshold),
                "--silence-ms", String(vadSilenceMs),
                "--min-speech-ms", String(vadMinimumSpeechMs));
        }
        liveProcess.exec(command);
        clock.restart();
        return true;
    }

    function stopRecording(submitAfter) {
        if (!recording || !liveProcess.running)
            return false;
        // submitAfter intentionally ignored. This is dictation, never action.
        voiceState = "stopping";
        clock.stop();
        liveProcess.write("STOP\n");
        return true;
    }

    function cancel() {
        wasCancelled = true;
        doneSeen = false;
        clock.stop();
        recordingStartedAt = 0;
        recordingElapsedSeconds = 0;
        lastTranscript = "";
        voiceState = backendReady ? "idle" : "unavailable";
        if (liveProcess.running) {
            // Give Python a chance to terminate *both* its PipeWire recorder
            // and the currently running Whisper process before hard teardown.
            liveProcess.write("CANCEL\n");
            cancelWatchdog.restart();
        }
        return true;
    }

    function acceptPacket(line) {
        if (wasCancelled || !busy || line.length > 8192)
            return;
        let data = null;
        try { data = JSON.parse(line); }
        catch (error) { return; }
        if (!data || typeof data.kind !== "string")
            return;
        if (data.kind === "stage") {
            // Python emits fixed low-cardinality lifecycle codes. The
            // allowlist prevents untrusted child output reaching the journal.
            const code = String(data.detail || "");
            if (!/^(RECORDER_STARTED|FIRST_AUDIO_QUEUED|FIRST_MODEL_STARTED|FIRST_MODEL_ENDED|FIRST_TEXT_READY|MODEL_TIMEOUT|MODEL_FAILURE|RECORDING_COMPLETED)$/.test(code))
                return;
            if (lastStage !== code) {
                lastStage = code;
                console.warn("HOSPITAL_VOICE_STAGE // " + code);
            }
            return;
        }
        if (data.kind === "partial") {
            if (typeof data.text !== "string")
                return;
            const sentence = data.text.trim();
            if (!sentence || /^\[\s*(?:BLANK_AUDIO|NO_SPEECH|SILENCE)\s*\]$/i.test(sentence))
                return;
            packetCount++;
            if (packetCount > maxPackets) {
                lastError = "LIVE DICTATION LENGTH LIMIT // STOPPING";
                voiceError(lastError);
                cancel();
                return;
            }
            lastTranscript = sentence;
            liveTextReady(sentence);
        } else if (data.kind === "done") {
            // Keep the microphone busy until the owned child fully exits;
            // otherwise a second click can race against the old process.
            doneSeen = true;
            clock.stop();
            voiceState = "stopping";
        } else if (data.kind === "error") {
            lastError = String(data.detail || "LOCAL DICTATION FAILED").slice(0,160);
            voiceError(lastError);
            cancel();
        }
    }

    Component.onCompleted: probe()

    Timer {
        id: clock
        interval: 1000
        repeat: true
        onTriggered: {
            if (!root.recording) {
                stop();
                return;
            }
            root.recordingElapsedSeconds = Math.max(0,
                Math.floor((Date.now() - root.recordingStartedAt) / 1000));
        }
    }
    Timer {
        id: cancelWatchdog
        interval: 1800
        repeat: false
        onTriggered: {
            // Emergency fallback if a child refuses graceful cancellation.
            if (liveProcess.running)
                liveProcess.running = false;
        }
    }
    Process {
        id: probeProcess
        onExited: function(code, status) {
            root.backendReady = Number(code) === 0;
            if (!root.busy)
                root.voiceState = root.backendReady ? "idle" : "unavailable";
        }
    }
    Process {
        id: liveProcess
        stdinEnabled: true
        stdout: SplitParser {
            onRead: function(data) {
                root.acceptPacket(String(data || ""));
            }
        }
        stderr: StdioCollector {
            // Do not echo raw model/process diagnostics or audio content.
        }
        onExited: function(code, status) {
            cancelWatchdog.stop();
            if (root.wasCancelled)
                return;
            root.recordingStartedAt = 0;
            root.recordingElapsedSeconds = 0;
            root.voiceState = root.backendReady ? "idle" : "unavailable";
            root.clockStop();
            if (root.doneSeen) {
                root.liveFinished();
                return;
            }
            if (!root.doneSeen) {
                root.lastError = Number(code) === 0
                    ? "LIVE DICTATION ENDED WITHOUT FINAL RECEIPT"
                    : "LOCAL LIVE DICTATION STOPPED UNEXPECTEDLY";
                root.voiceError(root.lastError);
            }
        }
    }

    function clockStop() {
        clock.stop();
    }
}
