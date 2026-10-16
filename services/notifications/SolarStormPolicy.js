.pragma library

// NOAA planetary Kp observations already fetched by SpaceService. Local
// notification labels are NOT official NOAA warning products or predictions.
function stormLevel(value) {
    if (value === null || value === undefined || value === ""
            || typeof value === "boolean")
        return -1;
    const kp = Number(value);
    if (!isFinite(kp) || kp < 0 || kp > 9)
        return -1;
    return kp >= 9 ? 5 : kp >= 8 ? 4 : kp >= 7 ? 3
           : kp >= 6 ? 2 : kp >= 5 ? 1 : 0;
}
function initial() {
    return { lastTimeMs: 0, lastLevel: 0 };
}
// One observation timestamp is processed once. Only new observations that
// enter a geomagnetic storm band or escalate generate alerts.
// A first valid observed storm can be shown, but NEVER called a new onset.
function transition(previous, kp, observedMs, nowMs) {
    const old = previous || initial();
    const state = {
        lastTimeMs: Number(old.lastTimeMs || 0),
        lastLevel: Number(old.lastLevel || 0)
    };
    const level = stormLevel(kp);
    if (level < 0 || typeof observedMs !== "number"
            || !isFinite(observedMs) || observedMs <= state.lastTimeMs
            || typeof nowMs !== "number" || !isFinite(nowMs)
            || nowMs - observedMs < -10 * 60 * 1000
            || nowMs - observedMs > 8 * 60 * 60 * 1000)
        return { state: state, emit: 0, kind: "" };

    const previousLevel = state.lastLevel;
    state.lastTimeMs = observedMs;
    state.lastLevel = level;
    const rising = level > 0 && level > previousLevel;
    return { state: state,
             emit: rising ? level : 0,
             kind: rising ? (previousLevel > 0 ? "escalated" : "observed") : "" };
}
