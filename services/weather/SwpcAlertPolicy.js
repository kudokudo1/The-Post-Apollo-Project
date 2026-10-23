.pragma library

// SWPC /products/alerts.json is a bulletin ARCHIVE. This module displays
// recent issued items, never infers which watches/warnings remain active.
function issuedTime(value) {
    if (typeof value !== "string" ||
            !/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}(?:\.\d{1,3})?$/.test(value))
        return -1;
    const ms = Date.parse(value.replace(" ", "T") + "Z");
    return isFinite(ms) && ms > 0 ? ms : -1;
}

function utcLabel(ms) {
    const value = Number(ms);
    if (!isFinite(value) || value <= 0)
        return "-- UTC";
    const date = new Date(value);
    if (!isFinite(date.getTime()))
        return "-- UTC";
    return date.toISOString().slice(5, 16).replace("T", " ") + " UTC";
}

function classify(message) {
    if (typeof message !== "string")
        return null;
    const match = message.match(/^\s*(CANCEL(?:LED|ATION)? (?:WATCH|WARNING|ALERT)|EXTENDED WARNING|WARNING|WATCH|ALERT|SUMMARY)\s*:\s*(.+)$/im);
    if (!match)
        return null;
    const originalType = match[1].toUpperCase();
    let kind = originalType;
    if (originalType.indexOf("CANCEL") === 0)
        kind = "CANCELLATION";
    else if (originalType === "EXTENDED WARNING")
        kind = "WARNING";

    const subject = match[2].trim().replace(/\s+/g, " ");
    if (!subject)
        return null;

    const scale = message.match(/^\s*NOAA Scale:\s*([GRS][1-5])\b/im);
    const code = message.match(/^\s*Space Weather Message Code:\s*([A-Z0-9-]+)\s*$/im);
    return {
        kind: kind,
        originalType: originalType,
        subject: subject.slice(0, 220),
        scale: scale ? scale[1].toUpperCase() : "",
        code: code ? code[1] : ""
    };
}

function parseBulletins(payload, nowMs, hours, limit) {
    if (!Array.isArray(payload))
        throw new Error("Invalid NOAA SWPC bulletins");
    const now = Number(nowMs);
    if (!isFinite(now) || now <= 0)
        throw new Error("Invalid clock");
    const span = typeof hours === "number" && isFinite(hours) &&
                 hours > 0 ? Math.min(168, hours) : 48;
    const max = typeof limit === "number" && isFinite(limit) &&
                limit > 0 ? Math.min(6, Math.floor(limit)) : 3;
    const seen = {};
    const all = [];

    for (let i = 0; i < payload.length; i++) {
        const raw = payload[i];
        if (!raw || typeof raw !== "object")
            continue;
        const issueMs = issuedTime(raw.issue_datetime);
        if (issueMs < now - span * 3600000 || issueMs > now + 300000)
            continue;
        const parsed = classify(raw.message);
        if (!parsed)
            continue;
        const id = typeof raw.product_id === "string"
                   ? raw.product_id.trim().slice(0, 24) : "";
        const key = id + "/" + issueMs + "/" + parsed.code;
        if (seen[key])
            continue;
        seen[key] = true;
        all.push({
            productId: id,
            issueMs: issueMs,
            issueUtc: utcLabel(issueMs),
            kind: parsed.kind,
            originalType: parsed.originalType,
            subject: parsed.subject,
            scale: parsed.scale,
            code: parsed.code
        });
    }
    all.sort(function(a, b) { return b.issueMs - a.issueMs; });
    return {
        count: all.length,
        bulletins: all.slice(0, max)
    };
}
