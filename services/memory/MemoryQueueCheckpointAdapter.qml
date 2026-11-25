import QtQuick
import Quickshell.Io
import "MemoryQueueSessionHost.js" as Host

// Unmounted one-shot IO adapter, not a second controller. Only a trusted
// wrapper may choose the paths and duration. Never dispatch queue frames.
QtObject {
    id: root
    property string pythonPath: ""
    property string helperPath: ""
    property string directory: ""
    property int timeoutMs: 0
    // Explicit generation namespace. Never downgrade an adapter after use.
    property bool generationMode: false
    property var pinnedMode: null
    property bool settling: false
    readonly property bool busy: request !== null || settling
    property var request: null
    property int ticket: 0
    property var reply: null
    property bool invalid: false
    property bool retired: false
    signal completed(int generation, int ticket, string operation, var result)

    function begin(operation,generation,record) {
        const allowed=generationMode?["GEN_LOAD","GEN_SAVE","GEN_ADVANCE"]:["LOAD","SAVE"];
        if (retired || busy || proc.running || !allowed.includes(operation)
            || (pinnedMode!==null && pinnedMode!==generationMode)
            || !Number.isInteger(generation) || generation<1 || generation>2147483646
            || ticket>=2147483646 || timeoutMs<1 || timeoutMs>60000
            || ![pythonPath,helperPath,directory].every(x=>x.startsWith("/") && !/[\x00-\x1f]/.test(x)))
            return 0;
        let input="";
        if (operation==="SAVE" || operation==="GEN_SAVE" || operation==="GEN_ADVANCE") {
            if (!record || !Host.safe(record)) return 0;
            if (operation!=="SAVE") {
                const field=operation==="GEN_SAVE"?"record":"receipt";
                if (!Host.exact(record,["version","generation",field]) || record.version!==1
                    || !Number.isSafeInteger(record.generation) || record.generation<0
                    || !record[field] || typeof record[field]!=="object" || Array.isArray(record[field])) return 0;
                if (operation==="GEN_ADVANCE" && (!Host.uuid(record.receipt.review?.action_id)
                    || record.receipt.startup_unlock!==false || record.receipt.can_execute!==false)) return 0;
            }
            input=JSON.stringify(record)+"\n";
            if (input.length>8192) return 0;
        } else if (record!==null) return 0;
        pinnedMode=generationMode;
        const id=++ticket;
        request={operation,generation,ticket:id,input};
        reply=null;
        invalid=false;
        proc.command=[pythonPath,"-B",helperPath,operation,directory];
        proc.stdinEnabled=true;
        deadline.interval=timeoutMs;
        deadline.start();
        proc.running=true;
        return id;
    }
    function receive(line) {
        if (!request || invalid) return;
        if (reply!==null || typeof line!=="string" || !line.length
            || line.length>=16384 || /[^\x20-\x7e]/.test(line)) {
            invalid=true;
            return;
        }
        try {
            const value=JSON.parse(line);
            if (!Host.safe(value) || JSON.stringify(value)!==line) throw Error("invalid");
            reply=value;
        } catch (_) { invalid=true; }
    }
    function finish(code,status) {
        if (!request) return;
        const saved=request;
        let value=null;
        if (!invalid && code===0 && status===0 && reply
            && reply.version===1 && reply.can_execute===false) {
            if (saved.operation==="SAVE" && Host.exact(reply,["version","kind","record","can_execute"])
                && reply.kind==="CHECKPOINT_SAVED"
                && Host.equal(reply.record,JSON.parse(saved.input))) value=reply;
            if (saved.operation==="LOAD" && Host.exact(reply,["version","kind","snapshot","can_execute"])
                && reply.kind==="CHECKPOINT_LOADED") value=reply;
            if (saved.operation==="GEN_LOAD" && Host.exact(reply,["version","kind","snapshot","can_execute"])
                && reply.kind==="CHECKPOINT_GENERATION_LOADED") {
                const s=reply.snapshot;
                if (Host.exact(s,["generation","checkpoint","sealed","receipt","startup_unlock","can_execute"])
                    && Number.isSafeInteger(s.generation) && s.generation>=0
                    && typeof s.sealed==="boolean" && s.sealed===(s.receipt!==null)
                    && s.startup_unlock===false && s.can_execute===false
                    && s.checkpoint && typeof s.checkpoint==="object" && !Array.isArray(s.checkpoint))
                    value=reply;
            }
            if (saved.operation==="GEN_SAVE") {
                const sent=JSON.parse(saved.input);
                if (Host.exact(reply,["version","kind","generation","record","can_execute"])
                    && reply.kind==="CHECKPOINT_GENERATION_SAVED" && reply.generation===sent.generation
                    && Host.equal(reply.record,sent.record)) value=reply;
            }
            if (saved.operation==="GEN_ADVANCE") {
                const sent=JSON.parse(saved.input);
                if (Host.exact(reply,["version","kind","generation","action_id","startup_unlock","can_execute"])
                    && reply.kind==="CHECKPOINT_GENERATION_ADVANCED" && reply.generation===sent.generation+1
                    && reply.action_id===sent.receipt.review.action_id && reply.startup_unlock===false)
                    value=reply;
            }
        }
        settling=true;
        deadline.stop();
        if (!value) retired=true;
        request=null;
        reply=null;
        settling=false;
        completed(saved.generation,saved.ticket,saved.operation,value);
    }
    function cancel() {
        if (!request) return;
        const saved=request;
        // Retire before stopping the process; no later callback can emit
        // a successful result or start another helper on this adapter.
        retired=true;
        request=null;
        reply=null;
        deadline.stop();
        proc.running=false;
        completed(saved.generation,saved.ticket,saved.operation,null);
    }
    property Timer deadline: Timer {
        repeat:false
        onTriggered:root.cancel()
    }
    property Process proc: Process {
        stdinEnabled: true
        onStarted: {
            if (!root.request) { running=false; return; }
            if (root.request.input) write(root.request.input);
            stdinEnabled=false;
        }
        stdout: SplitParser { onRead: data => root.receive(data) }
        stderr: SplitParser { onRead: data => { if (root.request) root.invalid=true; } }
        onExited: (exitCode,exitStatus) => root.finish(exitCode,exitStatus)
    }
}
