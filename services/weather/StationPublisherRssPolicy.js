.pragma library

// Independent, volatile last-good RSS headlines for each fixed publisher.
// Never creates a network request. A Quickshell restart clears the cache.
var _cache = {};

function validId(id) {
    return id === "bbc-world" || id === "al-jazeera-english";
}
function publisher(id) {
    return id === "bbc-world" ? "BBC WORLD"
         : id === "al-jazeera-english" ? "AL JAZEERA ENGLISH" : "";
}
function stateFor(id) {
    if (!validId(id)) return null;
    if (!_cache[id])
        _cache[id] = {rows:[],updatedAtMs:0,nextAllowedMs:0,lastClockMs:0};
    return _cache[id];
}
function reconcileClock(entry, nowMs) {
    const now = Number(nowMs);
    if (!entry || !isFinite(now) || now <= 0) return 0;
    // Match the GDELT clock-correction policy: preserve cooldown remaining.
    if (entry.lastClockMs > 0 && now < entry.lastClockMs - 60000)
        entry.nextAllowedMs = Math.max(now,
            entry.nextAllowedMs + now - entry.lastClockMs);
    entry.lastClockMs = now;
    return now;
}
function snapshot(id) {
    const entry = stateFor(id);
    return entry ? {rows:entry.rows.slice(), updatedAtMs:entry.updatedAtMs}
                 : {rows:[], updatedAtMs:0};
}
function waitMs(id, nowMs) {
    const entry = stateFor(id);
    const now = reconcileClock(entry, nowMs);
    return entry && now > 0 ? Math.max(0, entry.nextAllowedMs - now) : 0;
}
function reserve(id, nowMs) {
    const entry = stateFor(id);
    const now = reconcileClock(entry, nowMs);
    if (!entry || now <= 0 || waitMs(id, now) > 0) return false;
    // Separate 60-second limits, no background refresh or request chaining.
    entry.nextAllowedMs = now + 60000;
    return true;
}
function store(id, rows, nowMs) {
    const entry = stateFor(id);
    const now = reconcileClock(entry, nowMs);
    if (!entry || now <= 0 || !Array.isArray(rows) || rows.length === 0)
        return false;
    entry.rows = rows.slice(0, 20);
    entry.updatedAtMs = now;
    return true;
}
