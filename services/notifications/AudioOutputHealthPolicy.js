.pragma library

// Only observes the existing Volume bar's Pipewire.defaultAudioSink.ready.
// Does not identify physical devices, control audio, or infer the reason
// a default audio output becomes not-ready (switch, restart, unplug, etc.).
function initial() {
    return { stable: "", everReady: false, candidate: "",
             sinceMs: 0, lastMs: 0 };
}
function transition(previous, ready, observedMs) {
    const old = previous || initial();
    const state = {
        stable: String(old.stable || ""),
        everReady: old.everReady === true,
        candidate: String(old.candidate || ""),
        sinceMs: Number(old.sinceMs || 0),
        lastMs: Number(old.lastMs || 0)
    };
    if (typeof ready !== "boolean" || !isFinite(observedMs)
            || observedMs <= 0 || observedMs <= state.lastMs)
        return { state: state, event: "" };
    state.lastMs = observedMs;
    const next = ready ? "up" : "down";
    if (!state.stable) {
        state.stable = next;
        state.everReady = ready;
        return { state: state, event: "" }; // startup silent
    }
    if (state.stable === next) {
        state.candidate = "";
        state.sinceMs = 0;
        return { state: state, event: "" };
    }
    if (next === "up" && !state.everReady) {
        state.stable = "up";
        state.everReady = true;
        state.candidate = "";
        state.sinceMs = 0;
        return { state: state, event: "" }; // late first startup
    }
    if (state.candidate !== next) {
        state.candidate = next;
        state.sinceMs = observedMs;
        return { state: state, event: "" };
    }
    if (observedMs - state.sinceMs < 3500)
        return { state: state, event: "" };
    state.stable = next;
    state.everReady = state.everReady || ready;
    state.candidate = "";
    state.sinceMs = 0;
    return { state: state, event: ready ? "restored" : "unavailable" };
}
