import QtQuick
import Quickshell
import Quickshell.Io

// D17d: UI bridge to D17c's independently authorized income writer.
// One exact JSON command over stdin. No local permits, Actual credentials,
// budget writes, retries, or financial logging in this QML service.
Scope {
    id: bridge
    property string state: "idle" // idle, pending, committed, blocked, uncertain
    property string message: "FUNDING WRITES // SEPARATE OPERATOR GATE REQUIRED"
    property string inputFrame: ""
    property string outputStatus: ""
    signal saved()

    function submit(command) {
        if(state === "pending" || state === "uncertain"
                || worker.running || !command || command.mode !== "income")
            return false;
        inputFrame=JSON.stringify(command)+"\n";
        outputStatus="";
        state="pending";
        message="FUNDING PENDING // DO NOT RESTART QUICKSHELL";
        worker.exec({
            command: ["/usr/bin/env","node",
                Quickshell.shellPath("scripts/finance/write_funding.mjs")],
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
                    const match=/^FINANCEW_FUNDING_RESULT (committed|uncertain|blocked:[a-z0-9-]+)$/.exec(lines[i]);
                    if(match)bridge.outputStatus=match[1];
                }
            }
        }
        onExited: function(exitCode,exitStatus) {
            Qt.callLater(function() {
                if(bridge.outputStatus==="committed" && exitCode===0){
                    bridge.state="committed";
                    bridge.message="INCOME SAVED // VERIFY IN ACTUAL";
                    bridge.saved();
                } else if(bridge.outputStatus==="blocked:writes-disabled"){
                    // Missing permit means the write never started.
                    bridge.state="blocked";
                    bridge.message="FUNDING WRITES LOCKED // OPERATOR ACTIVATION REQUIRED";
                } else {
                    // A blocked writer may reflect a stale budget, a journal
                    // collision or an attempted operation. No second submit
                    // until independent recovery review, even for unknown output.
                    bridge.state="uncertain";
                    bridge.message="FUNDING REFUSED OR UNCERTAIN // CHECK ACTUAL AND JOURNAL. DO NOT RETRY.";
                }
                bridge.outputStatus="";
                bridge.inputFrame="";
            });
        }
    }
}
