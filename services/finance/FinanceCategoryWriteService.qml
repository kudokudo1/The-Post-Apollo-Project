import QtQuick
import Quickshell
import Quickshell.Io

// M3: explicit category confirmation bridge to M2's separately permitted
// writer. Never creates a permit, imports Actual, logs category names, or retries.
Scope {
    id: bridge
    property string state: "idle" // idle, pending, committed, blocked, uncertain
    property string message: "CATEGORY WRITES // OPERATOR AUTHORIZATION REQUIRED"
    property string inputFrame: ""
    property string outputStatus: ""
    signal saved()

    function submit(command) {
        if(state==="pending" || state==="uncertain" || worker.running
                || !command || (command.mode!=="create" && command.mode!=="rename"))
            return false;
        inputFrame=JSON.stringify(command)+"\n";
        outputStatus="";
        state="pending";
        message="CATEGORY PENDING // DO NOT RESTART QUICKSHELL";
        worker.exec({
            command: ["/usr/bin/env","node",
                Quickshell.shellPath("scripts/finance/write_category.mjs")],
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
            if(bridge.inputFrame) {
                worker.write(bridge.inputFrame);
                bridge.inputFrame="";
            }
        }
        stdout: StdioCollector {
            onStreamFinished: {
                const lines=String(text||"").split(/\r?\n/);
                for(let i=0;i<lines.length;i++){
                    const match=/^FINANCEW_CATEGORY_RESULT (committed|uncertain|blocked:[a-z0-9-]+)$/.exec(lines[i]);
                    if(match)bridge.outputStatus=match[1];
                }
            }
        }
        onExited: function(exitCode,exitStatus) {
            Qt.callLater(function() {
                if(bridge.outputStatus==="committed" && exitCode===0) {
                    bridge.state="committed";
                    bridge.message="CATEGORY SAVED // VERIFY IN ACTUAL";
                    bridge.saved();
                } else if(bridge.outputStatus==="blocked:writes-disabled") {
                    // A missing independent permit refuses before reading
                    // the command or creating the operations journal.
                    bridge.state="blocked";
                    bridge.message="CATEGORY WRITES LOCKED // OPERATOR ACTIVATION REQUIRED";
                } else {
                    // Even a preflight refusal needs explicit review; never
                    // automatically resubmit a request with a fresh ID.
                    bridge.state="uncertain";
                    bridge.message="CATEGORY REFUSED OR UNCERTAIN // CHECK ACTUAL AND JOURNAL. DO NOT RETRY.";
                }
                bridge.outputStatus="";
                bridge.inputFrame="";
            });
        }
    }
}
