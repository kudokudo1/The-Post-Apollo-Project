import QtQuick

QtObject {
    id: processPresentation

    // Pure process/resource presentation helpers.
    // No selection state, semantic app identity, mutation, confirmation UI,
    // or AppControl navigation/focus behavior belongs here.
    required property var processScope

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
        case "cpu":
            return Number(entry.cpu || 0) >= 80;
        case "mem":
        case "rss":
            return Number(entry.mem || 0) >= 80;
        case "threads":
            return Number(entry.threads || 0) >= 256;
        default:
            return false;
        }
    }

    function scopeProcessText(rows, entry) {
        if (!entry)
            return "NO LIVE PROCESS SCOPE FOUND";

        const sourceRows = Array.isArray(rows) ? rows : [];
        const pid = Number(entry.pid || 0);

        if (pid <= 1)
            return "NO LIVE PROCESS SCOPE FOUND";

        const scopedRows =
            processScope.treeRowsForRoots(sourceRows, [pid]).slice();
        const lines = [];
        const parent =
            processScope.rowForPid(sourceRows, Number(entry.ppid || 0));

        if (parent) {
            lines.push(
                "↑ PARENT • "
                + String(parent.comm || parent.name || "PROCESS")
                + " [" + String(parent.pid) + "] • NOT CHANGED"
            );
        }

        scopedRows.sort(function(a, b) {
            if (Number(a.pid || 0) === pid)
                return -1;
            if (Number(b.pid || 0) === pid)
                return 1;

            return Number(a.pid || 0) - Number(b.pid || 0);
        });

        for (let i = 0; i < scopedRows.length; i++) {
            const row = scopedRows[i];
            const root = Number(row && row.pid || 0) === pid;

            lines.push(
                (root ? "● PROCESS • " : "↳ CHILD • ")
                + String(row && (row.comm || row.name) || "PROCESS")
                + " [" + String(Number(row && row.pid || 0)) + "]"
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
}
