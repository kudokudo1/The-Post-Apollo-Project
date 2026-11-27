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


    function taskEntryForCapturedIdentity(pid, expectedName, expectedStartTicks) {
        const gate = host.hubProcessActionGate;
        if (!gate)
            return null;
        return gate.exactRow(Number(pid), Number(expectedStartTicks), String(expectedName || ""));
    }

    function executeProtectedTaskSignal(pid, expectedName, signalName, expectedStartTicks) {
        const gate = host.hubProcessActionGate;
        const entry = taskEntryForCapturedIdentity(pid, expectedName, expectedStartTicks);
        const action = signalName === "-STOP" ? "freeze" : signalName === "-TERM" ? "end" : "";
        if (!entry || !action || !gate)
            return false;
        // The donor has already shown its existing confirmation dialog.
        // Reuse the shared exact-target gateway, including lock revalidation,
        // mutual exclusion, pidfd dispatch and result observation.
        if (!gate.prepare(Number(pid), Number(expectedStartTicks), expectedName, action, 0))
            return false;
        const captured = gate.pending;
        if (gate.confirm())
            return true;
        if (!gate.busy && gate.pending === captured)
            gate.cancel();
        return false;
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




    function executeTaskRestart(pid, expectedName, expectedStartTicks) {
        const entry = taskEntryForCapturedIdentity(pid, expectedName, expectedStartTicks);

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
