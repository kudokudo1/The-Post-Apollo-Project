.pragma library

// Hub P2-B1: sanitized read-only projection of AppControl's existing
// ProcessTelemetry.rows. Never expose argv, usernames, environment, paths,
// target handles, or process control methods. No new acquisition cadence.
var MAX_ROWS = 24;

function cleanName(value) {
    if (typeof value !== "string") return "";
    return value.replace(/[\x00-\x1f\x7f]/g, " ").trim().slice(0, 70);
}

function percent(value) {
    if (typeof value !== "number" || !isFinite(value) || value < 0)
        return -1;
    return Math.min(100, Math.round(value * 10) / 10);
}

function processId(value) {
    return typeof value === "number" && isFinite(value)
           && Math.floor(value) === value && value > 1
           && value <= 2147483647 ? value : -1;
}

function snapshot(rows, loading, error) {
    if (typeof error === "string" && error.trim() !== "") {
        return {state:"error",source:"appcontrol-process-telemetry",
                error:"OWNER_SAMPLE_FAILED",total:0,shown:0,
                truncated:false,items:[]};
    }
    if (!Array.isArray(rows)) {
        return {state:"unavailable",source:"appcontrol-process-telemetry",
                error:"OWNER_NOT_CONNECTED",total:0,shown:0,
                truncated:false,items:[]};
    }
    const items = [];
    const seen = Object.create(null);
    let total = 0;
    for (let i = 0; i < rows.length; i++) {
        const row = rows[i];
        const pid = processId(row && row.pid);
        if (pid < 0 || seen[String(pid)]) continue;
        const name = cleanName(row && (row.comm || row.name));
        if (!name) continue;
        seen[String(pid)] = true;
        total++;
        if (items.length < MAX_ROWS) {
            // "T" in ps state means stopped/traced at observation time.
            // It is not evidence that Hub itself froze the process.
            const state = typeof row.state === "string"
                          ? row.state.slice(0, 8) : "";
            items.push({pid:pid,name:name,state:state,
                        stopped:state.indexOf("T") !== -1,
                        cpu:percent(row.cpu),
                        memoryPercent:percent(row.mem)});
        }
    }
    return {state:loading === true ? "refreshing"
                : total === 0 ? "empty" : "ready",
            source:"appcontrol-process-telemetry",
            error:"",total:total,shown:items.length,
            truncated:total > items.length,items:items};
}
