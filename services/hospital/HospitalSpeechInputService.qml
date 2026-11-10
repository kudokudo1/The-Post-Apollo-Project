import QtQuick
import Quickshell
import Quickshell.Io

Scope {
    id: root

    property string voiceState: "checking"
    property bool backendReady: false
    // Opt-in for Reception/Intercom; keeps legacy recording as a fallback.
    property bool liveStreaming: false
    // Host-owned single local recorder/recognizer shared with working Manage.
    // No extra nested microphone process or Whisper instance per front desk.
    property var liveEngine: null
    property bool otherVoiceBusy: false
    property string backendStatus: "CHECKING"
    property string lastError: ""
    property string lastTranscript: ""
    property bool submitAfterTranscription: false
    property bool stopRequested: false
    property bool recorderCancelled: false
    property bool transcriberCancelled: false
    property string audioFileName: "hospital-reception-voice.wav"
    property double recordingStartedAt: 0
    property int recordingElapsedSeconds: 0
    property bool vadAvailable: false
    property bool vadEnabled: false
    property string vadStatus: "CHECKING"
    property int vadSpeechThreshold: 600
    property int vadSilenceMs: 2200
    property int vadMinimumSpeechMs: 250
    property int vadMaxSeconds: 90

    readonly property bool recording:
        voiceState === "recording"
    readonly property bool stopping:
        voiceState === "stopping"
    readonly property bool transcribing:
        voiceState === "transcribing"
    readonly property bool busy:
        recording || stopping || transcribing
    readonly property string recordingElapsedLabel: {
        const total = Math.max(0, Number(recordingElapsedSeconds || 0));
        const minutes = Math.floor(total / 60);
        const seconds = total % 60;

        const minuteText =
            minutes < 10
            ? "0" + String(minutes)
            : String(minutes);
        const secondText =
            seconds < 10
            ? "0" + String(seconds)
            : String(seconds);

        return minuteText + ":" + secondText;
    }

    readonly property string audioPath:
        Quickshell.cachePath(audioFileName)
    readonly property string helperPath:
        Quickshell.shellPath("scripts/hospital-reception-stt.sh")
    readonly property string captureHelperPath:
        Quickshell.shellPath("scripts/hospital-voice-record.py")
    readonly property bool vadActive:
        vadEnabled && vadAvailable

    signal transcriptionReady(string text, bool submitRequested)
    signal liveTextReady(string text)
    signal transcriptionFinished(bool submitRequested)
    signal voiceError(string message)

    function compactError(value) {
        const lines =
            String(value || "")
                .split("\n")
                .map(function(line) {
                    return String(line || "").trim();
                })
                .filter(function(line) {
                    return line.length > 0;
                });

        return lines.length > 0
            ? lines[lines.length - 1]
            : "";
    }

    function probe() {
        if (probeProcess.running)
            return false;

        backendStatus = "CHECKING";
        probeProcess.command = [
            "bash",
            "-lc",
            'command -v pw-record >/dev/null 2>&1 && bash "$1" --check',
            "hospital-reception-probe",
            helperPath
        ];
        probeProcess.running = true;
        return true;
    }

    function probeVad() {
        if (vadProbeProcess.running)
            return false;

        vadStatus = "CHECKING";
        vadProbeProcess.command = [
            "bash",
            "-lc",
            'command -v python3 >/dev/null 2>&1 && test -f "$1"',
            "hospital-vad-probe",
            captureHelperPath
        ];
        vadProbeProcess.running = true;
        return true;
    }

    function setVadEnabled(value) {
        const desired = Boolean(value);

        if (desired && !vadAvailable) {
            vadEnabled = false;
            lastError = "VAD UNAVAILABLE // PYTHON3 OR CAPTURE HELPER MISSING";
            voiceError(lastError);
            return false;
        }

        vadEnabled = desired;
        lastError = "";
        return true;
    }

    function startRecording() {
        if (busy)
            return false;
        if (otherVoiceBusy) {
            lastError = "MIC BUSY // ANOTHER HOSPITAL VOICE INPUT IS ACTIVE";
            voiceError(lastError);
            return false;
        }

        if (!backendReady) {
            probe();
            lastError =
                "VOICE INPUT UNAVAILABLE // CHECKING PW-RECORD + WHISPER";
            voiceError(lastError);
            return false;
        }

        lastError = "";
        lastTranscript = "";
        submitAfterTranscription = false;
        stopRequested = false;
        recorderCancelled = false;
        recordingStartedAt = Date.now();
        recordingElapsedSeconds = 0;
        recordingClock.restart();
        voiceState = "recording";

        if (liveStreaming) {
            // No persistent Reception WAV and no stop-before-inference path.
            // The already used Manage helper owns and reaps its PipeWire child.
            if (!liveEngine || !liveEngine.backendReady) {
                if (liveEngine)
                    liveEngine.probe();
                recordingClock.stop();
                voiceState = "idle";
                lastError = "LOCAL LIVE MICROPHONE UNAVAILABLE // CHECK PIPEWIRE AND WHISPER";
                voiceError(lastError);
                return false;
            }
            // The shared Manage worker must use this front-desk VAD policy
            // only for the owning recording; it is reset on finish/cancel.
            liveEngine.vadActive = vadActive;
            liveEngine.vadSpeechThreshold = vadSpeechThreshold;
            liveEngine.vadSilenceMs = vadSilenceMs;
            liveEngine.vadMinimumSpeechMs = vadMinimumSpeechMs;
            if (!liveEngine.startRecording()) {
                recordingClock.stop();
                voiceState = "idle";
                lastError = liveEngine.lastError || "LOCAL LIVE MICROPHONE REFUSED";
                voiceError(lastError);
                return false;
            }
            return true;
        }

        recordProcess.command =
            vadActive
            ? [
                "python3",
                captureHelperPath,
                audioPath,
                "--threshold",
                String(vadSpeechThreshold),
                "--silence-ms",
                String(vadSilenceMs),
                "--min-speech-ms",
                String(vadMinimumSpeechMs),
                "--max-seconds",
                String(vadMaxSeconds)
              ]
            : [
                "bash",
                "-lc",
                [
                    'audio="$1"',
                    'rm -f "$audio"',
                    'exec pw-record --rate=16000 --channels=1 --format=s16 "$audio"'
                ].join("\n"),
                "hospital-reception-record",
                audioPath
              ];
        recordProcess.running = true;
        return true;
    }

    function stopRecording(submitAfter) {
        if (!recording)
            return false;

        submitAfterTranscription = Boolean(submitAfter);
        stopRequested = true;
        recordingClock.stop();
        voiceState = "stopping";
        if (liveStreaming) {
            if (!liveEngine || !liveEngine.stopRecording(false)) {
                voiceState = "recording";
                stopRequested = false;
                submitAfterTranscription = false;
                recordingClock.restart();
                return false;
            }
            return true;
        }
        recordProcess.running = false;
        return true;
    }

    function startTranscription() {
        stopRequested = false;
        voiceState = "transcribing";
        transcriberCancelled = false;
        transcriptionProcess.command = [
            "bash",
            helperPath,
            audioPath
        ];
        transcriptionProcess.running = true;
    }

    function cancel() {
        submitAfterTranscription = false;
        stopRequested = false;
        recordingClock.stop();
        recordingStartedAt = 0;
        recordingElapsedSeconds = 0;

        if (liveStreaming && busy && liveEngine) {
            liveEngine.cancel();
            liveEngine.vadActive = false;
        }

        if (recordProcess.running) {
            recorderCancelled = true;
            recordProcess.running = false;
        }

        if (transcriptionProcess.running) {
            transcriberCancelled = true;
            transcriptionProcess.running = false;
        }

        voiceState = backendReady ? "idle" : "unavailable";
        Quickshell.execDetached(["rm", "-f", audioPath]);
        return true;
    }

    Component.onCompleted: {
        probe();
        probeVad();
    }

    // The live worker has no submission authority. Phrases go straight to
    // the editor; only a separate user SEND/ASK action may dispatch them.
    Connections {
        target: root.liveEngine
        ignoreUnknownSignals: true

        function onLiveTextReady(text) {
            // Only the front desk currently owning the single microphone
            // may forward words. Manage and the other desk never receive them.
            if (!root.liveStreaming || !root.busy)
                return;
            root.lastTranscript = String(text || "");
            root.liveTextReady(text);
        }
        function onLiveFinished() {
            if (!root.liveStreaming || !root.busy)
                return;
            const shouldSubmit = root.submitAfterTranscription;
            root.submitAfterTranscription = false;
            root.stopRequested = false;
            root.recordingClock.stop();
            root.recordingStartedAt = 0;
            root.recordingElapsedSeconds = 0;
            root.voiceState = root.backendReady ? "idle" : "unavailable";
            root.liveEngine.vadActive = false;
            root.transcriptionFinished(shouldSubmit);
        }
        function onVoiceError(message) {
            if (!root.liveStreaming || !root.busy)
                return;
            root.recordingClock.stop();
            root.stopRequested = false;
            root.submitAfterTranscription = false;
            root.voiceState = root.backendReady ? "idle" : "unavailable";
            root.lastError = String(message || "LOCAL LIVE DICTATION FAILED");
            root.liveEngine.vadActive = false;
            root.voiceError(root.lastError);
        }
    }

    Timer {
        id: recordingClock
        interval: 1000
        repeat: true

        onTriggered: {
            if (!root.recording || root.recordingStartedAt <= 0) {
                stop();
                return;
            }

            root.recordingElapsedSeconds =
                Math.max(
                    0,
                    Math.floor(
                        (Date.now() - root.recordingStartedAt)
                        / 1000
                    )
                );
        }
    }

    Process {
        id: vadProbeProcess

        onExited: function(exitCode, exitStatus) {
            root.vadAvailable = exitCode === 0;
            root.vadStatus =
                root.vadAvailable
                ? "READY"
                : "UNAVAILABLE";

            if (!root.vadAvailable)
                root.vadEnabled = false;
        }
    }

    Process {
        id: probeProcess

        stdout: StdioCollector {
            id: probeOut
        }

        stderr: StdioCollector {
            id: probeErr
        }

        onExited: function(exitCode, exitStatus) {
            root.backendReady = exitCode === 0;

            if (root.backendReady) {
                root.backendStatus = "READY";
                root.voiceState = "idle";
                root.lastError = "";
                return;
            }

            const detail =
                root.compactError(probeErr.text);

            root.backendStatus =
                detail || "VOICE BACKEND UNAVAILABLE";
            root.voiceState = "unavailable";
        }
    }

    Process {
        id: recordProcess

        stderr: StdioCollector {
            id: recordErr
        }

        onExited: function(exitCode, exitStatus) {
            if (root.recorderCancelled) {
                root.recorderCancelled = false;
                return;
            }

            if (root.stopRequested) {
                root.startTranscription();
                return;
            }

            const recordDetail =
                String(recordErr.text || "");
            const autoStopped =
                root.vadActive
                && (
                    recordDetail.indexOf("VAD_STOP") >= 0
                    || recordDetail.indexOf("VAD_MAX") >= 0
                   );

            if (root.voiceState === "recording"
                    && autoStopped) {
                root.recordingClock.stop();
                root.startTranscription();
                return;
            }

            if (root.voiceState === "recording") {
                const detail =
                    root.compactError(recordErr.text);

                root.recordingClock.stop();
                root.recordingStartedAt = 0;
                root.recordingElapsedSeconds = 0;
                root.voiceState =
                    root.backendReady
                    ? "idle"
                    : "unavailable";
                root.lastError =
                    "VOICE RECORDING FAILED"
                    + (
                        detail
                        ? " // " + detail
                        : ""
                      );
                root.voiceError(root.lastError);
            }
        }
    }

    Process {
        id: transcriptionProcess

        stdout: StdioCollector {
            id: transcriptionOut
        }

        stderr: StdioCollector {
            id: transcriptionErr
        }

        onExited: function(exitCode, exitStatus) {
            if (root.transcriberCancelled) {
                root.transcriberCancelled = false;
                return;
            }

            const submitRequested =
                root.submitAfterTranscription;
            const transcript =
                String(transcriptionOut.text || "")
                    .replace(/\s+/g, " ")
                    .trim();

            root.submitAfterTranscription = false;
            root.recordingStartedAt = 0;
            root.recordingElapsedSeconds = 0;
            root.voiceState =
                root.backendReady
                ? "idle"
                : "unavailable";
            Quickshell.execDetached(
                ["rm", "-f", root.audioPath]
            );

            if (exitCode !== 0 || !transcript) {
                const detail =
                    root.compactError(
                        transcriptionErr.text
                    );

                root.lastError =
                    exitCode !== 0
                    ? (
                        "VOICE TRANSCRIPTION FAILED"
                        + (
                            detail
                            ? " // " + detail
                            : ""
                          )
                      )
                    : "VOICE TRANSCRIPTION EMPTY";
                root.voiceError(root.lastError);
                return;
            }

            root.lastError = "";
            root.lastTranscript = transcript;
            root.transcriptionReady(
                transcript,
                submitRequested
            );
        }
    }
}
