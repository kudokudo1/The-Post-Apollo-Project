.pragma library

// TimeW MACHINE: an intentionally session-local timeline of manually named
// moments. A marker contains only a label, UTC timestamp and monotonic TimeW
// instance age. It does NOT capture the screen, Sway layout or machine state.
var MAX_MARKERS = 24;
var MAX_NAME_LENGTH = 48;

function validNumber(value) {
    return typeof value === "number" && isFinite(value) && value >= 0;
}

function pad2(value) {
    var result = String(value);
    return result.length >= 2 ? result : "0" + result;
}

function ageLabel(elapsedMs) {
    if (!validNumber(elapsedMs))
        return "--D --:--:--";
    var seconds = Math.floor(elapsedMs / 1000);
    var days = Math.floor(seconds / 86400);
    var hours = Math.floor(seconds / 3600) % 24;
    var minutes = Math.floor(seconds / 60) % 60;
    var secs = seconds % 60;
    return pad2(days) + "D " + pad2(hours) + ":"
           + pad2(minutes) + ":" + pad2(secs);
}

function utcStamp(nowMs) {
    if (!validNumber(nowMs) || nowMs > 8640000000000000)
        return "";
    var date = new Date(nowMs);
    if (isNaN(date.getTime()))
        return "";
    return date.toISOString().slice(0, 19).replace("T", " ") + " UTC";
}

function createMarker(id, name, nowMs, elapsedMs) {
    if (!Number.isInteger(id) || id < 1 || typeof name !== "string"
            || name.length > MAX_NAME_LENGTH || !validNumber(elapsedMs))
        return null;
    var stamp = utcStamp(nowMs);
    if (!stamp)
        return null;
    var label = name.trim();
    if (!label)
        label = "MARKER " + pad2(id);
    return {
        id: id,
        label: label,
        utc: stamp,
        elapsedMs: Math.floor(elapsedMs)
    };
}

function appendMarker(existing, marker) {
    if (!Array.isArray(existing) || existing.length >= MAX_MARKERS
            || !marker || !Number.isInteger(marker.id) || marker.id < 1
            || existing.some(function(entry) { return entry.id === marker.id; }))
        return null;
    return [marker].concat(existing);
}

function removeMarker(existing, id) {
    if (!Array.isArray(existing) || !Number.isInteger(id))
        return existing;
    return existing.filter(function(entry) { return entry.id !== id; });
}
