import QtQuick
import Quickshell
import Quickshell.Io

// FinanceW D9 writer: requests arrive over stdin, not argv or QML logs.
// The Node writer refuses all budget writes until locally authorized.
Scope {
    id: bridge
    property string state: "idle" // idle, pending, committed, blocked, uncertain
    property string message: "Review a draft before saving."
    property string inputFrame: ""
    property string outputStatus: ""
    signal saved()

    function submit(command) {
        if (state === "pending" || state === "uncertain"
                || worker.running || !command)
            return false;
        inputFrame = JSON.stringify(command) + "\n";
        outputStatus = "";
        state = "pending";
        message = "Submitting one guarded operation.";
        worker.exec({
            command: ["/usr/bin/env", "node",
                Quickshell.shellPath("scripts/finance/write_transaction.mjs")],
            environment: ({
                ACTUAL_SYNC_ID: null,
                ACTUAL_SYNC_ID_FILE: null,
                ACTUAL_PASSWORD_FILE: null,
                ACTUAL_SERVER_URL: null
            })
        });
        return true;
    }

    Process {
        id: worker
        stdinEnabled: true

        onStarted: {
            // The only mutable budget fields travel via process stdin.
            if (bridge.inputFrame) {
                worker.write(bridge.inputFrame);
                bridge.inputFrame = "";
            }
        }
        stdout: StdioCollector {
            onStreamFinished: {
                const lines = String(text || "").split(/\r?\n/);
                for (let i = 0; i < lines.length; i++) {
                    const match = /^FINANCEW_TRANSACTION_RESULT (committed|uncertain|blocked:[a-z0-9-]+)$/.exec(lines[i]);
                    if (match) bridge.outputStatus = match[1];
                }
            }
        }
        onExited: function(exitCode, exitStatus) {
            Qt.callLater(function() {
                if (bridge.outputStatus === "committed" && exitCode === 0) {
                    bridge.state = "committed";
                    bridge.message = "Saved and synchronized with Actual.";
                    bridge.saved();
                } else if (bridge.outputStatus.indexOf("blocked:") === 0) {
                    bridge.state = "blocked";
                    const code = bridge.outputStatus.slice(8);
                    bridge.message = code === "writes-disabled"
                        ? "WRITES LOCKED // OPERATOR ACTIVATION REQUIRED"
                        : code === "possible-duplicate" || code === "already-exists"
                        ? "POSSIBLE DUPLICATE // CHECK ACTUAL"
                        : code === "recovery-needed"
                        || code === "write-in-progress-or-recovery-needed"
                        || code === "operation-already-attempted"
                        ? "RECOVERY REQUIRED // CHECK ACTUAL BEFORE RETRY"
                        : "SAVE REFUSED // " + code.toUpperCase();
                } else {
                    bridge.state = "uncertain";
                    bridge.message = "UNCERTAIN // VERIFY IN ACTUAL. DO NOT RETRY.";
                }
            });
        }
    }
}
