import QtQuick

QtObject {
    id: processResourceController

    // Shared higher-level resource orchestration for an already-resolved
    // process scope. Providers own semantic identity and scopeKey generation.
    required property var resourceScope
    required property var resourceState
    required property var processControl

    signal refreshRequested()

    function scopedRows(processRows, rootPids) {
        return resourceScope.rows(processRows, rootPids);
    }

    function scopedPids(processRows, rootPids) {
        const rows = scopedRows(processRows, rootPids);
        const pids = [];

        for (let i = 0; i < rows.length; i++) {
            const pid = Number(rows[i] && rows[i].pid || 0);

            if (pid > 1 && pids.indexOf(pid) === -1)
                pids.push(pid);
        }

        return pids;
    }

    function setMemoryLimitMiB(
            scopeKey,
            processRows,
            rootPids,
            requestedMiB) {
        if (!resourceScope.limitAvailable(processRows, rootPids))
            return false;

        const rows = scopedRows(processRows, rootPids);

        if (rows.length === 0)
            return false;

        const stored = resourceState.limitMiB(
            scopeKey,
            processRows,
            rootPids
        );
        const normalized = resourceState.normalizedRequestedLimit(
            processRows,
            rootPids,
            requestedMiB,
            stored
        );
        const capBytes =
            normalized > 0
            ? Math.floor(normalized * 1024 * 1024)
            : 0;
        const pids = scopedPids(processRows, rootPids);

        if (!processControl.setAddressSpaceLimitBytesMany(
                pids,
                capBytes))
            return false;

        resourceState.rememberLimit(
            scopeKey,
            processRows,
            rootPids,
            normalized
        );
        refreshRequested();
        return true;
    }

    function setMemoryLimitPercent(
            scopeKey,
            processRows,
            rootPids,
            percent) {
        const stored = resourceState.limitMiB(
            scopeKey,
            processRows,
            rootPids
        );
        const requested = resourceScope.limitMiBForPercent(
            processRows,
            rootPids,
            percent,
            stored
        );

        return setMemoryLimitMiB(
            scopeKey,
            processRows,
            rootPids,
            requested
        );
    }

    function reconcileMemoryLimit(
            scopeKey,
            processRows,
            rootPids) {
        if (!resourceScope.limitAvailable(processRows, rootPids))
            return false;

        const desired = resourceState.reconciliationTargetMiB(
            scopeKey,
            processRows,
            rootPids
        );

        if (desired <= 0)
            return false;

        const rows = scopedRows(processRows, rootPids);
        const capBytes = Math.floor(desired * 1024 * 1024);
        let changed = false;

        for (let i = 0; i < rows.length; i++) {
            const row = rows[i];
            const pid = Number(row && row.pid || 0);
            const pidKey = resourceState.pidPolicyKey(row);

            if (pid <= 1 || !pidKey)
                continue;

            const existing =
                resourceState.memoryLimitPidPolicies[pidKey];

            if (existing !== undefined
                    && Math.abs(
                        Number(existing || 0) - desired
                    ) <= 0.5)
                continue;

            if (!processControl.setAddressSpaceLimitBytes(
                    pid,
                    capBytes))
                continue;

            resourceState.noteReconciledPid(row, desired);
            changed = true;
        }

        if (changed)
            refreshRequested();

        return changed;
    }

    function isFrozen(scopeKey, processRows, rootPids) {
        return resourceState.isFrozen(
            scopeKey,
            processRows,
            rootPids
        );
    }

    function freezeAvailable(
            scopeKey,
            processRows,
            rootPids) {
        const rows = scopedRows(processRows, rootPids);

        if (rows.length === 0)
            return false;

        // Resume must always remain available so a stopped scope can recover.
        return isFrozen(scopeKey, processRows, rootPids)
               || !resourceScope.containsProtected(
                   processRows,
                   rootPids
               );
    }

    function toggleFreeze(
            scopeKey,
            processRows,
            rootPids) {
        if (!freezeAvailable(scopeKey, processRows, rootPids))
            return false;

        const frozen = isFrozen(
            scopeKey,
            processRows,
            rootPids
        );
        const pids = scopedPids(processRows, rootPids);

        if (!processControl.sendSignalMany(
                pids,
                frozen ? "-CONT" : "-STOP"))
            return false;

        resourceState.markFrozen(scopeKey, !frozen);
        refreshRequested();
        return true;
    }
}
