.pragma library

// Pure read-only projection of existing SystemTelemetry.systemRows.
// No process launch, device sampling, filesystem access, or actuator fields.
var MAX_SAMPLE_AGE_MS = 300000;

function observationFresh(observedAtMs, nowMs) {
    var then = Number(observedAtMs);
    var now = Number(nowMs);
    return isFinite(then) && then > 0 && isFinite(now)
           && now >= then && now - then <= MAX_SAMPLE_AGE_MS;
}

function rowById(rows, id) {
    if (!Array.isArray(rows))
        return null;
    for (var i = 0; i < rows.length; ++i) {
        var entry = rows[i];
        if (entry && entry.id === id && entry._systemRecord === true)
            return entry;
    }
    return null;
}

function usagePercent(row) {
    if (!row || row.usage === null || row.usage === undefined
            || String(row.usage).trim() === "")
        return -1;
    var value = Number(row.usage);
    return isFinite(value) && value >= 0 && value <= 100
           ? Math.round(value * 10) / 10 : -1;
}

function metric(row) {
    return row && typeof row.metric === "string" ? row.metric : "";
}

function snapshot(connected, loading, errorText, rows, observedAtMs, nowMs) {
    var attached = connected === true;
    var busy = attached && loading === true;
    var error = attached ? String(errorText || "") : "";
    var freshTime = attached && observationFresh(observedAtMs, nowMs);
    var cpu = rowById(rows, "system:cpu");
    var memory = rowById(rows, "system:memory");
    var swap = rowById(rows, "system:swap");
    var root = rowById(rows, "system:rootfs");

    var state = "disconnected";
    if (attached) {
        if (error !== "")
            state = "error";
        else if (busy)
            state = "loading";
        else if (!(Number(observedAtMs) > 0))
            state = "unobserved";
        else if (!freshTime)
            state = "stale";
        else if (!cpu || !memory
                || usagePercent(cpu) < 0 || usagePercent(memory) < 0)
            // Both rows and valid percentages are required for ready.
            // Missing/invalid readings must not look like healthy data.
            state = "unavailable";
        else
            state = "ready";
    }

    var usable = state === "ready";
    var stamp = Number(observedAtMs);
    var now = Number(nowMs);
    return {
        state: state,
        connected: attached,
        loading: busy,
        fresh: usable,
        error: error,
        observedAtMs: attached && stamp > 0 ? stamp : 0,
        ageMinutes: attached && stamp > 0 && now >= stamp
                    ? Math.floor((now - stamp) / 60000) : -1,
        cpuPercent: usable ? usagePercent(cpu) : -1,
        cpuMetric: usable ? metric(cpu) : "",
        memoryPercent: usable ? usagePercent(memory) : -1,
        memoryMetric: usable ? metric(memory) : "",
        swapPercent: usable ? usagePercent(swap) : -1,
        swapMetric: usable ? metric(swap) : "",
        rootFilesystemPercent: usable ? usagePercent(root) : -1,
        rootFilesystemMetric: usable ? metric(root) : ""
    };
}
