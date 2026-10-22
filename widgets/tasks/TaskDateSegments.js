.pragma library

// TASKS date segments: pure local Gregorian edits, one YYYY-MM-DD draft.
// No clock, timer, persistence, network, or second store is created.
function leap(year) {
    return year % 4 === 0 && (year % 100 !== 0 || year % 400 === 0);
}

function daysInMonth(year, month) {
    if (!Number.isInteger(year) || year < 1 || year > 9999
            || !Number.isInteger(month) || month < 1 || month > 12)
        return 0;
    return [31, leap(year) ? 29 : 28, 31, 30, 31, 30,
            31, 31, 30, 31, 30, 31][month - 1];
}

function parse(date) {
    if (typeof date !== "string" || !/^[0-9]{4}-[0-9]{2}-[0-9]{2}$/.test(date))
        return null;
    const year = Number(date.slice(0, 4));
    const month = Number(date.slice(5, 7));
    const day = Number(date.slice(8, 10));
    return year >= 1 && year <= 9999 && day >= 1
           && day <= daysInMonth(year, month)
        ? {year: year, month: month, day: day} : null;
}

function pad(value, digits) {
    return String(value).padStart(digits, "0");
}

function format(parts) {
    return pad(parts.year, 4) + "-" + pad(parts.month, 2) + "-" + pad(parts.day, 2);
}

function startingParts(date, referenceDate) {
    const parsed = parse(date);
    if (parsed) return parsed;
    const now = referenceDate instanceof Date && !isNaN(referenceDate.getTime())
        ? referenceDate : new Date();
    return {year: now.getFullYear(), month: now.getMonth() + 1,
            day: now.getDate()};
}

function part(date, kind) {
    const parts = parse(date);
    if (!parts) return "";
    return kind === "year" ? pad(parts.year, 4)
         : kind === "month" ? pad(parts.month, 2)
         : kind === "day" ? pad(parts.day, 2) : "";
}

function setPart(date, kind, raw, referenceDate) {
    const old = startingParts(date, referenceDate);
    const text = String(raw === null || raw === undefined ? "" : raw).trim();
    if (!/^[0-9]{1,4}$/.test(text))
        return {accepted: false, date: date || ""};
    const value = Number(text);
    if (kind === "year" && (value < 1 || value > 9999)
            || kind === "month" && (value < 1 || value > 12)
            || kind === "day" && (value < 1 || value > 31)
            || ["year", "month", "day"].indexOf(kind) === -1)
        return {accepted: false, date: date || ""};

    old[kind] = value;
    old.day = Math.min(old.day, daysInMonth(old.year, old.month));
    return {accepted: true, date: format(old)};
}

function step(date, kind, direction, referenceDate) {
    const current = startingParts(date, referenceDate);
    if (!Number.isInteger(direction) || Math.abs(direction) !== 1
            || ["year", "month", "day"].indexOf(kind) === -1)
        return date || "";
    if (kind === "year") {
        const year = current.year + direction;
        if (year < 1 || year > 9999) return format(current);
        current.year = year;
        current.day = Math.min(current.day, daysInMonth(year, current.month));
        return format(current);
    }
    if (kind === "month") {
        let year = current.year;
        let month = current.month + direction;
        if (month > 12) { year++; month = 1; }
        if (month < 1) { year--; month = 12; }
        if (year < 1 || year > 9999) return format(current);
        current.year = year;
        current.month = month;
        current.day = Math.min(current.day, daysInMonth(year, month));
        return format(current);
    }
    // UTC calendar arithmetic, not local timestamps: crossing DST cannot
    // cause the day to repeat or skip. setUTCFullYear handles years 1–99.
    const d = new Date(0);
    d.setUTCHours(12, 0, 0, 0);
    d.setUTCFullYear(current.year, current.month - 1, current.day + direction);
    const year = d.getUTCFullYear();
    return year < 1 || year > 9999 ? format(current)
        : format({year: year, month: d.getUTCMonth() + 1,
                  day: d.getUTCDate()});
}
