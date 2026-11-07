import QtQuick
import Quickshell
import Quickshell.Io

// Operator-facing Room labels only. Never edits Room ID, Patient, Team,
// Git branch, Doctor, Provider, Assignment, or live provider session.
Scope {
    id: root

    property bool saving: false
    property string lastError: ""
    property string lastStatus: ""
    property string pendingRoomId: ""
    property var lastSavedRoom: null

    signal nameSaved(var room)

    function clearStatus() {
        if (!saving) {
            lastError = "";
            lastStatus = "";
        }
    }

    function saveName(roomIdValue, displayNameValue) {
        const id = String(roomIdValue || "").trim();
        const name = String(displayNameValue || "").trim();
        if (!id || saving || saveProcess.running)
            return false;
        if (name.length > 96 || /[\x00-\x1f\x7f]/.test(name)) {
            lastError = "ROOM NAME // INVALID CHARACTERS OR LENGTH";
            return false;
        }

        pendingRoomId = id;
        saving = true;
        lastError = "";
        lastStatus = "ROOM NAME // SAVING";
        lastSavedRoom = null;
        saveProcess.exec([
            "bash",
            "-lc",
            'px="$HOME/.local/share/post-apollo-dev-runtime/bin/px"; '
                + '[ -x "$px" ] || px="$HOME/.local/bin/px"; '
                + 'exec "$px" "$@"',
            "hospital-room-name",
            "hospital", "room-name-set", id,
            "--name", name, "--json"
        ]);
        return true;
    }

    Process {
        id: saveProcess

        stdout: StdioCollector {
            onStreamFinished: {
                const body = String(this.text || "").trim();
                if (!body)
                    return;
                try {
                    const result = JSON.parse(body);
                    if (String(result.id || "") !== root.pendingRoomId)
                        throw new Error("ROOM NAME // IDENTITY MISMATCH");
                    root.lastSavedRoom = result;
                } catch (error) {
                    root.lastError = "ROOM NAME // INVALID PX REPLY // "
                        + String(error);
                }
            }
        }

        stderr: StdioCollector {
            onStreamFinished: {
                const detail = String(this.text || "").trim();
                if (detail) {
                    const rows = detail.split("\n").filter(function(row) {
                        return !!String(row || "").trim();
                    });
                    root.lastError = "ROOM NAME // PX ERROR // "
                        + (rows.length ? rows[rows.length - 1] : detail).slice(0, 220);
                }
            }
        }

        onExited: function(code, exitStatus) {
            root.saving = false;
            if (Number(code) === 0 && !root.lastError && root.lastSavedRoom) {
                root.lastStatus = "ROOM NAME // SAVED";
                root.nameSaved(root.lastSavedRoom);
                return;
            }
            if (!root.lastError)
                root.lastError = "ROOM NAME // PX EXIT " + String(code)
                    + " // CHECK PX V11";
            root.lastStatus = "ROOM NAME // STOPPED";
        }
    }
}
