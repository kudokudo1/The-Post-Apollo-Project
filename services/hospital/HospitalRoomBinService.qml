import QtQuick
import Quickshell
import Quickshell.Io

// Hospital's source-owned Trash inventory: metadata only, never a path or
// GIO item. Errors are separate from a genuinely empty Room bin.
Scope {
    id: root
    property bool active: false
    property bool busy: false
    property bool loaded: false
    property string lastError: ""
    property var rows: []

    function refresh() {
        if (!active || busy || binProcess.running)
            return false;
        busy = true;
        loaded = false;
        lastError = "";
        // PX protected source only. Missing/uninstalled readers are NOT
        // replaced with desktop-owned hospital.db or the old px CLI.
        try {
            binProcess.exec([
                "/usr/libexec/post-apollo/hospital/hospital-room-read",
                "bin"
            ]);
        } catch (error) {
            busy = false;
            rows = [];
            loaded = false;
            lastError = "HOSPITAL BACKEND NOT READY // PROTECTED BIN READER UNAVAILABLE";
            return false;
        }
        return true;
    }

    Process {
        id: binProcess
        property string outputText: ""
        property string errorText: ""
        stdout: StdioCollector {
            onStreamFinished: binProcess.outputText = String(this.text || "")
        }
        stderr: StdioCollector {
            onStreamFinished: binProcess.errorText = String(this.text || "")
        }
        onExited: function(code, status) {
            const output = binProcess.outputText;
            const error = binProcess.errorText;
            binProcess.outputText = "";
            binProcess.errorText = "";
            root.busy = false;
            try {
                if (Number(code) !== 0)
                    throw new Error("HOSPITAL BACKEND NOT READY");
                const parsed = JSON.parse(output || "[]");
                if (!Array.isArray(parsed) || parsed.length > 2500)
                    throw new Error("HOSPITAL BIN FORMAT INVALID");
                const valid = parsed.every(function(item) {
                    return item && item.state === "TRASHED"
                        && item.kind === "HOSPITAL ROOM"
                        && item.burnAllowed === false
                        && /^[A-Za-z0-9._:/-]{1,160}$/.test(String(item.roomId || ""))
                        && Number.isSafeInteger(item.revision)
                        && item.revision > 0;
                });
                if (!valid)
                    throw new Error("HOSPITAL BIN IDENTITY INVALID");
                root.rows = parsed;
                root.loaded = true;
                root.lastError = "";
            } catch (e) {
                root.rows = [];
                root.loaded = false;
                // Do not display raw px argparse usage or mistaken "0 Rooms".
                // An unavailable PX command is NOT an empty Trash++ bin.
                root.lastError = String(e).includes("HOSPITAL BACKEND NOT READY")
                    ? "HOSPITAL BACKEND NOT READY // PX ROOM BIN UNAVAILABLE"
                    : "HOSPITAL BIN // SOURCE RESPONSE INVALID";
            }
        }
    }
}
