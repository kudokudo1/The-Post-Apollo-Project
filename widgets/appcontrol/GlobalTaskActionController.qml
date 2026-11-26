import QtQuick

QtObject {
    id: globalTaskActionController

    required property var host
    required property var taskSafetyObject
    required property var processControlObject
    required property var processControllerObject
    required property var processLimitsObject
    required property var refreshTimer

    function clearTaskDangerActionUnlocks(entry) {
        taskSafetyObject.clearDangerActionUnlocks(entry);
    }


    function toggleTaskDangerActionUnlock(entry, actionKind) {
        taskSafetyObject.toggleDangerActionUnlock(entry, actionKind);
    }


    function toggleTaskDangerActionStickyUnlock(entry, actionKind) {
        taskSafetyObject.toggleDangerActionStickyUnlock(entry, actionKind);
    }


    function relockTaskDangerAction(entry, actionKind) {
        taskSafetyObject.relockDangerAction(entry, actionKind);
    }


    function toggleTaskDangerUnlock(entry) {
        taskSafetyObject.toggleDangerUnlock(entry);
    }


    function toggleTaskDangerStickyUnlock(entry) {
        taskSafetyObject.toggleDangerStickyUnlock(entry);
    }


    function relockTaskDanger(entry) {
        taskSafetyObject.relockDanger(entry);
    }


    function taskEntryForCapturedIdentity(pid, expectedName) {
        const wantedPid = Number(pid || 0);
        const wantedName = String(expectedName || "").trim().toLowerCase();
        if (wantedPid <= 1)
            return null;
        for (let i = 0; i < host.taskRows.length; i++) {
            const row = host.taskRows[i];
            if (Number(row && row.pid || 0) !== wantedPid)
                continue;
            const rowName = String(row.comm || row.name || "").trim().toLowerCase();
            if (wantedName && rowName !== wantedName)
                return null;
            return row;
        }
        return null;
    }


    function executeProtectedTaskSignal(pid, expectedName, signalName) {
        const entry = taskEntryForCapturedIdentity(pid, expectedName);
        if (!entry)
            return;
        processControlObject.sendSignal(entry.pid, signalName);
        if (signalName === "-STOP") {
            processControllerObject.markFrozen(entry, true);
            relockTaskDangerAction(entry, "freeze");
        } else {
            relockTaskDangerAction(entry, "kill");
        }
        refreshTimer.restart();
    }


    function requestKillAllEligibleTasks() {
        if (host.hunterOperationPhase !== "idle") {
            host.showHunterOperationWindow();
            return;
        }
        if (host.cpuBulkReview || host.destructiveConfirmOpen || host.hubProcessActionGate.pending
                || host.hubProcessActionGate.busy)
            return;
        const rows = host.killAllEligibleTasks().filter(function(row) {
            const capture = host.hunterTargetsFromRows([row])[0];
            return capture && Number.isSafeInteger(capture.pid) && capture.pid > 1
                && Number.isSafeInteger(capture.startTicks) && capture.startTicks > 0
                && !!capture.name && !!capture.identity
                && !host.hunterTargetIsFavorite(capture);
        });
        const captured = host.hunterTargetsFromRows(rows);
        if (captured.length === 0)
            return;

        host.openDestructiveConfirm(
            "kill-all",
            "⚠︎ CONFIRM KILL ALL ⚠︎",
            "TERMINATE THESE " + String(captured.length)
            + " ELIGIBLE USER PROCESSES?\n\n"
            + captured.map(function(target) {
                return "• " + target.name + " [PID " + String(target.pid) + "]";
            }).join("\n")
            + "\n\nALL ELIGIBLE PROCESSES, NOT JUST SEARCH RESULTS. "
            + "FAVORITES AND PROTECTED PROCESSES ARE EXCLUDED AND RECHECKED. "
            + "EACH EXACT CAPTURE IS CHECKED ONCE; NO AUTOMATIC RETRY.",
            "KILL ALL"
        );
        host.hunterPendingTargets = captured;
    }


    function toggleSelectedTaskFreeze() {
        processControllerObject.toggleFreeze();
    }


    function startQueuedTaskMemoryLimitApply() {
        processLimitsObject.startQueuedApply();
    }




    function setSelectedTaskMemoryLimitMiB(mib) {
        processControllerObject.setLimitMiB(mib);
    }


    function setSelectedTaskMemoryLimitPercent(percent) {
        processControllerObject.setLimitPercent(percent);
    }


    function terminateSelectedTask() {
        processControllerObject.requestTerminate();
    }




    function executeTaskRestart(pid, expectedName) {
        const entry = taskEntryForCapturedIdentity(pid, expectedName);

        if (!entry || Number(entry.pid || 0) <= 1)
            return;

        if (host.taskRequiresDangerUnlock(entry)
                && !host.taskDangerActionUnlocked(entry, "restart"))
            return;

        processControlObject.restart(entry.pid);
        relockTaskDangerAction(entry, "restart");
        refreshTimer.restart();
    }


    function restartSelectedTask() {
        processControllerObject.requestRestart();
    }


}
