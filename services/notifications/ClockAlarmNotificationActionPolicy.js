.pragma library

// Exact live occurrence witness for local Clock action controls.
// A historical notification is never sufficient to actuate the alarm.
// All fields must agree with the immutable event identity and the current
// scheduler state. No title, label, note or serialized callback is trusted.
function validMillis(ms) {
    return typeof ms === "number" && Number.isSafeInteger(ms)
        && ms > 0 && ms <= 8640000000000000;
}
function liveOccurrence(entry, alarm, nowMs) {
    const n = entry || {}, ctx = n.context || {}, a = alarm || {};
    const alarmId = ctx.alarmId;
    const ringMs = ctx.ringStartedAtMs;
    if (n.sourceId !== "clock-alarm"
            || ctx.eventType !== "alarm-rang"
            || ctx.origin !== "apollo" || ctx.domain !== "system"
            || !Number.isSafeInteger(alarmId) || alarmId < 1
            || alarmId > 2147483647
            || !validMillis(ringMs)
            || n.id !== "apollo-clock-alarm-" + alarmId + "-" + ringMs
            || ctx.resourceId !== "alarm-" + alarmId
            || a.id !== alarmId
            || a.enabled !== true || a.ringing !== true
            || a.ringStartedAtMs !== ringMs
            || !validMillis(nowMs)
            || ringMs > nowMs || nowMs - ringMs >= 15 * 60 * 1000)
        return null;
    return {alarmId: alarmId, startedMs: ringMs};
}
function validAction(action) { return action === "stop" || action === "snooze"; }
