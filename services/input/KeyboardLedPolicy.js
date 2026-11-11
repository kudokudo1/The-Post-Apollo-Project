.pragma library

// Observation is a Linux LED brightness proxy, NOT Wayland/XKB lock state.
// Saved samples never become "live" simply because Quickshell restarted.
var VERSION = 1;
var VALUES = ["unknown", "on", "off"];

function validValue(value) {
    return typeof value === "string" && VALUES.indexOf(value) >= 0;
}
function validTime(value) {
    return typeof value === "number" && isFinite(value)
        && Math.floor(value) === value && value >= 0
        && value <= 9007199254740991;
}
function emptyLock() {
    return {value: "unknown", observedAtMs: 0};
}
function initialDocument() {
    return {version: VERSION, enabled: false,
            num: emptyLock(), caps: emptyLock()};
}
function validLock(lock) {
    return lock && typeof lock === "object"
           && !Array.isArray(lock) && validValue(lock.value)
           && validTime(lock.observedAtMs)
           && (lock.value !== "unknown" || lock.observedAtMs === 0)
           && (lock.value === "unknown" || lock.observedAtMs > 0);
}
function validDocument(doc) {
    return !!doc && typeof doc === "object" && !Array.isArray(doc)
           && doc.version === VERSION && typeof doc.enabled === "boolean"
           && validLock(doc.num) && validLock(doc.caps);
}
function clone(doc) {
    return {version: VERSION, enabled: doc.enabled,
            num: {value: doc.num.value, observedAtMs: doc.num.observedAtMs},
            caps: {value: doc.caps.value, observedAtMs: doc.caps.observedAtMs}};
}
function parse(raw) {
    var doc;
    try { doc = JSON.parse(String(raw)); }
    catch (_) { return {ok: false, reason: "INVALID_JSON"}; }
    if (!validDocument(doc))
        return {ok: false, reason: "INVALID_OBSERVATION_DOCUMENT"};
    return {ok: true, document: clone(doc)};
}
function withEnabled(doc, enabled) {
    if (!validDocument(doc) || typeof enabled !== "boolean")
        return {ok: false, reason: "INVALID_MONITOR_STATE"};
    var next = clone(doc);
    next.enabled = enabled;
    return {ok: true, document: next};
}
function withObserved(doc, lock, value, atMs) {
    if (!validDocument(doc) || !doc.enabled
            || (lock !== "num" && lock !== "caps")
            || (value !== "on" && value !== "off")
            || !validTime(atMs) || atMs < 1)
        return {ok: false, reason: "UNTRUSTED_SAMPLE"};
    var next = clone(doc);
    var prior = next[lock];
    if (atMs < prior.observedAtMs)
        return {ok: false, reason: "STALE_SAMPLE"};
    // No disk write on each polling interval. Persist changes only.
    if (prior.value === value)
        return {ok: true, changed: false, document: next};
    next[lock] = {value: value, observedAtMs: atMs};
    return {ok: true, changed: true, document: next};
}
