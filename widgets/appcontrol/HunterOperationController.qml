import QtQuick

QtObject {
    id: hunterOperationController

    required property var host
    required property var favoriteStoreObject
    required property var executor
    required property var refreshTimer

    property string phase: "idle" // idle, running, report
    property string kind: ""
    property bool recipientOwned: false
    property string message: ""
    property var targets: []
    property var results: []
    property int completed: 0
    property int total: 0
    property var pendingTargets: []
    property int cursor: 0
    property var activeTarget: null
    property bool activeResultReceived: false

    function targetsFromRows(rows) {
        return rows.map(function(entry) {
            return {
                pid: Number(entry.pid || 0),
                startTicks: Number(entry.startTicks || 0),
                name: String(entry.comm || entry.name || "PROCESS").trim(),
                identity: host.taskPersistentIdentity(entry)
            };
        });
    }

    function targetIsFavorite(target) {
        if (!target)
            return false;

        const identity = String(target.identity || "").trim().toLowerCase();
        if (!identity)
            return false;

        const key = "task|" + encodeURIComponent(identity);
        return favoriteStoreObject.favoriteKeys.indexOf(key) !== -1;
    }

    function operationLabel() {
        return kind === "kill-all" ? "ALL" : kind === "kill-mice" ? "MICE" : "HOGS";
    }

    function operationStatusLine(result) {
        const status = String(result && result.status || "");
        const name = String(result && result.name || "PROCESS");
        const pid = String(result && result.pid || "?");
        const detail = String(result && result.detail || "");
        const mark = status === "killed" ? "✓"
                     : status === "gone" ? "◇"
                     : status === "favorite" ? "♥"
                     : "⚠︎";
        return mark + " " + name + "  [PID " + pid + "] — " + detail;
    }

    function refreshMessage() {
        const label = operationLabel();
        const lines = [];

        if (phase === "running") {
            lines.push(
                "HUNTING " + label + " • "
                + String(completed) + " / "
                + String(total) + " CHECKED"
            );
            lines.push("");

            for (let i = 0; i < results.length; i++)
                lines.push(operationStatusLine(results[i]));

            if (completed < total) {
                lines.push("");
                lines.push("… HUNTER STILL TRACKING "
                           + String(total - completed)
                           + " TARGET(S)");
            }
        } else if (phase === "report") {
            let killed = 0;
            let escaped = 0;
            let gone = 0;
            let favoritesReleased = 0;
            for (let i = 0; i < results.length; i++) {
                const status = String(results[i].status || "");
                if (status === "killed") killed += 1;
                else if (status === "gone") gone += 1;
                else if (status === "favorite") favoritesReleased += 1;
                else escaped += 1;
            }

            lines.push(
                label + " HUNT REPORT • " + String(total)
                + " TARGET(S)"
            );
            lines.push(
                "KILLED " + String(killed)
                + " • GOT AWAY " + String(escaped)
                + " • ALREADY GONE " + String(gone)
                + " • LET LOOSE FAVORITES " + String(favoritesReleased)
            );
            lines.push("");

            for (let i = 0; i < results.length; i++)
                lines.push(operationStatusLine(results[i]));
        }

        message = lines.join("\n");
        if (!recipientOwned) host.destructiveConfirmMessage = message;
    }

    function showWindow() {
        if (recipientOwned || (phase !== "running" && phase !== "report"))
            return false;

        host.destructiveConfirmKind = kind;
        host.destructiveConfirmChoice = 0;
        if (!recipientOwned) host.destructiveConfirmOpen = true;
        refreshMessage();
        return true;
    }

    function start(operationKind, operationTargets, cpuRecipient) {
        if (phase === "running") {
            showWindow();
            return;
        }

        // Review owns a fixed, nonempty set of exact identities. Do not
        // broaden malformed captures or let duplicate PIDs authorize a signal.
        const captured = [];
        const seen = new Set();
        if (operationKind !== "kill-all" && operationKind !== "kill-hogs" && operationKind !== "kill-mice")
            return;
        if (!Array.isArray(operationTargets) || operationTargets.length === 0)
            return;
        for (const target of operationTargets) {
            if (!target || !Number.isSafeInteger(target.pid) || target.pid <= 1
                    || !Number.isSafeInteger(target.startTicks) || target.startTicks <= 0
                    || typeof target.name !== "string" || !target.name
                    || typeof target.identity !== "string" || !target.identity
                    || seen.has(target.pid)) {
                host.cancelDestructiveConfirm();
                return;
            }
            seen.add(target.pid);
            captured.push(Object.freeze({
                pid: target.pid, startTicks: target.startTicks,
                name: target.name, identity: target.identity
            }));
        }

        recipientOwned = cpuRecipient === true;
        phase = "running";
        kind = String(operationKind || "kill-hogs");
        targets = captured;
        results = [];
        completed = 0;
        cursor = 0;
        activeTarget = null;
        activeResultReceived = false;
        total = captured.length;
        pendingTargets = [];

        if (!recipientOwned) {
            host.destructiveConfirmTargetPids = [];
            host.destructiveConfirmKind = kind;
            host.destructiveConfirmChoice = 0;
            host.destructiveConfirmTitle =
                kind === "kill-all" ? "⚠︎ KILL ALL • CHECKING CAPTURES… ⚠︎"
                : kind === "kill-mice"
                ? "⚠︎ (-_•)デ╾━  (ᐢ..ᐢ)౨  HUNTING MICE…  ⚠︎"
                : "⚠︎ (-_•)デ╾━  ₍˄·͈⚇·͈˄₎  HUNTING HOGS…  ⚠︎";
            host.destructiveConfirmOpen = true;
        }
        refreshMessage();

        dispatchNext();
    }

    function record(target, status, detail) {
        const next = results.slice();
        next.push({type: "result", pid: target.pid, name: target.name,
                   status: status, detail: detail});
        results = next;
        completed = next.length;
        refreshMessage();
        refreshTimer.restart();
    }

    function liveRow(target) {
        for (const row of host.taskRows) {
            if (Number(row.pid) === target.pid
                    && Number(row.startTicks) === target.startTicks
                    && String(row.comm || row.name || "").trim() === target.name
                    && host.taskPersistentIdentity(row) === target.identity)
                return row;
        }
        return null;
    }

    function dispatchNext() {
        if (phase !== "running" || activeTarget || executor.running)
            return;
        while (cursor < targets.length) {
            const target = targets[cursor++];
            if (targetIsFavorite(target)) {
                record(target, "favorite", "LET LOOSE • FAVORITE PROTECTED BEFORE FIRING");
                continue;
            }
            const row = liveRow(target);
            if (!row) {
                record(target, "gone", "CAPTURED IDENTITY NO LONGER OBSERVED");
                continue;
            }
            if (!host.taskEligibleForKillAll(row)
                    || (kind === "kill-mice" && host.hunterMouseProtectedReason(row).length > 0)) {
                record(target, "escaped", "CURRENT PROTECTION • NO SIGNAL");
                continue;
            }
            activeTarget = target;
            activeResultReceived = false;
            if (!executor.start([target])) {
                record(target, "escaped", "EXECUTOR REFUSED • NO RETRY");
                activeTarget = null;
                stopRemaining();
            }
            return;
        }
        completeReport();
    }

    function applyResult(result) {
        if (phase !== "running" || !activeTarget || activeResultReceived
                || !result || result.pid !== activeTarget.pid
                || result.name !== activeTarget.name
                || ["killed", "gone", "escaped"].indexOf(result.status) < 0)
            return;
        activeResultReceived = true;
        record(activeTarget, result.status, String(result.detail || ""));
    }

    function stopRemaining() {
        while (cursor < targets.length)
            record(targets[cursor++], "escaped", "NOT ATTEMPTED • PREVIOUS EXECUTION UNVERIFIED");
        completeReport();
    }

    // Only called by the executor after the child process has exited.
    function finish() {
        if (phase !== "running" || !activeTarget)
            return;
        const verified = activeResultReceived;
        if (!verified)
            record(activeTarget, "escaped", "NO VERIFIED RESULT • NOT RETRIED");
        activeTarget = null;
        activeResultReceived = false;
        if (!verified) {
            stopRemaining();
            return;
        }
        Qt.callLater(function() { hunterOperationController.dispatchNext(); });
    }

    function completeReport() {
        if (phase !== "running" || activeTarget)
            return;
        phase = "report";
        if (!recipientOwned) {
            host.destructiveConfirmTitle =
                kind === "kill-all" ? "⚠︎ KILL ALL • REPORT ⚠︎"
                : kind === "kill-mice"
                ? "⚠︎ (-_•)デ╾━  (ᐢ××ᐢ)౨  MICE HUNT COMPLETE  ⚠︎"
                : "⚠︎ (-_•)デ╾━  ₍˄×⚇×˄₎  HOG HUNT COMPLETE  ⚠︎";
            host.destructiveConfirmKind = kind;
            host.destructiveConfirmOpen = true;
        }
        refreshMessage();
        refreshTimer.restart();
    }
}
