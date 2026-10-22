import QtQuick
import Quickshell
import Quickshell.Io

// D12d UI bridge: one explicit operator-confirmed request to the D12c
// separately authorized writer. No credentials or amount data in argv/logs.
// No permission is provisioned here, and UNCERTAIN never auto-retries.
Scope {
    id: bridge
    property string state: "idle" // idle, pending, committed, blocked, uncertain
    property string message: "ALLOCATION WRITES // OPERATOR GATE REQUIRED"
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
        message = "ALLOCATION PENDING // DO NOT RESTART SHELL";
        worker.exec({
            command: ["/usr/bin/env","node",
                Quickshell.shellPath("scripts/finance/write_allocation.mjs")],
            environment: ({
                ACTUAL_SYNC_ID:null,
                ACTUAL_SYNC_ID_FILE:null,
                ACTUAL_PASSWORD_FILE:null,
                ACTUAL_SERVER_URL:null
            })
        });
        return true;
    }

    Process {
        id: worker
        stdinEnabled: true
        onStarted: {
            if (bridge.inputFrame) {
                worker.write(bridge.inputFrame);
                bridge.inputFrame = "";
            }
        }
        stdout: StdioCollector {
            onStreamFinished: {
                const lines=String(text || "").split(/\r?\n/);
                for (let i=0;i<lines.length;i++) {
                    const match=/^FINANCEW_ALLOCATION_RESULT (committed|uncertain|blocked:[a-z0-9-]+)$/.exec(lines[i]);
                    if(match)bridge.outputStatus=match[1];
                }
            }
        }
        onExited: function(exitCode,exitStatus) {
            Qt.callLater(function(){
                if(bridge.outputStatus==="committed" && exitCode===0) {
                    bridge.state="committed";
                    bridge.message="ALLOCATION SAVED // VERIFY ACTUAL LEDGER";
                    bridge.saved();
                } else if(bridge.outputStatus.indexOf("blocked:")===0) {
                    bridge.state="blocked";
                    const code=bridge.outputStatus.slice(8);
                    bridge.message=code==="writes-disabled"
                        ? "ALLOCATION WRITES LOCKED // OPERATOR ACTIVATION REQUIRED"
                        : code==="recovery-needed" || code==="write-in-progress-or-recovery-needed"
                          || code==="operation-already-attempted"
                        ? "RECOVERY REQUIRED // VERIFY ACTUAL BEFORE ANY WRITE"
                        : "ALLOCATION REFUSED // "+code.toUpperCase();
                } else {
                    // Includes an explicit uncertain result, failed process,
                    // or missing/malformed status output.
                    bridge.state="uncertain";
                    bridge.message="UNCERTAIN // CHECK ACTUAL AND JOURNAL. DO NOT RETRY.";
                }
                bridge.outputStatus="";
            });
        }
    }
}
