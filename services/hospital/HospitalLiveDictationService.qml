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
    // Only HospitalW may opt into the operator-approved one-chunk trial.
    // The standalone engine remains held unless an owning host enables it.
    property bool pilotOneChunk: false
    // Off by default: only the owning Hospital menu opts into a bounded
    // multi-chunk trial, never unguarded continuous transcription.
    property int pilotLiveChunks: 0
    // Optional, fail-closed private Unix socket model reuse. No network port.
    // HospitalW opts in; old Quickshell and CLI installs retain fallback.
    property bool preferPersistentModel: false
    // Optional pause-aware chunks. Disabled by default for standalone
    // engine, unguarded sessions, and nonpersistent CLI fallback.
    property int speechPauseMs: 0
    // A/B choice is supplied to startRecording() for one session only.
    // Other Hospital microphone clients call startRecording() with no
    // argument, which always retains Standard. No persistent setting.
    property string decoderModeUsed: "STANDARD"
    property string lastError: ""
    property string lastTranscript: ""
    // Short lifecycle code only, never spoken words or audio. A few stage
    // receipts permit post-crash correlation without reproducing speech.
    property string lastStage: "SAFETY_HOLD"
    // Persist the bounded capture reason past RECORDING_COMPLETED.
    // This is a fixed code, not spoken words or transcript content.
    property string captureStopReason: ""
    property bool audioDropped: false
    property bool safetyLimitSoon: false
    // In-memory, non-content performance measures. -1 = not yet measured.
    property int audioReadyMs: -1
    property int modelStartupMs: -1
    property int firstTextMs: -1
    property int lastInferenceMs: -1
    property int peakInferenceMs: -1
    property int peakQueueWaitMs: -1
    readonly property string timingSummary: {
        if (firstTextMs < 0)
            return "";
        const seconds = function(ms) {
            return ms < 0 ? "N/A" : (ms / 1000).toFixed(1) + "s";
        };
        return decoderModeUsed + " // AUDIO " + seconds(audioReadyMs)
            + " // LOAD " + seconds(modelStartupMs)
            + " // FIRST TEXT " + seconds(firstTextMs)
            + " // INFER MAX " + seconds(peakInferenceMs)
            + " // QUEUE MAX " + seconds(peakQueueWaitMs);
    }
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
    signal captureStopped()
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

    function startRecording(requestedDecoderMode) {
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
        const fastRequested = requestedDecoderMode === "FAST"
            && preferPersistentModel && pilotLiveChunks > 0 && !pilotOneChunk;
        const responsiveRequested = requestedDecoderMode === "RESPONSIVE"
            && preferPersistentModel && pilotLiveChunks > 0 && !pilotOneChunk
            && chunkSeconds === 2;
        // Surgery mode never leaks to Reception/Intercom default startRecording().
        decoderModeUsed = responsiveRequested ? "RESPONSIVE PENDING"
            : fastRequested ? "FAST PENDING" : "STANDARD";
        wasCancelled = false;
        doneSeen = false;
        packetCount = 0;
        lastError = "";
        lastTranscript = "";
        lastStage = "REQUESTED";
        captureStopReason = "";
        audioDropped = false;
        safetyLimitSoon = false;
        audioReadyMs = -1;
        modelStartupMs = -1;
        firstTextMs = -1;
        lastInferenceMs = -1;
        peakInferenceMs = -1;
        peakQueueWaitMs = -1;
        recordingStartedAt = Date.now();
        recordingElapsedSeconds = 0;
        voiceState = "recording";
        const command = ["python3", scriptPath, whisperHelper,
            "--chunk-seconds", String(Math.max(2, Math.min(4, chunkSeconds))),
            "--first-chunk-ms", String(Math.max(1000,
                Math.min(chunkSeconds * 1000, firstChunkMs)))];
        if (pilotOneChunk)
            command.push("--pilot-one-chunk");
        else if (pilotLiveChunks > 0)
            command.push("--pilot-live-chunks", String(Math.max(1, Math.min(8, pilotLiveChunks))));
        if (preferPersistentModel && pilotLiveChunks > 0) {
            command.push("--prefer-persistent");
            if (fastRequested)
                command.push("--decoder-trial", "fast");
            if (responsiveRequested)
                command.push("--responsive-partial-trial");
            if (speechPauseMs > 0)
                command.push("--speech-pause-ms",
                    String(Math.max(400, Math.min(650, speechPauseMs))));
        }
        if (vadActive) {
            command.push("--vad", "--threshold", String(vadSpeechThreshold),
                "--silence-ms", String(vadSilenceMs),
                "--min-speech-ms", String(vadMinimumSpeechMs));
        }
        liveProcess.exec(command);
        clock.restart();
        if (pilotOneChunk || pilotLiveChunks > 0)
            pilotWatchdog.restart();
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
        pilotWatchdog.stop();
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
        if (data.kind === "timing") {
            // Only bounded integer timings in named slots. No transcript,
            // raw timestamp, device name or network address is accepted.
            const metric = String(data.detail || "");
            const ms = data.ms;
            if (!/^(AUDIO_READY|MODEL_STARTUP|QUEUE_WAIT|INFERENCE|FIRST_TEXT)$/.test(metric)
                    || typeof ms !== "number" || !Number.isInteger(ms)
                    || ms < 0 || ms > 45000)
                return;
            if (metric === "AUDIO_READY")
                audioReadyMs = ms;
            else if (metric === "MODEL_STARTUP")
                modelStartupMs = ms;
            else if (metric === "FIRST_TEXT")
                firstTextMs = ms;
            else if (metric === "QUEUE_WAIT")
                peakQueueWaitMs = Math.max(peakQueueWaitMs, ms);
            else if (metric === "INFERENCE") {
                lastInferenceMs = ms;
                peakInferenceMs = Math.max(peakInferenceMs, ms);
            }
            // Retain one bounded numeric receipt per event in local logs,
            // never the speaker's text. Matches existing stage logging.
            console.warn("HOSPITAL_VOICE_TIMING // " + metric + " // " + ms + "ms");
            return;
        }
        if (data.kind === "stage") {
            // Python emits fixed low-cardinality lifecycle codes. The
            // allowlist prevents untrusted child output reaching the journal.
            const code = String(data.detail || "");
            if (!/^(RECORDER_STARTED|FIRST_AUDIO_QUEUED|FIRST_MODEL_STARTED|FIRST_MODEL_ENDED|FIRST_TEXT_READY|MODEL_TIMEOUT|MODEL_FAILURE|MODEL_BACKPRESSURE|CAPTURE_STOPPED|CAPTURE_LIMIT_NEAR|CAPTURE_CHUNK_LIMIT|CAPTURE_DURATION_LIMIT|CAPTURE_SILENCE_LIMIT|CAPTURE_SOURCE_ENDED|CAPTURE_USER_STOP|MODEL_EARLY_START|MODEL_SESSION_STARTING|MODEL_SESSION_READY|MODEL_SESSION_UNAVAILABLE|DECODER_FAST_ACTIVE|DECODER_FAST_FALLBACK|RESPONSIVE_TRIAL_ACTIVE|RESPONSIVE_TRIAL_FALLBACK|RESPONSIVE_CHUNK_READY|RESPONSIVE_CATCHUP_CHUNK|PAUSE_CHUNK_READY|SILENT_OVERLAP_SKIPPED|RECORDING_COMPLETED)$/.test(code))
                return;
            if (lastStage !== code) {
                lastStage = code;
                console.warn("HOSPITAL_VOICE_STAGE // " + code);
            }
            if (code === "DECODER_FAST_ACTIVE")
                decoderModeUsed = "FAST";
            if (code === "DECODER_FAST_FALLBACK")
                decoderModeUsed = "STANDARD FALLBACK";
            if (code === "RESPONSIVE_TRIAL_ACTIVE")
                decoderModeUsed = "RESPONSIVE";
            if (code === "RESPONSIVE_TRIAL_FALLBACK")
                decoderModeUsed = "STANDARD FALLBACK";
            if (code === "MODEL_BACKPRESSURE")
                audioDropped = true;
            if (code === "CAPTURE_LIMIT_NEAR")
                safetyLimitSoon = true;
            if (/^CAPTURE_(CHUNK_LIMIT|DURATION_LIMIT|SILENCE_LIMIT|SOURCE_ENDED|USER_STOP)$/.test(code))
                captureStopReason = code;
            if (code === "CAPTURE_STOPPED" && recording) {
                // Auto-ended capture still has at most one guarded model
                // processing queued chunks. Do not imply mic remains open.
                voiceState = "transcribing";
                clock.stop();
                captureStopped();
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
        id: pilotWatchdog
        interval: root.pilotLiveChunks > 0 ? 45000 : 20000
        repeat: false
        onTriggered: {
            if (root.busy) {
                root.lastError = "LIVE MICROPHONE PILOT TIME LIMIT // CANCELLED";
                root.cancel();
                root.voiceError(root.lastError);
            }
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
            pilotWatchdog.stop();
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
