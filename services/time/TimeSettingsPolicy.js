.pragma library

// Display-only calibration. Never changes Linux time, UTC, timezone, or DST.
// Persist milliseconds so fractional-second visual corrections are possible.
var VERSION = 1;
var MAX_OFFSET_MS = 300000;

function initialDocument() {
    return { version: VERSION, displayOffsetMs: 0 };
}

function validOffset(value) {
    return typeof value === "number" && isFinite(value)
           && Math.floor(value) === value
           && Math.abs(value) <= MAX_OFFSET_MS;
}

function parse(raw) {
    var object;
    try { object = JSON.parse(String(raw)); }
    catch (error) { return { ok: false, reason: "INVALID_JSON" }; }
    if (!object || typeof object !== "object" || Array.isArray(object))
        return { ok: false, reason: "INVALID_DOCUMENT" };
    if (object.version !== VERSION)
        return { ok: false, reason: "UNSUPPORTED_VERSION" };
    if (!validOffset(object.displayOffsetMs))
        return { ok: false, reason: "INVALID_OFFSET" };
    return { ok: true, document: {
        version: VERSION, displayOffsetMs: object.displayOffsetMs
    }};
}

function withOffset(document, offsetMs) {
    if (!validOffset(offsetMs))
        return { ok: false, reason: "OUT_OF_RANGE" };
    return { ok: true, document: {
        version: VERSION, displayOffsetMs: offsetMs
    }};
}

function adjustedEpochMs(epochMs, offsetMs) {
    if (typeof epochMs !== "number" || !isFinite(epochMs)
            || !validOffset(offsetMs))
        return null;
    return epochMs + offsetMs;
}

function formatOffset(offsetMs) {
    if (!validOffset(offsetMs)) return "INVALID";
    if (offsetMs === 0) return "0.000s";
    var sign = offsetMs < 0 ? "-" : "+";
    return sign + (Math.abs(offsetMs) / 1000).toFixed(3) + "s";
}
