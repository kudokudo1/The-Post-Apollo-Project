.pragma library

// NOAA-issued windows are NOT proof that a product remains in effect.
// SWPC extensions use Issue Time -> Now Valid Until (per SWPC Timeline);
// initial warnings use Valid From -> Valid To. Missing clocks stay unknown.
const months = {
    JAN: 0, FEB: 1, MAR: 2, APR: 3, MAY: 4, JUN: 5,
    JUL: 6, AUG: 7, SEP: 8, OCT: 9, NOV: 10, DEC: 11
};

function noaaTime(text) {
    if (typeof text !== "string")
        return -1;
    const m = text.trim().match(/^(\d{4})\s+([A-Za-z]{3})\s+(\d{1,2})\s+(\d{2})(\d{2})\s+UTC$/i);
    if (!m)
        return -1;
    const month = months[m[2].toUpperCase()];
    const year = Number(m[1]), day = Number(m[3]);
    const hour = Number(m[4]), minute = Number(m[5]);
    if (month === undefined || year < 2000 || day < 1 || day > 31
            || hour > 23 || minute > 59)
        return -1;
    const ms = Date.UTC(year, month, day, hour, minute);
    const date = new Date(ms);
    return date.getUTCFullYear() === year
           && date.getUTCMonth() === month && date.getUTCDate() === day
           ? ms : -1;
}

function issueTime(value) {
    if (typeof value !== "string" ||
            !/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}(?:\.\d{1,3})?$/.test(value))
        return -1;
    const ms = Date.parse(value.replace(" ", "T") + "Z");
    return isFinite(ms) && ms > 0 ? ms : -1;
}

function utcLabel(value) {
    if (!isFinite(value) || value <= 0)
        return "-- UTC";
    return new Date(value).toISOString().slice(5, 16).replace("T", " ") + " UTC";
}

function field(message, name) {
    if (typeof message !== "string")
        return "";
    const lines = message.split(/\r?\n/);
    for (let i = 0; i < lines.length; i++) {
        const index = lines[i].indexOf(":");
        if (index < 0)
            continue;
        if (lines[i].slice(0, index).trim().toLowerCase() === name.toLowerCase())
            return lines[i].slice(index + 1).trim();
    }
    return "";
}

function classification(message) {
    if (typeof message !== "string")
        return null;
    const m = message.match(/^\s*(CANCEL(?:LED|ATION)? (?:WATCH|WARNING|ALERT)|EXTENDED WARNING|WARNING|WATCH|ALERT|SUMMARY)\s*:\s*(.+)$/im);
    if (!m)
        return null;
    const original = m[1].toUpperCase();
    const kind = original.startsWith("CANCEL") ? "CANCELLATION"
                 : original === "EXTENDED WARNING" ? "WARNING" : original;
    return {kind: kind, original: original, subject: m[2].trim()};
}

function windowFrom(message, issueMs, original) {
    if (original === "EXTENDED WARNING") {
        const until = noaaTime(field(message, "Now Valid Until"));
        return until > 0 && until > issueMs
               ? {start: issueMs, end: until} : null;
    }
    const from = noaaTime(field(message, "Valid From"));
    const to = noaaTime(field(message, "Valid To"));
    return from > 0 && to > from && issueMs > 0
           ? {start: from, end: to} : null;
}

function assess(payload, nowMs, lookbackHours, limit) {
    if (!Array.isArray(payload))
        throw new Error("Invalid SWPC bulletin archive");
    if (!isFinite(nowMs) || nowMs <= 0)
        throw new Error("Invalid assessment time");
    const span = isFinite(lookbackHours) && lookbackHours > 0
                 ? Math.min(168, lookbackHours) : 168;
    const max = isFinite(limit) && limit > 0
                ? Math.min(6, Math.floor(limit)) : 3;
    const source = [];
    for (let i = 0; i < payload.length; i++) {
        const item = payload[i];
        if (!item || typeof item !== "object")
            continue;
        const issue = issueTime(item.issue_datetime);
        if (issue < nowMs - span * 3600000 || issue > nowMs + 300000)
            continue;
        const type = classification(item.message);
        if (!type)
            continue;
        source.push({
            id: typeof item.product_id === "string" ? item.product_id.trim() : "",
            issued: issue,
            type: type,
            text: item.message
        });
    }
    source.sort(function(a, b) { return b.issued - a.issued; });

    // Only later bulletins for the SAME product identity can suppress an
    // earlier warning. Watch-wide supersession is explicitly announced.
    const seen = {};
    let anyWatchSuperseded = false;
    let uncertain = 0;
    let expired = 0;
    let cancelledOrReplaced = 0;
    const windows = [];

    for (let i = 0; i < source.length; i++) {
        const row = source[i];
        const key = row.id || field(row.text, "Space Weather Message Code");
        const type = row.type;
        const watch = type.kind === "WATCH" ||
                      (type.kind === "CANCELLATION" &&
                       type.original.indexOf("WATCH") >= 0);
        if (watch) {
            if (!anyWatchSuperseded && type.kind === "WATCH")
                uncertain++;
            else
                cancelledOrReplaced++;
            if (/THIS SUPERSEDES ANY\s*\/\s*ALL PRIOR WATCHES IN EFFECT/i.test(row.text))
                anyWatchSuperseded = true;
            continue;
        }
        if (type.kind === "CANCELLATION") {
            if (key)
                seen[key] = true;
            cancelledOrReplaced++;
            continue;
        }
        if (type.kind !== "WARNING")
            continue;
        if (!key) {
            uncertain++;
            continue;
        }
        if (seen[key]) {
            cancelledOrReplaced++;
            continue;
        }
        seen[key] = true;
        const window = windowFrom(row.text, row.issued, type.original);
        if (!window) {
            uncertain++;
            continue;
        }
        if (nowMs < window.start || nowMs > window.end) {
            expired++;
            continue;
        }
        windows.push({
            productId: key,
            subject: type.subject.slice(0, 180),
            issueUtc: utcLabel(row.issued),
            untilUtc: utcLabel(window.end),
            endMs: window.end,
            state: "WINDOW OPEN"
        });
    }
    // User-visible count is explicitly the number of matched time windows,
    // not the count of officially active weather warnings.
    return {
        windowCount: windows.length,
        uncertainCount: uncertain,
        endedCount: expired,
        supersededCount: cancelledOrReplaced,
        windows: windows.slice(0, max)
    };
}
