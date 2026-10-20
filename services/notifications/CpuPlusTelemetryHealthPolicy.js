.pragma library

// Actual completed SystemTelemetry monitor outcomes ONLY. A requested
// refresh clears errorText optimistically and is NOT a recovery signal.
// No raw telemetry, system commands or hardware paths enter history.
function initial() {
    return { health: "unknown", candidate: "", count: 0,
             sinceMs: 0, lastMs: 0 };
}
function transition(previous, success, nowMs) {
    const old = previous || initial();
    const next = {
        health: String(old.health || "unknown"),
        candidate: String(old.candidate || ""),
        count: Number(old.count || 0),
        sinceMs: Number(old.sinceMs || 0),
        lastMs: Number(old.lastMs || 0)
    };
    if (typeof success !== "boolean" || !isFinite(nowMs)
            || nowMs <= 0 || nowMs <= next.lastMs)
        return { state: next, event: "" };
    if (next.lastMs && nowMs - next.lastMs > 60000) {
        next.candidate = "";
        next.count = 0;
        next.sinceMs = 0;
    }
    next.lastMs = nowMs;
    const observation = success ? "healthy" : "failed";
    if (observation === next.health
            || (next.health === "unknown" && success)) {
        if (next.health === "unknown" && success)
            next.health = "healthy";
        next.candidate = "";
        next.count = 0;
        next.sinceMs = 0;
        return { state: next, event: "" };
    }
    if (next.candidate !== observation) {
        next.candidate = observation;
        next.count = 1;
        next.sinceMs = nowMs;
    } else {
        next.count++;
    }
    if (next.count < 2 || nowMs - next.sinceMs < 3500)
        return { state: next, event: "" };

    next.health = observation;
    next.candidate = "";
    next.count = 0;
    next.sinceMs = 0;
    return { state: next, event: success ? "restored" : "unavailable" };
}
