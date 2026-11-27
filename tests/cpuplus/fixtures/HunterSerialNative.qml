import QtQuick
import Quickshell
import "services/kill"

ShellRoot {
    id: root
    property var first: ({pid:3010,startTicks:10,comm:"alpha",identity:"alpha"})
    property var second: ({pid:3011,startTicks:20,comm:"beta",identity:"beta"})
    property var third: ({pid:3012,startTicks:30,comm:"gamma",identity:"gamma"})
    property var fourth: ({pid:3013,startTicks:40,comm:"delta",identity:"delta"})
    QtObject {
        id: fakeHost
        property string destructiveConfirmMessage: ""
        property string destructiveConfirmKind: ""
        property string destructiveConfirmTitle: ""
        property int destructiveConfirmChoice: 0
        property bool destructiveConfirmOpen: false
        property var destructiveConfirmTargetPids: []
        property bool cancelled: false
        function cancelDestructiveConfirm() { cancelled=true; }
    }
    QtObject {
        id: policy
        property bool collectionEnabled: true
        property var rows: [root.first,root.second,root.third,root.fourth]
        function taskEligibleForKillAll(row) { return !row.protected; }
        function hunterMouseProtectedReason(row) { return row.protected ? "PROTECTED" : ""; }
    }
    QtObject { id: favorites; property var favoriteKeys: [] }
    QtObject { id: refresh; function restart() {} }
    QtObject {
        id: engine
        property bool running: false
        property bool completionVerified: false
        property var calls: []
        function start(batch) {
            if (running || batch.length !== 1) return false;
            calls = calls.concat([batch[0]]);
            running = true;
            return true;
        }
        function exit(withResult, mode) {
            const target=calls[calls.length-1];
            completionVerified = mode !== "abnormal" && mode !== "malformed"
                && mode !== "timeout" && withResult;
            if (withResult) {
                controller.applyResult({pid:target.pid,name:target.name,
                    status:mode === "escaped" ? "escaped" : "killed",detail:"FAKE"});
                if (mode === "duplicate")
                    controller.applyResult({pid:target.pid,name:target.name,status:"killed",detail:"DUPLICATE"});
            }
            running=false;
            controller.finish();
        }
    }
    HunterOperationController {
        id: controller
        legacyPresentationAvailable: true
        onLegacyMessagePublished: function(value) {
            fakeHost.destructiveConfirmMessage=value;
        }
        onLegacyWindowRequested: function(operationKind, title, resetChoice, clearTargets) {
            if (clearTargets) fakeHost.destructiveConfirmTargetPids=[];
            fakeHost.destructiveConfirmKind=operationKind;
            if (resetChoice) fakeHost.destructiveConfirmChoice=0;
            if (title) fakeHost.destructiveConfirmTitle=title;
            fakeHost.destructiveConfirmOpen=true;
        }
        onLegacyReviewRejected: fakeHost.cancelDestructiveConfirm()
        policyOwner: policy
        favoriteStoreObject: favorites
        executor: engine
        refreshTimer: refresh
    }
    function check(ok, reason) {
        if (!ok) {
            console.error("HUNTER_SERIAL_FAIL // "+reason);
            Qt.quit();
        }
        return ok;
    }
    Timer {
        interval: 100
        running: true
        repeat: false
        onTriggered: root.runChecks()
    }
    function runChecks() {
        if (Quickshell.env("POST_APOLLO_HUNTER_DISPOSABLE_CI") !== "1") {Qt.quit();return;}
        const captured=controller.targetsFromRows(policy.rows);
        controller.start("kill-hogs",[captured[0],captured[0]]);
        if (!check(fakeHost.cancelled && engine.calls.length===0,"duplicate capture refused")) return;
        controller.start("kill-hogs",captured);
        if (!check(engine.calls.length===1 && engine.running
                   && fakeHost.destructiveConfirmOpen
                   && fakeHost.destructiveConfirmKind==="kill-hogs"
                   && fakeHost.destructiveConfirmTitle.indexOf("HUNTING HOGS")>=0
                   && fakeHost.destructiveConfirmMessage.indexOf("HUNTING HOGS")>=0,
                   "one target dispatched and legacy presentation events applied")) return;
        favorites.favoriteKeys=["task|beta"];
        policy.rows=[first,second,{pid:3012,startTicks:31,comm:"gamma",identity:"gamma"},fourth];
        engine.exit(true);
        Qt.callLater(function() {
            if (!check(engine.calls.length===2 && engine.calls[1].pid===fourth.pid
                       && controller.results.length===3
                       && controller.results[1].status==="favorite"
                       && controller.results[2].status==="gone","live favorite and birth changes withheld")) return;
            engine.exit(true);
            Qt.callLater(function() {
                if (!check(controller.phase==="report" && controller.results.length===4
                           && fakeHost.destructiveConfirmTitle.indexOf("HOG HUNT COMPLETE")>=0
                           && fakeHost.destructiveConfirmMessage.indexOf("HOGS HUNT REPORT")>=0,
                           "one result per capture and legacy report published")) return;
                favorites.favoriteKeys=[];
                policy.rows=[first,second,third,fourth];
                controller.start("kill-mice",controller.targetsFromRows(policy.rows));
                if (!check(engine.calls.length===3,"second operation began")) return;
                engine.exit(false);
                if (!check(controller.phase==="report" && controller.results.length===4
                           && engine.calls.length===3,"unknown result stops remaining dispatch")) return;
                for (const mode of ["escaped","abnormal","malformed","timeout","duplicate"]) {
                    const before=engine.calls.length;
                    controller.start("kill-hogs",controller.targetsFromRows(policy.rows));
                    engine.exit(true,mode);
                    if (!check(controller.phase==="report" && engine.calls.length===before+1
                            && controller.results.length===4
                            && controller.results[0].status==="escaped"
                            && controller.results[1].detail.indexOf("NOT ATTEMPTED")===0,
                            "fail closed after "+mode)) return;
                }
                const priorCalls=engine.calls.length;
                controller.start("kill-all",[]);
                if (!check(engine.calls.length===priorCalls,"empty Kill All never expands")) return;
                controller.start("kill-all",[captured[0]]);
                if (!check(engine.calls.length===priorCalls+1
                           && engine.calls[priorCalls].pid===first.pid
                           && controller.operationLabel()==="ALL","Kill All uses exact serial capture")) return;
                engine.exit(true);
                Qt.callLater(function() {
                    if (!check(controller.phase==="report" && controller.results.length===1
                               && engine.calls.length===priorCalls+1,"Kill All reports reviewed set only")) return;
                    const before=engine.calls.length;
                    controller.legacyPresentationAvailable=false;
                    fakeHost.destructiveConfirmOpen=false;
                    const legacyMessage=fakeHost.destructiveConfirmMessage;
                    controller.start("kill-all",[captured[0]],false);
                    if (!check(engine.calls.length===before && !fakeHost.destructiveConfirmOpen,
                               "legacy admission requires presentation availability")) return;
                    policy.collectionEnabled=false;
                    controller.start("kill-all",[captured[0]],true);
                    if (!check(engine.calls.length===before,"unavailable policy refused")) return;
                    policy.collectionEnabled=true;
                    controller.start("kill-all",[captured[0]],true);
                    if (!check(engine.calls.length===before+1 && controller.recipientOwned,
                               "recipient starts without legacy dialog host")) return;
                    policy.collectionEnabled=false;
                    engine.exit(true);
                    Qt.callLater(function() {
                        if (!check(controller.phase==="report" && controller.results.length===1
                                   && !fakeHost.destructiveConfirmOpen
                                   && fakeHost.destructiveConfirmMessage===legacyMessage,
                                   "recipient report without legacy host")) return;
                        console.log("HUNTER_SERIAL_PASS");
                        Qt.quit();
                    });
                });
            });
        });
    }
}
