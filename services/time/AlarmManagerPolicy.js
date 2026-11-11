.pragma library

// Clock Alarm V2: at most 100 independent real-local-time alarms.
// Pure scheduling and transition rules; no filesystem, audio or system clock writes.
var VERSION = 2;
var MAX_ALARMS = 100;
var MAX_NAME_LENGTH = 40;
var MAX_NOTE_LENGTH = 256; // Same short, explicit-save note style as Angel
var MAX_LATE_MS = 2 * 60 * 1000;
var MAX_RING_MS = 15 * 60 * 1000;
var SNOOZE_MS = 5 * 60 * 1000;
var SOUND_IDS = ["chime", "soft", "urgent"];

function integer(n, min, max) {
    return typeof n === "number" && Number.isSafeInteger(n) && n >= min && n <= max;
}
function timestamp(n) { return integer(n, 0, 8640000000000000); }
function safeName(v) {
    return typeof v === "string" && v.length <= MAX_NAME_LENGTH
        && !/[\x00-\x1f\x7f]/.test(v);
}
function validNote(value) {
    return typeof value === "string" && value.length <= MAX_NOTE_LENGTH
        && !/[\x00-\x1f\x7f]/.test(value);
}
function validDate(value, allowEmpty) {
    if (allowEmpty && value === "") return true;
    if (typeof value !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(value))
        return false;
    var y = Number(value.slice(0, 4));
    var m = Number(value.slice(5, 7));
    var d = Number(value.slice(8, 10));
    if (y < 1970 || y > 9999 || m < 1 || m > 12 || d < 1 || d > 31)
        return false;
    var check = new Date(y, m - 1, d, 12, 0, 0, 0);
    return check.getFullYear() === y && check.getMonth() === m - 1
        && check.getDate() === d;
}
function dayKey(nowMs) {
    if (!timestamp(nowMs) || nowMs === 0) return "";
    var date = new Date(nowMs);
    function two(n) { return n < 10 ? "0" + n : String(n); }
    return date.getFullYear() + "-" + two(date.getMonth() + 1)
        + "-" + two(date.getDate());
}
function dayAt(key, hour, minute) {
    if (!validDate(key, false)) return NaN;
    var y = Number(key.slice(0, 4)), m = Number(key.slice(5, 7));
    var d = Number(key.slice(8, 10));
    return new Date(y, m - 1, d, hour, minute, 0, 0).getTime();
}
function dateOffset(nowMs, days) {
    var dt = new Date(nowMs);
    // Civil-date arithmetic, not +86400000ms: preserves local DST behavior.
    return dayKey(new Date(dt.getFullYear(), dt.getMonth(), dt.getDate() + days,
                           12, 0, 0, 0).getTime());
}
function weekdaysValid(days) {
    if (!Array.isArray(days) || days.length > 7) return false;
    var seen = {};
    for (var i = 0; i < days.length; i++) {
        if (!integer(days[i], 0, 6) || seen[days[i]]) return false;
        seen[days[i]] = true;
    }
    return true;
}
function validAlarm(a) {
    return !!a && typeof a === "object" && !Array.isArray(a)
        && integer(a.id, 1, Number.MAX_SAFE_INTEGER - 1)
        && safeName(a.name) && a.name.length > 0
        // New optional fields remain compatible with existing V2 files.
        && (a.favorite === undefined || typeof a.favorite === "boolean")
        && (a.note === undefined || validNote(a.note))
        && integer(a.hour, 0, 23) && integer(a.minute, 0, 59)
        && (a.mode === "once" || a.mode === "weekly")
        && weekdaysValid(a.weekdays)
        && (a.mode !== "weekly" || a.weekdays.length > 0)
        && validDate(a.date, a.mode !== "once")
        && typeof a.keepSaved === "boolean"
        && typeof a.enabled === "boolean"
        && validDate(a.pausedUntilDate, true)
        && SOUND_IDS.indexOf(a.soundId) >= 0
        && typeof a.soundEnabled === "boolean"
        && integer(a.volumePercent, 0, 100)
        && validDate(a.lastFiredDay, true)
        && typeof a.ringing === "boolean"
        && timestamp(a.ringStartedAtMs)
        && timestamp(a.snoozeUntilMs)
        && typeof a.completed === "boolean"
        && (!a.ringing || (a.enabled && a.ringStartedAtMs > 0))
        && (!a.completed || (a.mode === "once" && !a.enabled));
}
function validDocument(doc) {
    if (!doc || doc.version !== VERSION || !Array.isArray(doc.alarms)
            || doc.alarms.length > MAX_ALARMS
            || !integer(doc.nextId, 1, Number.MAX_SAFE_INTEGER - 1))
        return false;
    var seen = {};
    for (var i = 0; i < doc.alarms.length; i++) {
        var a = doc.alarms[i];
        if (!validAlarm(a) || seen[a.id] || a.id >= doc.nextId)
            return false;
        seen[a.id] = true;
    }
    return true;
}
function initialDocument() { return {version: VERSION, nextId: 1, alarms: []}; }
function parse(text) {
    var v;
    try { v = JSON.parse(String(text)); }
    catch (e) { return {ok: false, error: "INVALID_JSON"}; }
    if (!validDocument(v)) return {ok: false, error: "INVALID_ALARMS"};
    // Do not touch a readable on-disk V2 file merely to add defaults.
    // The next user-initiated save writes the fields atomically.
    return {ok: true, document: cloneDocument(v)};
}
function cloneDocument(doc) {
    return {version: VERSION, nextId: doc.nextId,
            alarms: doc.alarms.map(function(a) { return Object.assign(
                {favorite: false, note: ""}, a,
                {weekdays: a.weekdays.slice()}); })};
}
function byId(doc, id) {
    if (!validDocument(doc)) return null;
    for (var i = 0; i < doc.alarms.length; i++)
        if (doc.alarms[i].id === id) return doc.alarms[i];
    return null;
}
function freshAlarm(id, nowMs) {
    // Only the current local weekday is selected for a new alarm.
    // The caller supplies nowMs so the default is deterministic in tests.
    var instant = timestamp(nowMs) && nowMs > 0 ? nowMs : Date.now();
    return {id: id, name: "New Alarm " + id, favorite: false, note: "",
            hour: 7, minute: 0,
            mode: "weekly", weekdays: [new Date(instant).getDay()], date: "",
            keepSaved: true, enabled: false, pausedUntilDate: "",
            soundId: "chime", soundEnabled: true, volumePercent: 60,
            lastFiredDay: "", ringing: false, ringStartedAtMs: 0,
            snoozeUntilMs: 0, completed: false};
}
function create(doc, nowMs) {
    if (!validDocument(doc) || doc.alarms.length >= MAX_ALARMS
            || doc.nextId >= Number.MAX_SAFE_INTEGER - 1)
        return {ok: false, error: "MAX_ALARMS_OR_INVALID_STORE"};
    var next = cloneDocument(doc), alarm = freshAlarm(next.nextId, nowMs);
    // Stable monotonically increasing IDs remain unique even after deletion;
    // also skip any identical names a user might have assigned manually.
    var suffix = next.nextId;
    while (next.alarms.some(function(a) {
        return a.name === "New Alarm " + suffix;
    })) suffix++;
    alarm.name = "New Alarm " + suffix;
    next.nextId += 1;
    next.alarms.push(alarm);
    return {ok: true, document: next, id: alarm.id};
}
function duplicate(doc, id) {
    var old = byId(doc, id);
    if (!old || doc.alarms.length >= MAX_ALARMS
            || doc.nextId >= Number.MAX_SAFE_INTEGER - 1)
        return {ok: false, error: "MAX_ALARMS_OR_NOT_FOUND"};
    var next = cloneDocument(doc), copy = Object.assign({}, old, {
        id: next.nextId,
        name: (old.name.slice(0, MAX_NAME_LENGTH - 5) + " COPY"),
        enabled: false, pausedUntilDate: "", completed: false,
        favorite: false,
        lastFiredDay: "", ringing: false, ringStartedAtMs: 0,
        snoozeUntilMs: 0
    });
    next.nextId += 1;
    next.alarms.push(copy);
    return validDocument(next)
        ? {ok: true, document: next, id: copy.id}
        : {ok: false, error: "INVALID_COPY"};
}
function update(doc, id, patch, nowMs) {
    if (!validDocument(doc) || !timestamp(nowMs) || !nowMs
            || !patch || typeof patch !== "object" || Array.isArray(patch))
        return {ok: false, error: "INVALID_EDIT"};
    var old = byId(doc, id);
    if (!old) return {ok: false, error: "ALARM_NOT_FOUND"};
    var allowed = ["name", "hour", "minute", "mode", "weekdays", "date",
                   "keepSaved", "enabled", "pausedUntilDate", "soundId",
                   "soundEnabled", "volumePercent", "favorite", "note"];
    for (var key in patch)
        if (Object.prototype.hasOwnProperty.call(patch, key)
                && allowed.indexOf(key) < 0)
            return {ok: false, error: "INVALID_EDIT_FIELD"};
    var target = Object.assign({favorite: false, note: ""}, old, patch);
    // A schedule edit means a new future occurrence, without surprising
    // immediate playback when the chosen minute already happened today.
    var scheduleChanged = target.hour !== old.hour || target.minute !== old.minute
        || target.mode !== old.mode || target.date !== old.date
        || JSON.stringify(target.weekdays) !== JSON.stringify(old.weekdays);
    if (target.mode === "once" && (!validDate(target.date, false)
            || dayAt(target.date, target.hour, target.minute) <= nowMs)
            && (scheduleChanged || !old.completed && patch.enabled === true))
        return {ok: false, error: "ONE_TIME_DATE_MUST_BE_IN_FUTURE"};
    if (old.completed && patch.enabled === true && !scheduleChanged)
        return {ok: false, error: "COMPLETED_ALARM_EDIT_DATE_FIRST"};
    if (target.mode === "once" && target.completed && target.enabled)
        target.completed = false;
    if (scheduleChanged || (patch.enabled === true && !old.enabled)) {
        target.completed = false;
        target.lastFiredDay = "";
        target.ringing = false;
        target.ringStartedAtMs = 0;
        target.snoozeUntilMs = 0;
        if (target.mode === "weekly") {
            var today = dayKey(nowMs);
            if (target.weekdays.indexOf(new Date(nowMs).getDay()) >= 0
                    && dayAt(today, target.hour, target.minute) <= nowMs)
                target.lastFiredDay = today;
        }
    }
    if (target.pausedUntilDate !== ""
            && target.pausedUntilDate > dayKey(nowMs)) {
        target.ringing = false;
        target.ringStartedAtMs = 0;
        target.snoozeUntilMs = 0;
    }
    if (patch.enabled === false) {
        target.ringing = false;
        target.ringStartedAtMs = 0;
        target.snoozeUntilMs = 0;
    }
    if (!validAlarm(target))
        return {ok: false, error: "INVALID_EDIT_VALUES"};
    var next = cloneDocument(doc);
    next.alarms = next.alarms.map(function(a) { return a.id === id ? target : a; });
    return {ok: true, document: next};
}
function remove(doc, id) {
    if (!validDocument(doc) || !byId(doc, id))
        return {ok: false, error: "ALARM_NOT_FOUND"};
    var next = cloneDocument(doc);
    next.alarms = next.alarms.filter(function(a) { return a.id !== id; });
    return {ok: true, document: next};
}
function finishOnce(a) {
    a.ringing = false; a.ringStartedAtMs = 0; a.snoozeUntilMs = 0;
    a.completed = true; a.enabled = false;
}
function stop(doc, id) {
    var a = byId(doc, id);
    if (!a || !a.ringing) return {ok: false, error: "NOT_RINGING"};
    var next = cloneDocument(doc), row = byId(next, id);
    row.ringing = false; row.ringStartedAtMs = 0; row.snoozeUntilMs = 0;
    if (row.mode === "once") {
        if (row.keepSaved) finishOnce(row);
        else next.alarms = next.alarms.filter(function(e) { return e.id !== id; });
    }
    return {ok: true, document: next};
}
function snooze(doc, id, nowMs) {
    var a = byId(doc, id);
    if (!a || !a.ringing || !timestamp(nowMs) || !nowMs)
        return {ok: false, error: "NOT_RINGING"};
    var next = cloneDocument(doc), row = byId(next, id);
    row.ringing = false;
    row.ringStartedAtMs = 0;
    row.snoozeUntilMs = nowMs + SNOOZE_MS;
    return {ok: true, document: next};
}
function dueKey(a, nowMs) {
    var today = dayKey(nowMs);
    if (a.mode === "once")
        return a.date === today ? today : "";
    return a.weekdays.indexOf(new Date(nowMs).getDay()) >= 0 ? today : "";
}
function tick(doc, nowMs) {
    if (!validDocument(doc) || !timestamp(nowMs) || !nowMs)
        return {changed: false, document: doc, started: [], expired: [], missed: []};
    var next = cloneDocument(doc), started = [], expired = [], missed = [];
    var removedAfterExpiry = [];
    var changed = false, today = dayKey(nowMs);
    next.alarms.forEach(function(a) {
        if (!a.enabled) return;
        if (a.ringing) {
            if (nowMs >= a.ringStartedAtMs
                    && nowMs - a.ringStartedAtMs < MAX_RING_MS) return;
            if (a.mode === "once") {
                finishOnce(a);
                if (!a.keepSaved) removedAfterExpiry.push(a.id);
            } else { a.ringing = false; a.ringStartedAtMs = 0; }
            expired.push(a.id); changed = true; return;
        }
        if (a.snoozeUntilMs > 0) {
            if (nowMs < a.snoozeUntilMs) return;
            var lateSnooze = nowMs - a.snoozeUntilMs;
            a.snoozeUntilMs = 0; changed = true;
            if (lateSnooze > MAX_LATE_MS) {
                if (a.mode === "once") finishOnce(a);
                missed.push(a.id); return;
            }
            a.ringing = true; a.ringStartedAtMs = nowMs;
            started.push(a.id); return;
        }
        if (a.pausedUntilDate !== "" && today < a.pausedUntilDate) return;
        if (a.pausedUntilDate !== "") {
            a.pausedUntilDate = ""; changed = true;
        }
        if (a.mode === "once" && a.date < today) {
            finishOnce(a); missed.push(a.id); changed = true; return;
        }
        var due = dueKey(a, nowMs);
        if (due === "" || a.lastFiredDay === due) return;
        var late = nowMs - dayAt(today, a.hour, a.minute);
        if (late < 0) return;
        if (late > MAX_LATE_MS) {
            if (a.mode === "once") {
                finishOnce(a); missed.push(a.id); changed = true;
            }
            return;
        }
        a.lastFiredDay = due;
        a.ringing = true;
        a.ringStartedAtMs = nowMs;
        started.push(a.id); changed = true;
    });
    if (removedAfterExpiry.length) {
        next.alarms = next.alarms.filter(function(a) {
            return removedAfterExpiry.indexOf(a.id) < 0;
        });
    }
    return {changed: changed, document: changed ? next : doc,
            started: started, expired: expired, missed: missed};
}
function nextOccurrenceMs(a, nowMs) {
    if (!validAlarm(a) || !a.enabled || a.completed
            || !timestamp(nowMs) || !nowMs) return 0;
    if (a.snoozeUntilMs > nowMs) return a.snoozeUntilMs;
    if (a.ringing) return a.ringStartedAtMs;
    if (a.mode === "once") {
        var due = dayAt(a.date, a.hour, a.minute);
        return due > nowMs && (a.pausedUntilDate === ""
            || a.date >= a.pausedUntilDate) ? due : 0;
    }
    var start = nowMs;
    if (a.pausedUntilDate !== "" && a.pausedUntilDate > dayKey(nowMs))
        start = dayAt(a.pausedUntilDate, 0, 0);
    for (var d = 0; d <= 7; d++) {
        var key = dateOffset(start, d), ms = dayAt(key, a.hour, a.minute);
        if (a.weekdays.indexOf(new Date(ms).getDay()) >= 0
                && ms > nowMs && a.lastFiredDay !== key) return ms;
    }
    return 0;
}
function migrateLegacy(raw, nowMs) {
    var old;
    try { old = JSON.parse(String(raw)); }
    catch (e) { return {ok: false, error: "INVALID_LEGACY_JSON"}; }
    if (!old || old.version !== 1 || !old.alarm || !timestamp(nowMs)
            || !integer(old.alarm.hour, 0, 23)
            || !integer(old.alarm.minute, 0, 59)
            || typeof old.alarm.enabled !== "boolean"
            || !safeName(old.alarm.label)
            || !integer(old.alarm.volumePercent, 0, 100)
            || typeof old.alarm.soundEnabled !== "boolean"
            || !validDate(old.alarm.lastFiredDay, true)
            || !timestamp(old.alarm.snoozeUntilMs)
            || !timestamp(old.alarm.ringStartedAtMs)
            || typeof old.alarm.ringing !== "boolean")
        return {ok: false, error: "INVALID_LEGACY"};
    var a = freshAlarm(1, nowMs), v = old.alarm;
    // V1 was daily: migration must never silently narrow recurrence.
    a.weekdays = [0, 1, 2, 3, 4, 5, 6];
    a.name = v.label.trim() || "ALARM";
    a.hour = v.hour; a.minute = v.minute;
    a.enabled = v.enabled;
    a.soundEnabled = v.soundEnabled;
    a.volumePercent = v.volumePercent;
    a.lastFiredDay = v.lastFiredDay;
    a.snoozeUntilMs = v.snoozeUntilMs;
    a.ringing = v.ringing && v.enabled;
    a.ringStartedAtMs = a.ringing ? v.ringStartedAtMs : 0;
    var doc = {version: VERSION, nextId: 2, alarms: [a]};
    return validDocument(doc)
        ? {ok: true, document: doc} : {ok: false, error: "INVALID_LEGACY_STATE"};
}
