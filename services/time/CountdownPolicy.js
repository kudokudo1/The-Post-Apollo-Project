.pragma library

// TimeW countdown rules. QML's monotonic ElapsedTimer measures each running
// segment. A QML Timer merely samples the remaining time and detects expiry.
// No files, network, shell, system clock changes, or notifications.
var MAX_HOURS = 99;
var MAX_TIMERS = 8;
var MAX_NAME_LENGTH = 32;

function whole(value, max) {
    if (typeof value !== "string" || !/^\d{1,2}$/.test(value))
        return null;
    var number = Number(value);
    return number <= max ? number : null;
}

function parseDuration(hours, minutes, seconds) {
    var h = whole(hours, MAX_HOURS);
    var m = whole(minutes, 59);
    var s = whole(seconds, 59);
    if (h === null || m === null || s === null)
        return {valid: false, milliseconds: 0, error: "INVALID_DURATION"};
    var millis = (h * 3600 + m * 60 + s) * 1000;
    if (millis === 0)
        return {valid: false, milliseconds: 0, error: "ZERO_DURATION"};
    return {valid: true, milliseconds: millis, error: ""};
}

function remaining(segmentBudgetMs, segmentElapsedMs) {
    if (typeof segmentBudgetMs !== "number" || !isFinite(segmentBudgetMs)
            || segmentBudgetMs < 0 || typeof segmentElapsedMs !== "number"
            || !isFinite(segmentElapsedMs) || segmentElapsedMs < 0)
        return 0;
    return Math.max(0, Math.ceil(segmentBudgetMs - segmentElapsedMs));
}

function pad2(number) {
    return String(number).padStart(2, "0");
}

function format(milliseconds) {
    if (typeof milliseconds !== "number" || !isFinite(milliseconds)
            || milliseconds < 0)
        return "--:--:--";
    // Round upward so a positive remainder never appears as zero seconds.
    var seconds = Math.ceil(milliseconds / 1000);
    var h = Math.floor(seconds / 3600);
    var m = Math.floor(seconds / 60) % 60;
    var s = seconds % 60;
    return pad2(h) + ":" + pad2(m) + ":" + pad2(s);
}


// Multiple independent timers use one shared monotonic clock. Each running
// record stores its own starting tick and remaining budget. The caller
// replaces the array after every operation so QML sees property changes.
function createTimer(id) {
    if (!Number.isInteger(id) || id < 1)
        return null;
    return {
        id: id,
        name: "TIMER " + id,
        hours: "0",
        minutes: "5",
        seconds: "0",
        status: "ready",
        remainingMs: 0,
        segmentBudgetMs: 0,
        startedAtMs: 0,
        error: ""
    };
}

function copyWith(entry, patch) {
    var result = {};
    Object.keys(entry).forEach(function(key) { result[key] = entry[key]; });
    Object.keys(patch).forEach(function(key) { result[key] = patch[key]; });
    return result;
}

function byId(entries, id) {
    if (!Array.isArray(entries))
        return null;
    for (var i = 0; i < entries.length; i++)
        if (entries[i].id === id)
            return entries[i];
    return null;
}

function update(entries, id, patch) {
    if (!Array.isArray(entries) || !patch || typeof patch !== "object")
        return entries;
    return entries.map(function(entry) {
        return entry.id === id ? copyWith(entry, patch) : entry;
    });
}

function runningCount(entries) {
    if (!Array.isArray(entries)) return 0;
    return entries.filter(function(entry) {
        return entry.status === "running";
    }).length;
}

function displayMs(entry) {
    if (!entry) return 0;
    if (entry.status !== "ready")
        return entry.remainingMs;
    var parsed = parseDuration(entry.hours, entry.minutes, entry.seconds);
    return parsed.valid ? parsed.milliseconds : 0;
}

function tick(entries, nowMs) {
    if (!Array.isArray(entries) || typeof nowMs !== "number"
            || !isFinite(nowMs) || nowMs < 0)
        return entries;
    if (!entries.some(function(entry) { return entry.status === "running"; }))
        return entries;
    return entries.map(function(entry) {
        if (entry.status !== "running") return entry;
        var left = remaining(entry.segmentBudgetMs,
                             Math.max(0, nowMs - entry.startedAtMs));
        return copyWith(entry, {
            remainingMs: left,
            status: left <= 0 ? "finished" : "running"
        });
    });
}

function act(entries, id, action, nowMs) {
    if (!Array.isArray(entries) || typeof nowMs !== "number"
            || !isFinite(nowMs) || nowMs < 0)
        return entries;
    var timer = byId(entries, id);
    if (!timer) return entries;
    if (action === "start") {
        if (timer.status === "running") return entries;
        var budget;
        if (timer.status === "paused") {
            budget = timer.remainingMs;
        } else {
            var result = parseDuration(timer.hours, timer.minutes, timer.seconds);
            if (!result.valid)
                return update(entries, id, {error: result.error});
            budget = result.milliseconds;
        }
        return update(entries, id, {
            status: "running",
            remainingMs: budget,
            segmentBudgetMs: budget,
            startedAtMs: nowMs,
            error: ""
        });
    }
    if (action === "pause") {
        if (timer.status !== "running") return entries;
        var left = remaining(timer.segmentBudgetMs,
                             Math.max(0, nowMs - timer.startedAtMs));
        return update(entries, id, {
            status: left <= 0 ? "finished" : "paused",
            remainingMs: left,
            segmentBudgetMs: left,
            error: ""
        });
    }
    if (action === "reset") {
        return update(entries, id, {
            status: "ready",
            remainingMs: 0,
            segmentBudgetMs: 0,
            startedAtMs: 0,
            error: ""
        });
    }
    return entries;
}
