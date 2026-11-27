import QtQuick
import Quickshell
import "DiagnosticWidgetLifecycle.js" as Lifecycle

// Single shell-lifetime coordinator. No Process or repeating timer here.
Scope {
    id: recorder
    property var sources: ({})
    property bool blocked: false
    property var run: null
    readonly property bool observing: run!==null
    readonly property bool active: observing || awaitingResource
    readonly property bool finalizing: awaitingResource && !observing
    property var resourceCapture: null
    property bool awaitingResource: false
    property bool resourceRequested: false
    property bool stopRequested: false
    property var lifecycleResult: null
    property var resourceResult: null
    property var report: null
    signal completed(var result)
    function measures(id) { return observing && run.ids.includes(id); }
    function loopTick(elapsed,now) { return observing && Lifecycle.lifecycleLoopTick(run,elapsed,now); }
    function timing(id,channel,stage,mode,elapsed,now) {
        if(!measures(id))return false;
        return Lifecycle.lifecycleTiming(run,id,channel,stage,mode,elapsed,now);
    }
    function subscribed(id) {
        return observing && run.ids.includes(id) ? (sources[id] || null) : null;
    }
    function start(ids,durationMs) {
        if(active||blocked||!Lifecycle.validSelection(ids)||
            (resourceCapture && (resourceCapture.busy||resourceCapture.faulted||durationMs<5000||durationMs%1000!==0)))return false;
        const states={};
        for(const id of ids){
            const source=sources[id];
            if(!source)return false;
            states[id]=id==="media"?source.deckOpen:source.menuOpen;
        }
        const next=Lifecycle.lifecycleStart(ids,states,Date.now(),durationMs);
        if(!next)return false;
        report=null; lifecycleResult=null; resourceResult=null; stopRequested=false;
        resourceRequested=resourceCapture!==null;
        awaitingResource=resourceRequested;
        run=next;
        deadline.interval=durationMs;
        deadline.restart();
        if(resourceRequested && !resourceCapture.start(durationMs/1000,next.startedMs)){
            resourceResult={status:"NOT VERIFIED",evidence:null,reason:"RESOURCE START REFUSED"};
            // Keep the lock and finish the admitted lifecycle; mark partial.
        }
        return true;
    }
    function finalize() {
        if(!lifecycleResult || (resourceRequested&&!resourceResult))return false;
        report=Lifecycle.lifecycleCombined(lifecycleResult,resourceResult,resourceRequested,stopRequested);
        lifecycleResult=null;resourceResult=null;resourceRequested=false;awaitingResource=false;
        completed(report);
        return true;
    }
    function publish(result) {
        if(!observing)return false;
        deadline.stop();
        lifecycleResult=result || {schema:Lifecycle.lifecycleSchema,status:"FAILED",reason:"INVALID TERMINAL WITNESS"};
        run=null;
        if(resourceRequested && !resourceResult && lifecycleResult.status!=="COMPLETE" && resourceCapture)
            resourceCapture.cancel();
        finalize();
        return true;
    }
    Connections {
        target: recorder.resourceCapture
        function onCompleted(result) {
            if(!recorder.resourceRequested || recorder.resourceResult)return;
            recorder.resourceResult=result;
            recorder.finalize();
        }
    }
    function finishDeadline(now) {
        if(!observing)return false;
        if(now<run.lastMs)return publish({schema:Lifecycle.lifecycleSchema,status:"FAILED",reason:"CLOCK MOVED BACKWARDS"});
        if(now<run.deadlineMs){
            deadline.interval=Math.max(1,run.deadlineMs-now);
            deadline.restart();
            return false;
        }
        return publish(Lifecycle.lifecycleFinishObserved(run,now));
    }
    function observe(id,open) {
        if(!observing||!run.ids.includes(id))return;
        const now=Date.now();
        if(now>run.deadlineMs){finishDeadline(now);return;}
        if(!Lifecycle.lifecycleObserve(run,id,open,now))
            publish({schema:Lifecycle.lifecycleSchema,status:"FAILED",reason:run.fault||"INVALID OBSERVATION"});
    }
    function cancel() {
        if(!active||stopRequested)return false;
        stopRequested=true;
        if(observing){
            const now=Date.now();
            return publish(Lifecycle.lifecycleFinish(run,Math.min(now,run.deadlineMs),"CANCELLED"));
        }
        if(resourceRequested&&!resourceResult&&resourceCapture)resourceCapture.cancel();
        finalize();
        return true;
    }
    onBlockedChanged: if(blocked&&active)cancel()
    onSourcesChanged: if(observing)publish({schema:Lifecycle.lifecycleSchema,status:"FAILED",reason:"SOURCE MAP CHANGED"})
    Timer {
        id: deadline
        repeat: false
        onTriggered: recorder.finishDeadline(Date.now())
    }
    Connections {
        target: recorder.subscribed("appcontrol")
        function onMenuOpenChanged() { if(target)recorder.observe("appcontrol",target.menuOpen); }
    }
    Connections {
        target: recorder.subscribed("camera")
        function onMenuOpenChanged() { if(target)recorder.observe("camera",target.menuOpen); }
    }
    Connections {
        target: recorder.subscribed("hospital")
        function onMenuOpenChanged() { if(target)recorder.observe("hospital",target.menuOpen); }
    }
    Connections {
        target: recorder.subscribed("finance")
        function onMenuOpenChanged() { if(target)recorder.observe("finance",target.menuOpen); }
    }
    Connections {
        target: recorder.subscribed("git")
        function onMenuOpenChanged() { if(target)recorder.observe("git",target.menuOpen); }
    }
    Connections {
        target: recorder.subscribed("company-network")
        function onMenuOpenChanged() { if(target)recorder.observe("company-network",target.menuOpen); }
    }
    Connections {
        target: recorder.subscribed("tasks")
        function onMenuOpenChanged() { if(target)recorder.observe("tasks",target.menuOpen); }
    }
    Connections {
        target: recorder.subscribed("forest")
        function onMenuOpenChanged() { if(target)recorder.observe("forest",target.menuOpen); }
    }
    Connections {
        target: recorder.subscribed("apollo-hub")
        function onMenuOpenChanged() { if(target)recorder.observe("apollo-hub",target.menuOpen); }
    }
    Connections {
        target: recorder.subscribed("cpuplus")
        function onMenuOpenChanged() { if(target)recorder.observe("cpuplus",target.menuOpen); }
    }
    Connections {
        target: recorder.subscribed("weather")
        function onMenuOpenChanged() { if(target)recorder.observe("weather",target.menuOpen); }
    }
    Connections {
        target: recorder.subscribed("social")
        function onMenuOpenChanged() { if(target)recorder.observe("social",target.menuOpen); }
    }
    Connections {
        target: recorder.subscribed("time")
        function onMenuOpenChanged() { if(target)recorder.observe("time",target.menuOpen); }
    }
    Connections {
        target: recorder.subscribed("notifications")
        function onMenuOpenChanged() { if(target)recorder.observe("notifications",target.menuOpen); }
    }
    Connections {
        target: recorder.subscribed("media")
        function onDeckOpenChanged() { if(target)recorder.observe("media",target.deckOpen); }
    }
}
