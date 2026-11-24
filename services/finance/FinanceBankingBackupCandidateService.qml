import QtQuick
import Quickshell
import Quickshell.Io
import "../../widgets/FinanceBankingBackupControlsPolicy.js" as Policy

// M4s1 candidate only. No automatic start, restore, import or live mount.
Scope {
    id: service
    property bool allowed: false
    readonly property bool busy: pending!==null
    property var pending: null
    property string frame: ""
    property string output: ""
    signal completed(var receipt)
    signal refused()

    function invoke(request) {
        if(!allowed||busy||worker.running||!Policy.validRequest(request))return false;
        pending=JSON.parse(JSON.stringify(request));
        frame=JSON.stringify(pending)+"\n";
        output="";
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
            if(service.frame!==""){
                worker.write(service.frame);
                service.frame="";
            }
        }
        stdout: StdioCollector {
            onStreamFinished: service.output=String(text||"")
        }
        onExited: function(code,status) {
            Qt.callLater(function(){
                const receipt=Policy.accept(service.output,code,service.pending);
                service.output="";
                service.frame="";
                service.pending=null;
                if(receipt!==null)service.completed(receipt);
                else service.refused();
            });
        }
    }
}
