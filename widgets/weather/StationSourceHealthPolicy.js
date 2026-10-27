.pragma library

function finiteNumber(value, fallback) {
    if (value === undefined || value === null || String(value).trim() === "")
        return fallback;
    const number = Number(value);
    return isFinite(number) ? number : fallback;
}

function ageMinutes(nowMs, lastSuccessMs) {
    const now = finiteNumber(nowMs, -1);
    const stamp = finiteNumber(lastSuccessMs, -1);
    if (now <= 0 || stamp <= 0 || stamp > now + 300000)
        return -1;
    return Math.max(0, Math.floor((now - stamp) / 60000));
}

function compactAge(minutes) {
    const value = finiteNumber(minutes, -1);
    if (value < 0)
        return "--";
    if (value < 1)
        return "<1m";
    return Math.floor(value) + "m";
}

function accentFor(state) {
    switch (String(state || "")) {
    case "LIVE": return "magenta";
    case "UPDATING": return "cyan";
    case "READING":
    case "RETRYING":
    case "WAITING": return "orange";
    case "STALE":
    case "DEGRADED": return "yellow";
    case "OFFLINE": return "red";
    default: return "white";
    }
}

function sourceRow(config, nowMs) {
    const source = config || {};
    const ready = !!source.ready;
    const loading = !!source.loading;
    const error = String(source.error || "").trim();
    const successAge = ageMinutes(nowMs, source.lastSuccessMs);
    const sampleAge = finiteNumber(source.sampleAgeMinutes, -1);
    const staleAfter = finiteNumber(source.staleAfterMinutes, -1);
    const freshnessAge = sampleAge >= 0 ? sampleAge : successAge;
    const stale = ready && staleAfter >= 0
                  && freshnessAge >= staleAfter;

    let state = "WAITING";
    if (loading && error)
        state = "RETRYING";
    else if (loading)
        state = ready ? "UPDATING" : "READING";
    else if (error)
        state = ready ? "DEGRADED" : "OFFLINE";
    else if (stale)
        state = "STALE";
    else if (ready)
        state = "LIVE";

    let detail = String(source.provider || "");
    if (error)
        detail = "LAST FAILURE // " + error.toUpperCase();
    else if (stale && freshnessAge >= 0)
        detail = "SOURCE SAMPLE " + compactAge(freshnessAge) + " OLD";
    else if (!ready && !loading)
        detail = "NO SUCCESSFUL SAMPLE YET";

    const footer = [];
    footer.push("LAST SUCCESS " + compactAge(successAge));
    if (sampleAge >= 0)
        footer.push("SAMPLE " + compactAge(sampleAge));

    return {
        id: String(source.id || ""),
        title: String(source.title || ""),
        provider: String(source.provider || ""),
        state: state,
        accent: accentFor(state),
        detail: detail,
        footer: footer.join(" // "),
        lastSuccessAgeMinutes: successAge,
        sampleAgeMinutes: sampleAge,
        staleAfterMinutes: staleAfter
    };
}

function buildCoreSources(input) {
    const state = input || {};
    const now = finiteNumber(state.nowMs, Date.now());
    const order = [
        state.weather,
        state.aqi,
        state.kp,
        state.solarWind,
        state.magneticField,
        state.solarFlux
    ];
    const rows = [];
    for (let i = 0; i < order.length; i++)
        rows.push(sourceRow(order[i], now));
    return rows;
}
