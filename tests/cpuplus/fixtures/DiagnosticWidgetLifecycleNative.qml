import QtQuick
import Quickshell
import qs.services.diagnostics

ShellRoot {
    id: root
    property int phase: 0
    function check(ok,message) {
        if(!ok){console.error("CPU_Q5_NATIVE_FAIL // "+message);Qt.exit(1);return false;}
        return true;
    }
    QtObject { id: source0; property bool menuOpen: false }
    QtObject { id: source1; property bool menuOpen: false }
    QtObject { id: source2; property bool menuOpen: false }
    QtObject { id: source3; property bool menuOpen: false }
    QtObject { id: source4; property bool menuOpen: false }
    QtObject { id: source5; property bool menuOpen: false }
    QtObject { id: source6; property bool menuOpen: false }
    QtObject { id: source7; property bool menuOpen: false }
    QtObject { id: source8; property bool menuOpen: false }
    QtObject { id: source9; property bool menuOpen: false }
    QtObject { id: source10; property bool menuOpen: false }
    QtObject { id: source11; property bool menuOpen: false }
    QtObject { id: source12; property bool menuOpen: false }
    QtObject { id: source13; property bool menuOpen: false }
    QtObject { id: source14; property bool deckOpen: false }
    DiagnosticDumpResourceCapture { id: resources }
    DiagnosticWidgetLifecycleAdapter {
        id: recorder
        sources: ({
            "appcontrol": source0,
            "camera": source1,
            "hospital": source2,
            "finance": source3,
            "git": source4,
            "company-network": source5,
            "tasks": source6,
            "forest": source7,
            "apollo-hub": source8,
            "cpuplus": source9,
            "weather": source10,
            "social": source11,
            "time": source12,
            "notifications": source13,
            "media": source14
        })
    }
    Binding { target: CpuPlusDiagnostics; property: "lifecycleRecorder"; value: recorder }
    Timer {
        interval: 50
        running: true
        repeat: true
        onTriggered: {
            if(root.phase===0){
                source0.menuOpen=true;
                if(!root.check(!recorder.active && recorder.report===null,"idle signal ignored"))return;
                const ids=Object.keys(recorder.sources);
                if(!root.check(CpuPlusDiagnostics.setLifecycleSelection(ids) && CpuPlusDiagnostics.setLifecycleDuration(1) && CpuPlusDiagnostics.startLifecycleCapture() && !CpuPlusDiagnostics.startLifecycleCapture() && !CpuPlusDiagnostics.request("threads") && !CpuPlusDiagnostics.loadWorkflowCatalog(),"one capture only, owner mutual exclusion"))return;
                root.phase=1;return;
            }
            if(root.phase===1){
                source0.menuOpen=false;
                source1.menuOpen=true;
                source2.menuOpen=true;
                source3.menuOpen=true;
                source4.menuOpen=true;
                source5.menuOpen=true;
                source6.menuOpen=true;
                source7.menuOpen=true;
                source8.menuOpen=true;
                source9.menuOpen=true;
                source10.menuOpen=true;
                source11.menuOpen=true;
                source12.menuOpen=true;
                source13.menuOpen=true;
                source14.deckOpen=true;
                if(!root.check(recorder.timing("git","dock","toggle","",0,Date.now()) && recorder.timing("media","frame","cava-apply","",0,Date.now()),"selected timing samples"))return;
                root.phase=2;return;
            }
            if(root.phase===2){
                if(recorder.active)return;
                const r=recorder.report;
                if(!root.check(r && r.status==="COMPLETE" && r.elapsedMs===1000 && r.completionDelayMs>=0
                    && r.events.length===15 && r.stats.length===15 && r.timings.length===2
                    && r.stats[0].closes===1 && r.stats[14].opens===1,"all 15 real QML signals"))return;
                if(!root.check(CpuPlusDiagnostics.lifecycleReport && CpuPlusDiagnostics.setLifecycleSelection(["git"]) && CpuPlusDiagnostics.startLifecycleCapture(),"single selection via owner"))return;
                source0.menuOpen=true;
                source4.menuOpen=false;
                if(!root.check(!recorder.timing("media","frame","cava-apply","",0,Date.now()),"unselected timing refused"))return;
                if(!root.check(CpuPlusDiagnostics.cancelLifecycleCapture()&&recorder.report.status==="CANCELLED"
                    && recorder.report.events.length===1 && recorder.report.events[0].id==="git",
                    "unselected ignored, cancellation bounded"))return;
                recorder.blocked=true;
                if(!root.check(!recorder.start(["git"],1000),"shared busy admission"))return;
                recorder.blocked=false;
                recorder.resourceCapture=resources;
                if(!root.check(!resources.busy && CpuPlusDiagnostics.setLifecycleDuration(5) && CpuPlusDiagnostics.startLifecycleCapture() && resources.busy,"joint explicit start"))return;
                root.phase=3;return;
            }
            if(root.phase===3){
                if(recorder.observing) {
                    const now=Date.now();
                    const last=recorder.run.loop.lastOffsetMs;
                    const elapsed=last===null?100:now-recorder.run.startedMs-last;
                    if(elapsed>=100)recorder.loopTick(elapsed,now);
                    return;
                }
                if(recorder.active){
                    if(!root.check(!CpuPlusDiagnostics.request("threads") && !CpuPlusDiagnostics.startLifecycleCapture(),"drain lock"))return;
                    return;
                }
                const r=recorder.report;
                if(!root.check(r && r.status==="COMPLETE" && r.resource.status==="COMPLETE" && r.resource.evidence.pid===123
                    && r.eventLoop.ticks>0 && !resources.busy,"joint completion evidence"))return;
                if(!root.check(CpuPlusDiagnostics.startLifecycleCapture(),"joint second capture"))return;
                root.phase=4;return;
            }
            if(root.phase===4){
                if(!root.check(CpuPlusDiagnostics.cancelLifecycleCapture(),"joint cancel"))return;
                root.phase=5;return;
            }
            if(root.phase===5){
                if(recorder.active)return;
                if(!root.check(recorder.report.status==="CANCELLED" && !resources.busy,"joint cancel terminal"))return;
                console.log("CPU_Q5E_JOINT_PASS");
                console.log("CPU_Q5_NATIVE_PASS");Qt.quit();
            }
        }
    }
}
