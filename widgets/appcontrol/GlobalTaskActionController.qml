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
        const rows = host.killAllEligibleTasks();
        if (rows.length === 0)
            return;

        host.openDestructiveConfirm(
            "kill-all",
            "⚠︎ CONFIRM KILL ALL ⚠︎",
            "TERMINATE " + String(rows.length)
            + " ELIGIBLE USER PROCESSES?\n"
            + "SWAY, QUICKSHELL, AUDIO, DBUS AND SESSION SERVICES ARE PROTECTED.",
            "KILL ALL"
        );
        host.destructiveConfirmTargetPids = rows.map(function(entry) {
            return Number(entry.pid || 0);
        });
    }


    function executeKillAllEligibleTasks(targetPids) {
        const wanted = Array.isArray(targetPids) ? targetPids : [];
        const rows = host.killAllEligibleTasks().filter(function(entry) {
            return wanted.length === 0
                   || wanted.indexOf(Number(entry.pid || 0)) !== -1;
        });
        if (rows.length === 0)
            return;

        console.log("AppControl: KILL ALL eligible count", rows.length);
        processControlObject.sendSignalMany(
            rows.map(function(entry) { return Number(entry.pid || 0); }),
            "-TERM"
        );
        refreshTimer.restart();
    }


    function executeBulkTaskTermination(targetPids, label) {
        const wanted = Array.isArray(targetPids) ? targetPids : [];
        if (wanted.length === 0)
            return;

        const rows = host.taskRows.filter(function(entry) {
            return host.taskEligibleForKillAll(entry)
                   && wanted.indexOf(Number(entry.pid || 0)) !== -1;
        });
        if (rows.length === 0)
            return;

        console.log("AppControl:", label || "BULK TERM", rows.length);
        processControlObject.sendSignalMany(
            rows.map(function(entry) { return Number(entry.pid || 0); }),
            "-TERM"
        );
        refreshTimer.restart();
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
                && !host.taskDangerActionUnlocked(entry, "kill"))
            return;

        processControlObject.restart(entry.pid);
        relockTaskDangerAction(entry, "kill");
        refreshTimer.restart();
    }


    function restartSelectedTask() {
        processControllerObject.requestRestart();
    }


}
