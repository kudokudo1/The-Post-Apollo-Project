import QtQuick
import Quickshell

ShellRoot {
    id: witness
    property int scenario: 0
    property var active: null
    property int steps: 0
    property string last: ""
    property bool failed: false
    property var modes: ["commit","refuse","detach"]
    QtObject { id: ownerA }
    QtObject { id: ownerB }
    function fail(reason) {
        if (failed) return;
        failed = true;
        console.error("R6_PARENT_FAIL " + reason);
        if (active && !active.reaped) active.hold("HARNESS");
        else Qt.quit();
    }
    function startCase() {
        if (active !== null || scenario >= modes.length) { fail("case start"); return; }
        steps=0; last="";
        const p = trialType.createObject(witness,{
            trial:String(scenario+1).repeat(32),
            fixtureDirectory:Quickshell.shellPath("private"+scenario),
            originalOwner:ownerA, observedOwner:ownerA, eligible:true,
            acceptOffer:scenario!==1});
        if (!p) { fail("create"); return; }
        active=p;
        p.actionFinished.connect(function(code) {
            if (active !== p || failed) { fail("stale action"); return; }
            last=code;
            // Never dispatch another action inside a framing callback.
            drive.restart();
        });
        p.finished.connect(function() {
            if (active !== p) { fail("stale exit"); return; }
            if (failed) { Qt.quit(); return; }
            const stats=p.wire.snapshot();
            let ok=p.reaped && !p.running && p.ref===null && p.status===""
                && stats.retained===0 && stats.bytes<=131072 && stats.frames<=160;
            if (scenario===0)
                ok=ok && !p.failure && p.closeResult && last==="CLOSED"
                    && p.outcome==="COMMITTED_LOCAL" && steps===5
                    && p.action===8 && stats.ended;
            else if (scenario===1)
                ok=ok && !p.failure && p.refusedResult && last==="REFUSED"
                    && p.outcome==="REFUSED" && p.action===2 && stats.ended;
            else
                ok=ok && p.failure==="OWNER_LOST" && p.outcome==="UNKNOWN_HOLD"
                    && p.action===2 && p.cleanupStarted;
            if (!ok) { fail("terminal evidence "+scenario); return; }
            console.info("R6_PARENT_CASE_PASS "+scenario+" "+modes[scenario]
                +" actions="+p.action+" bytes="+stats.bytes+" frames="+stats.frames);
            active=null;
            p.destroy();
            scenario++;
            if (scenario===modes.length) {
                console.info("R6_PARENT_NATIVE_PASS");
                Qt.quit();
            } else Qt.callLater(startCase); // explicit CI case, not a runtime restart
        });
        if (!p.start()) fail("start");
    }
    Component { id: trialType; ParentProcess {} }
    Timer {
        id: drive
        interval: 30
        onTriggered: {
            const p=witness.active;
            if (!p || witness.failed) return;
            let ok=false;
            if (witness.last==="READY") ok=p.request("NEXT");
            else if (witness.last==="TURN_STARTED" && witness.scenario===2) {
                // Different owner object, independently observed after true ACK.
                p.observedOwner=ownerB;
                ok=p.cleanupStarted && p.ref===null && p.outcome==="UNKNOWN_HOLD";
            } else if (witness.last==="TURN_STARTED" || witness.last==="ACTIVE") {
                witness.steps++;
                ok=witness.steps<=5 && p.request("STEP");
            } else if (witness.last==="COMMITTED_LOCAL") {
                ok=witness.steps===5 && p.sequence===4
                    && p.status==="LOCAL_COMMIT_RECORDED" && p.request("CLOSE");
            } else if (witness.last==="REFUSED" || witness.last==="CLOSED") return;
            if (!ok) witness.fail("explicit action "+witness.scenario);
        }
    }
    Timer { interval: 35000; running:true; onTriggered:witness.fail("outer deadline") }
    Component.onCompleted: Qt.callLater(startCase)
}
