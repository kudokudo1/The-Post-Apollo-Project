.pragma library

// GDACS recent multi-hazard event list normalization.
// This feed is situational-awareness context, not a replacement for
// competent local/national warning, evacuation, or emergency authorities.
function validNumber(value) {
    if (value === undefined || value === null || value === "")
        return null;
    const number = Number(value);
    return isFinite(number) ? number : null;
}

function eventTypeLabel(code) {
    switch (String(code || "").toUpperCase()) {
    case "EQ": return "EARTHQUAKE";
    case "TC": return "TROPICAL CYCLONE";
    case "FL": return "FLOOD";
    case "VO": return "VOLCANO";
    case "DR": return "DROUGHT";
    case "WF": return "WILDFIRE";
    default: return String(code || "DISASTER").toUpperCase();
    }
}

function normalizeAlertLevel(value) {
    const level = String(value || "").trim().toUpperCase();
    if (level === "RED" || level === "ORANGE" || level === "GREEN")
        return level;
    return "UNKNOWN";
}

function alertToken(level) {
    switch (normalizeAlertLevel(level)) {
    case "RED": return "red";
    case "ORANGE": return "orange";
    case "GREEN": return "cyan";
    default: return "white";
    }
}

function alertRank(level) {
    switch (normalizeAlertLevel(level)) {
    case "RED": return 3;
    case "ORANGE": return 2;
    case "GREEN": return 1;
    default: return 0;
    }
}

function alertRadius(level) {
    switch (normalizeAlertLevel(level)) {
    case "RED": return 9;
    case "ORANGE": return 7;
    case "GREEN": return 5;
    default: return 4;
    }
}

function parseTime(value) {
    if (!value)
        return -1;
    const ms = Date.parse(String(value));
    return isFinite(ms) ? ms : -1;
}

function formatUtc(value) {
    const ms = parseTime(value);
    if (ms <= 0)
        return "-- UTC";
    const date = new Date(ms);
    if (isNaN(date.getTime()))
        return "-- UTC";
    return date.toISOString().slice(0, 16).replace("T", " ") + " UTC";
}

function parseEventList(root, limit) {
    if (!root || root.type !== "FeatureCollection"
        || !Array.isArray(root.features))
        throw new Error("Invalid GDACS feature collection");

    const requested = Number(limit);
    const size = isFinite(requested) && requested > 0
               ? Math.min(100, Math.floor(requested)) : 100;
    const result = [];

    for (let i = 0; i < root.features.length; ++i) {
        const feature = root.features[i];
        if (!feature || !feature.properties || !feature.geometry
            || feature.geometry.type !== "Point"
            || !Array.isArray(feature.geometry.coordinates))
            continue;

        const p = feature.properties;
        const coords = feature.geometry.coordinates;
        const lon = validNumber(coords[0]);
        const lat = validNumber(coords[1]);
        if (lon === null || lat === null
            || Math.abs(lon) > 180 || Math.abs(lat) > 90)
            continue;

        const eventType = String(p.eventtype || "").toUpperCase();
        const eventId = String(p.eventid === undefined ? "" : p.eventid);
        const episodeId = String(p.episodeid === undefined ? "" : p.episodeid);
        const alertLevel = normalizeAlertLevel(p.alertlevel);
        const severity = p.severitydata && typeof p.severitydata === "object"
                       ? p.severitydata : {};
        const severityValue = validNumber(severity.severity);
        const alertScore = validNumber(p.alertscore);
        const reportUrl = p.url && typeof p.url === "object"
                        ? String(p.url.report || "") : "";
        const detailsUrl = p.url && typeof p.url === "object"
                         ? String(p.url.details || "") : "";
        const endMs = parseTime(p.todate);
        const startMs = parseTime(p.fromdate);
        const current = p.iscurrent === true
                     || String(p.iscurrent || "").toLowerCase() === "true";

        result.push({
            id: eventType + ":" + eventId + ":" + episodeId,
            eventId: eventId,
            episodeId: episodeId,
            eventType: eventType,
            eventTypeLabel: eventTypeLabel(eventType),
            name: String(p.name || eventTypeLabel(eventType)),
            alertLevel: alertLevel,
            alertScore: alertScore === null ? -1 : alertScore,
            alertToken: alertToken(alertLevel),
            isCurrent: current,
            country: String(p.country || ""),
            iso3: String(p.iso3 || ""),
            source: String(p.source || "GDACS"),
            latitude: lat,
            longitude: lon,
            coordinates: lat.toFixed(2) + ", " + lon.toFixed(2),
            geometryType: "Point",
            fromUtc: formatUtc(p.fromdate),
            toUtc: formatUtc(p.todate),
            timeMs: Math.max(endMs, startMs),
            severity: severityValue === null ? -1 : severityValue,
            severityText: String(severity.severitytext || "NOT REPORTED"),
            severityUnit: String(severity.severityunit || ""),
            reportUrl: reportUrl,
            detailsUrl: detailsUrl
        });
    }

    result.sort(function (a, b) {
        if (a.isCurrent !== b.isCurrent)
            return a.isCurrent ? -1 : 1;
        const alertDelta = alertRank(b.alertLevel) - alertRank(a.alertLevel);
        if (alertDelta !== 0)
            return alertDelta;
        return b.timeMs - a.timeMs;
    });
    return result.slice(0, size);
}

function summary(rows) {
    const out = { count: 0, current: 0, red: 0, orange: 0, green: 0 };
    if (!Array.isArray(rows))
        return out;
    out.count = rows.length;
    for (let i = 0; i < rows.length; ++i) {
        const row = rows[i] || {};
        if (row.isCurrent)
            out.current++;
        switch (normalizeAlertLevel(row.alertLevel)) {
        case "RED": out.red++; break;
        case "ORANGE": out.orange++; break;
        case "GREEN": out.green++; break;
        }
    }
    return out;
}
