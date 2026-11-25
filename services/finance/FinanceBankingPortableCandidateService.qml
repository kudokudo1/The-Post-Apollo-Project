import QtQuick
import Quickshell
import Quickshell.Io
import "../../widgets/FinanceBankingPortableControlsPolicy.js" as Policy

// Detached M4s2. Only export and authenticated metadata preview.
Scope {
    id: service
    property bool allowed: false
    readonly property bool busy: pending!==null || retired
    property bool retired: false // deadline failure requires a new instance
    property bool refusalReported: false
    property var pending: null // non-secret intent only
    property string frame: ""
    property string output: ""
    property bool discarded: false
    signal completed(var receipt)
    signal refused()

    // Context changes are sticky for this request, even if the same context returns.
    onAllowedChanged: { if(!allowed)discardContext(); }
    function discardContext() {
        if(pending===null)return;
        discarded=true;
        frame="";
    }
    function expire() {
        if(pending===null||retired)return;
        discarded=true;
        retired=true;
        frame="";
        output="";
        refusalReported=true;
        // An already submitted write may have committed. Never retry.
        if(worker.running)worker.running=false;
        refused();
    }
    Timer {
        id: deadline
        interval: 35000
        repeat: false
        onTriggered: service.expire()
    }
    function invoke(intent,password) {
        if(!allowed||busy||worker.running)return false;
        var requestFrame=Policy.frame(intent,password);
        if(requestFrame===null)return false;
        pending=JSON.parse(JSON.stringify(intent));
        frame=requestFrame;
        output="";
        discarded=false;
        refusalReported=false;
        deadline.restart();
        worker.exec({
            command:["/usr/bin/python3","-B",
                Quickshell.shellPath("scripts/finance/banking_manual_portable.py")],
            environment: ({ACTUAL_PASSWORD_FILE:null,ACTUAL_SYNC_ID:null,
                ACTUAL_SERVER_URL:null,ACTUAL_SYNC_ID_FILE:null})
        });
        return true;
    }
    Process {
        id: worker
        stdinEnabled: true
        onStarted: {
            // If disabled before start, send only an invalid empty command.
            worker.write(service.discarded ? "{}\n" : service.frame);
            service.frame="";
        }
        stdout: StdioCollector {
            onStreamFinished: { if(!service.discarded)service.output=String(text||""); }
        }
        stderr: StdioCollector {}
        onExited: function(code,status) {
            Qt.callLater(function(){
                const receipt=service.discarded||!service.allowed?null:
                    Policy.accept(service.output,code,service.pending);
                deadline.stop();
                service.output="";
                service.frame="";
                service.pending=null;
                if(receipt!==null)service.completed(receipt);
                else if(!service.refusalReported)service.refused();
            });
        }
    }
}
