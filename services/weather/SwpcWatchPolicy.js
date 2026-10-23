.pragma library

// NOAA geomagnetic WATCH products forecast whole UTC calendar days.
// They do not confirm a storm occurred or prove there are no active warnings.
// Parse only explicitly reported watch-day levels, with conservative
// supersession and cancellation handling.
const watchMonths = {
    JAN: 0, FEB: 1, MAR: 2, APR: 3, MAY: 4, JUN: 5,
    JUL: 6, AUG: 7, SEP: 8, OCT: 9, NOV: 10, DEC: 11
};

function watchIssueTime(value) {
    if (typeof value !== "string" ||
            !/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}(?:\.\d{1,3})?$/.test(value))
        return -1;
    const time = Date.parse(value.replace(" ", "T") + "Z");
    return isFinite(time) && time > 0 ? time : -1;
}

function watchUtcDay(ms) {
    const date = new Date(ms);
    return Date.UTC(date.getUTCFullYear(), date.getUTCMonth(),
                    date.getUTCDate());
}

function watchDate(monthName, dayText, issueMs) {
    const month = watchMonths[String(monthName || "").toUpperCase()];
    const day = Number(dayText);
    if (month === undefined || day < 1 || day > 31 || !isFinite(issueMs))
        return -1;
    const issueYear = new Date(issueMs).getUTCFullYear();
    const issueDay = watchUtcDay(issueMs);
    let resolved = -1;
    let nearest = Infinity;
    for (let offset = -1; offset <= 1; ++offset) {
        const year = issueYear + offset;
        const candidate = Date.UTC(year, month, day);
        const valid = new Date(candidate);
        if (valid.getUTCFullYear() !== year ||
                valid.getUTCMonth() !== month || valid.getUTCDate() !== day)
            continue;
        const distance = Math.abs(candidate - issueDay);
        if (distance < nearest) {
            nearest = distance;
            resolved = candidate;
        }
    }
    // NOAA 3-day outlooks cover the issue day or shortly thereafter.
    // A cross-year watch must resolve to a nearby UTC date.
    return resolved >= issueDay - 86400000 &&
           resolved <= issueDay + 4 * 86400000 ? resolved : -1;
}

function watchField(message, name) {
    const lines = String(message || "").split(/\r?\n/);
    for (let i = 0; i < lines.length; ++i) {
        const at = lines[i].indexOf(":");
        if (at >= 0 &&
                lines[i].slice(0, at).trim().toLowerCase() === name.toLowerCase())
            return lines[i].slice(at + 1).trim();
    }
    return "";
}

function watchHeading(message) {
    const text = String(message || "");
    const m = text.match(/^\s*(WATCH|CANCEL(?:LED|ATION)? WATCH)\s*:\s*(.+)$/im);
    if (!m)
        return null;
    return {
        kind: m[1].toUpperCase().startsWith("CANCEL") ? "CANCEL" : "WATCH",
        subject: m[2].trim().slice(0, 160)
    };
}

function predictedDays(message, issueMs) {
    if (typeof message !== "string" ||
            !/Highest Storm Level Predicted by Day:/i.test(message))
        return [];

    const section = message.split(/Highest Storm Level Predicted by Day:\s*/i)[1]
          .split(/THIS SUPERSEDES|Comment:|NOAA Space Weather Scale|Potential Impacts:/i)[0];
    const expression = /\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{1,2})\s*:\s*(G([1-5])\s*\([^)]*\)|None\s*\(Below G1\))/gi;
    const days = [];
    const seen = {};
    let match;
    while ((match = expression.exec(section)) !== null) {
        const dateMs = watchDate(match[1], match[2], issueMs);
        if (dateMs < 0 || seen[dateMs])
            continue;
        seen[dateMs] = true;
        const level = match[4] ? Number(match[4]) : 0;
        days.push({
            dateMs: dateMs,
            dateUtc: new Date(dateMs).toISOString().slice(5, 10) + " UTC",
            level: level,
            levelLabel: level > 0 ? "G" + level : "BELOW G1",
            state: "WATCH FORECAST"
        });
    }
    days.sort(function(a, b) { return a.dateMs - b.dateMs; });
    // Partial forecast lines must not be promoted to a complete outlook.
    return days.length <= 3 ? days : [];
}

