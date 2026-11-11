.pragma library

// One daily wall-clock alarm, separate from visual calibration and Chrony.
// Pure scheduling/state transitions. Audio is an independent optional output.
var VERSION = 1;
var MAX_LABEL_LENGTH = 40;
var MAX_LATE_MS = 2 * 60 * 1000; // catch short suspend/reload interruptions
var MAX_RING_MS = 15 * 60 * 1000;
var SNOOZE_MS = 5 * 60 * 1000;
var MAX_TIMESTAMP = 8640000000000000;

function timestamp(value) {
    return typeof value === "number" && isFinite(value)
        && Math.floor(value) === value && value >= 0
        && value <= MAX_TIMESTAMP;
}

function validName(value) {
    return typeof value === "string" && value.length <= MAX_LABEL_LENGTH
        && !/[\x00-\x1f\x7f]/.test(value);
}

function validDay(value) {
    return value === "" || (typeof value === "string"
        && /^\d{4}-\d{2}-\d{2}$/.test(value));
}

function validAlarm(alarm) {
    return !!alarm && typeof alarm === "object" && !Array.isArray(alarm)
        && Number.isInteger(alarm.hour) && alarm.hour >= 0 && alarm.hour <= 23
        && Number.isInteger(alarm.minute) && alarm.minute >= 0 && alarm.minute <= 59
        && validName(alarm.label)
        && Number.isInteger(alarm.volumePercent)
        && alarm.volumePercent >= 0 && alarm.volumePercent <= 100
        && typeof alarm.enabled === "boolean"
        && typeof alarm.soundEnabled === "boolean"
        && validDay(alarm.lastFiredDay)
        && timestamp(alarm.snoozeUntilMs)
        && typeof alarm.ringing === "boolean"
        && timestamp(alarm.ringStartedAtMs)
        && (!alarm.ringing || (alarm.enabled && alarm.ringStartedAtMs > 0));
}

function initialDocument() {
    return { version: VERSION, alarm: {
        hour: 7, minute: 0, label: "ALARM", enabled: false,
        soundEnabled: true, volumePercent: 60,
        lastFiredDay: "", snoozeUntilMs: 0,
        ringing: false, ringStartedAtMs: 0
    }};
}

function copy(alarm) {
    return {
        hour: alarm.hour, minute: alarm.minute,
        label: alarm.label, enabled: alarm.enabled,
        soundEnabled: alarm.soundEnabled,
        volumePercent: alarm.volumePercent,
        lastFiredDay: alarm.lastFiredDay,
        snoozeUntilMs: alarm.snoozeUntilMs,
        ringing: alarm.ringing, ringStartedAtMs: alarm.ringStartedAtMs
    };
}

function parse(raw) {
    var value;
    try { value = JSON.parse(String(raw)); }
    catch (error) { return { ok: false, reason: "INVALID_JSON" }; }
    if (!value || typeof value !== "object" || Array.isArray(value)
            || value.version !== VERSION || !validAlarm(value.alarm))
        return { ok: false, reason: "INVALID_ALARM" };
    return { ok: true, document: { version: VERSION, alarm: copy(value.alarm) }};
}

function dayKey(nowMs) {
    if (!timestamp(nowMs) || nowMs === 0)
        return "";
    var date = new Date(nowMs);
    function two(n) { return (n < 10 ? "0" : "") + n; }
    return String(date.getFullYear()) + "-" + two(date.getMonth() + 1)
           + "-" + two(date.getDate());
}

function todayAt(nowMs, hour, minute) {
    if (!timestamp(nowMs) || nowMs === 0)
        return 0;
    var day = new Date(nowMs);
    // The local Date constructor handles timezone transitions. A nonexistent
    // spring-forward time moves to its first corresponding valid wall time.
    return new Date(day.getFullYear(), day.getMonth(), day.getDate(),
                    hour, minute, 0, 0).getTime();
}

function parseTimePart(value, max) {
    if (typeof value !== "string" || !/^\d{1,2}$/.test(value))
        return null;
    var n = Number(value);
    return n <= max ? n : null;
}

function withSettings(doc, hourText, minuteText, name, nowMs) {
    if (!doc || !validAlarm(doc.alarm) || !timestamp(nowMs) || !nowMs)
        return { ok: false, reason: "STORE_UNAVAILABLE" };
    var h = parseTimePart(hourText, 23);
    var m = parseTimePart(minuteText, 59);
    if (h === null || m === null)
        return { ok: false, reason: "TIME_MUST_BE_24H_HH_MM" };
    if (!validName(name))
        return { ok: false, reason: "INVALID_NAME" };
    var alarm = copy(doc.alarm);
    alarm.hour = h;
    alarm.minute = m;
    alarm.label = name.trim() || "ALARM";
    alarm.enabled = true;
    alarm.snoozeUntilMs = 0;
    alarm.ringing = false;
    alarm.ringStartedAtMs = 0;
    // Arming for a time which has already arrived means tomorrow, not an
    // immediate surprise alarm because today's minute is still in range.
    alarm.lastFiredDay = todayAt(nowMs, h, m) <= nowMs ? dayKey(nowMs) : "";
    return { ok: true, document: { version: VERSION, alarm: alarm } };
}

