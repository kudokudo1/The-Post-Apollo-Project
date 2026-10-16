.pragma library

// Read only existing CPU++ / AppControl SystemTelemetry rows. Percentages are
// software-configured notification thresholds, NOT hardware safety limits.
// High swap usage alone is not evidence of current memory pressure.
function percent(value) {
    if (value === null || value === undefined || value === ""
            || typeof value === "boolean")
        return null;
    const n = Number(value);
    return isFinite(n) && n >= 0 && n <= 100 ? n : null;
}

function observation(rows) {
    if (!Array.isArray(rows))
        return null;
    const metrics = { memory: null, storage: null, swap: null };
    for (let i = 0; i < rows.length; ++i) {
        const row = rows[i] || {};
        if (row._systemRecord !== true)
            continue;
        const value = percent(row.usage);
        if (row.id === "system:memory")
            metrics.memory = value;
        else if (row.id === "system:rootfs")
            metrics.storage = value;
        else if (row.id === "system:swap")
            metrics.swap = value;
    }
    if (metrics.memory === null && metrics.storage === null)
        return null;
    return metrics;
}

// Configurable notification defaults. Require corroborated readings rather
// than treating one busy sample as an actionable failure.
function thresholds(kind) {
    if (kind === "memory" || kind === "storage")
        return { warning: 90, critical: 97, recovered: 87 };
    return null;
}

function level(kind, value) {
    const t = thresholds(kind);
    const v = percent(value);
    if (!t || v === null)
        return 0;
    return v >= t.critical ? 2 : v >= t.warning ? 1 : 0;
}

function initial() {
    return { sent: 0, candidate: 0, candidateCount: 0,
             candidateSinceMs: 0, clearCount: 0, clearSinceMs: 0,
             lastSampleMs: 0 };
}
function resetCandidate(state) {
    state.candidate = 0;
    state.candidateCount = 0;
    state.candidateSinceMs = 0;
}
function resetRecovery(state) {
    state.clearCount = 0;
    state.clearSinceMs = 0;
}

// Existing shared monitor updates about every 1.9s while open. Three samples
// spanning >= 3.5s are required for warning, escalation and full recovery.
// Monitoring pauses do NOT count as evidence of a sustained problem.
function transition(previous, kind, raw, observedMs) {
    const old = previous || initial();
    const state = {
        sent: Number(old.sent || 0),
        candidate: Number(old.candidate || 0),
        candidateCount: Number(old.candidateCount || 0),
        candidateSinceMs: Number(old.candidateSinceMs || 0),
        clearCount: Number(old.clearCount || 0),
        clearSinceMs: Number(old.clearSinceMs || 0),
        lastSampleMs: Number(old.lastSampleMs || 0)
    };
    const value = percent(raw);
    const t = thresholds(kind);
    if (!t || value === null || typeof observedMs !== "number"
            || !isFinite(observedMs) || observedMs <= state.lastSampleMs
            || observedMs <= 0)
        return { state: state, event: "" };

    if (state.lastSampleMs && observedMs - state.lastSampleMs > 15000) {
        resetCandidate(state);
        resetRecovery(state);
    }
    state.lastSampleMs = observedMs;
    const observedLevel = level(kind, value);
    if (observedLevel > state.sent) {
        resetRecovery(state);
        if (state.candidate !== observedLevel) {
            state.candidate = observedLevel;
            state.candidateCount = 1;
            state.candidateSinceMs = observedMs;
        } else {
            state.candidateCount += 1;
        }
        if (state.candidateCount >= 3
                && observedMs - state.candidateSinceMs >= 3500) {
            state.sent = observedLevel;
            resetCandidate(state);
            return { state: state,
                     event: observedLevel === 2 ? "critical" : "warning" };
        }
        return { state: state, event: "" };
    }

    resetCandidate(state);
    if (state.sent > 0 && value <= t.recovered) {
        if (!state.clearCount)
            state.clearSinceMs = observedMs;
        state.clearCount += 1;
        if (state.clearCount >= 3
                && observedMs - state.clearSinceMs >= 3500) {
            state.sent = 0;
            resetRecovery(state);
            return { state: state, event: "recovered" };
        }
    } else {
        resetRecovery(state);
    }
    return { state: state, event: "" };
}
