.pragma library

// TimeW stopwatch presentation helpers. Clock samples come from Quickshell's
// monotonic ElapsedTimer, not from Date.now() or the UI refresh interval.
// No side effects, processes, persistence, OS clock writes or polling.
var MAX_LAPS = 100;

function validMs(value) {
    return typeof value === "number" && isFinite(value) && value >= 0;
}

function sample(accumulatedMs, segmentMs) {
    if (!validMs(accumulatedMs) || !validMs(segmentMs))
        return 0;
    return Math.floor(accumulatedMs + segmentMs);
}

function pad2(value) {
    var s = String(value);
    return s.length >= 2 ? s : "0" + s;
}

function format(milliseconds) {
    if (!validMs(milliseconds))
        return "00:00:00.00";
    var centiseconds = Math.floor(milliseconds / 10);
    var cs = centiseconds % 100;
    var seconds = Math.floor(centiseconds / 100) % 60;
    var minutes = Math.floor(centiseconds / 6000) % 60;
    var hours = Math.floor(centiseconds / 360000);
    return pad2(hours) + ":" + pad2(minutes) + ":"
           + pad2(seconds) + "." + pad2(cs);
}

function appendLap(existing, totalMs, previousLapMs, sequence) {
    if (!Array.isArray(existing) || !validMs(totalMs)
            || !validMs(previousLapMs) || totalMs < previousLapMs
            || !Number.isInteger(sequence) || sequence < 1)
        return null;
    var lap = {
        index: sequence,
        totalMs: Math.floor(totalMs),
        splitMs: Math.floor(totalMs - previousLapMs)
    };
    // Newest first; memory remains bounded while sequence numbers increase.
    var next = [lap].concat(existing);
    return next.slice(0, MAX_LAPS);
}
