import QtQuick

QtObject {
    id: processResourceState

    // Provider-neutral resource policy/state. Callers supply a semantic
    // scopeKey plus explicit process rows/root PID(s). This object does not
    // generate scope identity and does not mutate the kernel.
    required property var processIdentity
    required property var resourceScope

    // Identity-keyed state keeps APP/WINDOW/TAB/RUN controls stable across
    // process respawns. PID mirrors keep overlapping scopes visually honest.
    property var memoryLimitPolicies: ({})
    property var memoryLimitPidPolicies: ({})
    property var frozenScopes: ({})

    function normalizedScopeKey(scopeKey) {
        return String(scopeKey || "").trim();
    }

    function pidPolicyKey(entry) {
        return processIdentity.pidPolicyKey(entry);
    }

    function rootLimitState(processRows, rootPids) {
        const roots = resourceScope.rootPids(rootPids);

        if (roots.length === 0)
            return {
                known: 0,
                mixed: false,
                value: -1
            };

        const rows = Array.isArray(processRows) ? processRows : [];
        let known = 0;
        let first = -1;
        let mixed = false;
        let strictestFinite = 0;

        for (let i = 0; i < roots.length; i++) {
            let row = null;

            for (let r = 0; r < rows.length; r++) {
                if (Number(rows[r] && rows[r].pid || 0) === roots[i]) {
                    row = rows[r];
                    break;
                }
            }

            if (!row)
                continue;

            const key = pidPolicyKey(row);

            if (!key || memoryLimitPidPolicies[key] === undefined)
                continue;

            const value = Math.max(
                0,
                Number(memoryLimitPidPolicies[key] || 0)
            );

            known++;

            if (first < 0)
                first = value;
            else if (Math.abs(first - value) > 0.5)
                mixed = true;

            if (value > 0
                    && (strictestFinite <= 0
                        || value < strictestFinite))
                strictestFinite = value;
        }

        // A partially-known multi-root scope is mixed too. Another scope may
        // have capped only one shared root.
        if (known > 0 && known < roots.length)
            mixed = true;

        return {
            known: known,
            mixed: mixed,
            value:
                mixed && strictestFinite > 0
                ? strictestFinite
                : first
        };
    }

    function limitMixed(processRows, rootPids) {
        return !!rootLimitState(processRows, rootPids).mixed;
    }

    function limitMiB(scopeKey, processRows, rootPids) {
        const rootState = rootLimitState(processRows, rootPids);

        if (rootState.known > 0 && rootState.value >= 0)
            return Number(rootState.value || 0);

        const key = normalizedScopeKey(scopeKey);

        if (!key || memoryLimitPolicies[key] === undefined)
            return 0;

        return Number(memoryLimitPolicies[key] || 0);
    }

    function hasLimit(scopeKey, processRows, rootPids) {
        return limitMiB(scopeKey, processRows, rootPids) > 0;
    }

    function normalizedRequestedLimit(
            processRows,
            rootPids,
            requestedMiB,
            storedMiB) {
        const requested = Number(requestedMiB);
        const maximum = resourceScope.limitMaximumMiB(
            processRows,
            rootPids,
            storedMiB
        );

        if (!isFinite(requested)
                || requested >= maximum * 0.995)
            return 0;

        const minimum = resourceScope.limitMinimumMiB(
            processRows,
            rootPids
        );

        return Math.max(
            minimum,
            Math.min(maximum - 1, requested)
        );
    }

    function rememberScopeLimit(
            scopeKey,
            processRows,
            rootPids,
            requestedMiB) {
        const key = normalizedScopeKey(scopeKey);
        const scopedRows = resourceScope.rows(processRows, rootPids);

        if (!key || scopedRows.length === 0)
            return 0;

        const previous = limitMiB(
            key,
            processRows,
            rootPids
        );
        const normalized = normalizedRequestedLimit(
            processRows,
            rootPids,
            requestedMiB,
            previous
        );
        const nextScopes = Object.assign({}, memoryLimitPolicies);

        if (normalized > 0)
            nextScopes[key] = normalized;
        else
            delete nextScopes[key];

        memoryLimitPolicies = nextScopes;
        return normalized;
    }

    function rowForMutationPid(processRows, pid) {
        const wanted = Number(pid || 0);
        const rows = Array.isArray(processRows) ? processRows : [];

        if (wanted <= 1)
            return null;

        for (let i = 0; i < rows.length; i++) {
            if (Number(rows[i] && rows[i].pid || 0) === wanted)
                return rows[i];
        }

        return null;
    }

    function verifiedMiBFromResult(result) {
        if (!result || !result.ok)
            return -1;

        const soft = Number(result.soft);

        // ProcessLimitMutation reports RLIM_INFINITY as -1.
        if (!isFinite(soft) || soft < 0)
            return 0;

        return soft / (1024 * 1024);
    }

    function noteMutationResults(processRows, results) {
        const source = Array.isArray(results) ? results : [];
        const next = Object.assign({}, memoryLimitPidPolicies);
        let changed = false;
        let successCount = 0;
        let failureCount = 0;

        for (let i = 0; i < source.length; i++) {
            const result = source[i];

            if (!result || !result.ok) {
                failureCount++;
                continue;
            }

            const row = rowForMutationPid(
                processRows,
                Number(result.pid || 0)
            );
            const key = pidPolicyKey(row);

            if (!key) {
                failureCount++;
                continue;
            }

            const verifiedMiB = verifiedMiBFromResult(result);

            if (verifiedMiB < 0) {
                failureCount++;
                continue;
            }

            successCount++;

            if (next[key] === undefined
                    || Math.abs(
                        Number(next[key] || 0) - verifiedMiB
                    ) > 0.5) {
                next[key] = verifiedMiB;
                changed = true;
            }
        }

        if (changed)
            memoryLimitPidPolicies = next;

        return {
            successCount: successCount,
            failureCount: failureCount,
            changed: changed
        };
    }

    function rememberLimit(
            scopeKey,
            processRows,
            rootPids,
            requestedMiB) {
        const normalized = rememberScopeLimit(
            scopeKey,
            processRows,
            rootPids,
            requestedMiB
        );
        const scopedRows = resourceScope.rows(processRows, rootPids);
        const nextPids = Object.assign({}, memoryLimitPidPolicies);

        for (let i = 0; i < scopedRows.length; i++) {
            const pidKey = pidPolicyKey(scopedRows[i]);

            if (pidKey)
                nextPids[pidKey] = normalized;
        }

        memoryLimitPidPolicies = nextPids;
        return normalized;
    }

    function rememberLimitPercent(
            scopeKey,
            processRows,
            rootPids,
            percent) {
        const stored = limitMiB(
            scopeKey,
            processRows,
            rootPids
        );
        const mib = resourceScope.limitMiBForPercent(
            processRows,
            rootPids,
            percent,
            stored
        );

        return rememberLimit(
            scopeKey,
            processRows,
            rootPids,
            mib
        );
    }

    function reconciliationTargetMiB(
            scopeKey,
            processRows,
            rootPids) {
        const key = normalizedScopeKey(scopeKey);
        const scopedRows = resourceScope.rows(processRows, rootPids);

        if (!key || scopedRows.length === 0)
            return -1;

        const rootState = rootLimitState(
            processRows,
            rootPids
        );

        // Never collapse a deliberately mixed shared scope implicitly.
        if (rootState.mixed)
            return -1;

        let desired = -1;

        if (rootState.known > 0 && rootState.value >= 0)
            desired = Number(rootState.value || 0);
        else if (memoryLimitPolicies[key] !== undefined)
            desired = Math.max(
                0,
                Number(memoryLimitPolicies[key] || 0)
            );

        // Unlimited is already the kernel default. Reconciliation is only
        // needed to carry an explicit finite policy onto replacements.
        return desired > 0 ? desired : -1;
    }

    function noteReconciledPid(entry, desiredMiB) {
        const key = pidPolicyKey(entry);

        if (!key)
            return false;

        const desired = Math.max(0, Number(desiredMiB || 0));
        const existing = memoryLimitPidPolicies[key];

        if (existing !== undefined
                && Math.abs(Number(existing || 0) - desired) <= 0.5)
            return false;

        const next = Object.assign({}, memoryLimitPidPolicies);
        next[key] = desired;
        memoryLimitPidPolicies = next;
        return true;
    }

    function isFrozen(scopeKey, processRows, rootPids) {
        const key = normalizedScopeKey(scopeKey);

        if (!key)
            return false;

        return resourceScope.allFrozen(
            processRows,
            rootPids,
            !!frozenScopes[key]
        );
    }

    function markFrozen(scopeKey, frozen) {
        const key = normalizedScopeKey(scopeKey);

        if (!key)
            return false;

        const next = Object.assign({}, frozenScopes);

        if (frozen)
            next[key] = true;
        else
            delete next[key];

        frozenScopes = next;
        return true;
    }

    function clearScope(scopeKey) {
        const key = normalizedScopeKey(scopeKey);

        if (!key)
            return;

        const limits = Object.assign({}, memoryLimitPolicies);
        const frozen = Object.assign({}, frozenScopes);

        delete limits[key];
        delete frozen[key];

        memoryLimitPolicies = limits;
        frozenScopes = frozen;
    }
}
