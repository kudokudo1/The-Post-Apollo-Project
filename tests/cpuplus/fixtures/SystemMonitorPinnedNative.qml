import QtQuick
import QtQuick.Window
import Quickshell
import "widgets/appcontrol"

ShellRoot {
    id: smoke
    readonly property bool armed: Quickshell.env("POST_APOLLO_SYSTEM_PIN_SMOKE") === "CI_DISPOSABLE_ONLY"
    property int phase: 0
    property int ticks: 0
    property real fixedY: 0
    property real actionY: 0
    property bool done: false

    QtObject {
        id: fakeController
        property string savedSystemWatchSourceId: ""
        property string savedSystemWatchBoxId: ""
        property bool systemRebootArmed: false
        property int calls: 0
        property var record: ({id:"memory:test", category:"MEMORY", usage:70, metric:"22 / 32 GiB",
            role:"ACTIVE RAM ALLOCATION", secondary:"22 GiB / 32 GiB", detail:"AVAILABLE 10 GiB",
            contributorNote:"Synthetic contributors", canDisconnect:false, canReconnect:false, canReboot:true})
        property var rows: Array.from({length:24}, (_,i)=>({name:"synthetic " + i,pid:1000+i,valueText:"12 MiB",killable:false}))
        function selectedResultIsSystemComponent() { return true; }
        function selectedResult() { return record; }
        function favoriteSourceItem(entry) { return entry; }
        function systemAccent(entry) { return "#55CFCA"; }
        function isMonitorBoxFavorite(entry, box) { return false; }
        function toggleMonitorBoxFavorite(entry, box) { calls++; }
        function systemRateMetricParts(entry) { return []; }
        function systemIconFor(entry) { return "M"; }
        function systemComponentWarning(entry) { return "TEST ONLY"; }
        function runSystemComponentAction(entry, action) { calls++; }
        function contributorRows(entry) { return rows; }
        function terminateSystemContributor(entry) { calls++; }
    }
    Window {
        id: win
        visible: smoke.armed
        width: 390
        height: 450
        Loader {
            id: scene
            anchors.fill: parent
            active: smoke.armed
            sourceComponent: SystemMonitorView {
                pinnedInstrument: true
                controller: fakeController
            }
        }
    }
    function find(item, name) {
        if (!item) return null;
        if (item.objectName === name) return item;
        for (const child of item.children || []) {
            const found = find(child, name);
            if (found) return found;
        }
        return null;
    }
    function check(ok, reason) {
        if (!ok) {
            done = true;
            console.error("SYSTEM_PIN_NATIVE_FAIL // " + reason);
            Qt.quit();
        }
        return ok;
    }
    Timer {
        interval: 120
        repeat: true
        running: smoke.armed && !smoke.done
        onTriggered: {
            if (++smoke.ticks > 60) { smoke.check(false,"timeout"); return; }
            const view = scene.item;
            if (!view || view.height <= 0) return;
            const fixed = smoke.find(view,"systemMonitorFixedInstrument");
            const actions = smoke.find(view,"systemMonitorFixedActions");
            const scroll = smoke.find(view,"systemMonitorContributorScroll");
            if (!fixed || !actions || !scroll || scroll.contentHeight <= 0) return;
            if (smoke.phase === 0) {
                if (!smoke.check(scroll.height > 50 && scroll.contentHeight > scroll.height && scroll.interactive,
                    "contributor viewport " + scroll.height + "/" + scroll.contentHeight)) return;
                smoke.fixedY = fixed.mapToItem(view,0,0).y;
                smoke.actionY = actions.mapToItem(view,0,0).y;
                scroll.contentY = 150;
                smoke.phase++;
                return;
            }
            if (smoke.phase === 1) {
                if (!smoke.check(scroll.contentY > 0 && fixed.mapToItem(view,0,0).y === smoke.fixedY
                    && actions.mapToItem(view,0,0).y === smoke.actionY, "fixed positions changed")) return;
                fakeController.record = Object.assign({},fakeController.record,{usage:75});
                smoke.phase++;
                return;
            }
            if (smoke.phase === 2) {
                if (!smoke.check(scroll.contentY > 0,"same identity refresh reset")) return;
                fakeController.record = Object.assign({},fakeController.record,{id:"memory:next"});
                smoke.phase++;
                return;
            }
            if (smoke.phase === 3) {
                if (!smoke.check(scroll.contentY === 0 && fakeController.calls === 0,"source reset or unintended action")) return;
                view.pinnedInstrument = false;
                smoke.phase++;
                return;
            }
            if (!smoke.check(!scroll.interactive && Math.abs(scroll.height-scroll.contentHeight)<1,
                "legacy full-height flow")) return;
            console.log("SYSTEM_PIN_NATIVE_PASS");
            smoke.done = true;
            Qt.quit();
        }
    }
    Component.onCompleted: if (!armed) Qt.quit()
}
