.pragma library

// COSMOS C5 repair // The USNO local civil day is independent of wttr.in's
// optional daily astronomy forecast. Prefer the existing Open-Meteo timezone
// offset, never the PC timezone or an invented geographic default.
function localCivilDate(nowMs, offsetMinutes) {
    if (offsetMinutes === null || offsetMinutes === undefined
            || offsetMinutes === "") return "";
    var offset = Number(offsetMinutes), now = Number(nowMs);
    if (!isFinite(offset) || offset < -720 || offset > 840
            || !isFinite(now) || now <= 0) return "";
    var date = new Date(now + Math.round(offset) * 60000);
    return isFinite(date.getTime()) ? date.toISOString().slice(0,10) : "";
}

function exactDay(value) {
    if (typeof value !== "string"
            || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return "";
    var parsed = new Date(value + "T00:00:00Z");
    return isFinite(parsed.getTime())
        && parsed.toISOString().slice(0,10) === value ? value : "";
}

function focusedDate(forecastDate, nowMs, offsetMinutes, sourceOnly) {
    if (!sourceOnly) return forecastDate;
    return localCivilDate(nowMs,offsetMinutes)
        || exactDay(forecastDate) || "";
}
