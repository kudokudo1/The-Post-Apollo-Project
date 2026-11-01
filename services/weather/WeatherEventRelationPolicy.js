.pragma library

// Cross-source MAP relationship ranking.
//
// This policy never declares two records to be the same event. It only ranks
// bounded spatial/temporal context between independently sourced observations.
// Missing time data can produce SPACE ONLY context, never a stronger claim.

function finite(value) {
    if (value === undefined || value === null || value === "")
        return null;
    const number = Number(value);
    return isFinite(number) ? number : null;
}

function validPoint(latitude, longitude) {
    const lat = finite(latitude), lon = finite(longitude);
    return lat !== null && lon !== null
        && Math.abs(lat) <= 90 && Math.abs(lon) <= 180;
}

function timeMs(value) {
    if (value === undefined || value === null || value === "")
        return -1;
    if (typeof value === "number")
        return isFinite(value) && value > 0 ? value : -1;
    let text = String(value).trim();
    if (!text)
        return -1;
    // FIRMS uses "YYYY-MM-DD HH:MMZ"; make the UTC separator explicit.
    if (/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}Z$/.test(text))
        text = text.slice(0, 10) + "T" + text.slice(11);
    const parsed = Date.parse(text);
    return isFinite(parsed) && parsed > 0 ? parsed : -1;
}

function distanceKm(latA, lonA, latB, lonB) {
    if (!validPoint(latA, lonA) || !validPoint(latB, lonB))
        return -1;
    const rad = Math.PI / 180;
    const a = Number(latA) * rad;
    const b = Number(latB) * rad;
    const da = (Number(latB) - Number(latA)) * rad;
    const dl = (Number(lonB) - Number(lonA)) * rad;
    const h = Math.sin(da / 2) * Math.sin(da / 2)
            + Math.cos(a) * Math.cos(b)
            * Math.sin(dl / 2) * Math.sin(dl / 2);
    return 6371 * 2 * Math.atan2(
        Math.sqrt(h),
        Math.sqrt(Math.max(0, 1 - h))
    );
}

function canonicalHazard(value) {
    const raw = String(value || "").trim().toLowerCase();
    if (!raw)
        return "unknown";
    if (raw === "wf" || raw.indexOf("wildfire") >= 0
            || raw.indexOf("fire") >= 0)
        return "fire";
    if (raw === "eq" || raw.indexOf("earthquake") >= 0
            || raw.indexOf("seismic") >= 0)
        return "earthquake";
    if (raw === "tc" || raw.indexOf("severestorm") >= 0
            || raw.indexOf("severe storm") >= 0
            || raw.indexOf("cyclone") >= 0
            || raw.indexOf("hurricane") >= 0
            || raw.indexOf("typhoon") >= 0)
        return "storm";
    if (raw === "fl" || raw.indexOf("flood") >= 0)
        return "flood";
    if (raw === "vo" || raw.indexOf("volcano") >= 0)
        return "volcano";
    if (raw === "dr" || raw.indexOf("drought") >= 0)
        return "drought";
    return "unknown";
}

function limits(hazard) {
    switch (canonicalHazard(hazard)) {
    case "fire": return { distanceKm: 120, hours: 48 };
    case "earthquake": return { distanceKm: 180, hours: 36 };
    case "storm": return { distanceKm: 600, hours: 72 };
    case "flood": return { distanceKm: 300, hours: 96 };
    case "volcano": return { distanceKm: 150, hours: 120 };
    case "drought": return { distanceKm: 800, hours: 720 };
    default: return { distanceKm: 120, hours: 48 };
    }
}

function anchor(source, id, title, hazard, latitude, longitude, observedMs) {
    if (!validPoint(latitude, longitude))
        return null;
    return {
        source: String(source || ""),
        id: String(id || ""),
        title: String(title || ""),
        hazard: canonicalHazard(hazard),
        latitude: Number(latitude),
        longitude: Number(longitude),
        observedMs: timeMs(observedMs)
    };
}

function anchorFromEonet(row) {
    if (!row) return null;
    return anchor(
        "NASA EONET", row.id, row.title,
        row.categoryId || row.category,
        row.latitude, row.longitude, row.rawTime || row.time
    );
}

function anchorFromGdacs(row) {
    if (!row) return null;
    return anchor(
        "GDACS", row.id, row.name,
        row.eventType || row.eventTypeLabel,
        row.latitude, row.longitude, row.timeMs
    );
}

function anchorFromEarthquake(row) {
    if (!row) return null;
    return anchor(
        "USGS", row.id, row.place,
        "earthquake", row.latitude, row.longitude, row.time
    );
}

function anchorFromHotspot(row) {
    if (!row) return null;
    return anchor(
        "NASA FIRMS", row.id, row.title || "VIIRS HOTSPOT",
        "fire", row.latitude, row.longitude, row.acquiredUtc
    );
}

function candidate(source, id, title, hazard, latitude, longitude, observedMs, extra) {
    if (!validPoint(latitude, longitude))
        return null;
    const out = {
        source: String(source || ""),
        id: String(id || ""),
        title: String(title || ""),
        hazard: canonicalHazard(hazard),
        latitude: Number(latitude),
        longitude: Number(longitude),
        observedMs: timeMs(observedMs),
        mentionOnly: false,
        detail: ""
    };
    if (extra) {
        out.mentionOnly = extra.mentionOnly === true;
        out.detail = String(extra.detail || "");
    }
    return out;
}

