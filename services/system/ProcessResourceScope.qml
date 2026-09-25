import QtQuick

QtObject {
    id: processResourceScope

    // Provider-neutral APP/WINDOW/TAB/RUN process-resource physiology.
    // Callers supply concrete root PID(s) and process rows. This object does
    // not discover semantic identity, own scope keys, or perform mutations.
    required property var processScope
    required property var safetyService

    function rootPids(rootPids) {
        return processScope.uniquePositivePids(rootPids);
    }

    function rows(processRows, rootPids) {
        return processScope.treeRowsForRoots(
            Array.isArray(processRows) ? processRows : [],
            rootPids
        );
    }

    function parentRows(processRows, rootPids) {
        const sourceRows = Array.isArray(processRows) ? processRows : [];
        const roots = processScope.uniquePositivePids(rootPids);
        const rootSet = ({});
        const seen = ({});
        const parents = [];

        for (let i = 0; i < roots.length; i++)
            rootSet[String(roots[i])] = true;

        for (let i = 0; i < roots.length; i++) {
            const row = processScope.rowForPid(sourceRows, roots[i]);
            const parent = processScope.rowForPid(
                sourceRows,
                Number(row && row.ppid || 0)
            );
            const pid = Number(parent && parent.pid || 0);

            if (pid > 1
                    && !rootSet[String(pid)]
                    && !seen[String(pid)]) {
                seen[String(pid)] = true;
                parents.push(parent);
            }
        }

        return parents;
    }

    function containsProtected(processRows, rootPids) {
        const scopedRows = rows(processRows, rootPids);

        for (let i = 0; i < scopedRows.length; i++) {
            if (safetyService.requiresDangerUnlock(scopedRows[i]))
                return true;
        }

        return false;
    }

    function containsLockedProtected(processRows, rootPids) {
        const scopedRows = rows(processRows, rootPids);

        for (let i = 0; i < scopedRows.length; i++) {
            const row = scopedRows[i];

            if (safetyService.requiresDangerUnlock(row)
                    && !safetyService.dangerUnlocked(row))
                return true;
        }

        return false;
    }

    function limitAvailable(processRows, rootPids) {
        const scopedRows = rows(processRows, rootPids);

        // Higher-level scopes must not bypass per-process safety. A protected
        // process must be handled explicitly through the process action path.
        return scopedRows.length > 0
               && !containsProtected(processRows, rootPids);
    }

    function limitMinimumMiB(processRows, rootPids) {
        const scopedRows = rows(processRows, rootPids);
        let minimum = 128;

        for (let i = 0; i < scopedRows.length; i++) {
            minimum = Math.max(
                minimum,
                Math.ceil(Number(scopedRows[i].vsz || 0) / 1024) + 64
            );
        }

        return minimum;
    }

    function limitMaximumMiB(processRows, rootPids, storedMiB) {
        const minimum = limitMinimumMiB(processRows, rootPids);
        const stored = Math.max(0, Number(storedMiB || 0));

        return Math.max(
            8192,
            Math.ceil((minimum * 4) / 1024) * 1024,
            stored > 0
            ? Math.ceil((stored * 1.25) / 1024) * 1024
            : 0
        );
    }

    function limitPercent(processRows, rootPids, limitMiB) {
        const value = Math.max(0, Number(limitMiB || 0));

        if (value <= 0)
            return 100;

        const minMiB = limitMinimumMiB(processRows, rootPids);
        const maxMiB = limitMaximumMiB(
            processRows,
            rootPids,
            value
        );
        const clamped = Math.max(minMiB, Math.min(maxMiB, value));

        return Math.max(
            0,
            Math.min(
                98.5,
                ((clamped - minMiB)
                 / Math.max(1, maxMiB - minMiB))
                * 98.5
            )
        );
    }

    function limitMiBForPercent(
            processRows,
            rootPids,
            percent,
            storedMiB) {
        const pct = Math.max(0, Math.min(100, Number(percent || 0)));
        const minMiB = limitMinimumMiB(processRows, rootPids);
        const maxMiB = limitMaximumMiB(
            processRows,
            rootPids,
            storedMiB
        );

        if (pct >= 99.5)
            return maxMiB;

        return minMiB + (maxMiB - minMiB) * (pct / 98.5);
    }

    function allFrozen(processRows, rootPids, optimisticFrozen) {
        const scopedRows = rows(processRows, rootPids);

        if (scopedRows.length === 0)
            return !!optimisticFrozen;

        for (let i = 0; i < scopedRows.length; i++) {
            if (String(scopedRows[i].state || "").indexOf("T") === -1)
                return !!optimisticFrozen;
        }

        return true;
    }

    function processText(processRows, rootPids) {
        const sourceRows = Array.isArray(processRows) ? processRows : [];
        const roots = processScope.uniquePositivePids(rootPids);
        const rootSet = ({});
        const parents = parentRows(sourceRows, roots);
        const affected = rows(sourceRows, roots).slice();
        const lines = [];

        for (let i = 0; i < roots.length; i++)
            rootSet[String(roots[i])] = true;

        for (let i = 0; i < parents.length; i++) {
            lines.push(
                "↑ PARENT • "
                + String(parents[i].comm || parents[i].name || "PROCESS")
                + " [" + String(parents[i].pid) + "] • NOT CHANGED"
            );
        }

        affected.sort(function(a, b) {
            const aRoot =
                rootSet[String(Number(a && a.pid || 0))] ? 0 : 1;
            const bRoot =
                rootSet[String(Number(b && b.pid || 0))] ? 0 : 1;

            if (aRoot !== bRoot)
                return aRoot - bRoot;

            return Number(a && a.pid || 0)
                   - Number(b && b.pid || 0);
        });

        for (let i = 0; i < affected.length; i++) {
            const row = affected[i];
            const root =
                rootSet[String(Number(row && row.pid || 0))];

            lines.push(
                (root ? "● ROOT • " : "↳ CHILD • ")
                + String(row && (row.comm || row.name) || "PROCESS")
                + " [" + String(Number(row && row.pid || 0)) + "] • AFFECTED"
            );
        }

        return lines.length > 0
               ? lines.join("\n")
               : "NO LIVE PROCESS SCOPE FOUND";
    }
}
