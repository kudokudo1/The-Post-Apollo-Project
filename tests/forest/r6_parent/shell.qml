import QtQuick
import Quickshell

ShellRoot {
    id: witness
    property int scenario: 0
    property var active: null
    property int steps: 0
    property string last: ""
    property bool failed: false
    property var modes: ["commit","refuse","detach","two-commit-stop","history"]
    property int commits: 0
    property int historyStage: 0
    property string firstAlias: ""
    property bool sawStop: false
    property bool sawAbort: false
    property var oldRef: null
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
        steps=0; last=""; commits=0; sawStop=false; sawAbort=false; oldRef=null; historyStage=0; firstAlias="";
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
            else if (scenario===2)
                ok=ok && p.failure==="OWNER_LOST" && p.outcome==="UNKNOWN_HOLD"
                    && p.action===2 && p.cleanupStarted;
            else if (scenario===3)
                ok=ok && !p.failure && p.closeResult && last==="CLOSED"
                    && commits===2 && sawStop && sawAbort && p.turnsStarted===3
                    && p.action===21 && p.outcome==="ABORTED_LOCAL" && stats.ended;
            else ok=ok && !p.failure && p.closeResult && last==="CLOSED"
                && historyStage===5 && p.action===13 && p.historyScope===null && stats.ended;
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
            if (witness.scenario===4) {
                const id = n => ("0000000000000000000000000000000"+n);
                if (witness.last==="READY") ok=p.request("HISTORY_ATTACH");
                else if (witness.last==="HISTORY_ATTACHED") {
                    ok=p.historyScope.revision===(witness.historyStage===0?0:2)
                        && p.request("HISTORY_PAGE",id(witness.historyStage===0?1:2),1);
                } else if (witness.last==="PAGE_READY") {
                    const d=p.historyDisplay;
                    if (witness.historyStage===0) {
                        witness.historyStage=1;
                        witness.firstAlias=p.sessionAlias;
                        ok=d.state==="COMPLETE" && d.messages.length===0
                            && !p.request("HISTORY_PAGE",id(3),1) && p.request("NEXT")
                            && p.historyScope===null;
                    } else if (witness.historyStage===2) {
                        witness.historyStage=3;
                        ok=d.state==="PARTIAL" && d.messages.length===1 && d.nextAfter===1
                            && !p.request("HISTORY_PAGE",id(2),1)
                            && p.request("HISTORY_PAGE",id(3),1);
                    } else if (witness.historyStage===3) {
                        witness.historyStage=5;
                        ok=d.state==="COMPLETE" && d.messages.length===2
                            && d.messages[0].direction==="outgoing" && d.messages[1].direction==="incoming"
                            && p.sessionAlias===witness.firstAlias && p.status==="LOCAL_COMMIT_RECORDED"
                            && p.request("CLOSE");
                    }
                } else if (witness.last==="TURN_STARTED" || witness.last==="ACTIVE") {
                    witness.steps++;
                    ok=p.historyScope===null && witness.steps<=5 && p.request("STEP");
                } else if (witness.last==="COMMITTED_LOCAL") {
                    witness.historyStage=2;
                    ok=p.historyScope===null && witness.steps===5 && p.request("HISTORY_ATTACH");
                } else if (witness.last==="CLOSED") return;
            } else if (witness.last==="READY") ok=p.request("NEXT");
            else if (witness.last==="TURN_STARTED" && witness.scenario===2) {
                // Different owner object, independently observed after true ACK.
                p.observedOwner=ownerB;
                ok=p.cleanupStarted && p.ref===null && p.outcome==="UNKNOWN_HOLD";
            } else if (witness.scenario===3) {
                if (witness.last==="TURN_STARTED") {
                    if (p.sequence!==0 || p.status!=="" || !p.ref
                        || (witness.oldRef && (p.ref.requestId===witness.oldRef.requestId
                            || p.ref.viewKey===witness.oldRef.viewKey))) {
                        witness.fail("new lifetime"); return;
                    }
                    witness.steps=1;
                    ok=p.request("STEP");
                } else if (witness.last==="ACTIVE") {
                    if (p.turnsStarted===3 && witness.steps===4) {
                        ok=!p.request("STEP") && p.status==="GENERATING"
                            && p.request("STOP");
                    } else {
                        witness.steps++;
                        ok=witness.steps<=5 && p.request("STEP");
                    }
                } else if (witness.last==="COMMITTED_LOCAL") {
                    witness.commits++;
                    witness.oldRef=p.ref;
                    ok=witness.steps===5 && p.sequence===4
                        && p.status==="LOCAL_COMMIT_RECORDED"
                        && witness.commits<=2 && p.request("NEXT");
                } else if (witness.last==="STOP_OBSERVED") {
                    witness.sawStop=p.phase==="ACTIVE" && p.status==="STOP_REQUESTED"
                        && p.outcome!=="ABORTED_LOCAL";
                    ok=witness.sawStop && !p.request("STOP") && p.request("STEP");
                } else if (witness.last==="ABORTED_LOCAL") {
                    witness.sawAbort=p.phase==="BLOCKED" && p.outcome==="ABORTED_LOCAL";
                    ok=witness.sawAbort && !p.request("NEXT") && !p.request("STEP")
                        && !p.request("STOP") && p.request("CLOSE");
                } else if (witness.last==="CLOSED") return;
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
