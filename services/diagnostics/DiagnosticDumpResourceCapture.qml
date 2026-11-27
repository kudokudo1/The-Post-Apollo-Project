import QtQuick
import Quickshell
import Quickshell.Io
import "DiagnosticDumpResource.js" as Resource
import "CpuPlusDiagnosticsPolicy.js" as Policy

// One demand-activated worker using the already existing memory observer.
// No automatic startup, retry, arbitrary PID or executable.
Scope {
    id: capture
    property bool busy: false
    property bool faulted: false
    property bool cancelled: false
    property bool stdoutSeen: false
    property bool exitSeen: false
    property bool exitOk: false
    property string output: ""
    property var request: null
    property var report: null
    signal completed(var result)
    function start(seconds,originMs) {
        const plan=Resource.dumpResourcePlan(seconds);
        const now=Date.now();
        if(busy||faulted||worker.running||!plan||!Number.isSafeInteger(originMs)||originMs<0||now<originMs||now-originMs>1000)return false;
        request={seconds:seconds,originMs:originMs};
        report=null;output="";stdoutSeen=false;exitSeen=false;exitOk=false;cancelled=false;
        busy=true;
        deadline.interval=(seconds+15)*1000;
        deadline.restart();
        worker.exec(["/usr/bin/timeout","--kill-after=3s",String(seconds+10)+"s",
            "/usr/bin/python3","-E","-s","-B",Quickshell.shellPath("scripts/cpuplus_quickshell_memory_observer.py"),
            "--workshop","--parent-quickshell","--duration",String(seconds),"--interval",String(plan.intervalMs/1000)]);
        return true;
    }
    function cancel() {
        if(!busy||cancelled)return false;
        cancelled=true;
        worker.running=false;
        return true;
    }
    function publish(result) {
        deadline.stop();
        report=result;request=null;output="";
        busy=false;
        completed(report);
    }
    function finish() {
        if(!busy||!stdoutSeen||!exitSeen)return;
        const evidence=!cancelled&&exitOk?Resource.dumpResourceEvidence(output,request.originMs,request.seconds,{
            configuredEvidence:(kind,text,plan)=>Policy.configuredEvidence(kind,text,plan),
            summarize:(kind,text)=>Policy.summarize(kind,text)}):null;
        publish(evidence?{status:"COMPLETE",evidence:evidence}:
            {status:cancelled?"CANCELLED":"NOT VERIFIED",evidence:null});
    }
    Timer {
        id: deadline
        repeat: false
        onTriggered: {
            if(!capture.busy)return;
            capture.faulted=true;
            capture.publish({status:"NOT VERIFIED",evidence:null,reason:"COMPLETION NOT OBSERVED"});
            worker.running=false;
        }
    }
    Process {
        id: worker
        stdout: StdioCollector {
            onStreamFinished: {
                if(!capture.busy)return;
                capture.output=this.text.length<=65536?this.text:"";
                capture.stdoutSeen=true;
                capture.finish();
            }
        }
        stderr: StdioCollector {}
        onExited: function(code,exitStatus) {
            if(!capture.busy)return;
            capture.exitOk=code===0&&exitStatus===0;
            capture.exitSeen=true;
            capture.finish();
        }
    }
}
