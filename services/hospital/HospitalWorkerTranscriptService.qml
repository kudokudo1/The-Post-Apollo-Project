import QtQuick
import Quickshell
import Quickshell.Io

// Hospital worker transcript: read-only durable Room messages by exact Room ID.
// Never sends a turn, binds a Room, or creates an agent session.
Scope {
    id: root
    property string roomId: ""
    property string requestedRoomId: ""
    property var messages: []
    property bool loading: false
    property string lastError: ""
    property bool refreshQueued: false
    property int messageLimit: 100

    signal refreshed()

    function refresh() {
        const wanted = String(root.roomId || "").trim();
        if (!wanted) {
            if (!readProcess.running) {
                messages = [];
                lastError = "";
                loading = false;
            } else {
                refreshQueued = true;
            }
            return false;
        }
        if (readProcess.running) {
            refreshQueued = true;
            return false;
        }
        requestedRoomId = wanted;
        messages = [];
        lastError = "";
        loading = true;
        refreshQueued = false;
        readProcess.exec([
            "bash",
            "-lc",
            'px="$HOME/.local/share/post-apollo-dev-runtime/bin/px"; '
                + '[ -x "$px" ] || px="$HOME/.local/bin/px"; '
                + 'exec "$px" "$@"',
            "hospital-worker-transcript",
            "hospital", "messages", wanted,
            "--limit", String(Math.max(1, Math.min(100, messageLimit))),
            "--json"
        ]);
        return true;
    }

    onRoomIdChanged: refresh()

    Process {
        id: readProcess
        property string outputText: ""
        property string errorText: ""

        stdout: StdioCollector {
            onStreamFinished: readProcess.outputText = this.text
        }
        stderr: StdioCollector {
            onStreamFinished: readProcess.errorText = this.text
        }

        onExited: function(code, exitStatus) {
            const requested = root.requestedRoomId;
            root.requestedRoomId = "";
            root.loading = false;
            if (requested === String(root.roomId || "").trim()) {
                if (Number(code) !== 0) {
                    root.lastError = String(readProcess.errorText
                        || "PX HOSPITAL MESSAGES EXIT " + code).trim().slice(0, 260);
                } else {
                    try {
                        const result = JSON.parse(String(readProcess.outputText || "[]"));
                        if (!Array.isArray(result))
                            throw new Error("ROOM MESSAGES // EXPECTED ARRAY");
                        root.messages = result;
                        root.lastError = "";
                    } catch (error) {
                        root.lastError = "ROOM MESSAGES // " + String(error);
                    }
                }
                root.refreshed();
            }
            readProcess.outputText = "";
            readProcess.errorText = "";
            if (root.refreshQueued || requested !== String(root.roomId || "").trim()) {
                root.refreshQueued = false;
                Qt.callLater(function() { root.refresh(); });
            }
        }
    }
}
