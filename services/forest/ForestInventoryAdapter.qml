import QtQuick
import Quickshell
import Quickshell.Io
import "ForestInventoryPolicy.js" as InventoryPolicy

// Only the B0 list-models action is accessible to ForestW.
// No automatic start, inference, session storage, arbitrary commands or tools.
Scope {
    id: inventory
    property bool scanning: false
    property string status: "NOT_CHECKED"
    property string reason: ""
    property var models: []
    readonly property int modelCount: models.length
    property int exitCode: -999
    property bool stdoutReady: false
    property string stdoutBody: ""

    function scanModels() {
        if (scanning || scanProcess.running)
            return false;
        scanning = true;
        status = "CHECKING";
        reason = "";
        models = [];
        exitCode = -999;
        stdoutReady = false;
        stdoutBody = "";
        scanProcess.exec([
            "python3",
            Quickshell.shellPath("scripts/forest/ollama_inventory.py"),
            "list-models"
        ]);
        return true;
    }

    function complete() {
        if (!scanning || exitCode === -999)
            return;
        var reply = stdoutReady
                ? InventoryPolicy.parseInventory(stdoutBody)
                : {valid: false};
        var expected = reply.status === "REACHABLE" ? 0 : 2;
        if (!reply.valid || exitCode !== expected) {
            status = "UNAVAILABLE";
            reason = "INVALID_RESPONSE";
            models = [];
        } else {
            status = reply.status;
            reason = reply.reason;
            models = reply.models;
        }
        scanning = false;
    }

    Process {
        id: scanProcess
        running: false
        stdout: StdioCollector {
            onStreamFinished: {
                inventory.stdoutBody = String(this.text || "");
                inventory.stdoutReady = true;
                inventory.complete();
            }
        }
        stderr: StdioCollector {
            // Hide raw OS errors; only static B0 refusal codes reach the UI.
            onStreamFinished: {}
        }
        onExited: function(code, exitStatus) {
            inventory.exitCode = Number(code);
            Qt.callLater(function() { inventory.complete(); });
        }
    }
}