function compatible(anchorHazard, candidateHazard, mentionOnly) {
    if (mentionOnly)
        return true;
    const a = canonicalHazard(anchorHazard);
    const b = canonicalHazard(candidateHazard);
    return a !== "unknown" && a === b;
}

function pushCandidate(out, row, source, hazard, observedMs, title, extra) {
    if (!row)
        return;
    const next = candidate(
        source, row.id || row.featureId || "",
        title, hazard,
        row.latitude, row.longitude, observedMs, extra
    );
    if (next)
        out.push(next);
}

function sourceCandidates(inputs) {
    const input = inputs || {};
    const out = [];
    const eonet = Array.isArray(input.eonet) ? input.eonet : [];
    const gdacs = Array.isArray(input.gdacs) ? input.gdacs : [];
    const earthquakes = Array.isArray(input.earthquakes) ? input.earthquakes : [];
    const hotspots = Array.isArray(input.hotspots) ? input.hotspots : [];
    const mentions = Array.isArray(input.newsMentions) ? input.newsMentions : [];

    for (let i = 0; i < eonet.length; i++)
        pushCandidate(
            out, eonet[i], "NASA EONET",
            eonet[i].categoryId || eonet[i].category,
            eonet[i].rawTime || eonet[i].time,
            eonet[i].title, null
        );
    for (let i = 0; i < gdacs.length; i++)
        pushCandidate(
            out, gdacs[i], "GDACS",
            gdacs[i].eventType || gdacs[i].eventTypeLabel,
            gdacs[i].timeMs, gdacs[i].name, null
        );
    for (let i = 0; i < earthquakes.length; i++)
        pushCandidate(
            out, earthquakes[i], "USGS", "earthquake",
            earthquakes[i].time, earthquakes[i].place, null
        );
    for (let i = 0; i < hotspots.length; i++)
        pushCandidate(
            out, hotspots[i], "NASA FIRMS", "fire",
            hotspots[i].acquiredUtc, hotspots[i].title || "VIIRS HOTSPOT",
            { detail: hotspots[i].confidenceLabel || "" }
        );
    for (let i = 0; i < mentions.length; i++)
        pushCandidate(
            out, mentions[i], "GDELT GKG", "unknown", -1,
            mentions[i].name || "NEWS MENTION",
            {
                mentionOnly: true,
                detail: "MENTIONED PLACE // NOT VERIFIED EVENT LOCATION"
            }
        );
    return out;
}

function relationsForAnchor(selectedAnchor, inputs, maxRows) {
    if (!selectedAnchor || !validPoint(
            selectedAnchor.latitude, selectedAnchor.longitude))
        return [];

    const source = sourceCandidates(inputs);
    const limit = Number(maxRows);
    const maximum = isFinite(limit) && limit > 0
                  ? Math.min(24, Math.floor(limit)) : 8;
    const rule = limits(selectedAnchor.hazard);
    const result = [];

    for (let i = 0; i < source.length; i++) {
        const row = source[i];
        if (row.source === selectedAnchor.source
                && row.id !== "" && row.id === selectedAnchor.id)
            continue;
        if (!compatible(
                selectedAnchor.hazard, row.hazard, row.mentionOnly))
            continue;

        const distance = distanceKm(
            selectedAnchor.latitude, selectedAnchor.longitude,
            row.latitude, row.longitude
        );
        if (distance < 0 || distance > rule.distanceKm)
            continue;

        const anchorTime = timeMs(selectedAnchor.observedMs);
        const candidateTime = timeMs(row.observedMs);
        let deltaHours = -1;
        let timeMatched = false;
        if (anchorTime > 0 && candidateTime > 0) {
            deltaHours = Math.abs(anchorTime - candidateTime) / 3600000;
            if (deltaHours > rule.hours)
                continue;
            timeMatched = true;
        }

        const relationKind = row.mentionOnly
            ? "MENTION NEARBY"
            : timeMatched ? "TIME + SPACE" : "SPACE ONLY";
        const ranking = (row.mentionOnly ? 0 : 100000)
                      + (timeMatched ? 50000 : 0)
                      + Math.max(0, rule.distanceKm - distance)
                      - (deltaHours >= 0 ? Math.min(deltaHours, 1000) : 0);

        result.push({
            source: row.source,
            id: row.id,
            title: row.title,
            hazard: row.hazard,
            latitude: row.latitude,
            longitude: row.longitude,
            distanceKm: distance,
            deltaHours: deltaHours,
            relationKind: relationKind,
            mentionOnly: row.mentionOnly,
            detail: row.detail,
            ranking: ranking,
            semantics: row.mentionOnly
                ? "ARTICLE MENTION NEAR AN EVENT ANCHOR, NOT VERIFIED EVENT LOCATION"
                : "RELATED SOURCE CONTEXT, NOT SAME-EVENT IDENTITY"
        });
    }

    result.sort(function(a, b) {
        if (b.ranking !== a.ranking)
            return b.ranking - a.ranking;
        return a.distanceKm - b.distanceKm;
    });
    return result.slice(0, maximum);
}
