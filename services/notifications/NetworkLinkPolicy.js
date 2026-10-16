.pragma library

// Consume the Network dock's EXISTING nmcli DEVICE,TYPE,STATE,CONNECTION
// output. Wi-Fi and Ethernet are separate local link observations: an active
// Ethernet connection must NOT hide an actual Wi-Fi disconnection.
// This policy does not test internet reachability or start extra processes.
function parseDeviceStatus(raw) {
    if (typeof raw !== "string" || !raw.trim())
        return null;

    const summary = {
        wifi: { up: 0, down: 0, uncertain: 0 },
        ethernet: { up: 0, down: 0, uncertain: 0 }
    };
    let seen = 0;
    const lines = raw.split(/\r?\n/);
    for (let i = 0; i < lines.length; ++i) {
        const fields = lines[i].trim().split(":");
        if (fields.length < 3)
            continue;
        const type = String(fields[1] || "").trim().toLowerCase();
        if (type !== "wifi" && type !== "ethernet")
            continue;
        seen += 1;
        const state = String(fields[2] || "").trim().toLowerCase();
        if (state === "connected" || /^connected \([^)]+\)$/.test(state))
            summary[type].up += 1;
        else if (state === "disconnected" || state === "unavailable")
            summary[type].down += 1;
        else
            summary[type].uncertain += 1;
    }
    if (seen === 0)
        return null;

    function status(kind) {
        const s = summary[kind];
        if (s.up > 0)
            return true;
        if (s.uncertain === 0 && s.down > 0)
            return false;
        return null; // no device or connecting/unknown state
    }
    return { wifi: status("wifi"), ethernet: status("ethernet") };
}

function initialLink() {
    return { stable: "", candidate: "", count: 0,
             sinceMs: 0, lastSampleMs: 0 };
}

function initial() {
    return { wifi: initialLink(), ethernet: initialLink() };
}

// Two observations spanning >= 1 second confirm a link transition; startup
// establishes each link's baseline silently. Never announce an unobserved
// device or a temporary "connecting" state as a disconnection.
function advance(previous, connected, observedMs) {
    const old = previous || initialLink();
    const state = {
        stable: String(old.stable || ""),
        candidate: String(old.candidate || ""),
        count: Number(old.count || 0),
        sinceMs: Number(old.sinceMs || 0),
        lastSampleMs: Number(old.lastSampleMs || 0)
    };
    if (typeof connected !== "boolean"
            || typeof observedMs !== "number" || !isFinite(observedMs)
            || observedMs <= 0 || observedMs <= state.lastSampleMs)
        return { state: state, event: "" };

    if (state.lastSampleMs > 0 && observedMs - state.lastSampleMs > 10000) {
        state.candidate = "";
        state.count = 0;
        state.sinceMs = 0;
    }
    state.lastSampleMs = observedMs;
    const seen = connected ? "up" : "down";
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
    if (state.count < 2 || observedMs - state.sinceMs < 1000)
        return { state: state, event: "" };

    const before = state.stable;
    state.stable = seen;
    state.candidate = "";
    state.count = 0;
    state.sinceMs = 0;
    return { state: state,
             event: before === "" ? "" : seen === "up" ? "restored" : "disconnected" };
}

function transition(previous, observation, observedMs) {
    const old = previous || initial();
    const state = { wifi: old.wifi || initialLink(),
                    ethernet: old.ethernet || initialLink() };
    const events = [];
    if (!observation)
        return { state: state, events: events };

    for (const kind of ["wifi", "ethernet"]) {
        const result = advance(state[kind], observation[kind], observedMs);
        state[kind] = result.state;
        if (result.event)
            events.push({ kind: kind, event: result.event });
    }
    return { state: state, events: events };
}
