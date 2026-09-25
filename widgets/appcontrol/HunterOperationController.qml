import QtQuick

QtObject {
    id: hunterOperationController

    required property var host
    required property var favoriteStoreObject
    required property var executor
    required property var refreshTimer

    property string phase: "idle" // idle, running, report
    property string kind: ""
    property var targets: []
    property var results: []
    property int completed: 0
    property int total: 0
    property var pendingTargets: []

    function targetsFromRows(rows) {
        return rows.map(function(entry) {
            return {
                pid: Number(entry.pid || 0),
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
        return kind === "kill-mice" ? "MICE" : "HOGS";
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

        host.destructiveConfirmMessage = lines.join("\n");
    }

    function showWindow() {
        if (phase !== "running" && phase !== "report")
            return false;

        host.destructiveConfirmKind = kind;
        host.destructiveConfirmChoice = 0;
        host.destructiveConfirmOpen = true;
        refreshMessage();
        return true;
    }

    function start(operationKind, operationTargets) {
        if (phase === "running") {
            showWindow();
            return;
        }

        const captured =
            Array.isArray(operationTargets) ? operationTargets.slice() : [];
        if (captured.length === 0) {
            host.cancelDestructiveConfirm();
            return;
        }

        const activeTargets = [];
        const releasedFavorites = [];

        for (let i = 0; i < captured.length; i++) {
            const target = captured[i];
            if (targetIsFavorite(target)) {
                releasedFavorites.push({
                    type: "result",
                    pid: Number(target.pid || 0),
                    name: String(target.name || "PROCESS"),
                    status: "favorite",
                    detail: "LET LOOSE • FAVORITE PROTECTED BEFORE FIRING"
                });
            } else {
                activeTargets.push(target);
            }
        }

        phase = "running";
        kind = String(operationKind || "kill-hogs");
        targets = captured;
        results = releasedFavorites;
        completed = releasedFavorites.length;
        total = captured.length;
        pendingTargets = [];

        host.destructiveConfirmTargetPids = [];
        host.destructiveConfirmKind = kind;
        host.destructiveConfirmChoice = 0;
        host.destructiveConfirmTitle =
            kind === "kill-mice"
            ? "⚠︎ (-_•)デ╾━  (ᐢ..ᐢ)౨  HUNTING MICE…  ⚠︎"
            : "⚠︎ (-_•)デ╾━  ₍˄·͈⚇·͈˄₎  HUNTING HOGS…  ⚠︎";
        host.destructiveConfirmOpen = true;
        refreshMessage();

        if (activeTargets.length === 0) {
            finish();
            return;
        }

        executor.start(activeTargets);
    }

    function applyResult(result) {
        if (phase !== "running")
            return;

        const payload = result || ({});
        const next = results.slice();
        next.push(payload);
        results = next;
        completed = Math.min(total, next.length);
        refreshMessage();
        refreshTimer.restart();
    }

    function finish() {
        if (phase !== "running")
            return;

        const seen = ({});
        for (let i = 0; i < results.length; i++)
            seen[String(results[i].pid || 0)] = true;

        const finalResults = results.slice();
        for (let i = 0; i < targets.length; i++) {
            const target = targets[i];
            const key = String(target.pid || 0);
            if (!seen[key]) {
                finalResults.push({
                    type: "result",
                    pid: Number(target.pid || 0),
                    name: String(target.name || "PROCESS"),
                    status: "escaped",
                    detail: "NO VERIFIED RESULT • NOT RETRIED"
                });
            }
        }

        results = finalResults;
        completed = total;
        phase = "report";
        host.destructiveConfirmTitle =
            kind === "kill-mice"
            ? "⚠︎ (-_•)デ╾━  (ᐢ××ᐢ)౨  MICE HUNT COMPLETE  ⚠︎"
            : "⚠︎ (-_•)デ╾━  ₍˄×⚇×˄₎  HOG HUNT COMPLETE  ⚠︎";
        host.destructiveConfirmKind = kind;
        host.destructiveConfirmOpen = true;
        refreshMessage();
        refreshTimer.restart();
    }
}
