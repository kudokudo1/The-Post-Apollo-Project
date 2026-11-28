import QtQuick
import Quickshell
import "services/kill" as KillBackend
import "services/system"

// Production shared gateway, real helper, disposable same-user process only.
ShellRoot {
    id: smoke
    readonly property bool armed: Quickshell.env("POST_APOLLO_CPU_KILL_SMOKE") === "CI_DISPOSABLE_ONLY"
    readonly property var identity: JSON.parse(Quickshell.env("POST_APOLLO_KILL_PRIORITY_CHILD") || "null")
    property var rows: []
    property int phase: 0
    property int ticks: 0
    property bool done: false
    property int original: 0
    property int requested: 0
    property var baseline: null
    function row(birth,name) {
        return {_taskRecord:true,pid:identity[0],startTicks:birth,comm:name,user:"ci-child"};
    }
    function record() {
        return gate.priorityRecordFor(identity[0],identity[1],identity[2]);
    }
    function capture() { return gate.capturePriority(identity[0],identity[1],identity[2]); }
    function prepare(operation,value) {
        return gate.preparePriority(identity[0],identity[1],identity[2],operation,value);
    }
    function check(ok,label) {
        if (ok) return true;
        console.error("KILL_PRIORITY_NATIVE_FAIL " + label + " // " + gate.feedback);
        done=true;
        Qt.quit();
        return false;
    }
    function pass(label) {
        console.log("KILL_PRIORITY_NATIVE_PASS " + label);
        done=true;
        Qt.quit();
    }
    TaskSafety { id: safety }
    QtObject {
        id: limits
        property bool applyLoading: false
        property var queuedRequest: null
        signal limitCompleted(var result)
    }
    Timer { id: refresh; interval: 10; repeat: false }
    KillBackend.AppControlHubActionGate {
        id: gate
        ownerRows: smoke.rows
        safetyOwner: safety
        presentationOwner: null
        controlOwner: null
        limitsOwner: limits
        refreshOwner: refresh
    }
    Timer {
        interval: 50
        repeat: true
        running: smoke.armed && !smoke.done
        onTriggered: {
            if (++smoke.ticks>350) { smoke.check(false,"bounded lifecycle"); return; }
            if (smoke.phase===0) {
                if (!smoke.check(smoke.identity && smoke.identity.length===3 && !gate.busy
                    && !smoke.capture() && !gate.confirm(),"no implicit dispatch or absent target")) return;
                smoke.rows=[smoke.row(smoke.identity[1],"sway")];
                if (!smoke.check(!gate.capturePriority(smoke.identity[0],smoke.identity[1],"sway"),
                    "protected target rejected before helper")) return;
                smoke.rows=[smoke.row(smoke.identity[1],smoke.identity[2])];
                gate.bulkBlocked=true;
                if (!smoke.check(!smoke.capture(),"bulk exclusion")) return;
                gate.bulkBlocked=false;
                limits.applyLoading=true;
                if (!smoke.check(!smoke.capture(),"limit exclusion")) return;
                limits.applyLoading=false;
                if (!smoke.check(!smoke.prepare("apply",5) && smoke.capture() && gate.busy
                    && !smoke.capture() && !gate.confirm(),"explicit capture and busy exclusion")) return;
                smoke.phase=1;
            } else if (smoke.phase===1 && !gate.busy) {
                const rec=smoke.record();
                if (!smoke.check(rec && rec.state==="observed" && rec.current.uid>0
                    && rec.original===rec.current.nice && gate.priorityRequest===null
                    && gate.pending===null,"real unprivileged original capture")) return;
                smoke.baseline=JSON.stringify(rec);
                smoke.original=rec.original;
                smoke.rows=[smoke.row(smoke.identity[1]+1,smoke.identity[2])];
                if (!smoke.check(gate.capturePriority(smoke.identity[0],smoke.identity[1]+1,smoke.identity[2]),
                    "stale birth reaches real helper")) return;
                smoke.phase=2;
            } else if (smoke.phase===2 && !gate.busy) {
                const stale=gate.priorityRecordFor(smoke.identity[0],smoke.identity[1]+1,smoke.identity[2]);
                if (!smoke.check(stale && stale.state==="unavailable"
                    && JSON.stringify(smoke.record())===smoke.baseline,"stale reply isolated from original")) return;
                smoke.rows=[smoke.row(smoke.identity[1],smoke.identity[2])];
                const soft=smoke.record().current.soft;
                const candidate=[smoke.original+1,smoke.original-1].find(n=>n>=-20 && n<=19
                    && soft>=1 && soft<=40 && Math.min(n,smoke.original)>=20-soft);
                if (candidate===undefined) {
                    const impossible=smoke.original<19 ? smoke.original+1 : smoke.original-1;
                    if (!smoke.check(!smoke.prepare("apply",impossible) && !gate.pending
                        && !gate.busy && !gate.confirm(),"irreversible request refused before mutation")) return;
                    smoke.pass("REFUSAL_ONLY");
                    return;
                }
                smoke.requested=candidate;
                if (!smoke.check(smoke.prepare("apply",candidate) && !gate.busy
                    && gate.pending.target===candidate && gate.cancel() && !gate.pending,
                    "review cancellation dispatches nothing")) return;
                if (!smoke.check(smoke.prepare("apply",candidate) && gate.confirm()
                    && gate.busy && !gate.confirm(),"single confirmed dispatch")) return;
                smoke.phase=3;
            } else if (smoke.phase===3 && !gate.busy) {
                const rec=smoke.record();
                if (!smoke.check(rec && rec.state==="managed" && rec.original===smoke.original
                    && rec.current.nice===smoke.requested && !gate.pending,"real apply readback")) return;
                if (!smoke.check(smoke.prepare("restore",smoke.original) && gate.confirm(),"explicit restore")) return;
                smoke.phase=4;
            } else if (smoke.phase===4 && !gate.busy) {
                if (!smoke.check(JSON.stringify(smoke.record())===smoke.baseline && !gate.pending,
                    "real original restoration readback")) return;
                smoke.pass("ROUNDTRIP");
            }
        }
    }
    Component.onCompleted: if (!armed) Qt.quit()
}
