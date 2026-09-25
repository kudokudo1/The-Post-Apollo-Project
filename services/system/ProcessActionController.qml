import QtQuick
import Quickshell

Scope {
    id: processActionController

    // Entry-driven process/resource action policy for reuse outside Task/HUNTER.
    // Callers own semantic identity, selection, navigation, and confirmation UI.
    // This controller owns shared per-process policy/orchestration only.
    required property var safetyService
    required property var limitsService
    required property var controlService
    required property var processIdentity

    property var frozenOptimistic: ({})

    signal confirmationRequested(var request)
    signal refreshRequested()

    function sourceEntry(entry) {
        return processIdentity.sourceEntry(entry);
    }

    function entryPid(entry) {
        const source = sourceEntry(entry);
        return Number(source && source.pid || 0);
    }

    function entryName(entry) {
        const source = sourceEntry(entry);
        return String(
            source && (source.comm || source.name) || ""
        ).trim();
    }

    function validEntry(entry) {
        return entryPid(entry) > 1;
    }

    function targetMatches(entry, request) {
        if (!validEntry(entry) || !request)
            return false;

        return processIdentity.matchesCaptured(
            entry,
            request.captured || {
                pid: Number(request.pid || 0),
                name: String(request.name || ""),
                identity: String(request.identity || "")
            }
        );
    }

    function requiresDangerUnlock(entry) {
        return safetyService.requiresDangerUnlock(sourceEntry(entry));
    }

    function dangerActionUnlocked(entry, actionKind) {
        return safetyService.dangerActionUnlocked(
            sourceEntry(entry),
            actionKind
        );
    }

    function relockDangerAction(entry, actionKind) {
        safetyService.relockDangerAction(
            sourceEntry(entry),
            actionKind
        );
    }

    function actionAllowed(entry, actionKind) {
        if (!validEntry(entry))
            return false;

        return !requiresDangerUnlock(entry)
               || dangerActionUnlocked(entry, actionKind);
    }

    function isFrozen(entry) {
        if (!validEntry(entry))
            return false;

        const key = "pid:" + String(entryPid(entry));

        if (frozenOptimistic[key] !== undefined)
            return !!frozenOptimistic[key];

        const source = sourceEntry(entry);
        return String(source && source.state || "").indexOf("T") !== -1;
    }

    function markFrozen(entry, frozen) {
        if (!validEntry(entry))
            return false;

        const next = Object.assign({}, frozenOptimistic);
        next["pid:" + String(entryPid(entry))] = !!frozen;
        frozenOptimistic = next;
        optimisticReset.restart();
        return true;
    }

    function hasSoftLimit(entry) {
        const source = sourceEntry(entry);
        return validEntry(source) && limitsService.hasSoftLimit(source);
    }

    function limitMinimumMiB(entry) {
        return limitsService.minimumMiB(sourceEntry(entry));
    }

    function limitMaximumMiB(entry) {
        return limitsService.maximumMiB(sourceEntry(entry));
    }

    function limitMiB(entry) {
        return limitsService.limitMiB(sourceEntry(entry));
    }

    function limitPercent(entry) {
        return limitsService.limitPercent(sourceEntry(entry));
    }

    function setLimitMiB(entry, mib) {
        if (!actionAllowed(entry, "limit"))
            return false;

        limitsService.setLimitMiB(sourceEntry(entry), mib);
        return true;
    }

    function setLimitPercent(entry, percent) {
        if (!validEntry(entry))
            return false;

        const pct = Math.max(0, Math.min(100, Number(percent || 0)));

        if (pct >= 99.5)
            return setLimitMiB(
                entry,
                limitsService.maximumMiB(sourceEntry(entry))
            );

        const source = sourceEntry(entry);
        const minMiB = limitsService.minimumMiB(source);
        const maxMiB = limitsService.maximumMiB(source);
        const capMiB =
            minMiB + (maxMiB - minMiB) * (pct / 98.5);

        return setLimitMiB(entry, capMiB);
    }

    function confirmationFor(entry, operation) {
        if (!validEntry(entry))
            return null;

        const op = String(operation || "").trim().toLowerCase();
        const protectedProcess = requiresDangerUnlock(entry);
        const captured = processIdentity.capturedIdentity(entry);
        const name = String(captured.name || entryName(entry) || "PROCESS");
        const pid = Number(captured.pid || entryPid(entry));
        let title = "";
        let message = "";
        let actionLabel = "";
        let actionKind = "kill";
        let compatibilityKind = "";

        if (op === "restart") {
            compatibilityKind =
                protectedProcess ? "protected-restart" : "task-restart";
            title = protectedProcess
                    ? "⚠︎ PROTECTED PROCESS • RESTART ⚠︎"
                    : "CONFIRM PROCESS RESTART";
            message =
                name + "  [PID " + String(pid) + "]\n\n"
                + "THIS TERMINATES THE CAPTURED PROCESS, THEN RELAUNCHES ITS ORIGINAL /proc CMDLINE.\n\n"
                + (
                    protectedProcess
                    ? safetyService.dangerReason(sourceEntry(entry))
                      + "\n\nTHE KILL ACTION IS UNLOCKED FOR THIS TARGET. CONFIRM RESTART?"
                    : "CONFIRM RESTART?"
                );
            actionLabel = "RESTART PROCESS";
        } else if (op === "terminate") {
            compatibilityKind =
                protectedProcess ? "protected-term" : "task-term";
            title = protectedProcess
                    ? "⚠︎ PROTECTED PROCESS • TERMINATE ⚠︎"
                    : "CONFIRM PROCESS TERMINATION";
            message =
                name + "  [PID " + String(pid) + "]\n\n"
                + (
                    protectedProcess
                    ? safetyService.dangerReason(sourceEntry(entry))
                      + "\n\nTERMINATING THIS PROCESS CAN END OR DESTABILIZE THE CURRENT DESKTOP SESSION.\n\n"
                    : "THIS SENDS SIGTERM TO ONLY THE CAPTURED PROCESS TARGET.\n\n"
                )
                + (
                    protectedProcess
                    ? "THE KILL ACTION IS UNLOCKED FOR THIS TARGET. CONFIRM SIGTERM?"
                    : "CONFIRM SIGTERM?"
                );
            actionLabel = "END PROCESS";
        } else if (op === "freeze") {
            compatibilityKind =
                protectedProcess ? "protected-freeze" : "task-freeze";
            title = protectedProcess
                    ? "⚠︎ PROTECTED PROCESS • FREEZE ⚠︎"
                    : "CONFIRM PROCESS FREEZE";
            message =
                name + "  [PID " + String(pid) + "]\n\n"
                + (
                    protectedProcess
                    ? safetyService.dangerReason(sourceEntry(entry))
                      + "\n\nFREEZING A SESSION-CRITICAL PROCESS CAN MAKE THE DESKTOP UNRESPONSIVE OR REMOVE THE CONTROLS NEEDED TO RESUME IT.\n\n"
                    : "FREEZING STOPS THIS PROCESS FROM EXECUTING UNTIL IT IS RESUMED.\n\n"
                )
                + (
                    protectedProcess
                    ? "THE FREEZE ACTION IS UNLOCKED FOR THIS TARGET. CONFIRM FREEZE?"
                    : "CONFIRM FREEZE?"
                );
            actionLabel = "FREEZE";
            actionKind = "freeze";
        } else {
            return null;
        }

        return {
            operation: op,
            kind: compatibilityKind,
            protectedProcess: protectedProcess,
            actionKind: actionKind,
            pid: pid,
            name: name,
            identity: String(captured.identity || ""),
            captured: captured,
            title: title,
            message: message,
            actionLabel: actionLabel
        };
    }

    function requestRestart(entry) {
        if (!actionAllowed(entry, "kill"))
            return false;

        const request = confirmationFor(entry, "restart");

        if (!request)
            return false;

        confirmationRequested(request);
        return true;
    }

    function requestTerminate(entry) {
        if (!actionAllowed(entry, "kill"))
            return false;

        const request = confirmationFor(entry, "terminate");

        if (!request)
            return false;

        confirmationRequested(request);
        return true;
    }

    function requestToggleFreeze(entry) {
        if (!actionAllowed(entry, "freeze"))
            return false;

        if (isFrozen(entry)) {
            markFrozen(entry, false);

            if (!controlService.sendSignal(entryPid(entry), "-CONT"))
                return false;

            relockDangerAction(entry, "freeze");
            refreshRequested();
            return true;
        }

        const request = confirmationFor(entry, "freeze");

        if (!request)
            return false;

        confirmationRequested(request);
        return true;
    }

    function cancelConfirmed(request, liveEntry) {
        if (!request || !liveEntry)
            return false;

        if (!targetMatches(liveEntry, request))
            return false;

        const actionKind = String(
            request.actionKind
            || (
                String(request.operation || "").toLowerCase() === "freeze"
                ? "freeze"
                : "kill"
            )
        );

        relockDangerAction(liveEntry, actionKind);
        return true;
    }

    function executeConfirmed(request, liveEntry) {
        if (!targetMatches(liveEntry, request))
            return false;

        const operation = String(request.operation || "").toLowerCase();
        const actionKind = String(request.actionKind || "kill");

        if (!actionAllowed(liveEntry, actionKind))
            return false;

        let mutated = false;

        if (operation === "freeze") {
            mutated = controlService.sendSignal(entryPid(liveEntry), "-STOP");

            if (mutated)
                markFrozen(liveEntry, true);
        } else if (operation === "terminate") {
            mutated = controlService.sendSignal(entryPid(liveEntry), "-TERM");
        } else if (operation === "restart") {
            mutated = controlService.restart(entryPid(liveEntry));
        }

        if (!mutated)
            return false;

        relockDangerAction(liveEntry, actionKind);
        refreshRequested();
        return true;
    }

    Timer {
        id: optimisticReset

        interval: 1400
        repeat: false

        onTriggered: processActionController.frozenOptimistic = ({})
    }
}
