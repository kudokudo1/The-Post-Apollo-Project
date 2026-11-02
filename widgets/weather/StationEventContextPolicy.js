.pragma library

// Weather MAP M13 selected-event spatial context.
//
// This policy joins already-loaded MAP records. It never fetches, persists,
// interprets radar pixels, or asserts that nearby records describe one event.

function finite(value, fallback) {
    if (value === undefined || value === null || value === "")
        return fallback;
    const number = Number(value);
    return isFinite(number) ? number : fallback;
}

function safeText(value, limit) {
    return String(value === undefined || value === null ? "" : value)
        .trim().replace(/\s+/g, " ")
        .slice(0, Math.max(1, Number(limit) || 120));
}

function validPoint(latitude, longitude) {
    const lat = finite(latitude, null);
    const lon = finite(longitude, null);
    return lat !== null && lon !== null
        && Math.abs(lat) <= 90 && Math.abs(lon) <= 180;
}

function distanceKm(latA, lonA, latB, lonB) {
    if (!validPoint(latA, lonA) || !validPoint(latB, lonB))
        return -1;
    const a = Number(latA);
    const b = Number(lonA);
    const c = Number(latB);
    const d = Number(lonB);
    const rad = Math.PI / 180;
    const dLat = (c - a) * rad;
    const dLon = (d - b) * rad;
    const h = Math.sin(dLat / 2) * Math.sin(dLat / 2)
            + Math.cos(a * rad) * Math.cos(c * rad)
            * Math.sin(dLon / 2) * Math.sin(dLon / 2);
    return 6371 * 2 * Math.atan2(
        Math.sqrt(h),
        Math.sqrt(Math.max(0, 1 - h))
    );
}

function sourceLabel(sourceId) {
    switch (String(sourceId || "")) {
    case "gdacs": return "GDACS";
    case "usgs": return "USGS";
    case "eonet": return "NASA EONET";
    case "firms": return "NASA FIRMS";
    default: return "MAP SOURCE";
    }
}

function parseMillis(value) {
    if (value === undefined || value === null || value === "")
        return -1;
    const direct = Number(value);
    if (isFinite(direct) && direct > 0)
        return direct;
    const parsed = Date.parse(String(value));
    return isFinite(parsed) && parsed > 0 ? parsed : -1;
}

function utcLabel(value) {
    const ms = parseMillis(value);
    if (ms <= 0)
        return "-- UTC";
    const date = new Date(ms);
    return isNaN(date.getTime())
        ? "-- UTC"
        : date.toISOString().slice(0, 16).replace("T", " ") + " UTC";
}

function normalizeSelected(sourceId, row) {
    const source = String(sourceId || "");
    if (!row || typeof row !== "object")
        return null;

    let id = "";
    let title = "";
    let typeLabel = "";
    let latitude = null;
    let longitude = null;
    let timeMs = -1;
    let timeLabel = "-- UTC";

    if (source === "gdacs") {
        id = safeText(row.id, 100);
        title = safeText(row.name, 180);
        typeLabel = safeText(row.eventTypeLabel, 80);
        latitude = finite(row.latitude, null);
        longitude = finite(row.longitude, null);
        timeMs = parseMillis(row.timeMs);
        timeLabel = safeText(row.toUtc || row.fromUtc, 48) || utcLabel(timeMs);
    } else if (source === "usgs") {
        id = safeText(row.id, 100);
        title = "M" + (
            finite(row.magnitude, null) === null
            ? "--" : Number(row.magnitude).toFixed(1)
        ) + " // " + safeText(row.place, 150);
        typeLabel = "EARTHQUAKE";
        latitude = finite(row.latitude, null);
        longitude = finite(row.longitude, null);
        timeMs = parseMillis(row.time);
        timeLabel = utcLabel(timeMs);
    } else if (source === "eonet") {
        id = safeText(row.id, 100);
        title = safeText(row.title, 180);
        typeLabel = safeText(row.category, 80) || "NATURAL EVENT";
        latitude = finite(row.latitude, null);
        longitude = finite(row.longitude, null);
        timeMs = parseMillis(row.rawTime || row.time);
        timeLabel = safeText(row.time, 48) || utcLabel(timeMs);
    } else if (source === "firms") {
        id = safeText(row.id, 160);
        title = safeText(row.title, 120) || "VIIRS HOTSPOT";
        typeLabel = "THERMAL HOTSPOT";
        latitude = finite(row.latitude, null);
        longitude = finite(row.longitude, null);
        timeMs = parseMillis(row.acquiredUtc);
        timeLabel = safeText(row.acquiredUtc, 48) || utcLabel(timeMs);
    } else {
        return null;
    }

    return {
        sourceId: source,
        sourceLabel: sourceLabel(source),
        id: id,
        title: title || sourceLabel(source) + " EVENT",
        typeLabel: typeLabel || "EVENT",
        latitude: latitude,
        longitude: longitude,
        hasPoint: validPoint(latitude, longitude),
        coordinates: validPoint(latitude, longitude)
            ? Number(latitude).toFixed(3) + ", "
              + Number(longitude).toFixed(3)
            : "POINT LOCATION UNAVAILABLE",
        timeMs: timeMs,
        timeLabel: timeLabel
    };
}

