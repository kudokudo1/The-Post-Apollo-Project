import QtQuick
import Quickshell
import Quickshell.Io
import "ForestInventoryPolicy.js" as InventoryPolicy

// Forest B0 UI-owned read-only invocation. Never a generation/session host.
// Delay model publication until stdout + stderr + normal exit all finish.
Scope {
    id: inventory
    property bool scanning: false
    property string status: "NOT_CHECKED"
    property string reason: ""
    property var models: []
    readonly property int modelCount: models.length
    property var scanState: InventoryPolicy.beginScan()

    function scanModels() {
        if (scanning || scanProcess.running)
            return false;
        scanState = InventoryPolicy.beginScan();
        scanning = true;
        status = "CHECKING";
        reason = "";
        models = [];
        // No shell, model execution, arbitrary endpoint, or user-supplied argv.
        scanProcess.exec([
            "python3",
            Quickshell.shellPath("scripts/forest/ollama_inventory.py"),
            "list-models"
        ]);
        return true;
    }

    function acceptProgress(nextState) {
        if (!scanning || !nextState)
            return;
        scanState = nextState;
        if (!scanState.complete)
            return;
        status = scanState.status;
        reason = scanState.reason;
        models = scanState.accepted ? scanState.models : [];
        scanning = false;
    }

    Process {
        id: scanProcess
        running: false
        stdout: StdioCollector {
            onStreamFinished: {
                inventory.acceptProgress(
                    InventoryPolicy.captureStdoutScan(
                        inventory.scanState, String(this.text || "")));
            }
        }
        stderr: StdioCollector {
            onStreamFinished: {
                // Stderr is an error bit only; never expose raw host output.
                inventory.acceptProgress(
                    InventoryPolicy.captureStderrScan(
                        inventory.scanState, String(this.text || "")));
            }
        }
        onExited: function(code, exitStatus) {
            inventory.acceptProgress(
                InventoryPolicy.captureExitScan(
                    inventory.scanState, code, exitStatus));
        }
    }
}
