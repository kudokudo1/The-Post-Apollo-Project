import QtQuick
import Quickshell
import Quickshell.Io
import "../../widgets/FinanceBankingBackupControlsPolicy.js" as Policy

// M4s1 candidate only. No automatic start, restore, import or live mount.
Scope {
    id: service
    property bool allowed: false
    readonly property bool busy: pending!==null || retired
    readonly property bool drained: pending===null && !worker.running
    property bool retired: false // deadline failure requires a new instance
    property bool refusalReported: false
    property var pending: null
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
    function invoke(request) {
        if(!allowed||busy||worker.running||!Policy.validRequest(request))return false;
        pending=JSON.parse(JSON.stringify(request));
        frame=JSON.stringify(pending)+"\n";
        output="";
        discarded=false;
        refusalReported=false;
        deadline.restart();
        worker.exec({
            command:["/usr/bin/python3","-B",
                     Quickshell.shellPath("scripts/finance/banking_manual_archive.py")],
            environment: ({ACTUAL_PASSWORD_FILE:null,ACTUAL_SYNC_ID:null,
                           ACTUAL_SERVER_URL:null,ACTUAL_SYNC_ID_FILE:null})
        });
        return true;
    }
    Process {
        id: worker
        stdinEnabled: true
        onStarted: {
            worker.write(service.discarded ? "{}\n" : service.frame);
            service.frame="";
        }
        stdout: StdioCollector {
            onStreamFinished: { if(!service.discarded)service.output=String(text||""); }
        }
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
