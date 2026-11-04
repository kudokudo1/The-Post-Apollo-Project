.pragma library

// ANGEL M1: explicit, local observations of number sequences.
// An observation is what the user noticed, not a claim about why it happened.
// No time-setting, astronomy queries, interpretation feeds or background writes.
var VERSION = 1;
var MAX_ROWS = 4096;
var MAX_DIGITS = 8;
var MAX_FILE_LENGTH = 2097152;
var MAX_SEQUENCE = 1000000000;
var FILTERS = ["all", "repeat", "mirror", "sequence", "add", "subtract", "other", "err"];

function integer(value, low, high) {
    return typeof value === "number" && isFinite(value)
           && Math.floor(value) === value && value >= low && value <= high;
}

function validDigits(value) {
    return typeof value === "string"
           && value.length >= 1 && value.length <= MAX_DIGITS
           && !/[^0-9]/.test(value);
}

function validZone(value) {
    return typeof value === "string" && value.length <= 100
           && !/[\r\n]/.test(value)
           && (value === "UNKNOWN" || value === "UTC"
               || /^[A-Za-z][A-Za-z0-9._+-]*(?:\/[A-Za-z0-9._+-]+)+$/.test(value));
}

function validDisplayTime(value) {
    return typeof value === "string"
           && !/[\r\n]/.test(value)
           && /^([1-9]|1[0-2]):[0-5][0-9] (AM|PM)$/.test(value);
}

function validObservation(row) {
    return !!row && typeof row === "object" && !Array.isArray(row)
           && typeof row.id === "string"
           && /^a[1-9][0-9]*$/.test(row.id)
           && !/[\r\n]/.test(row.id)
           && integer(Number(row.id.slice(1)), 1, MAX_SEQUENCE)
           && validDigits(row.digits)
           && integer(row.observedAtMs, 1, Number.MAX_SAFE_INTEGER)
           && validDisplayTime(row.displayTime)
           && validZone(row.zoneId)
           && integer(row.utcOffsetMinutes, -840, 840)
           && integer(row.displayCalibrationMs, -300000, 300000)
           && (row.captureMode === "clock" || row.captureMode === "manual")
           // v1 journals written before ERR existed have no mark property.
           && (row.errMarked === undefined || typeof row.errMarked === "boolean");
}

function emptyDocument() {
    return {version: VERSION, nextId: 1, observations: []};
}

function validate(document) {
    if (!document || typeof document !== "object" || Array.isArray(document))
        return {ok: false, reason: "INVALID_DOCUMENT"};
    if (document.version !== VERSION)
        return {ok: false, reason: "UNSUPPORTED_VERSION"};
    if (!integer(document.nextId, 1, MAX_SEQUENCE))
        return {ok: false, reason: "INVALID_SEQUENCE"};
    if (!Array.isArray(document.observations)
            || document.observations.length > MAX_ROWS)
        return {ok: false, reason: "INVALID_OBSERVATIONS"};

    var seen = {};
    var highest = 0;
    for (var i = 0; i < document.observations.length; ++i) {
        var row = document.observations[i];
        if (!validObservation(row))
            return {ok: false, reason: "INVALID_OBSERVATION"};
        if (Object.prototype.hasOwnProperty.call(seen, row.id))
            return {ok: false, reason: "DUPLICATE_ID"};
        seen[row.id] = true;
        highest = Math.max(highest, Number(row.id.slice(1)));
    }
    if (highest >= document.nextId)
        return {ok: false, reason: "SEQUENCE_REWIND"};
    return {ok: true, reason: ""};
}

function clone(document) {
    return {
        version: VERSION, nextId: document.nextId,
        observations: document.observations.map(function(row) {
            return {
                id: row.id, digits: row.digits,
                observedAtMs: row.observedAtMs,
                displayTime: row.displayTime,
                zoneId: row.zoneId,
                utcOffsetMinutes: row.utcOffsetMinutes,
                displayCalibrationMs: row.displayCalibrationMs,
                captureMode: row.captureMode,
                errMarked: row.errMarked === true
            };
        })
    };
}

function parse(raw) {
    if (typeof raw !== "string" || raw.length < 2
            || raw.length > MAX_FILE_LENGTH)
        return {ok: false, reason: "INVALID_FILE"};
    var document;
    try { document = JSON.parse(raw); }
    catch (error) { return {ok: false, reason: "INVALID_JSON"}; }
    var check = validate(document);
    return check.ok ? {ok: true, document: clone(document)} : check;
}

