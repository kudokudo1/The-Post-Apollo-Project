.pragma library

// ApolloHub Linux uptime: read-only /proc/uptime projection.
// This is OS boot age, not time since Quickshell or the Hub opened.
// No subprocess, clock setting, mutation, or idle-time inference.
var MAX_SAMPLE_AGE_MS = 150000;

function parseSeconds(raw) {
    // Linux /proc/uptime is "<uptime seconds> <cumulative idle seconds>".
    // Only the first field is relevant; never expose the second.
    if (typeof raw !== "string")
        return -1;
    var match = raw.trim().match(/^([0-9]+(?:\.[0-9]+)?)\s+[0-9]+(?:\.[0-9]+)?$/);
    if (!match)
        return -1;
    var seconds = Number(match[1]);
    return isFinite(seconds) && seconds >= 0 && seconds <= 10000000000
           ? seconds : -1;
}

function snapshot(raw, observedAtMs, nowMs, loadError) {
    var now = Number(nowMs);
    var observed = Number(observedAtMs);
    var age = now - observed;
    var seconds = parseSeconds(raw);
    var error = loadError === true;
    var timeValid = isFinite(now) && isFinite(observed)
                    && observed > 0 && isFinite(age) && age >= 0;
    var state = error ? "error"
              : !timeValid ? "unobserved"
              : seconds < 0 ? "unavailable"
              : age > MAX_SAMPLE_AGE_MS ? "stale" : "ready";
    var ready = state === "ready";
    var totalSeconds = ready ? Math.floor(seconds + age / 1000) : -1;
    var totalMinutes = ready ? Math.floor(totalSeconds / 60) : -1;
    var days = ready ? Math.floor(totalMinutes / (24 * 60)) : -1;
    var hours = ready ? Math.floor(totalMinutes / 60) % 24 : -1;
    var minutes = ready ? totalMinutes % 60 : -1;

    return {
        state: state,
        ready: ready,
        source: "linux-procfs",
        approximate: ready,
        observedAtMs: timeValid ? observed : 0,
        ageSeconds: timeValid ? Math.floor(age / 1000) : -1,
        uptimeSeconds: totalSeconds,
        days: days,
        hours: hours,
        minutes: minutes,
        label: ready ? days + "D " + String(hours).padStart(2, "0")
                       + "H " + String(minutes).padStart(2, "0") + "M" : "--"
    };
}