function assessWatchDays(payload, nowMs, lookbackHours, limit) {
    if (!Array.isArray(payload))
        throw new Error("Invalid NOAA watch archive");
    if (!isFinite(nowMs) || nowMs <= 0)
        throw new Error("Invalid assessment clock");
    const span = isFinite(lookbackHours) && lookbackHours > 0
                 ? Math.min(168, lookbackHours) : 168;
    const size = isFinite(limit) && limit > 0
                 ? Math.min(4, Math.floor(limit)) : 3;
    const matches = [];

    for (let i = 0; i < payload.length; ++i) {
        const item = payload[i];
        if (!item || typeof item !== "object")
            continue;
        const issueMs = watchIssueTime(item.issue_datetime);
        if (issueMs < nowMs - span * 3600000 || issueMs > nowMs + 300000)
            continue;
        const heading = watchHeading(item.message);
        if (!heading)
            continue;
        const text = String(item.message);
        matches.push({
            issueMs: issueMs,
            id: typeof item.product_id === "string" ? item.product_id.trim() : "",
            serial: watchField(text, "Serial Number"),
            cancelSerial: watchField(text, "Cancel Serial Number"),
            text: text,
            heading: heading,
            global: /THIS SUPERSEDES ANY\s*\/\s*ALL PRIOR WATCHES IN EFFECT/i.test(text)
        });
    }
    matches.sort(function(a, b) { return b.issueMs - a.issueMs; });

    const handled = {};
    let superseded = false;
    let canceledCount = 0;
    let supersededCount = 0;
    let unresolvedCount = 0;
    const selected = [];
    const issueDay = watchUtcDay(nowMs);

    for (let i = 0; i < matches.length; ++i) {
        const row = matches[i];
        if (superseded) {
            supersededCount++;
            continue;
        }
        if (!row.id) {
            unresolvedCount++;
            if (row.global)
                superseded = true;
            continue;
        }
        if (row.heading.kind === "CANCEL") {
            if (!handled[row.id])
                handled[row.id] = true;
            canceledCount++;
            continue;
        }
        if (handled[row.id]) {
            supersededCount++;
            if (row.global)
                superseded = true;
            continue;
        }
        handled[row.id] = true;
        const dates = predictedDays(row.text, row.issueMs);
        if (!dates.length)
            unresolvedCount++;
        else {
            for (let j = 0; j < dates.length; ++j) {
                if (dates[j].dateMs < issueDay ||
                        dates[j].dateMs > issueDay + 3 * 86400000)
                    continue;
                selected.push({
                    dateMs: dates[j].dateMs,
                    dateUtc: dates[j].dateUtc,
                    level: dates[j].level,
                    levelLabel: dates[j].levelLabel,
                    state: dates[j].state,
                    productId: row.id,
                    subject: row.heading.subject,
                    issuedMs: row.issueMs
                });
            }
        }
        if (row.global)
            superseded = true;
    }

    // One card per UTC date. If non-superseded products overlap, show the
    // highest explicitly predicted level (not a measured storm intensity).
    const byDay = {};
    for (let i = 0; i < selected.length; ++i) {
        const day = selected[i];
        const prior = byDay[day.dateMs];
        if (!prior || day.level > prior.level ||
                (day.level === prior.level && day.issuedMs > prior.issuedMs))
            byDay[day.dateMs] = day;
    }
    const days = Object.keys(byDay).map(function(key) { return byDay[key]; });
    days.sort(function(a, b) { return a.dateMs - b.dateMs; });
    return {
        days: days.slice(0, size),
        projectedDays: days.filter(function(d) { return d.level > 0; }).length,
        forecastDayCount: days.length,
        unresolvedCount: unresolvedCount,
        canceledCount: canceledCount,
        supersededCount: supersededCount
    };
}
