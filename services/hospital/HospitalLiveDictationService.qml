import QtQuick
import Quickshell
import Quickshell.Io

// Scope: Surgery Manage long-form fields ONLY.
// Different transport from Reception; supports local chunked partial text.
// No form submit, cloud request or durable audio.
Scope {
    id: root
    property string voiceState: "checking"
    property bool backendReady: false
    property string lastError: ""
    property string lastTranscript: ""
    property int recordingElapsedSeconds: 0
    property double recordingStartedAt: 0
    property bool liveStreaming: true
    property bool wasCancelled: false
    property bool doneSeen: false
    property int packetCount: 0
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
        recordingStartedAt = Date.now();
        recordingElapsedSeconds = 0;
        voiceState = "recording";
        liveProcess.exec(["python3", scriptPath, whisperHelper]);
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
        if (liveProcess.running)
            liveProcess.running = false; // kills and reaps owned Python/PipeWire child
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
        if (data.kind === "partial") {
            if (typeof data.text !== "string")
                return;
            const sentence = data.text.trim();
            if (!sentence || /^\[\s*(?:BLANK_AUDIO|NO_SPEECH|SILENCE)\s*\]$/i.test(sentence))
                return;
            packetCount++;
            if (packetCount > 30) {
                lastError = "LIVE DICTATION LENGTH LIMIT // STOPPING";
                voiceError(lastError);
                cancel();
                return;
            }
            lastTranscript = sentence;
            liveTextReady(sentence);
        } else if (data.kind === "done") {
            doneSeen = true;
            clock.stop();
            voiceState = backendReady ? "idle" : "unavailable";
            liveFinished();
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
            if (root.wasCancelled)
                return;
            root.recordingStartedAt = 0;
            root.recordingElapsedSeconds = 0;
            root.voiceState = root.backendReady ? "idle" : "unavailable";
            root.clockStop();
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
