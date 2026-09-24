import QtQuick
import Quickshell

Scope {
    id: processPresentationController

    // Reusable process-view policy/operations layer. Low-level mutation remains
    // in ProcessControl/ProcessLimits, and the host still owns confirmation UI.

    required property var safetyService
    required property var limitsService
    required property var controlService

    property var currentTask: null
    property var taskRows: []
    property var frozenOptimistic: ({})

    signal confirmationRequested(
        string kind,
        string title,
        string message,
        string actionLabel,
        var targetPids,
        string targetName
    )
    signal refreshRequested()

    function formatMemory(kib) {
        const value = Number(kib || 0);

        if (value >= 1048576)
            return (value / 1048576).toFixed(1) + " GiB";

        if (value >= 1024)
            return (value / 1024).toFixed(1) + " MiB";

        return Math.round(value) + " KiB";
    }

    function metricIsCritical(entry, metricId) {
        if (!entry)
            return false;

        switch (String(metricId || "")) {
        case "cpu": return Number(entry.cpu || 0) >= 80;
        case "mem": return Number(entry.mem || 0) >= 80;
        case "rss": return Number(entry.mem || 0) >= 80;
        case "threads": return Number(entry.threads || 0) >= 256;
        default: return false;
        }
    }

    function requiresDangerUnlock(entry) {
        return safetyService.requiresDangerUnlock(entry);
    }

    function dangerActionUnlocked(entry, actionKind) {
        return safetyService.dangerActionUnlocked(entry, actionKind);
    }

    function relockDangerAction(entry, actionKind) {
        safetyService.relockDangerAction(entry, actionKind);
    }

    function isFrozen(entry) {
        const target = entry || currentTask;
        if (!target)
            return false;

        const key = "pid:" + String(Number(target.pid || 0));

        if (frozenOptimistic[key] !== undefined)
            return !!frozenOptimistic[key];

        return String(target.state || "").indexOf("T") !== -1;
    }

    function markFrozen(entry, frozen) {
        const target = entry || currentTask;
        if (!target || Number(target.pid || 0) <= 1)
            return;

        const next = Object.assign({}, frozenOptimistic);
        next["pid:" + String(Number(target.pid))] = !!frozen;
        frozenOptimistic = next;
        optimisticReset.restart();
    }

    function hasSoftLimit(entry) {
        return limitsService.hasSoftLimit(entry || currentTask);
    }

    function limitMinimumMiB(entry) {
        return limitsService.minimumMiB(entry || currentTask);
    }

    function limitMaximumMiB(entry) {
        return limitsService.maximumMiB(entry || currentTask);
    }

    function limitMiB(entry) {
        return limitsService.limitMiB(entry || currentTask);
    }

    function limitPercent(entry) {
        return limitsService.limitPercent(entry || currentTask);
    }

    function setLimitMiB(mib, entry) {
        const target = entry || currentTask;

        if (!target || Number(target.pid || 0) <= 1)
            return;

        if (requiresDangerUnlock(target)
                && !dangerActionUnlocked(target, "limit"))
            return;

        limitsService.setLimitMiB(target, mib);
    }

    function setLimitPercent(percent, entry) {
        const target = entry || currentTask;
        if (!target)
            return;

        const pct = Math.max(0, Math.min(100, Number(percent || 0)));

        if (pct >= 99.5) {
            setLimitMiB(limitsService.maximumMiB(target), target);
            return;
        }

        const minMiB = limitsService.minimumMiB(target);
        const maxMiB = limitsService.maximumMiB(target);
        const capMiB =
            minMiB + (maxMiB - minMiB) * (pct / 98.5);

        setLimitMiB(capMiB, target);
    }

    function rowForPid(pid) {
        const wanted = Number(pid || 0);
        if (wanted <= 1)
            return null;

        const rows = Array.isArray(taskRows) ? taskRows : [];

        for (let i = 0; i < rows.length; i++) {
            const row = rows[i];
            if (Number(row && row.pid || 0) === wanted)
                return row;
        }

        return null;
    }

    function uniquePositivePids(values) {
        const source = Array.isArray(values) ? values : [];
        const seen = ({});
        const result = [];

        for (let i = 0; i < source.length; i++) {
            const pid = Number(source[i] || 0);
            if (pid <= 1 || seen[String(pid)])
                continue;

            seen[String(pid)] = true;
            result.push(pid);
        }

        return result;
    }

    function treeRowsForRoots(rootPids) {
        const roots = uniquePositivePids(rootPids);
        if (roots.length === 0)
            return [];

        const rows = Array.isArray(taskRows) ? taskRows : [];
        const wanted = ({});

        for (let i = 0; i < roots.length; i++)
            wanted[String(roots[i])] = true;

        let changed = true;
        let guard = 0;

        while (changed && guard < 64) {
            changed = false;
            guard++;

            for (let i = 0; i < rows.length; i++) {
                const row = rows[i];
                const pid = Number(row && row.pid || 0);
                const ppid = Number(row && row.ppid || 0);

                if (pid > 1
                        && wanted[String(ppid)]
                        && !wanted[String(pid)]) {
                    wanted[String(pid)] = true;
                    changed = true;
                }
            }
        }

        const result = [];

        for (let i = 0; i < rows.length; i++) {
            const row = rows[i];

            if (wanted[String(Number(row && row.pid || 0))])
                result.push(row);
        }

        return result;
    }

    function scopeProcessText(entry) {
        const target = entry || currentTask;

        if (!target)
            return "NO LIVE PROCESS SCOPE FOUND";

        const pid = Number(target.pid || 0);
        const rows = treeRowsForRoots([pid]);
        const lines = [];
        const parent = rowForPid(Number(target.ppid || 0));

        if (parent) {
            lines.push(
                "↑ PARENT • "
                + String(parent.comm || parent.name || "PROCESS")
                + " [" + String(parent.pid) + "] • NOT CHANGED"
            );
        }

        rows.sort(function(a, b) {
            if (Number(a.pid || 0) === pid) return -1;
            if (Number(b.pid || 0) === pid) return 1;
            return Number(a.pid || 0) - Number(b.pid || 0);
        });

        for (let i = 0; i < rows.length; i++) {
            const row = rows[i];
            const root = Number(row.pid || 0) === pid;

            lines.push(
                (root ? "● PROCESS • " : "↳ CHILD • ")
                + String(row.comm || row.name || "PROCESS")
                + " [" + String(row.pid) + "]"
                + (
                    root
                    ? " • LIMIT/FREEZE/KILL TARGET"
                    : " • PROCESS TREE"
                )
            );
        }

        return lines.length > 0
               ? lines.join("\n")
               : "NO LIVE PROCESS SCOPE FOUND";
    }

    function requestRestart(entry) {
        const target = entry || currentTask;

        if (!target || Number(target.pid || 0) <= 1)
            return;

        const protectedTask = requiresDangerUnlock(target);

        if (protectedTask && !dangerActionUnlocked(target, "kill"))
            return;

        confirmationRequested(
            protectedTask ? "protected-restart" : "task-restart",
            protectedTask
            ? "⚠︎ PROTECTED PROCESS • RESTART ⚠︎"
            : "CONFIRM PROCESS RESTART",
            String(target.comm || target.name || "PROCESS")
            + "  [PID " + String(target.pid) + "]\n\n"
            + "THIS TERMINATES THE CAPTURED PROCESS, THEN RELAUNCHES ITS ORIGINAL /proc CMDLINE.\n\n"
            + (
                protectedTask
                ? safetyService.dangerReason(target)
                  + "\n\nTHE KILL ACTION IS UNLOCKED FOR THIS TARGET. CONFIRM RESTART?"
                : "CONFIRM RESTART?"
            ),
            "RESTART PROCESS",
            [Number(target.pid)],
            String(target.comm || target.name || "").trim()
        );
    }

    function requestTerminate(entry) {
        const target = entry || currentTask;

        if (!target || Number(target.pid || 0) <= 1)
            return;

        const protectedTask = requiresDangerUnlock(target);

        if (protectedTask && !dangerActionUnlocked(target, "kill"))
            return;

        confirmationRequested(
            protectedTask ? "protected-term" : "task-term",
            protectedTask
            ? "⚠︎ PROTECTED PROCESS • TERMINATE ⚠︎"
            : "CONFIRM PROCESS TERMINATION",
            String(target.comm || target.name || "PROCESS")
            + "  [PID " + String(target.pid) + "]\n\n"
            + (
                protectedTask
                ? safetyService.dangerReason(target)
                  + "\n\nTERMINATING THIS PROCESS CAN END OR DESTABILIZE THE CURRENT DESKTOP SESSION.\n\n"
                : "THIS SENDS SIGTERM TO ONLY THE CAPTURED PROCESS TARGET.\n\n"
            )
            + (
                protectedTask
                ? "THE KILL ACTION IS UNLOCKED FOR THIS TARGET. CONFIRM SIGTERM?"
                : "CONFIRM SIGTERM?"
            ),
            "END PROCESS",
            [Number(target.pid)],
            String(target.comm || target.name || "").trim()
        );
    }

    function toggleFreeze(entry) {
        const target = entry || currentTask;

        if (!target || Number(target.pid || 0) <= 1)
            return;

        const frozen = isFrozen(target);
        const protectedTask = requiresDangerUnlock(target);

        if (protectedTask && !dangerActionUnlocked(target, "freeze"))
            return;

        if (frozen) {
            markFrozen(target, false);
            controlService.sendSignal(target.pid, "-CONT");
            relockDangerAction(target, "freeze");
            refreshRequested();
            return;
        }

        confirmationRequested(
            protectedTask ? "protected-freeze" : "task-freeze",
            protectedTask
            ? "⚠︎ PROTECTED PROCESS • FREEZE ⚠︎"
            : "CONFIRM PROCESS FREEZE",
            String(target.comm || target.name || "PROCESS")
            + "  [PID " + String(target.pid) + "]\n\n"
            + (
                protectedTask
                ? safetyService.dangerReason(target)
                  + "\n\nFREEZING A SESSION-CRITICAL PROCESS CAN MAKE THE DESKTOP UNRESPONSIVE OR REMOVE THE CONTROLS NEEDED TO RESUME IT.\n\n"
                : "FREEZING STOPS THIS PROCESS FROM EXECUTING UNTIL IT IS RESUMED.\n\n"
            )
            + (
                protectedTask
                ? "THE FREEZE ACTION IS UNLOCKED FOR THIS TARGET. CONFIRM FREEZE?"
                : "CONFIRM FREEZE?"
            ),
            "FREEZE",
            [Number(target.pid)],
            String(target.comm || target.name || "").trim()
        );
    }

    Timer {
        id: optimisticReset
        interval: 1400
        repeat: false
        onTriggered: processPresentationController.frozenOptimistic = ({})
    }
}
