.pragma library

// Current observed system state from existing shared SystemTelemetry only.
// Never infer a hazard from high utilization alone; no control side effects.
function localDayKey(date) {
    const pad = function(n) { return String(n).padStart(2, "0"); };
    return date.getFullYear() + "-" + pad(date.getMonth() + 1)
        + "-" + pad(date.getDate());
}
function percent(raw) {
    if (raw === null || raw === undefined || raw === ""
            || typeof raw === "boolean")
        return null;
    const n = Number(raw);
    return isFinite(n) && n >= 0 && n <= 100 ? n : null;
}
function observation(rows, observedMs) {
    if (!Array.isArray(rows) || !isFinite(observedMs) || observedMs <= 0)
        return null;
    const record = {
        cpuPercent: null, memoryPercent: null, swapPercent: null,
        rootStoragePercent: null, gpuPercent: null,
        networkUp: 0, networkDown: 0, networkUnknown: 0,
        observedAtUtc: new Date(observedMs).toISOString()
    };
    for (let i = 0; i < rows.length; ++i) {
        const row = rows[i];
        if (!row || row._systemRecord !== true)
            continue;
        const id = String(row.id || "");
        const value = percent(row.usage);
        if (id === "system:cpu")
            record.cpuPercent = value;
        else if (id === "system:memory")
            record.memoryPercent = value;
        else if (id === "system:swap")
            record.swapPercent = value;
        else if (id === "system:rootfs")
            record.rootStoragePercent = value;
        else if (id.indexOf("system:gpu:") === 0
                && value !== null
                && (record.gpuPercent === null || value > record.gpuPercent))
            record.gpuPercent = value;
        else if (id.indexOf("system:net:") === 0) {
            const state = String(row.secondary || "").trim().toUpperCase();
            if (state === "UP")
                record.networkUp += 1;
            else if (state === "DOWN" || state === "LOWERLAYERDOWN")
                record.networkDown += 1;
            else
                record.networkUnknown += 1;
        }
    }
    if (record.cpuPercent === null && record.memoryPercent === null
            && record.swapPercent === null
            && record.rootStoragePercent === null
            && record.gpuPercent === null
            && record.networkUp + record.networkDown
               + record.networkUnknown === 0)
        return null;
    return record;
}
function summary(report) {
    function fmt(v) { return v === null ? "N/A" : v.toFixed(1) + "%"; }
    const lines = [
        "CPU // " + fmt(report.cpuPercent)
            + "  RAM // " + fmt(report.memoryPercent),
        "SWAP // " + fmt(report.swapPercent)
            + "  ROOT STORAGE // " + fmt(report.rootStoragePercent),
        "GPU // " + fmt(report.gpuPercent)
    ];
    const interfaces = report.networkUp + report.networkDown
                     + report.networkUnknown;
    if (interfaces > 0)
        lines.push("NETWORK // " + report.networkUp + " UP"
            + "  " + report.networkDown + " DOWN"
            + "  " + report.networkUnknown + " OTHER");
    lines.push("OBSERVED // " + report.observedAtUtc);
    return lines.join("\n");
}
