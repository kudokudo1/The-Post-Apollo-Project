import QtQuick
import Quickshell
import Quickshell.Io
import "KillResourceEvidence.js" as Evidence

// Explicit read-only probe. No recurring collection or resource mutations.
Scope {
    id: root
    property string targetKey: ""
    property bool eligible: false
    property var result: null
    property string status: "NOT INSPECTED"
    property bool busy: false
    property string requestKey: ""
    property bool exited: false
    property bool stdoutDone: false
    property bool stderrDone: false
    property int exitCode: -1
    property int exitStatus: -1
    property string output: ""
    property string errors: ""
    property bool timedOut: false

    function invalidate() {
        result=null;
        requestKey="";
        status="NOT INSPECTED";
        if (busy) helper.running=false;
    }
    onTargetKeyChanged: invalidate()
    onEligibleChanged: if (!eligible) invalidate()

    function inspect() {
        if (!eligible || busy || !targetKey) return false;
        let identity;
        try { identity=JSON.parse(targetKey); } catch(error) { return false; }
        if (!Array.isArray(identity)||identity.length!==3||!Number.isSafeInteger(identity[0])
                ||identity[0]<=1||!Number.isSafeInteger(identity[1])||identity[1]<=0
                ||typeof identity[2]!=="string"||!identity[2]) return false;
        const url=String(Qt.resolvedUrl("resource_capability_probe.py"));
        if (!url.startsWith("file:///")) { status="HELPER PATH UNAVAILABLE"; return false; }
        let path;
        try { path=decodeURIComponent(url.slice(7)); } catch(error) { return false; }
        result=null;
        requestKey=targetKey;
        busy=true;
        exited=false; stdoutDone=false; stderrDone=false;
        exitCode=-1; exitStatus=-1; output=""; errors=""; timedOut=false;
        status="INSPECTING // READ ONLY";
        watchdog.restart();
        helper.exec(["/usr/bin/python3",path,"--pid="+identity[0],
            "--start-ticks="+identity[1],"--comm="+identity[2]]);
        return true;
    }
    function finish() {
        if (!busy||!exited||!stdoutDone||!stderrDone) return;
        watchdog.stop();
        const current=eligible&&requestKey&&requestKey===targetKey;
        const decoded=current&&!timedOut&&exitCode===0&&exitStatus===0&&!errors.trim()
            ? Evidence.decode(output,requestKey) : null;
        result=decoded;
        status=!current ? "NOT INSPECTED" : timedOut ? "INSPECTION TIMED OUT"
            : decoded ? "OBSERVED // READ ONLY" : "EVIDENCE UNAVAILABLE // NOT VERIFIED";
        requestKey="";
        busy=false;
    }
    Process {
        id: helper
        onExited: function(code,exitState) {
            root.exited=true; root.exitCode=code; root.exitStatus=exitState; root.finish();
        }
        stdout: StdioCollector {
            onStreamFinished: { root.output=String(text||""); root.stdoutDone=true; root.finish(); }
        }
        stderr: StdioCollector {
            onStreamFinished: { root.errors=String(text||""); root.stderrDone=true; root.finish(); }
        }
    }
    Timer {
        id: watchdog
        interval: 5000
        repeat: false
        onTriggered: {
            root.timedOut=true;
            root.result=null;
            root.status="INSPECTION TIMED OUT // DRAINING";
            helper.running=false;
            root.finish();
        }
    }
}
