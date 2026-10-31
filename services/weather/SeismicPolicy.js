.pragma library

// USGS past-day GeoJSON summary feed. Only observed and published event
// fields are displayed; this is not an earthquake prediction/alert feed.
function validNumber(value) {
    if (value === undefined || value === null || value === "")
        return null;
    const number = Number(value);
    return isFinite(number) ? number : null;
}

function distanceKm(latA, lonA, latB, lonB) {
    const a = validNumber(latA), b = validNumber(lonA);
    const c = validNumber(latB), d = validNumber(lonB);
    if (a === null || b === null || c === null || d === null
        || Math.abs(a) > 90 || Math.abs(c) > 90
        || Math.abs(b) > 180 || Math.abs(d) > 180)
        return -1;

    const rad = Math.PI / 180;
    const da = (c - a) * rad;
    const db = (d - b) * rad;
    const h = Math.sin(da / 2) ** 2 +
              Math.cos(a * rad) * Math.cos(c * rad) *
              Math.sin(db / 2) ** 2;
    return 6371 * 2 * Math.atan2(Math.sqrt(h), Math.sqrt(Math.max(0, 1 - h)));
}

function formatUtc(timeMs) {
    const ms = validNumber(timeMs);
    if (ms === null || ms <= 0)
        return "-- UTC";
    const date = new Date(ms);
    if (isNaN(date.getTime()))
        return "-- UTC";
    return date.toISOString().slice(11, 16) + " UTC";
}

function parseFeed(root, limit) {
    if (!root || root.type !== "FeatureCollection"
        || !Array.isArray(root.features))
        throw new Error("Invalid USGS feature collection");

    const requested = Number(limit);
    const size = isFinite(requested) && requested > 0
               ? Math.min(100, Math.floor(requested)) : 3;
    const result = [];

    for (let i = 0; i < root.features.length; ++i) {
        const feature = root.features[i];
        if (!feature || !feature.properties || !feature.geometry
            || feature.geometry.type !== "Point"
            || !Array.isArray(feature.geometry.coordinates))
            continue;
        const p = feature.properties;
        if (p.type && p.type !== "earthquake")
            continue;
        const magnitude = validNumber(p.mag);
        const time = validNumber(p.time);
        const coords = feature.geometry.coordinates;
        const lon = validNumber(coords[0]);
        const lat = validNumber(coords[1]);
        const depth = validNumber(coords[2]);
        if (magnitude === null || magnitude < 2.5
            || time === null || time <= 0 || lon === null || lat === null
            || Math.abs(lat) > 90 || Math.abs(lon) > 180)
            continue;

        const significance = validNumber(p.sig);
        const updated = validNumber(p.updated);
        result.push({
            id: String(feature.id || ""),
            magnitude: magnitude,
            place: String(p.place || "LOCATION UNAVAILABLE"),
            time: time,
            updated: updated === null ? -1 : updated,
            utc: formatUtc(time),
            depthKm: depth === null ? -1 : depth,
            latitude: lat,
            longitude: lon,
            significance: significance === null ? -1 : significance,
            tsunami: Number(p.tsunami) === 1,
            status: String(p.status || ""),
            alert: String(p.alert || ""),
            magType: String(p.magType || "")
        });
    }
    result.sort(function (a, b) { return b.time - a.time; });
    return result.slice(0, size);
}


function depthBand(depthKm) {
    const depth = validNumber(depthKm);
    if (depth === null || depth < 0)
        return { id: "unknown", label: "DEPTH UNKNOWN", token: "white" };
    if (depth < 70)
        return { id: "shallow", label: "SHALLOW <70 KM", token: "orange" };
    if (depth < 300)
        return { id: "intermediate", label: "INTERMEDIATE 70–299 KM", token: "cyan" };
    return { id: "deep", label: "DEEP ≥300 KM", token: "blue" };
}

function magnitudeRadius(magnitude) {
    const value = validNumber(magnitude);
    if (value === null)
        return 4;
    return Math.max(4, Math.min(10, 4 + (value - 2.5) * 1.45));
}

function recentRows(rows, limit) {
    if (!Array.isArray(rows))
        return [];
    const requested = Number(limit);
    const size = isFinite(requested) && requested > 0
               ? Math.min(100, Math.floor(requested)) : 3;
    return rows.slice(0, size);
}
