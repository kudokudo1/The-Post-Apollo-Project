import QtQuick
import QtQuick.Window
import Quickshell
import "widgets/cpuplus"

ShellRoot {
    id: smoke
    readonly property bool armed:
        Quickshell.env("POST_APOLLO_CPU_KILL_SMOKE") === "CI_DISPOSABLE_ONLY"
    property int phase: 0
    property int ticks: 0
    property bool done: false

    QtObject {
        id: fakePresentation
        function metricIsCritical(row, key) { return false; }
        function formatMemory(kib) { return Number(kib || 0).toFixed(0) + " KiB"; }
        function hasSoftLimit(row) { return false; }
        function limitMinimumMiB(row) { return 128; }
        function limitMaximumMiB(row) { return 4096; }
        function limitMiB(row) { return 4096; }
        function limitPercent(row) { return 100; }
        function isFrozen(row) { return false; }
        function scopeProcessText(row) { return "PROCESS " + row.pid; }
    }

    QtObject {
        id: fakeGate
        property var presentationOwner: fakePresentation
        property var pending: null
        property bool busy: false
        property string feedback: ""
        property int preparations: 0
        property int confirmations: 0
        property int cancels: 0
        function exactRow(pid, ticks, name) {
            for (const r of fakeOwner.taskRows) {
                if (r.pid === pid && r.startTicks === ticks && r.comm === name)
                    return r;
            }
            return null;
        }
        function isProtected(pid, ticks, name) { return false; }
        function isUnlocked(pid, ticks, name, action) { return true; }
        function currentLimitPercent(pid, ticks, name) { return 100; }
        function toggleOneShotUnlock(pid, ticks, name) { return false; }
        function prepare(pid, ticks, name, action, percent) {
            if (pending || busy || !exactRow(pid,ticks,name))
                return false;
            pending = {pid:pid, startTicks:ticks, name:name, action:action,
                       percent:percent};
            preparations++;
            feedback = "REVIEW AND CONFIRM // NOT EXECUTED";
            return true;
        }
        function cancel() {
            if (!pending || busy) return false;
            pending = null;
            cancels++;
            feedback = "CANCELLED";
            return true;
        }
        function confirm() {
            if (!pending || !exactRow(pending.pid,pending.startTicks,pending.name))
                return false;
            confirmations++;
            pending = null;
            feedback = "SYNTHETIC CONFIRMATION";
            return true;
        }
    }

    QtObject {
        id: fakeOwner
        property var hubProcessActionGate: fakeGate
        property var taskRows: [{
            _taskRecord: true, pid: 3442, startTicks: 967833,
            comm:"synthetic-worker", name:"synthetic-worker",
            cpu:12, mem:4, rss:23456, vsz:100000,
            threads:3, state:"S", ppid:1, elapsed:"00:55",
            user:"ci", args:"synthetic-worker --test"
        }]
        property bool menuOpen: false
        property int selectedModeIndex: 0
        readonly property int killModeIndex: 7
        property int refreshes: 0
        function refreshTaskManager() { refreshes++; }
        function isTaskMetricFavorite(entry,metricId) { return false; }
        function toggleTaskMetricFavorite(entry,metricId) { }
    }

    Window {
        id: win
        visible: smoke.armed
        width: 980
        height: 690
        Loader {
            id: scene
            anchors.fill: parent
            active: smoke.armed
            sourceComponent: CpuPlusKillWorkspace {
                appControlWindow: fakeOwner
                active: smoke.armed
            }
        }
    }

    function find(item, name) {
        if (!item) return null;
        if (item.objectName === name) return item;
        for (const child of item.children || []) {
            const found = find(child,name);
            if (found) return found;
        }
        return null;
    }

    function check(ok, reason) {
        if (!ok) {
            console.error("CPU_KILL_NATIVE_FAIL // " + reason);
            done = true;
            Qt.quit();
            return false;
        }
        return true;
    }

    Timer {
        interval: 120
        repeat: true
        running: smoke.armed && !smoke.done
        onTriggered: {
            if (++smoke.ticks > 65) { smoke.check(false,"timeout"); return; }
            const view = scene.item;
            if (!view || view.width <= 0) return;
            const detail = smoke.find(view,"cpuPlusKillSharedTaskView");
            const targets = smoke.find(view,"cpuPlusKillLiveTargets");
            if (!detail || !targets || targets.count !== 1) {
                if (smoke.ticks > 12) {
                    smoke.check(false, "mount incomplete: loader="
                        + String(scene.status) + " view=" + (!!view)
                        + " detail=" + (!!detail) + " targets=" + (!!targets)
                        + " count=" + (targets ? targets.count : "none")
                        + " rows=" + fakeOwner.taskRows.length);
                }
                return;
            }

            if (smoke.phase === 0) {
                if (!smoke.check(!view.currentTask && fakeGate.preparations===0
                    && fakeGate.confirmations===0, "no default target / mutation"))
                    return;
                view.selectTarget(fakeOwner.taskRows[0]);
                smoke.phase = 1;
                return;
            }
            if (smoke.phase === 1) {
                if (!smoke.check(view.currentTask
                    && view.currentTask.pid===3442
                    && detail.visible, "shared detail mounting"))
                    return;
                if (!smoke.check(view.prepareAction("end")
                    && fakeGate.preparations===1
                    && fakeGate.confirmations===0
                    && view.hasOwnedPending, "prepare without execution"))
                    return;
                view.cancelOwned();
                smoke.phase = 2;
                return;
            }
            if (smoke.phase === 2) {
                if (!smoke.check(fakeGate.pending===null
                    && fakeGate.cancels===1
                    && fakeGate.confirmations===0, "cancelled without execution"))
                    return;
                if (!smoke.check(view.prepareAction("freeze")
                    && view.hasOwnedPending, "freeze prepared")) return;
                fakeGate.confirm();
                smoke.phase = 3;
                return;
            }
            if (smoke.phase === 3) {
                if (!smoke.check(fakeGate.confirmations===1
                    && fakeGate.pending===null
                    && !view.hasOwnedPending, "confirm controls only"))
                    return;
                fakeOwner.taskRows = [];
                smoke.phase = 4;
                return;
            }
            if (!smoke.check(!view.currentTask && !view.exactTargetAvailable
                && !view.prepareAction("end"), "stale selection refusal"))
                return;
            console.log("CPU_KILL_NATIVE_PASS");
            smoke.done = true;
            Qt.quit();
        }
    }

    Component.onCompleted: if (!armed) Qt.quit()
}
