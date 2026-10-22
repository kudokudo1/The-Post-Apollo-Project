.pragma library

// Decode the existing Media dock's mpc status output. Empty stdout (including
// process/connection errors reported on stderr) is NOT an offline observation.
// Only recognized MPD state envelopes advance the public observation clock.
function parseStatus(raw) {
    var status = typeof raw === "string" ? raw.trim() : "";
    if (!status)
        return null;

    var active = status.match(/^\[(playing|paused|stopped)\](?:\s|$)/m);
    if (active) {
        var firstLine = status.split(/\r?\n/)[0].trim();
        return {
            state: active[1],
            title: firstLine.charAt(0) === "[" ? "" : firstLine
        };
    }

    // mpc prints volume/repeat metadata but no track row when the queue stops.
    if (/^volume:\s*/m.test(status))
        return {state: "stopped", title: ""};

    return null;
}
