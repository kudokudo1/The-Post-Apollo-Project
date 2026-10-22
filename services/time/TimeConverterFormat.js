.pragma library

// CALC presentation only. Python zoneinfo continues to accept canonical
// HH:MM and returns immutable 24-hour timestamps with DST fold information.
// Input and output format choices remain independent, with no process calls.

function pad2(value) {
    return String(value).padStart(2, "0");
}

function invalid(reason) {
    return {valid: false, canonical: "", error: reason || "INVALID_TIME"};
}

function parseInput(value, is24Hour) {
    if (typeof value !== "string"
            || (is24Hour !== true && is24Hour !== false))
        return invalid("INVALID_TIME");
    const trimmed = value.trim();
    let match;
    let hour;
    let minute;
    if (is24Hour) {
        match = /^(\d{1,2}):(\d{2})$/.exec(trimmed);
        if (!match) return invalid("INVALID_24H_TIME");
        hour = Number(match[1]);
        minute = Number(match[2]);
        if (hour > 23 || minute > 59)
            return invalid("INVALID_24H_TIME");
    } else {
        // Accept both conventional 01:19 PM and TimeW's 01:19//PM.
        match = /^(\d{1,2}):(\d{2})\s*(?:\/\/)?\s*(AM|PM)$/i.exec(trimmed);
        if (!match) return invalid("INVALID_12H_TIME");
        hour = Number(match[1]);
        minute = Number(match[2]);
        if (hour < 1 || hour > 12 || minute > 59)
            return invalid("INVALID_12H_TIME");
        hour = (hour % 12) + (match[3].toUpperCase() === "PM" ? 12 : 0);
    }
    return {valid: true, canonical: pad2(hour) + ":" + pad2(minute), error: ""};
}

function displayInput(canonical, use24Hour) {
    const time = parseInput(canonical, true);
    if (!time.valid || (use24Hour !== true && use24Hour !== false))
        return invalid("INVALID_TIME");
    if (use24Hour)
        return {valid: true, text: time.canonical, error: ""};
    const hour = Number(time.canonical.slice(0, 2));
    const suffix = hour < 12 ? "AM" : "PM";
    return {
        valid: true,
        text: pad2(hour % 12 || 12) + time.canonical.slice(2) + "//" + suffix,
        error: ""
    };
}

function convertInput(value, sourceIs24Hour, targetIs24Hour) {
    const parsed = parseInput(value, sourceIs24Hour);
    if (!parsed.valid) return {valid: false, text: value, error: parsed.error};
    return displayInput(parsed.canonical, targetIs24Hour);
}

// The backend outputs YYYY-MM-DD HH:MM:SS ZONE (+0000). Format only its
// clock substring; preserve date, abbreviation and signed UTC offset.
// Keep //AM|PM in BOTH modes per TimeW's approved clock grammar.
function formatResult(value, use24Hour) {
    if (typeof value !== "string" || (use24Hour !== true && use24Hour !== false))
        return typeof value === "string" ? value : "";
    const match = /^(\d{4}-\d{2}-\d{2}) (\d{2}):(\d{2}):(\d{2})(\s.+)$/.exec(value);
    if (!match) return value;
    const hour = Number(match[2]);
    if (hour > 23 || Number(match[3]) > 59 || Number(match[4]) > 59)
        return value;
    const displayHour = use24Hour ? hour : (hour % 12 || 12);
    return match[1] + " " + pad2(displayHour) + ":" + match[3] + ":"
           + match[4] + "//" + (hour < 12 ? "AM" : "PM") + match[5];
}
