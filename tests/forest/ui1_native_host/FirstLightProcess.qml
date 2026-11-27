import QtQuick
import Quickshell
import Quickshell.Io

// Fixed FL7 test-only asynchronous native parent. No installed transport.
// ASCII fixed-public fixture; SplitParser allocation occurs before this cap.
// One request/reply at a time, bounded lifetime, no retry or raw diagnostics.
Item {
    id: root
    property bool ready: false
    property bool pending: false
    property bool finished: false
    property bool cleanExit: false
    property var reply: null
    property string failure: ""
    property string buffer: ""
    property int commands: 0
    property int bytes: 0
    property bool closing: false
    property bool closeReply: false
    property bool started: false
    property int pid: 0
    readonly property bool running: worker.running

    ElapsedTimer { id: lifetime }
    ElapsedTimer { id: deadline }

    function start() {
        if (started || worker.running) return;
        lifetime.restartMs(); deadline.restartMs();
        worker.running=true;
    }
    function fail(reason) {
        if (failure!=="") return;
        failure=reason;
        ready=false;
        if (worker.running) worker.signal(9);
    }
    function request(cmd) {
        if (!ready || pending || reply!==null || finished || closing || failure!==""
                || !worker.running || worker.processId!==pid || commands>=64) return false;
        const wire=JSON.stringify(cmd)+"\n";
        if (wire.length>512 || !/^[\x20-\x7e]+\n$/.test(wire)) return false;
        pending=true; commands++; closing=cmd.op==="CLOSE";
        deadline.restartMs();
        worker.write(wire);
        return true;
    }
    function consume() {
        const value=reply;
        reply=null;
        return value;
    }
    function receive(chunk) {
        if (failure!=="") return;
        if (!pending || !worker.running || worker.processId!==pid
                || typeof chunk!=="string" || !/^[\x20-\x7e\n]*$/.test(chunk)
                || buffer.length+chunk.length>1024 || bytes+chunk.length>32768) {
            fail("STDOUT"); return;
        }
        bytes+=chunk.length; buffer+=chunk;
        const i=buffer.indexOf("\n");
        if (i<0) return;
        if (i!==buffer.length-1) { fail("EXTRA_STDOUT"); return; }
        const raw=buffer.slice(0,i);
        buffer="";
        try {
            const value=JSON.parse(raw);
            if (!value || typeof value!=="object" || Array.isArray(value)
                    || JSON.stringify(value)!==raw || typeof value.ok!=="boolean") {
                fail("INVALID_REPLY"); return;
            }
            reply=value; pending=false;
            if (closing) closeReply=value.ok===true;
        } catch (_) { fail("INVALID_REPLY"); }
    }

    Process {
        id: worker
        running: false
        command: ["/usr/bin/python3","-E","-s","-B","-u",
            Quickshell.shellPath("runtime/first_light_delivery_child.py")]
        workingDirectory: Quickshell.shellPath("privateFirstLight")
        clearEnvironment: true
        environment: ({HOME:workingDirectory,TMPDIR:workingDirectory,LANG:"C.UTF-8"})
        stdinEnabled: true
        onStarted: {
            if (root.started || !processId) { root.fail("START"); return; }
            root.started=true; root.pid=processId; root.ready=true;
        }
        stdout: SplitParser {
            splitMarker: ""
            onRead: function(data) { root.receive(data); }
        }
        stderr: SplitParser {
            splitMarker: ""
            onRead: function(data) { if (data.length) root.fail("STDERR"); }
        }
        onExited: function(code,exitStatus) {
            root.ready=false;
            if (!root.started || code!==0 || exitStatus!==0 || !root.closing
                    || !root.closeReply || root.pending || root.buffer!=="")
                root.fail("EXIT_UNCERTAIN");
            root.cleanExit=root.failure==="";
            settle.restart();
        }
    }
    Timer {
        interval: 50
        repeat:true
        running: !root.finished && (worker.running || root.started)
        onTriggered: {
            if (root.failure!=="" || root.finished) return;
            if (lifetime.elapsedMs()>=20000 || ((!root.started || root.pending || root.closing)
                    && deadline.elapsedMs()>=5000)) root.fail("DEADLINE");
        }
    }
    Timer {
        id: settle
        interval: 100
        onTriggered: {
            if (worker.running) root.fail("UNREAPED");
            root.finished=true;
        }
    }
}
