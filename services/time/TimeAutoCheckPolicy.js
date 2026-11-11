.pragma library

// Separate from display calibration and privileged host time correction.
// Automatic reference measurements only; no process here sets Linux time.
var VERSION = 1;
var MIN_HOURS = 1;
var MAX_HOURS = 168;
var HOUR_MS = 60 * 60 * 1000;

function validHours(value) {
    return typeof value === "number" && isFinite(value)
           && Math.floor(value) === value
           && value >= MIN_HOURS && value <= MAX_HOURS;
}

function validTimestamp(value) {
    return typeof value === "number" && isFinite(value)
           && Math.floor(value) === value
           && value >= 0 && value <= 8640000000000000;
}

function initialDocument() {
    // The master AUTO switch remains opt-in. When enabled, trigger
    // preferences default ON for reload/open but are independently mutable.
    return { version: VERSION, enabled: false, intervalHours: 6,
             lastAttemptAtMs: 0, checkOnReload: true,
             checkOnClockOpen: true };
}

function validOptionalTrigger(value) {
    return value === undefined || typeof value === "boolean";
}

function normalizedTrigger(doc, name) {
    // Existing v1 documents have no trigger keys. Treat omitted keys as ON
    // without destructive migration or silently resetting the saved interval.
    return doc[name] === undefined ? true : doc[name];
}

function parse(raw) {
    var doc;
    try { doc = JSON.parse(String(raw)); }
    catch (error) { return { ok: false, reason: "INVALID_JSON" }; }
    if (!doc || typeof doc !== "object" || Array.isArray(doc))
        return { ok: false, reason: "INVALID_DOCUMENT" };
    if (doc.version !== VERSION)
        return { ok: false, reason: "UNSUPPORTED_VERSION" };
    if (typeof doc.enabled !== "boolean" || !validHours(doc.intervalHours)
            || !validTimestamp(doc.lastAttemptAtMs)
            || !validOptionalTrigger(doc.checkOnReload)
            || !validOptionalTrigger(doc.checkOnClockOpen))
        return { ok: false, reason: "INVALID_SCHEDULE" };
    return { ok: true, document: {
        version: VERSION, enabled: doc.enabled,
        intervalHours: doc.intervalHours,
        lastAttemptAtMs: doc.lastAttemptAtMs,
        checkOnReload: normalizedTrigger(doc, "checkOnReload"),
        checkOnClockOpen: normalizedTrigger(doc, "checkOnClockOpen")
    }};
}

function withSchedule(doc, enabled, hours) {
    if (typeof enabled !== "boolean" || !validHours(hours))
        return { ok: false, reason: "INVALID_SCHEDULE" };
    return { ok: true, document: {
        version: VERSION, enabled: enabled, intervalHours: hours,
        lastAttemptAtMs: doc && validTimestamp(doc.lastAttemptAtMs)
                         ? doc.lastAttemptAtMs : 0,
        checkOnReload: doc ? normalizedTrigger(doc, "checkOnReload") : true,
        checkOnClockOpen: doc ? normalizedTrigger(doc, "checkOnClockOpen") : true
    }};
}

function withTrigger(doc, name, enabled) {
    if (!doc || (name !== "checkOnReload" && name !== "checkOnClockOpen")
            || typeof enabled !== "boolean")
        return { ok: false, reason: "INVALID_TRIGGER" };
    var next = withSchedule(doc, doc.enabled, doc.intervalHours);
    if (!next.ok)
        return next;
    next.document[name] = enabled;
    return next;
}

function withAttempt(doc, nowMs) {
    if (!doc || !validTimestamp(nowMs))
        return { ok: false, reason: "INVALID_TIMESTAMP" };
    return { ok: true, document: {
        version: VERSION, enabled: doc.enabled,
        intervalHours: doc.intervalHours, lastAttemptAtMs: nowMs,
        checkOnReload: normalizedTrigger(doc, "checkOnReload"),
        checkOnClockOpen: normalizedTrigger(doc, "checkOnClockOpen")
    }};
}

function triggerEnabled(doc, trigger) {
    if (!doc || !doc.enabled)
        return false;
    if (trigger === "reload")
        return normalizedTrigger(doc, "checkOnReload");
    if (trigger === "clock-open")
        return normalizedTrigger(doc, "checkOnClockOpen");
    return trigger === "interval";
}

function isDue(doc, nowMs, lastStartedAtMs) {
    if (!doc || !doc.enabled || !validHours(doc.intervalHours)
            || !validTimestamp(nowMs))
        return false;
    // Session-level guard protects against rapid rechecks while FileView saves.
    var last = validTimestamp(lastStartedAtMs) && lastStartedAtMs > 0
               ? lastStartedAtMs : doc.lastAttemptAtMs;
    // Recheck after a backwards host clock step instead of waiting indefinitely.
    return !last || nowMs < last
           || nowMs - last >= doc.intervalHours * HOUR_MS;
}

function nextDueAtMs(doc, lastStartedAtMs) {
    if (!doc || !doc.enabled || !validHours(doc.intervalHours))
        return 0;
    var last = validTimestamp(lastStartedAtMs) && lastStartedAtMs > 0
               ? lastStartedAtMs : doc.lastAttemptAtMs;
    return last ? last + doc.intervalHours * HOUR_MS : 0;
}
