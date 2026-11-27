import QtQuick
import Quickshell
import "DiagnosticWidgetLifecycle.js" as Lifecycle

// Passive, single shell-lifetime observer. No Process, polling, or actuation.
Scope {
    id: recorder
    property var sources: ({})
    property bool blocked: false
    property var run: null
    readonly property bool active: run!==null
    property var report: null
    signal completed(var result)
    function measures(id) { return active && run.ids.includes(id); }
    function timing(id,channel,stage,mode,elapsed,now) {
        if(!measures(id))return false;
        return Lifecycle.lifecycleTiming(run,id,channel,stage,mode,elapsed,now);
    }
    function subscribed(id) {
        return active && run.ids.includes(id) ? (sources[id] || null) : null;
    }
    function start(ids,durationMs) {
        if(active||blocked||!Lifecycle.validSelection(ids))return false;
        const states={};
        for(const id of ids){
            const source=sources[id];
            if(!source)return false;
            states[id]=id==="media"?source.deckOpen:source.menuOpen;
        }
        const next=Lifecycle.lifecycleStart(ids,states,Date.now(),durationMs);
        if(!next)return false;
        report=null;
        run=next;
        deadline.interval=durationMs;
        deadline.restart();
        return true;
    }
    function publish(result) {
        if(!active)return false;
        deadline.stop();
        run=null;
        report=result || {schema:Lifecycle.lifecycleSchema,status:"FAILED",reason:"INVALID TERMINAL WITNESS"};
        completed(report);
        return true;
    }
    function finishDeadline(now) {
        if(!active)return false;
        if(now<run.lastMs)return publish({schema:Lifecycle.lifecycleSchema,status:"FAILED",reason:"CLOCK MOVED BACKWARDS"});
        if(now<run.deadlineMs){
            deadline.interval=Math.max(1,run.deadlineMs-now);
            deadline.restart();
            return false;
        }
        return publish(Lifecycle.lifecycleFinishObserved(run,now));
    }
    function observe(id,open) {
        if(!active||!run.ids.includes(id))return;
        const now=Date.now();
        if(now>run.deadlineMs){finishDeadline(now);return;}
        if(!Lifecycle.lifecycleObserve(run,id,open,now))
            publish({schema:Lifecycle.lifecycleSchema,status:"FAILED",reason:run.fault||"INVALID OBSERVATION"});
    }
    function cancel() {
        if(!active)return false;
        const now=Date.now();
        return publish(Lifecycle.lifecycleFinish(run,now,"CANCELLED"));
    }
    onBlockedChanged: if(blocked&&active)cancel()
    onSourcesChanged: if(active)publish({schema:Lifecycle.lifecycleSchema,status:"FAILED",reason:"SOURCE MAP CHANGED"})
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
