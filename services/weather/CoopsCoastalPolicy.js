.pragma library

var _catalogCache = {
    waterlevels: {rows: [], fetchedAt: 0},
    tidepredictions: {rows: [], fetchedAt: 0}
};

function finite(value) {
    if (value === undefined || value === null || value === "")
        return null;
    const number = Number(value);
    return isFinite(number) ? number : null;
}

function shortText(value, limit) {
    return String(value === undefined || value === null ? "" : value)
        .replace(/[\u0000-\u001f\u007f]/g, " ")
        .trim()
        .replace(/\s+/g, " ")
        .slice(0, limit);
}

function distanceKm(latA, lonA, latB, lonB) {
    const a = finite(latA), b = finite(lonA);
    const c = finite(latB), d = finite(lonB);
    if (a === null || b === null || c === null || d === null
            || Math.abs(a) > 90 || Math.abs(c) > 90
            || Math.abs(b) > 180 || Math.abs(d) > 180)
        return -1;
    const rad = Math.PI / 180;
    const dLat = (c - a) * rad;
    const dLon = (d - b) * rad;
    const h = Math.sin(dLat / 2) * Math.sin(dLat / 2)
        + Math.cos(a * rad) * Math.cos(c * rad)
        * Math.sin(dLon / 2) * Math.sin(dLon / 2);
    return 6371 * 2 * Math.atan2(
        Math.sqrt(h), Math.sqrt(Math.max(0, 1 - h))
    );
}

function normalizeStation(row) {
    if (!row || typeof row !== "object")
        return null;
    const id = shortText(row.id, 24);
    const name = shortText(row.name, 100);
    const latitude = finite(row.lat);
    const longitude = finite(
        row.lng !== undefined ? row.lng : row.lon
    );
    if (!id || latitude === null || longitude === null
            || Math.abs(latitude) > 90 || Math.abs(longitude) > 180)
        return null;
    return {
        id:id,
        name:name || id,
        latitude:latitude,
        longitude:longitude,
        state:shortText(row.state, 24),
        timezone:shortText(row.timezone, 64),
        tidal:row.tidal === true,
        greatLakes:row.greatlakes === true,
        affiliations:shortText(row.affiliations, 80)
    };
}

function parseStationCatalog(root) {
    if (!root || typeof root !== "object")
        throw new Error("Invalid CO-OPS station catalog");
    const source = Array.isArray(root.stations)
        ? root.stations
        : Array.isArray(root.stationList) ? root.stationList : [];
    const rows = [];
    for (let i = 0; i < source.length; i++) {
        const station = normalizeStation(source[i]);
        if (station)
            rows.push(station);
    }
    if (rows.length === 0)
        throw new Error("CO-OPS station catalog empty");
    return rows;
}

function nearestStation(rows, latitudeRaw, longitudeRaw) {
    const latitude = finite(latitudeRaw);
    const longitude = finite(longitudeRaw);
    if (!Array.isArray(rows) || latitude === null || longitude === null)
        return null;
    let best = null;
    for (let i = 0; i < rows.length; i++) {
        const row = rows[i];
        const distance = distanceKm(
            latitude, longitude, row.latitude, row.longitude
        );
        if (distance < 0)
            continue;
        if (!best || distance < best.distanceKm)
            best = Object.assign({}, row, {distanceKm:distance});
    }
    return best;
}

function cacheGet(kind, nowMs, ttlMs) {
    const entry = _catalogCache[String(kind || "")];
    const now = Number(nowMs);
    const ttl = Number(ttlMs);
    if (!entry || !Array.isArray(entry.rows) || entry.rows.length === 0
            || !isFinite(now) || !isFinite(ttl) || ttl <= 0
            || now - Number(entry.fetchedAt) < 0
            || now - Number(entry.fetchedAt) > ttl)
        return [];
    return entry.rows;
}

function cachePut(kind, rows, nowMs) {
    const key = String(kind || "");
    if (!_catalogCache[key] || !Array.isArray(rows) || rows.length === 0)
        return false;
    _catalogCache[key] = {
        rows:rows.slice(0),
        fetchedAt:Number(nowMs) || Date.now()
    };
    return true;
}

function clearCacheForTest() {
    _catalogCache.waterlevels = {rows:[], fetchedAt:0};
    _catalogCache.tidepredictions = {rows:[], fetchedAt:0};
}

function observationDatum(station) {
    if (!station)
        return "STND";
    if (station.greatLakes)
        return "LWD";
    if (station.tidal)
        return "MLLW";
    return "STND";
}

function parseWaterLevel(root) {
    if (!root || typeof root !== "object" || root.error)
        throw new Error("Invalid CO-OPS water-level response");
    const rows = Array.isArray(root.data) ? root.data : [];
    if (rows.length === 0)
        throw new Error("CO-OPS water level missing");
    const row = rows[rows.length - 1] || {};
    const value = finite(row.v);
    const time = shortText(row.t, 40);
    if (value === null || !time)
        throw new Error("CO-OPS water level unusable");
    return {
        value:value,
        time:time,
        sigma:finite(row.s),
        flags:shortText(row.f, 40),
        quality:shortText(row.q, 12)
    };
}

function parsePredictions(root) {
    if (!root || typeof root !== "object" || root.error)
        throw new Error("Invalid CO-OPS tide-prediction response");
    const source = Array.isArray(root.predictions) ? root.predictions : [];
    const rows = [];
    for (let i = 0; i < source.length; i++) {
        const row = source[i] || {};
        const value = finite(row.v);
        const time = shortText(row.t, 40);
        const type = shortText(row.type, 8).toUpperCase();
        if (value === null || !time || (type !== "H" && type !== "L"))
            continue;
        rows.push({
            time:time,
            value:value,
            type:type,
            label:type === "H" ? "HIGH" : "LOW"
        });
    }
    if (rows.length === 0)
        throw new Error("CO-OPS tide predictions missing");
    return rows.slice(0, 8);
}

function requestKey(latitudeRaw, longitudeRaw) {
    const latitude = finite(latitudeRaw);
    const longitude = finite(longitudeRaw);
    if (latitude === null || longitude === null
            || Math.abs(latitude) > 90 || Math.abs(longitude) > 180)
        return "";
    return latitude.toFixed(3) + "|" + longitude.toFixed(3);
}
