import QtQuick
import Quickshell
import Quickshell.Io

// Read-only gate probe. Deliberately separate from allocation writes.
Scope {
    id: lockCheck
    property string state: "unchecked"
    property string message: "WRITE LOCK // NOT CHECKED"
    property string observed: ""

    function check() {
        if (probe.running || state === "checking")
            return false;
        observed = "";
        state = "checking";
        message = "CHECKING LOCAL ALLOCATION PERMISSION";
        probe.exec({
            command: ["/usr/bin/env", "node",
                Quickshell.shellPath("scripts/finance/check_allocation_gate.mjs")]
        });
        return true;
    }

    Process {
        id: probe
        stdout: StdioCollector {
            onStreamFinished: {
                const lines=String(text || "").split(/\r?\n/);
                for(let i=0;i<lines.length;i++) {
                    const match=/^FINANCEW_ALLOCATION_GATE (locked|permit-present|unsafe|error)$/.exec(lines[i]);
                    if(match)lockCheck.observed=match[1];
                }
            }
        }
        onExited: function(exitCode, exitStatus) {
            Qt.callLater(function() {
                const token=exitCode===0 ? lockCheck.observed : "error";
                lockCheck.state=["locked","permit-present","unsafe"].indexOf(token)>=0
                    ? token : "error";
                lockCheck.message=lockCheck.state==="locked"
                    ? "WRITES LOCKED // NO ALLOCATION PERMIT"
                    : lockCheck.state==="permit-present"
                    ? "PERMIT DETECTED // DO NOT TEST LIVE WRITES"
                    : lockCheck.state==="unsafe"
                    ? "UNSAFE PERMISSION FILE // REVIEW REQUIRED"
                    : "LOCK CHECK UNAVAILABLE // NO SAFETY CLAIM";
                lockCheck.observed="";
            });
        }
    }
}
