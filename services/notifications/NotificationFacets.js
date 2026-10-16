.pragma library

// Independent semantic facets for one notification, not competing buckets.
// This policy is staged separately from the Hub while its shared UI source
// is owned by the active scrollbar migration. No history rewrite is needed.
function token(value) {
    return String(value === null || value === undefined ? "" : value)
        .trim().toLowerCase();
}
function warning(category, severity) {
    const c = token(category);
    const s = token(severity);
    return s === "warning" || s === "critical" || s === "emergency"
        || c === "warning" || c === "critical" || c === "emergency";
}
function inFamily(value, family) {
    return family.indexOf(value) !== -1;
}
function facetsFor(event) {
    const e = event || {};
    const ctx = e.context || {};
    const source = token(e.source);
    const sourceId = token(e.sourceId);
    const category = token(e.category);
    const categoryFamily = category.split(".")[0];
    const explicitOrigin = token(ctx.origin);
    const explicitDomain = token(ctx.domain);
    const severity = token(e.severity);

    const internal = explicitOrigin === "apollo"
        || source.indexOf("apollo") !== -1
        || sourceId.indexOf("apollo") !== -1
        || category === "internal" || category === "apollo"
        || inFamily(source, ["cpu++", "appcontrol", "hospital", "git",
                              "weather station", "weather report", "solar report"]);
    const origin = internal ? "apollo" : "external";

    let domain = "";
    if (inFamily(explicitDomain, ["system", "weather", "social", "media"]))
        domain = explicitDomain;
    else if (origin === "apollo" && (
                source === "cpu++" || source === "appcontrol"
                || sourceId.indexOf("cpu-plus") === 0))
        domain = "system";
    else if (origin === "apollo" && (
                source.indexOf("weather") !== -1
                || source.indexOf("solar") !== -1
                || sourceId.indexOf("weather-") === 0))
        domain = "weather";
    else if (inFamily(categoryFamily, ["device", "network"])
                || inFamily(category, ["system", "technical",
                                       "hardware", "resource", "telemetry"]))
        domain = "system";
    else if (inFamily(categoryFamily, ["email", "im", "call", "presence"])
                || inFamily(category, ["social", "friend", "friends",
                                       "message", "communication"]))
        domain = "social";
    else
        domain = "apps";

    return {
        origin: origin,
        domain: domain,
        severity: warning(category, severity) ? "warning" : "normal"
    };
}
function matches(filter, facets, favorite) {
    const view = token(filter);
    const f = facets || {};
    if (view === "all")
        return true;
    if (view === "favorites")
        return favorite === true;
    if (view === "warning")
        return f.severity === "warning";
    if (view === "apollo")
        return f.origin === "apollo";
    if (view === "system" || view === "social")
        return f.domain === view;
    if (view === "apps")
        return f.origin !== "apollo" && f.domain === "apps";
    return false;
}
