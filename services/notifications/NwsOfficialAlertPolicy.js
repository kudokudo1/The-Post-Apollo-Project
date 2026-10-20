.pragma library

// Official NWS products ONLY. Never infer warnings from current conditions.
// Alert point is explicitly supplied by the operator; never trust IP-derived
// wttr.in coordinates for emergency-alert geographic targeting.
function configuredPoint(raw) {
    const text = String(raw || "").trim();
    if (!/^-?\d{1,2}(?:\.\d{1,4})?\s*,\s*-?\d{1,3}(?:\.\d{1,4})?$/.test(text))
        return "";
    const values = text.split(",").map(function(v) { return Number(v.trim()); });
    if (!isFinite(values[0]) || !isFinite(values[1])
            || Math.abs(values[0]) > 90 || Math.abs(values[1]) > 180)
        return "";
    return String(values[0]) + "," + String(values[1]);
}

function when(raw) {
    const n = Date.parse(String(raw || ""));
    return isFinite(n) ? n : NaN;
}

function notificationSeverity(raw) {
    const s = String(raw || "").toLowerCase();
    return s === "extreme" || s === "severe" ? "critical"
        : s === "moderate" ? "warning" : "normal";
}

function clean(value, maximum) {
    return String(value || "").replace(/\s+/g, " ").trim().slice(0, maximum);
}

function parseActive(raw, nowMs) {
    let data;
    try {
        data = JSON.parse(raw);
    } catch (e) { return null; }
    if (!data || data.type !== "FeatureCollection"
            || !Array.isArray(data.features)
            || !isFinite(nowMs) || nowMs <= 0)
        return null;

    const list = [];
    const seen = {};
    for (let i = 0; i < data.features.length && i < 500; i++) {
        const feature = data.features[i] || {};
        const p = feature.properties || {};
        const id = clean(feature.id || p.id, 512);
        const event = clean(p.event, 128);
        const status = String(p.status || "");
        const endMs = when(p.expires);
        if (!id || !event || status !== "Actual" || !isFinite(endMs)
                || endMs <= nowMs || seen[id])
            continue;
        seen[id] = true;
        const sent = clean(p.sent, 45);
        const updated = clean(p.updated, 45);
        const headline = clean(p.headline, 300);
        const area = clean(p.areaDesc, 240);
        const issuer = clean(p.senderName || p.sender, 120);
        const severity = clean(p.severity, 24);
        const revision = [updated || sent, headline, severity, String(endMs)].join("|");
        list.push({
            id: id, event: event, headline: headline, area: area,
            issuer: issuer, severity: severity,
            displaySeverity: notificationSeverity(severity),
            description: clean(p.description, 640),
            instruction: clean(p.instruction, 320),
            sent: sent, updated: updated,
            expires: new Date(endMs).toISOString(),
            revision: revision
        });
    }
    return list;
}

// A successful active-feed response is evidence of what is currently listed,
// NOT proof that any missing alert was officially canceled. On a failed fetch,
// no lifecycle state is changed and no "all clear" is emitted.
function advance(oldState, alerts) {
    if (!Array.isArray(alerts))
        return { state: oldState || {}, changes: [] };
    const previous = oldState || {};
    const next = {};
    const changes = [];
    for (let i = 0; i < alerts.length; i++) {
        const alert = alerts[i];
        const prior = previous[alert.id];
        next[alert.id] = { revision: alert.revision, absent: 0, alert: alert };
        if (!prior || prior.revision !== alert.revision)
            changes.push({ kind: prior ? "updated" : "observed", alert: alert });
    }
    for (const id of Object.keys(previous)) {
        if (Object.prototype.hasOwnProperty.call(next, id))
            continue;
        const prior = previous[id];
        const absent = Number(prior.absent || 0) + 1;
        if (absent < 2)
            next[id] = { revision: prior.revision, absent: absent, alert: prior.alert };
        else if (absent === 2)
            changes.push({ kind: "not-listed", alert: prior.alert });
    }
    return { state: next, changes: changes };
}