function withSound(doc, enabled) {
    if (!doc || !validAlarm(doc.alarm) || typeof enabled !== "boolean")
        return { ok: false, reason: "INVALID_SOUND_STATE" };
    var alarm = copy(doc.alarm);
    alarm.soundEnabled = enabled;
    return { ok: true, document: { version: VERSION, alarm: alarm } };
}

function withVolume(doc, value) {
    if (!doc || !validAlarm(doc.alarm) || !Number.isInteger(value)
            || value < 0 || value > 100)
        return { ok: false, reason: "INVALID_VOLUME" };
    var alarm = copy(doc.alarm);
    alarm.volumePercent = value;
    return { ok: true, document: { version: VERSION, alarm: alarm } };
}

function stop(doc) {
    if (!doc || !validAlarm(doc.alarm))
        return { ok: false, reason: "INVALID_ALARM" };
    var alarm = copy(doc.alarm);
    alarm.ringing = false;
    alarm.ringStartedAtMs = 0;
    alarm.snoozeUntilMs = 0;
    return { ok: true, document: { version: VERSION, alarm: alarm } };
}

function disarm(doc) {
    var result = stop(doc);
    if (!result.ok) return result;
    result.document.alarm.enabled = false;
    return result;
}

function snooze(doc, nowMs) {
    if (!doc || !validAlarm(doc.alarm) || !doc.alarm.ringing
            || !timestamp(nowMs) || !nowMs)
        return { ok: false, reason: "NOT_RINGING" };
    var alarm = copy(doc.alarm);
    alarm.ringing = false;
    alarm.ringStartedAtMs = 0;
    alarm.snoozeUntilMs = nowMs + SNOOZE_MS;
    return { ok: true, document: { version: VERSION, alarm: alarm } };
}

function tick(doc, nowMs) {
    if (!doc || !validAlarm(doc.alarm) || !timestamp(nowMs) || !nowMs)
        return { changed: false, event: "invalid", document: doc };
    var a = copy(doc.alarm);
    if (!a.enabled)
        return { changed: false, event: "off", document: doc };

    if (a.ringing) {
        if (nowMs >= a.ringStartedAtMs
                && nowMs - a.ringStartedAtMs < MAX_RING_MS)
            return { changed: false, event: "ringing", document: doc };
        a.ringing = false;
        a.ringStartedAtMs = 0;
        return { changed: true, event: "expired",
                 document: { version: VERSION, alarm: a } };
    }

    if (a.snoozeUntilMs > 0) {
        if (nowMs < a.snoozeUntilMs)
            return { changed: false, event: "snoozing", document: doc };
        var late = nowMs - a.snoozeUntilMs;
        a.snoozeUntilMs = 0;
        if (late > MAX_LATE_MS)
            return { changed: true, event: "snooze-missed",
                     document: { version: VERSION, alarm: a } };
        a.ringing = true;
        a.ringStartedAtMs = nowMs;
        return { changed: true, event: "ring",
                 document: { version: VERSION, alarm: a } };
    }

    var key = dayKey(nowMs);
    var when = todayAt(nowMs, a.hour, a.minute);
    var lateBy = nowMs - when;
    if (a.lastFiredDay === key || lateBy < 0 || lateBy > MAX_LATE_MS)
        return { changed: false, event: "waiting", document: doc };
    a.lastFiredDay = key;
    a.ringing = true;
    a.ringStartedAtMs = nowMs;
    return { changed: true, event: "ring",
             document: { version: VERSION, alarm: a } };
}

function nextLabel(doc, nowMs) {
    if (!doc || !validAlarm(doc.alarm))
        return "UNAVAILABLE";
    var a = doc.alarm;
    if (!a.enabled) return "OFF";
    if (a.ringing) return "RINGING";
    if (a.snoozeUntilMs > 0)
        return "SNOOZED // " + new Date(a.snoozeUntilMs).toLocaleTimeString();
    if (!timestamp(nowMs) || !nowMs) return "UNKNOWN";
    var next = todayAt(nowMs, a.hour, a.minute);
    if (next <= nowMs || a.lastFiredDay === dayKey(nowMs))
        next = new Date(new Date(nowMs).getFullYear(),
            new Date(nowMs).getMonth(), new Date(nowMs).getDate() + 1,
            a.hour, a.minute).getTime();
    return "NEXT // " + new Date(next).toLocaleString();
}
