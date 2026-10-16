.pragma library

// Consume the Network dock's EXISTING "nmcli -t -f DEVICE,TYPE,STATE,CONNECTION
// device" result. This observes local Wi-Fi/Ethernet link state, NOT reachability
// of the internet. No extra polling, network requests, or execution.
function parseDeviceStatus(raw) {
    if (typeof raw !== "string" || !raw.trim())
        return null;

    const lines = raw.split(/\r?\n/);
    let up = 0;
    let down = 0;
    let uncertain = 0;
    let interfaces = 0;
    for (let i = 0; i < lines.length; i++) {
        const fields = lines[i].trim().split(":");
        if (fields.length < 4)
            continue;
        const type = String(fields[1] || "").trim().toLowerCase();
        if (type !== "wifi" && type !== "ethernet")
            continue;
        const state = String(fields[2] || "").trim().toLowerCase();
        interfaces += 1;
        if (state === "connected" || /^connected \([^)]+\)$/.test(state))
            up += 1;
        else if (state === "disconnected" || state === "unavailable")
            down += 1;
        else
            uncertain += 1;
    }

    // Failed/partial NMCLI output and machines without Wi-Fi/Ethernet devices
    // cannot be interpreted as an outage.
    if (!interfaces)
        return null;
    if (up > 0)
        return { connected: true };
    if (uncertain > 0 || down === 0)
        return null; // "connecting", "unmanaged", unknown: no confirmed loss
    return { connected: false };
}

function initial() {
    return {
        stable: "",
        candidate: "",
        count: 0,
        sinceMs: 0,
        lastSampleMs: 0
    };
}

// Three independent, consecutive observations spanning at least 2 seconds
// establish either baseline or a real transition. No startup alerts.
// Stale gaps clear candidates, not the previously confirmed link state.
function transition(previous, observation, observedMs) {
    const original = previous || initial();
    const state = {
        stable: String(original.stable || ""),
        candidate: String(original.candidate || ""),
        count: Number(original.count || 0),
        sinceMs: Number(original.sinceMs || 0),
        lastSampleMs: Number(original.lastSampleMs || 0)
    };
    if (!observation || typeof observation.connected !== "boolean"
            || typeof observedMs !== "number" || !isFinite(observedMs)
            || observedMs <= 0 || observedMs <= state.lastSampleMs)
        return { state: state, event: "" };

    if (state.lastSampleMs > 0 && observedMs - state.lastSampleMs > 10000) {
        state.candidate = "";
        state.count = 0;
        state.sinceMs = 0;
    }
    state.lastSampleMs = observedMs;

    const seen = observation.connected ? "up" : "down";
    if (seen === state.stable) {
        state.candidate = "";
        state.count = 0;
        state.sinceMs = 0;
        return { state: state, event: "" };
    }

    if (state.candidate !== seen) {
        state.candidate = seen;
        state.count = 1;
        state.sinceMs = observedMs;
    } else {
        state.count += 1;
    }

    if (state.count < 3 || observedMs - state.sinceMs < 2000)
        return { state: state, event: "" };

    const previouslyStable = state.stable;
    state.stable = seen;
    state.candidate = "";
    state.count = 0;
    state.sinceMs = 0;
    // Establish initial baseline silently after startup, not an outage.
    const event = previouslyStable === "" ? ""
        : seen === "up" ? "restored" : "disconnected";
    return { state: state, event: event };
}
