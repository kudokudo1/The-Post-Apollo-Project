.pragma library

// TimeW countdown rules. QML's monotonic ElapsedTimer measures each running
// segment. A QML Timer merely samples the remaining time and detects expiry.
// No files, network, shell, system clock changes, or notifications.
var MAX_HOURS = 99;

function whole(value, max) {
    if (typeof value !== "string" || !/^\d{1,2}$/.test(value))
        return null;
    var number = Number(value);
    return number <= max ? number : null;
}

function parseDuration(hours, minutes, seconds) {
    var h = whole(hours, MAX_HOURS);
    var m = whole(minutes, 59);
    var s = whole(seconds, 59);
    if (h === null || m === null || s === null)
        return {valid: false, milliseconds: 0, error: "INVALID_DURATION"};
    var millis = (h * 3600 + m * 60 + s) * 1000;
    if (millis === 0)
        return {valid: false, milliseconds: 0, error: "ZERO_DURATION"};
    return {valid: true, milliseconds: millis, error: ""};
}

function remaining(segmentBudgetMs, segmentElapsedMs) {
    if (typeof segmentBudgetMs !== "number" || !isFinite(segmentBudgetMs)
            || segmentBudgetMs < 0 || typeof segmentElapsedMs !== "number"
            || !isFinite(segmentElapsedMs) || segmentElapsedMs < 0)
        return 0;
    return Math.max(0, Math.ceil(segmentBudgetMs - segmentElapsedMs));
}

function pad2(number) {
    return String(number).padStart(2, "0");
}

function format(milliseconds) {
    if (typeof milliseconds !== "number" || !isFinite(milliseconds)
            || milliseconds < 0)
        return "--:--:--";
    // Round upward so a positive remainder never appears as zero seconds.
    var seconds = Math.ceil(milliseconds / 1000);
    var h = Math.floor(seconds / 3600);
    var m = Math.floor(seconds / 60) % 60;
    var s = seconds % 60;
    return pad2(h) + ":" + pad2(m) + ":" + pad2(s);
}
