.pragma library

// Independent semantic facets for one notification, not competing buckets.
// Origin/domain/severity filtering is independent of legacy tone selection.
// No history rewrite, duplicate event, or content-derived inference is needed.
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
// Keep established external Social senders in Social even without a desktop
// category hint. Do not infer sender/domain from private message contents.
function isCommunicationSender(source, sourceId) {
    const name = token(source);
    const id = token(sourceId);
    if (name === "proton mail" || name === "proton-mail")
        return true;
    const tokens = (name + " " + id).split(/[^a-z0-9]+/);
    const known = [
        "discord", "vesktop", "equibop", "session", "signal",
        "telegram", "telegramdesktop", "element", "matrix",
        "slack", "teams", "whatsapp", "thunderbird", "gmail",
        "outlook", "protonmail", "skype", "zoom", "mattermost",
        "mastodon", "bluesky", "youtube", "twitch", "reddit"
    ];
    for (let i = 0; i < known.length; ++i) {
        if (tokens.indexOf(known[i]) !== -1)
            return true;
    }
    return false;
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
    else if (isCommunicationSender(source, sourceId)
                || inFamily(categoryFamily, ["email", "im", "call", "presence"])
                || inFamily(category, ["social", "friend", "friends",
                                       "message", "communication", "audio",
                                       "voice", "media", "fullscreen"]))
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