function pointInBounds(latitude, longitude, bounds) {
    if (!validPoint(latitude, longitude)
            || !plainBoundsAvailable(bounds))
        return false;
    const west = finite(bounds.west, null);
    const south = finite(bounds.south, null);
    const east = finite(bounds.east, null);
    const north = finite(bounds.north, null);
    if (west === null || south === null
            || east === null || north === null
            || !(west < east) || !(south < north))
        return false;
    const lat = Number(latitude);
    const lon = Number(longitude);
    return lon >= west && lon <= east
        && lat >= south && lat <= north;
}

function radarCoverage(
    selected, bounds, loadedHistoryMinutes,
    requestedTimeMs, usingCache
) {
    const hasFrame = !!bounds && bounds.valid === true;
    const hasPoint = !!selected && selected.hasPoint === true;
    const covered = hasFrame && hasPoint
        && pointInBounds(selected.latitude, selected.longitude, bounds);
    const minutes = Math.max(
        0,
        Math.round(Number(loadedHistoryMinutes) || 0)
    );
    const frameLabel = minutes > 0 ? "-" + minutes + "M" : "NOW";
    const requested = Number(requestedTimeMs);
    return {
        available: hasFrame,
        covered: covered,
        frameLabel: frameLabel,
        timeLabel: isFinite(requested) && requested > 0
            ? utcLabel(requested) : "LATEST FRAME",
        usingCache: usingCache === true,
        status: !hasFrame
            ? "NO LOADED MRMS FRAME"
            : !hasPoint
              ? "EVENT HAS NO POINT COORDINATE"
              : covered
                ? "FRAME COVERS EVENT COORDINATE"
                : "EVENT OUTSIDE LOADED FRAME"
    };
}

function plainBoundsAvailable(bounds) {
    if (!bounds || typeof bounds !== "object" || bounds.valid === false)
        return false;
    const west = finite(bounds.west, null);
    const south = finite(bounds.south, null);
    const east = finite(bounds.east, null);
    const north = finite(bounds.north, null);
    return west !== null && south !== null
        && east !== null && north !== null
        && west < east && south < north;
}

function lightningCoverage(
    selected, bounds, ready, latestTime,
    windowMinutes, resolutionKm, radiusKm, usingCache
) {
    const hasFrame = ready === true && plainBoundsAvailable(bounds);
    const hasPoint = !!selected && selected.hasPoint === true;
    const covered = hasFrame && hasPoint
        && pointInBounds(selected.latitude, selected.longitude, bounds);
    const window = Math.max(
        0,
        Math.round(Number(windowMinutes) || 0)
    );
    const resolution = Math.max(
        0,
        Math.round(Number(resolutionKm) || 0)
    );
    const radius = Math.max(
        0,
        Math.round(Number(radiusKm) || 0)
    );
    return {
        available: hasFrame,
        covered: covered,
        timeLabel: safeText(latestTime, 48) || "LATEST",
        windowMinutes: window,
        resolutionKm: resolution,
        radiusKm: radius,
        usingCache: usingCache === true,
        status: !hasFrame
            ? "NO LOADED LIGHTNING FRAME"
            : !hasPoint
              ? "EVENT HAS NO POINT COORDINATE"
              : covered
                ? "FRAME COVERS EVENT COORDINATE"
                : "EVENT OUTSIDE LIGHTNING FRAME"
    };
}

function weatherFixDistance(selected, latitude, longitude) {
    if (!selected || selected.hasPoint !== true
            || !validPoint(latitude, longitude))
        return -1;
    return distanceKm(
        selected.latitude, selected.longitude,
        latitude, longitude
    );
}

function normalizeCompanion(sourceId, row) {
    return normalizeSelected(sourceId, row);
}

function nearbyEvidence(selected, bundles, radiusKm, maximum) {
    if (!selected || selected.hasPoint !== true)
        return [];

    const radius = Math.max(
        1,
        Math.min(2000, Number(radiusKm) || 250)
    );
    const limit = Math.max(
        1,
        Math.min(12, Math.floor(Number(maximum) || 6))
    );
    const sourceBundles = Array.isArray(bundles) ? bundles : [];
    const out = [];

    for (let i = 0; i < sourceBundles.length; i++) {
        const bundle = sourceBundles[i] || {};
        const sourceId = String(bundle.sourceId || "");
        if (!sourceId || sourceId === selected.sourceId)
            continue;
        const rows = Array.isArray(bundle.rows) ? bundle.rows : [];
        for (let j = 0; j < rows.length; j++) {
            const event = normalizeCompanion(sourceId, rows[j]);
            if (!event || event.hasPoint !== true)
                continue;
            const distance = distanceKm(
                selected.latitude, selected.longitude,
                event.latitude, event.longitude
            );
            if (distance < 0 || distance > radius)
                continue;
            out.push({
                sourceId: event.sourceId,
                sourceLabel: event.sourceLabel,
                id: event.id,
                title: event.title,
                typeLabel: event.typeLabel,
                latitude: event.latitude,
                longitude: event.longitude,
                coordinates: event.coordinates,
                timeMs: event.timeMs,
                timeLabel: event.timeLabel,
                distanceKm: distance
            });
        }
    }

    out.sort(function(a, b) {
        if (a.distanceKm !== b.distanceKm)
            return a.distanceKm - b.distanceKm;
        return Number(b.timeMs || -1) - Number(a.timeMs || -1);
    });

    return out.slice(0, limit);
}
