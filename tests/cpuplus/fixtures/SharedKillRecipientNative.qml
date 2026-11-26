import QtQuick
// P3c3 main-lineage native qualification: exercise the recipient after the P3c2 parent merge.
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
    property int previousRevision: 0
    property var lastRow: null

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
        function isProtected(pid, ticks, name) { return !!exactRow(pid,ticks,name); }
        function isUnlocked(pid, ticks, name, action) {
            return !!exactRow(pid,ticks,name) && fakeOwner.taskDangerActionUnlockMode(
                exactRow(pid,ticks,name),action)!=="";
        }
        function currentLimitPercent(pid, ticks, name) { return 100; }
        function toggleOneShotUnlock(pid, ticks, name) {
            if (!exactRow(pid,ticks,name)) return false;
            fakeOwner.masterMode=fakeOwner.masterMode ? "" : "once";
            return true;
        }
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
            id: "task:3442", _taskRecord: true, pid: 3442, startTicks: 967833,
            comm:"synthetic-worker", name:"synthetic-worker",
            cpu:12, mem:4, rss:23456, vsz:100000,
            threads:3, state:"S", ppid:1, elapsed:"00:55",
            user:"ci", args:"synthetic-worker --test"
        }]
        property var taskMiniCpuHistories: ({"pid:3442":[2,5,12]})
        property var taskMiniHunterMetricHistories: ({
            "cpu:pid:3442":[2,5,12], "mem:pid:3442":[20,21,23],
            "io:pid:3442":[0,1,2], "age:pid:3442":[0.5,0.7,0.9],
            "combined:pid:3442":[2,6,14]})
        property int taskMiniDisplayRevision: 1
        property var favoriteStore: QtObject { property var favoriteKeys: [] }
        property bool destructiveConfirmOpen: false
        property var cpuBulkReview: null
        property bool cpuBulkOperation: false
        property string hunterOperationPhase: "idle"
        property string hunterOperationKind: ""
        property string cpuBulkMessage: ""
        property int bulkConfirmed: 0
        property int bulkCancelled: 0
        function cpuBulkCandidates(kind,metric,visibility) { return taskRows; }
        function prepareCpuBulkReview(kind,metric,visibility) {
            if (cpuBulkReview || cpuBulkOperation) return null;
            cpuBulkReview={kind:kind,metric:metric,visibility:visibility,label:"FAKE",
                targets:[{pid:3442,startTicks:967833,name:"synthetic-worker"}]};
            return cpuBulkReview;
        }
        function cancelCpuBulkReview(review) {
            if (review !== cpuBulkReview) return false;
            cpuBulkReview=null; bulkCancelled++; return true;
        }
        function confirmCpuBulkReview(review) {
            if (review !== cpuBulkReview) return false;
            hunterOperationKind=review.kind; cpuBulkReview=null;
            cpuBulkOperation=true; hunterOperationPhase="running"; bulkConfirmed++;
            return true;
        }
        function acknowledgeCpuBulkReport() {
            cpuBulkOperation=false; hunterOperationPhase="idle"; return true;
        }
        property string masterMode: ""
        property var actionModes: ({})
        function taskRequiresDangerUnlock(row) { return !!row; }
        function taskDangerUnlockMode(row) { return masterMode; }
        function taskDangerActionUnlockMode(row,action) {
            return masterMode || String(actionModes[action] || "");
        }
        function toggleTaskDangerStickyUnlock(row) {
            masterMode=masterMode==="sticky"?"":"sticky";
        }
        function toggleTaskDangerActionStickyUnlock(row,action) {
            let next=Object.assign({},actionModes);
            next[action]=next[action]==="sticky"?"":"sticky";
            actionModes=next;
        }
        function toggleTaskDangerActionUnlock(row,action) {
            let next=Object.assign({},actionModes);
            next[action]=next[action]?"":"once";
            actionModes=next;
        }
        function taskFavoriteKey(row) { return "task|"+row.comm; }
        function taskSimplePurpose(row) { return "Synthetic purpose"; }
        function monitorResultIcon(row) { return "(╭ರ_•́)"; }
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
            if (!detail || !targets
                    || (smoke.phase === 0 && targets.count !== 1)) {
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
                const header=smoke.find(view,"cpuPlusProcessIdentity");
                const master=smoke.find(view,"cpuPlusProcessMasterLock");
                const actionTarget=smoke.find(view,"cpuPlusSharedActionTarget");
                const search=smoke.find(view,"cpuPlusKillSearch");
                const hunter=smoke.find(view,"cpuPlusSharedHunterControls");
                if (!smoke.check(view.currentTask && view.currentTask.pid===3442
                    && detail.visible && header && header.visible
                    && master && master.visible && actionTarget
                    && detail.restartAction.parent===actionTarget
                    && detail.endAction.parent===actionTarget
                    && search && hunter
                    && smoke.find(view,"cpuPlusKillTargetScroll")
                    && smoke.find(view,"cpuPlusKillDetailScroll"),
                    "shared detail, identity, controls, scrollbar mounting")) return;
                if (!smoke.check(view.toggleLock(view.currentTask,"limit",false)
                    && view.lockMode(view.currentTask,"limit")==="once"
                    && view.toggleLock(view.currentTask,"limit",true)
                    && view.lockMode(view.currentTask,"limit")==="sticky"
                    && view.toggleLock(view.currentTask,"",false)
                    && master.mode==="once"
                    && view.toggleLock(view.currentTask,"",true)
                    && master.mode==="sticky", "three real owner lock states")) return;
                view.toggleTaskFavorite(view.currentTask);
                if (!smoke.check(view.isTaskFavorite(view.currentTask)
                    && fakeOwner.favoriteStore.favoriteKeys[0]==="task|synthetic-worker",
                    "shared favorite identity")) return;
                const initial=detail.cpuCanvas.graphRevision;
                fakeOwner.taskRows=[Object.assign({},fakeOwner.taskRows[0],{cpu:24,cpuInstant:37,mem:7})];
                smoke.previousRevision=initial;
                smoke.phase=10;
                return;
            }
            if (smoke.phase===10) {
                if (!smoke.check(detail.cpuCanvas.graphRevision>smoke.previousRevision,
                    "new owner sample repaints shared detail")) return;
                const observed=detail.presentationState.taskCpuHistory;
                if (!smoke.check(observed[observed.length-1]===37,
                    "detail graph reads instantaneous CPU, not lifetime ps average")) return;
                const revision=detail.cpuCanvas.graphRevision;
                view.selectTarget(view.currentTask);
                if (!smoke.check(detail.cpuCanvas.graphRevision===revision,
                    "hover same target does not reset graph")) return;
                const search=smoke.find(view,"cpuPlusKillSearch");
                search.text="not-present";
                smoke.phase=11;
                return;
            }
            if (smoke.phase===11) {
                if (!smoke.check(targets.count===0 && !view.exactTargetAvailable
                    && !view.prepareAction("end"),
                    "search hides selected target and locks actuation")) return;
                smoke.find(view,"cpuPlusKillSearch").text="synthetic";
                view.setKillViewMode(view.killViewHunter);
                view.setHunterVisibilityMode(view.hunterVisibilityAll);
                // view requests are serialized, so explicitly switch after first settles
                smoke.phase=12;
                return;
            }
            if (smoke.phase===12) {
                if (view.modelBlank) return;
                if (view.killViewMode!==view.killViewHunter) {
                    view.setKillViewMode(view.killViewHunter); return;
                }
                if (view.hunterVisibilityMode!==view.hunterVisibilityAll) {
                    view.setHunterVisibilityMode(view.hunterVisibilityAll); return;
                }
                if (!smoke.check(targets.count===1
                    && view.hunterMetricMode===view.hunterMetricCombined,
                    "shared Hunter / COMBI / ALL filters")) return;
                const different={pid:9999,comm:"other",cpuInstant:42,rss:1048576,ioRate:0};
                if (!smoke.check(view.taskRowMetric(different).indexOf("42.0%")>=0
                    && view.taskRowMetric(different).indexOf("1024 MiB")>=0
                    && view.taskRowMetric(different)!==view.taskRowMetric(view.currentTask),
                    "Hunter row label comes from that row, not selected detail")) return;
                view.setHunterVisibilityMode(view.hunterVisibilityTargets);
                smoke.phase=13;
                return;
            }
            if (smoke.phase===13) {
                if (view.modelBlank) return;
                if (!smoke.check(targets.count===0 && !view.exactTargetAvailable
                    && !view.prepareAction("end"),
                    "protected row excluded by TARGETS and not actionable")) return;
                view.setHunterVisibilityMode(view.hunterVisibilityProtected);
                smoke.phase=14;
                return;
            }
            if (smoke.phase===14) {
                if (view.modelBlank) return;
                if (!smoke.check(targets.count===1,"PROTECTED filter uses owner policy")) return;
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
                if (!smoke.check(view.prepareAction("end") && view.hasOwnedPending,
                    "prepare before process removal")) return;
                smoke.lastRow = fakeOwner.taskRows[0];
            fakeOwner.taskRows = [];
                smoke.phase = 4;
                return;
            }
            if (!smoke.check(!view.currentTask && !view.exactTargetAvailable
                && !view.prepareAction("end") && !view.hasOwnedPending
                && fakeGate.pending===null && fakeGate.cancels===2
                && fakeGate.confirmations===1, "stale selection refusal and owned review cancelled"))
                return;
            fakeOwner.taskRows = [smoke.lastRow];
            if (!smoke.check(view.requestKillHogs() && view.hasBulkReview
                    && fakeOwner.bulkConfirmed===0
                    && fakeOwner.cpuBulkReview.metric===view.hunterMetricMode,
                    "bulk click prepares only, uses recipient metric")) return;
            view.cancelBulk();
            if (!smoke.check(fakeOwner.bulkCancelled===1 && !view.hasBulkReview
                    && fakeOwner.bulkConfirmed===0,"bulk cancellation sends no command")) return;
            if (!smoke.check(view.requestKillMice() && view.confirmBulk()
                    && fakeOwner.bulkConfirmed===1 && view.bulkOperation
                    && !view.hasBulkReview && !view.confirmBulk(),
                    "bulk review consumed once, progress remains owner-owned")) return;
            console.log("CPU_KILL_NATIVE_PASS");
            smoke.done = true;
            Qt.quit();
        }
    }

    Component.onCompleted: if (!armed) Qt.quit()
}
