import QtQuick
import Quickshell
import Quickshell.Io

// FinanceW M6 // group save bridge. Neither this service nor the menu can
// provision the separately approved M5 category-group write permit.
// Never log names, retry an attempt, or mutate Actual in QML.
Scope {
    id: bridge
    property string state: "idle" // idle, pending, committed, blocked, uncertain
    property string message: "GROUP WRITES // SEPARATE OPERATOR GATE REQUIRED"
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
        message="GROUP SAVE PENDING // DO NOT RESTART QUICKSHELL";
        worker.exec({
            command: ["/usr/bin/env","node",
                Quickshell.shellPath("scripts/finance/write_category_group.mjs")],
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
                    const result=/^FINANCEW_CATEGORY_GROUP_RESULT (committed|uncertain|blocked:[a-z0-9-]+)$/.exec(lines[i]);
                    if(result)bridge.outputStatus=result[1];
                }
            }
        }
        onExited: function(exitCode,exitStatus) {
            Qt.callLater(function() {
                if(bridge.outputStatus==="committed" && exitCode===0) {
                    bridge.state="committed";
                    bridge.message="GROUP SAVED // VERIFY IN ACTUAL";
                    bridge.saved();
                } else if(bridge.outputStatus==="blocked:writes-disabled") {
                    // Without independent operator permit there was no write.
                    bridge.state="blocked";
                    bridge.message="GROUP WRITES LOCKED // OPERATOR ACTIVATION REQUIRED";
                } else {
                    // Even a preflight refusal cannot silently resubmit under
                    // a fresh ID. If mutation may have happened, inspect journal.
                    bridge.state="uncertain";
                    bridge.message="GROUP REFUSED OR UNCERTAIN // CHECK ACTUAL AND JOURNAL. DO NOT RETRY.";
                }
                bridge.outputStatus="";
                bridge.inputFrame="";
            });
        }
    }
}