function create(document, digits, capture, nowMs) {
    var check = validate(document);
    if (!check.ok) return check;
    if (!validDigits(digits))
        return {ok: false, reason: "INVALID_DIGITS"};
    if (!integer(nowMs, 1, Number.MAX_SAFE_INTEGER))
        return {ok: false, reason: "INVALID_TIME"};
    if (!capture || typeof capture !== "object"
            || !validDisplayTime(capture.displayTime)
            || !validZone(capture.zoneId)
            || !integer(capture.utcOffsetMinutes, -840, 840)
            || !integer(capture.displayCalibrationMs, -300000, 300000)
            || (capture.captureMode !== "clock" && capture.captureMode !== "manual"))
        return {ok: false, reason: "INVALID_CAPTURE"};
    if (document.observations.length >= MAX_ROWS)
        return {ok: false, reason: "CAPACITY"};
    if (document.nextId >= MAX_SEQUENCE)
        return {ok: false, reason: "ID_EXHAUSTED"};

    var next = clone(document);
    next.observations.push({
        id: "a" + next.nextId,
        digits: digits, observedAtMs: nowMs,
        displayTime: capture.displayTime,
        zoneId: capture.zoneId,
        utcOffsetMinutes: capture.utcOffsetMinutes,
        displayCalibrationMs: capture.displayCalibrationMs,
        captureMode: capture.captureMode,
        errMarked: false
    });
    next.nextId += 1;
    return {ok: true, document: next};
}

function remove(document, id, confirmed) {
    var check = validate(document);
    if (!check.ok) return check;
    if (confirmed !== true)
        return {ok: false, reason: "CONFIRM_REQUIRED"};
    var index = document.observations.findIndex(function(row) {
        return row.id === id;
    });
    if (index < 0)
        return {ok: false, reason: "UNKNOWN_ID"};
    var next = clone(document);
    next.observations.splice(index, 1);
    return {ok: true, document: next};
}

// Explicit user review marking is per observation ID, never per number.
// 222 marked ERR leaves every other 222 observation untouched. This stages
// a new document; the singleton publishes only after atomic save succeeds.
function toggleErr(document, id) {
    var check = validate(document);
    if (!check.ok) return check;
    var index = document.observations.findIndex(function(row) {
        return row.id === id;
    });
    if (index < 0)
        return {ok: false, reason: "UNKNOWN_ID"};
    var next = clone(document);
    next.observations[index].errMarked = !next.observations[index].errMarked;
    return {
        ok: true, document: next,
        errMarked: next.observations[index].errMarked
    };
}

function repeat(digits) {
    return validDigits(digits) && digits.length > 1
           && digits.split("").every(function(ch) { return ch === digits[0]; });
}

function mirror(digits) {
    return validDigits(digits) && digits.length > 2 && !repeat(digits)
           && digits === digits.split("").reverse().join("");
}

function sequence(digits) {
    if (!validDigits(digits) || digits.length < 3)
        return false;
    var delta = Number(digits[1]) - Number(digits[0]);
    if (delta !== 1 && delta !== -1) return false;
    for (var i = 2; i < digits.length; i++) {
        if (Number(digits[i]) - Number(digits[i - 1]) !== delta)
            return false;
    }
    return true;
}

function add(digits) {
    return validDigits(digits) && digits.length === 3
           && Number(digits[0]) + Number(digits[1]) === Number(digits[2]);
}

function subtract(digits) {
    return validDigits(digits) && digits.length === 3
           && Number(digits[0]) - Number(digits[1]) === Number(digits[2]);
}

function patternTags(digits) {
    if (!validDigits(digits)) return [];
    var tags = [];
    if (repeat(digits)) tags.push("REPEAT");
    if (mirror(digits)) tags.push("MIRROR");
    if (sequence(digits)) tags.push("SEQUENCE");
    if (add(digits)) tags.push("ADD");
    if (subtract(digits)) tags.push("SUBTRACT");
    if (tags.length === 0) tags.push("OTHER");
    return tags;
}

function matchesFilter(digits, kind) {
    if (!validDigits(digits)) return false;
    switch (kind) {
    case "all": return true;
    case "repeat": return repeat(digits);
    case "mirror": return mirror(digits);
    case "sequence": return sequence(digits);
    case "add": return add(digits);
    case "subtract": return subtract(digits);
    case "other": return patternTags(digits)[0] === "OTHER";
    case "err": return patternTags(digits)[0] === "OTHER";
    default: return false;
    }
}

function filter(observations, query, kind) {
    if (!Array.isArray(observations)
            || typeof query !== "string" || query.length > MAX_DIGITS
            || (query !== "" && !/^[0-9]+$/.test(query))
            || FILTERS.indexOf(kind) < 0)
        return [];
    return observations.filter(function(row) {
        return validObservation(row)
               && row.digits.indexOf(query) !== -1
               && (kind === "err"
                   ? (row.errMarked === true || matchesFilter(row.digits, "other"))
                   : matchesFilter(row.digits, kind));
    }).sort(function(a, b) {
        return b.observedAtMs - a.observedAtMs
               || Number(b.id.slice(1)) - Number(a.id.slice(1));
    });
}

function clockCapture(displayEpochMs) {
    if (!integer(displayEpochMs, 1, Number.MAX_SAFE_INTEGER))
        return null;
    var date = new Date(displayEpochMs);
    if (isNaN(date.getTime()))
        return null;
    // Explicit 12H reference for the observed pattern: 2:22 => 222.
    // The separate UTC timestamp retains the true wall instant.
    var hour24 = date.getHours();
    var hour12 = hour24 % 12 || 12;
    var minute = date.getMinutes();
    var mm = minute < 10 ? "0" + minute : String(minute);
    return {
        digits: String(hour12) + mm,
        displayTime: String(hour12) + ":" + mm + (hour24 < 12 ? " AM" : " PM")
    };
}
