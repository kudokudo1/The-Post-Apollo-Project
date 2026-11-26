import QtQuick
import Quickshell
import "widgets/appcontrol"

ShellRoot {
    id: root
    property var first: ({pid:3010,startTicks:10,comm:"alpha",identity:"alpha"})
    property var second: ({pid:3011,startTicks:20,comm:"beta",identity:"beta"})
    property var third: ({pid:3012,startTicks:30,comm:"gamma",identity:"gamma"})
    property var fourth: ({pid:3013,startTicks:40,comm:"delta",identity:"delta"})
    QtObject {
        id: fakeHost
        property var taskRows: [root.first,root.second,root.third,root.fourth]
        property string destructiveConfirmMessage: ""
        property string destructiveConfirmKind: ""
        property string destructiveConfirmTitle: ""
        property int destructiveConfirmChoice: 0
        property bool destructiveConfirmOpen: false
        property var destructiveConfirmTargetPids: []
        property bool cancelled: false
        function taskPersistentIdentity(row) { return row.identity; }
        function taskEligibleForKillAll(row) { return !row.protected; }
        function hunterMouseProtectedReason(row) { return row.protected ? "PROTECTED" : ""; }
        function cancelDestructiveConfirm() { cancelled=true; }
    }
    QtObject { id: favorites; property var favoriteKeys: [] }
    QtObject { id: refresh; function restart() {} }
    QtObject {
        id: engine
        property bool running: false
        property var calls: []
        function start(batch) {
            if (running || batch.length !== 1) return false;
            calls = calls.concat([batch[0]]);
            running = true;
            return true;
        }
        function exit(withResult) {
            const target=calls[calls.length-1];
            if (withResult) {
                controller.applyResult({pid:target.pid,name:target.name,status:"killed",detail:"FAKE"});
                controller.applyResult({pid:target.pid,name:target.name,status:"killed",detail:"DUPLICATE"});
            }
            running=false;
            controller.finish();
        }
    }
    HunterOperationController {
        id: controller
        host: fakeHost
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
        const captured=controller.targetsFromRows(fakeHost.taskRows);
        controller.start("kill-hogs",[captured[0],captured[0]]);
        if (!check(fakeHost.cancelled && engine.calls.length===0,"duplicate capture refused")) return;
        controller.start("kill-hogs",captured);
        if (!check(engine.calls.length===1 && engine.running,"one target dispatched")) return;
        favorites.favoriteKeys=["task|beta"];
        fakeHost.taskRows=[first,second,{pid:3012,startTicks:31,comm:"gamma",identity:"gamma"},fourth];
        engine.exit(true);
        Qt.callLater(function() {
            if (!check(engine.calls.length===2 && engine.calls[1].pid===fourth.pid
                       && controller.results.length===3
                       && controller.results[1].status==="favorite"
                       && controller.results[2].status==="gone","live favorite and birth changes withheld")) return;
            engine.exit(true);
            Qt.callLater(function() {
                if (!check(controller.phase==="report" && controller.results.length===4,"one result per capture")) return;
                favorites.favoriteKeys=[];
                fakeHost.taskRows=[first,second,third,fourth];
                controller.start("kill-mice",controller.targetsFromRows(fakeHost.taskRows));
                if (!check(engine.calls.length===3,"second operation began")) return;
                engine.exit(false);
                if (!check(controller.phase==="report" && controller.results.length===4
                           && engine.calls.length===3,"unknown result stops remaining dispatch")) return;
                console.log("HUNTER_SERIAL_PASS");
                Qt.quit();
            });
        });
    }
}
