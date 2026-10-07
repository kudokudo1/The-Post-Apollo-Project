import QtQuick
import Quickshell
import Quickshell.Io

Scope {
    id: root

    property string voiceState: "checking"
    property bool backendReady: false
    property string backendStatus: "CHECKING"
    property string lastError: ""
    property string lastTranscript: ""
    property bool submitAfterTranscription: false
    property bool stopRequested: false
    property bool recorderCancelled: false
    property bool transcriberCancelled: false
    property string audioFileName: "hospital-reception-voice.wav"

    readonly property bool recording:
        voiceState === "recording"
    readonly property bool stopping:
        voiceState === "stopping"
    readonly property bool transcribing:
        voiceState === "transcribing"
    readonly property bool busy:
        recording || stopping || transcribing

    readonly property string audioPath:
        Quickshell.cachePath(audioFileName)
    readonly property string helperPath:
        Quickshell.shellPath("scripts/hospital-reception-stt.sh")

    signal transcriptionReady(string text, bool submitRequested)
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

    function startRecording() {
        if (busy)
            return false;

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
        voiceState = "recording";

        recordProcess.command = [
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
        voiceState = "stopping";
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

    Component.onCompleted: probe()

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

            if (root.voiceState === "recording") {
                const detail =
                    root.compactError(recordErr.text);

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
