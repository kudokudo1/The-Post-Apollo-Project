.pragma library

// C35 // Presentation-only clock sweep.
// LIVE receives a verified local civil minute from the existing StationSky
// source; REPLAY is a user-controlled fast-forward *of that same civil day*.
// No source timestamps, planetary positions, or USNO events are modified.
var FORMAT = "post-apollo.weather.cosmos-clock-chronograph.c35.v1";
var DAY_MINUTES = 1440;

function validMinute(value) {
    return typeof value === "number" && isFinite(value)
        && Math.floor(value) === value && value >= 0 && value < DAY_MINUTES;
}

function advance(minute, delta) {
    if (!validMinute(minute)
        || typeof delta !== "number" || !isFinite(delta)
        || Math.floor(delta) !== delta || Math.abs(delta) > DAY_MINUTES)
        return null;
    return ((minute + delta) % DAY_MINUTES + DAY_MINUTES) % DAY_MINUTES;
}

function fractionToMinute(fraction) {
    if (typeof fraction !== "number" || !isFinite(fraction)) return null;
    var f = Math.max(0, Math.min(1, fraction));
    return Math.max(0, Math.min(1439, Math.floor(f * DAY_MINUTES)));
}

function futureEvent(events, minute) {
    if (!validMinute(minute) || !events || typeof events === "string")
        return null;
    var count = Number(events.length);
    if (!isFinite(count) || count < 0 || count > 15
        || Math.floor(count) !== count) return null;
    var next = null;
    for (var i=0; i<count; i++) {
        var e = events[i];
        if (!e || !validMinute(e.minute) || e.minute < minute) continue;
        if (!next || e.minute < next.minute) next = e;
    }
    // Do not wrap to tomorrow while continuing to display today's date.
    return next;
}

function atSweep(minute, event, range) {
    if (!validMinute(minute) || !event || !validMinute(event.minute))
        return false;
    return typeof range === "number" && isFinite(range)
        && range >= 0 && range <= 30
        && Math.abs(event.minute - minute) <= range;
}
