.pragma library

// Strict one-occurrence payload. The notification source is Clock, while
// RESOURCE is the immutable saved-alarm ID. Names are display only, never
// the key for DND, Block, ZZ, Favorites or navigation.
var SOURCE_ID = "clock-alarm";
var EVENT_TYPE = "alarm-rang";

function boundedName(value) {
    if (typeof value !== "string" || !value.trim()
            || value.length > 40 || /[\x00-\x1f\x7f]/.test(value))
        return "";
    return value.trim();
}
function validMillis(ms) {
    return typeof ms === "number" && Number.isSafeInteger(ms) && ms > 0
        && ms <= 8640000000000000;
}
function resourceId(id) {
    return Number.isSafeInteger(id) && id > 0 && id <= 2147483647
        ? "alarm-" + id : "";
}
function eventId(id, startedMs) {
    const resource = resourceId(id);
    return resource && validMillis(startedMs)
        ? "apollo-clock-" + resource + "-" + startedMs : "";
}
function clockText(hour, minute) {
    const pad = n => (n < 10 ? "0" : "") + n;
    return pad(hour) + ":" + pad(minute);
}
function scheduleText(a) {
    if (a.mode === "once")
        return "ONE TIME // " + a.date;
    if (a.weekdays.length === 7)
        return "REPEATS // EVERY DAY";
    const days = ["SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT"];
    return "REPEATS // " + a.weekdays.slice().sort((x, y) => x - y)
        .map(d => days[d]).join(" ");
}
function payload(alarm, startedMs) {
    const a = alarm || {};
    const label = boundedName(a.name);
    const resource = resourceId(a.id);
    const id = eventId(a.id, startedMs);
    if (!id || !label || a.ringing !== true
            || a.ringStartedAtMs !== startedMs
            || !Number.isInteger(a.hour) || a.hour < 0 || a.hour > 23
            || !Number.isInteger(a.minute) || a.minute < 0 || a.minute > 59
            || (a.mode !== "once" && a.mode !== "weekly")
            || !Array.isArray(a.weekdays) || a.weekdays.length > 7
            || a.weekdays.some(d => !Number.isInteger(d) || d < 0 || d > 6)
            || (a.mode === "weekly" && a.weekdays.length < 1)
            || (a.mode === "once" && !/^\d{4}-\d{2}-\d{2}$/.test(a.date)))
        return null;

    const at = clockText(a.hour, a.minute);
    return {
        id: id,
        source: "CLOCK",
        sourceId: SOURCE_ID,
        category: "internal",
        severity: "warning",
        title: "CLOCK // ALARM // " + label,
        message: at + " // " + scheduleText(a)
            + " // Open Clock to STOP or SNOOZE.",
        tags: ["clock", "alarm", "scheduled"],
        createdAt: startedMs,
        context: {
            origin: "apollo",
            domain: "system",
            eventType: EVENT_TYPE,
            resourceId: resource,
            resourceLabel: label,
            alarmId: a.id,
            ringStartedAtMs: startedMs,
            timeLocal: at,
            scheduleMode: a.mode,
            weekdays: a.weekdays.slice(),
            localDate: a.mode === "once" ? a.date : "",
            soundId: String(a.soundId || ""),
            soundEnabled: a.soundEnabled === true,
            favoriteAtRing: a.favorite === true
        }
    };
}

// Validate an existing history record before offering direct navigation.
// Never infer an alarm number from its title, name, body, note or URL.
function destinationId(entry) {
    const e = entry || {}, ctx = e.context || {};
    const id = ctx.alarmId;
    const started = ctx.ringStartedAtMs;
    if (e.sourceId !== SOURCE_ID || ctx.eventType !== EVENT_TYPE
            || ctx.origin !== "apollo" || ctx.domain !== "system"
            || ctx.resourceId !== resourceId(id)
            || e.id !== eventId(id, started))
        return 0;
    return id;
}
