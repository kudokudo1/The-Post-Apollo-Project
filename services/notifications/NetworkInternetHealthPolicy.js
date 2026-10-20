.pragma library

// External direct-HTTPS probes are evidence for those specific destinations,
// NOT a declaration that the whole Internet, router or ISP has failed.
// Samples come only from the fixed, read-only scripts/network probe.
function parseResult(raw) {
    let row;
    try { row = JSON.parse(String(raw || "")); }
    catch (error) { return null; }
    if (!row || row.schema !== 1 || !Array.isArray(row.results)
            || row.results.length !== 2 || row.probeCount !== 2)
        return null;
    const names = ["example.com", "www.cloudflare.com"];
    const allowed = ["ok", "dns", "https", "http", "unknown"];
    let successes = 0, dnsFailures = 0, uncertain = false;
    for (let i = 0; i < names.length; ++i) {
        const result = row.results[i] || {};
        if (result.target !== names[i] || allowed.indexOf(result.stage) < 0)
            return null;
        if (result.stage === "ok") successes++;
        if (result.stage === "dns") dnsFailures++;
        if (result.stage === "unknown") uncertain = true;
    }
    const status = uncertain ? "unknown"
          : successes > 0 ? "reachable"
          : dnsFailures === 2 ? "dns-failed" : "https-failed";
    if (row.status !== status || row.successes !== successes
            || row.dnsFailures !== dnsFailures)
        return null;
    return { status: status, successes: successes,
             dnsFailures: dnsFailures, probeCount: 2 };
}

function initial() {
    return { stable: "", candidate: "", count: 0,
             sinceMs: 0, lastSampleMs: 0 };
}
function resetCandidate(state) {
    state.candidate = "";
    state.count = 0;
    state.sinceMs = 0;
}

// Two matching observations at least one minute apart. One successful
// endpoint counts as externally reachable; neither endpoint failure alone
// proves a whole-Internet outage. Unknown observations never cause alerts.
function transition(previous, observation, timeMs) {
    const old = previous || initial();
    const state = {
        stable: String(old.stable || ""),
        candidate: String(old.candidate || ""),
        count: Number(old.count || 0),
        sinceMs: Number(old.sinceMs || 0),
        lastSampleMs: Number(old.lastSampleMs || 0)
    };
    if (!observation || ["reachable", "dns-failed", "https-failed"]
            .indexOf(observation.status) < 0
            || typeof timeMs !== "number" || !isFinite(timeMs)
            || timeMs <= 0 || timeMs <= state.lastSampleMs)
        return { state: state, event: "" };

    if (state.lastSampleMs && timeMs - state.lastSampleMs > 420000)
        resetCandidate(state);
    state.lastSampleMs = timeMs;

    if (state.stable === "" && observation.status === "reachable") {
        state.stable = "reachable"; // normal startup: silent
        resetCandidate(state);
        return { state: state, event: "" };
    }
    const wanted = observation.status === "reachable"
                 ? "reachable" : "impaired";
    if (wanted === state.stable) {
        resetCandidate(state);
        return { state: state, event: "" };
    }
    // For a new impairment, the two samples must agree on the failure
    // class (DNS vs HTTPS), rather than a shifting/uncertain diagnosis.
    const candidate = wanted === "impaired"
                    ? observation.status : "reachable";
    if (candidate !== state.candidate) {
        state.candidate = candidate;
        state.count = 1;
        state.sinceMs = timeMs;
    } else {
        state.count++;
    }
    if (state.count < 2 || timeMs - state.sinceMs < 60000)
        return { state: state, event: "" };

    state.stable = wanted;
    resetCandidate(state);
    return {
        state: state,
        event: wanted === "reachable" ? "restored" : candidate
    };
}
