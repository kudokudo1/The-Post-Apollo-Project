import QtQuick
import Quickshell
import Quickshell.Io

// Read-only Assignment selector for a pinned Hospital Room.
// No attachment, creation, activation, or approval commands.
Scope {
    id: root
    property string roomId: ""
    property string requestedRoomId: ""
    property var assignments: []
    property bool loaded: false
    property bool loading: false
    property bool retryPending: false
    property string lastError: ""

    function refresh() {
        const id = String(roomId || "").trim();
        if (!id) {
            assignments = [];
            loaded = false;
            lastError = "";
            return false;
        }
        if (request.running) {
            retryPending = true;
            return false;
        }
        requestedRoomId = id;
        retryPending = false;
        loading = true;
        loaded = false;
        assignments = [];
        lastError = "";
        request.exec([
            "bash", "-lc",
            'px="$HOME/.local/share/post-apollo-dev-runtime/bin/px"; '
            + '[ -x "$px" ] || px="$HOME/.local/bin/px"; '
            + 'exec "$px" "$@"',
            "hospital-attach-preview",
            "hospital", "assignments",
            "--room-id", id, "--status", "ALL", "--limit", "200", "--json"
        ]);
        return true;
    }

    onRoomIdChanged: Qt.callLater(root.refresh)

    Process {
        id: request
        property string responseText: ""
        property string errorText: ""
        stdout: StdioCollector {
            onStreamFinished: request.responseText = String(this.text || "")
        }
        stderr: StdioCollector {
            onStreamFinished: request.errorText = String(this.text || "")
        }
        onExited: function(code, exitStatus) {
            const requested = root.requestedRoomId;
            root.loading = false;
            if (requested === String(root.roomId || "").trim()) {
                if (Number(code) !== 0) {
                    root.lastError = "PX ASSIGNMENTS // "
                        + (request.errorText || "EXIT " + String(code)).trim().slice(0,180);
                } else {
                    try {
                        const rows = JSON.parse(request.responseText || "[]");
                        if (!Array.isArray(rows))
                            throw new Error("expected Assignment array");
                        // Never expose a foreign Room's Assignment as selectable.
                        root.assignments = rows.filter(function(row) {
                            return String((row || {}).roomId || "") === requested;
                        });
                        if (root.assignments.length !== rows.length)
                            throw new Error("PX returned foreign Room Assignments");
                        root.loaded = true;
                        root.lastError = "";
                    } catch (error) {
                        root.assignments = [];
                        root.loaded = false;
                        root.lastError = "PX ASSIGNMENTS // " + String(error).slice(0,180);
                    }
                }
            }
            request.responseText = "";
            request.errorText = "";
            if (root.retryPending || requested !== String(root.roomId || "").trim()) {
                root.retryPending = false;
                Qt.callLater(root.refresh);
            }
        }
    }
}
