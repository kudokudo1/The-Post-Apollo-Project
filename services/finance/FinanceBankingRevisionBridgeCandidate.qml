import QtQuick
import Quickshell
import Quickshell.Io
import "../../widgets/FinanceBankingAccountsPolicy.js" as Accounts

// CI-only, single-use candidate. Never mounted in production FinanceW.
Scope {
    id: bridge
    property bool reviewEnabled: false
    readonly property bool allowed: reviewEnabled
        && Quickshell.env("GITHUB_ACTIONS")==="true"
        && Quickshell.env("POST_APOLLO_BANKING_M4T2")==="CI_DISPOSABLE_ONLY"
    property string phase: "idle"
    property string generation: ""
    property var document: null
    property int sequence: 0
    property var pending: null
    property bool closeReceipt: false
    readonly property bool ready: phase==="ready" && allowed && worker.running
    readonly property bool childRunning: worker.running
    signal sessionInvalidated()

    onAllowedChanged: {
        if(!allowed && phase!=="idle" && phase!=="closed") fail();
    }
    function exact(v,keys) {
        return v!==null && typeof v==="object" && !Array.isArray(v)
            && Object.keys(v).length===keys.length
            && keys.every(function(k){return Object.prototype.hasOwnProperty.call(v,k);});
    }
    function equal(a,b) {
        if(a===b)return true;
        if(!a||!b||typeof a!=="object"||typeof b!=="object"
            ||Array.isArray(a)!==Array.isArray(b))return false;
        var keys=Object.keys(a);
        return keys.length===Object.keys(b).length
            && keys.every(function(k){return Object.prototype.hasOwnProperty.call(b,k)&&equal(a[k],b[k]);});
    }
    function validDocument(d) {
        return exact(d,["version","revision","session"])&&d.version===1
            && Number.isSafeInteger(d.revision)&&d.revision>=0&&d.revision<=2147483646
            && Accounts.validState(d.session)&&["manual","empty"].includes(d.session.mode);
    }
    function invalidate() {
        generation="";
        document=null;
        pending=null;
        sessionInvalidated();
    }
    function fail() {
        if(phase==="failed"||phase==="closed")return;
        phase="failed";
        deadline.stop();
        invalidate();
        if(worker.running)worker.running=false;
    }
    function start() {
        if(!allowed||phase!=="idle"||worker.running)return false;
        phase="starting";
        deadline.restart();
        worker.exec({command:["/usr/bin/python3","-B",
            Quickshell.shellPath("scripts/finance/banking_client_bridge_candidate.py")]});
        return true;
    }
    function request(action,sessionGeneration,expectedRevision,session,confirm) {
        if(!ready||pending!==null||sessionGeneration!==generation
            ||expectedRevision!==document.revision||sequence>=1000000)return false;
        if(!["refresh","save","clear","close"].includes(action))return false;
        var r={action:action,generation:generation,sequence:sequence+1,expectedRevision:expectedRevision};
        if(action==="save"){
            if(confirm!==true||!Accounts.validState(session)||session.mode!=="manual")return false;
            r.session=JSON.parse(JSON.stringify(session));r.confirm=true;
        } else if(action==="clear"){
            if(confirm!==true)return false;
            r.confirm=true;
        }
        var frame=JSON.stringify(r)+"\n";
        // Conservative UTF-8 upper bound; Python separately checks byte limit.
        if(frame.length>176000)return false;
        pending=r;
        sequence=r.sequence;
        phase=action==="close"?"closing":"pending";
        deadline.restart();
        worker.write(frame);
        return true;
    }
    function receive(line) {
        if(!allowed||phase==="failed"||phase==="closed")return;
        const prefix="FINANCEW_BANKING_CLIENT ";
        if(typeof line!=="string"||line.length>530100||!line.startsWith(prefix)){fail();return;}
        try {
            var v=JSON.parse(line.slice(prefix.length));
            if(phase==="starting"){
                if(!exact(v,["kind","generation","sequence","document"])||v.kind!=="ready"
                    ||typeof v.generation!=="string"||v.generation.length!==32
                    ||!/^[0-9a-f]{32}$/.test(v.generation)||v.sequence!==0
                    ||!validDocument(v.document)){fail();return;}
                generation=v.generation;document=v.document;deadline.stop();phase="ready";
                return;
            }
            if(pending===null||v.kind!=="result"||v.generation!==generation
                ||v.sequence!==pending.sequence||v.action!==pending.action){fail();return;}
            var keys=["kind","generation","sequence","action"];
            if(pending.action==="close"){
                if(!exact(v,keys)||closeReceipt){fail();return;}
                closeReceipt=true;
                // Keep deadline armed until actual exit.
                pending=null;
                return;
            }
            if(!exact(v,keys.concat(["document"]))||!validDocument(v.document)){fail();return;}
            var action=pending.action;
            var expected=pending.expectedRevision+(action==="refresh"?0:1);
            var session=action==="refresh"?document.session:action==="save"?pending.session:Accounts.emptyState();
            if(v.document.revision!==expected||!equal(v.document.session,session)){fail();return;}
            document=v.document;
            pending=null;deadline.stop();phase="ready";
        }catch(error){fail();}
    }
    Timer {
        id: deadline
        interval: 10000
        repeat: false
        onTriggered: bridge.fail()
    }
    Process {
        id: worker
        stdinEnabled: true
        stdout: SplitParser {
            onRead: function(line) { bridge.receive(line); }
        }
        stderr: SplitParser {
            onRead: function(line) { bridge.fail(); }
        }
        onExited: function(code,status) {
            Qt.callLater(function(){
                bridge.deadlineFinished(code);
            });
        }
    }
    function deadlineFinished(code) {
        deadline.stop();
        if(phase==="closing"&&closeReceipt&&code===0){
            phase="closed";invalidate();
        }else fail();
    }
}
