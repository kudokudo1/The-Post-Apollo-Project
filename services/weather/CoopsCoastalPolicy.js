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

function boolValue(value) {
    if (value === true || value === 1)
        return true;
    if (value === false || value === 0)
        return false;
    const text = String(value === undefined || value === null ? "" : value)
        .trim().toLowerCase();
    if (text === "true" || text === "yes" || text === "1")
        return true;
    if (text === "false" || text === "no" || text === "0")
        return false;
    return null;
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
    if (!/^[A-Za-z0-9_-]{1,24}$/.test(id)
            || latitude === null || longitude === null
            || Math.abs(latitude) > 90 || Math.abs(longitude) > 180)
        return null;
    return {
        id:id,
        name:name || id,
        latitude:latitude,
        longitude:longitude,
        state:shortText(row.state, 24),
        timezone:shortText(row.timezone, 64),
        tidal:boolValue(row.tidal) === true,
        greatLakes:boolValue(row.greatlakes) === true,
        affiliations:shortText(row.affiliations, 80),
        predictionType:shortText(row.type, 8).toUpperCase(),
        referenceId:shortText(row.reference_id, 24)
    };
}

function parseStationCatalog(root) {
    if (!root || typeof root !== "object" || Array.isArray(root) || root.error)
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

function coopsUtcMillis(value) {
    const text = String(value || "").trim();
    const match = /^(\d{4})-(\d{2})-(\d{2})[ T](\d{2}):(\d{2})$/.exec(text);
    if (!match)
        return -1;
    const year = Number(match[1]);
    const month = Number(match[2]);
    const day = Number(match[3]);
    const hour = Number(match[4]);
    const minute = Number(match[5]);
    const millis = Date.UTC(year, month - 1, day, hour, minute);
    const check = new Date(millis);
    if (check.getUTCFullYear() !== year
            || check.getUTCMonth() !== month - 1
            || check.getUTCDate() !== day
            || check.getUTCHours() !== hour
            || check.getUTCMinutes() !== minute)
        return -1;
    return millis;
}

function utcLabel(millisRaw) {
    const millis = Number(millisRaw);
    if (!isFinite(millis) || millis <= 0)
        return "--";
    const iso = new Date(millis).toISOString();
    return iso.slice(0, 10) + " " + iso.slice(11, 16) + "Z";
}

function parseWaterLevel(root) {
    if (!root || typeof root !== "object" || Array.isArray(root) || root.error)
        throw new Error("Invalid CO-OPS water-level response");
    const rows = Array.isArray(root.data) ? root.data : [];
    let latest = null;
    for (let i = 0; i < rows.length; i++) {
        const row = rows[i] || {};
        const value = finite(row.v);
        const millis = coopsUtcMillis(row.t);
        if (value === null || millis < 0)
            continue;
        const sample = {
            value:value,
            time:shortText(row.t, 40),
            sampleMillis:millis,
            sampleUtc:utcLabel(millis),
            sigma:finite(row.s),
            flags:shortText(row.f, 40),
            quality:shortText(row.q, 12).toLowerCase()
        };
        if (!latest || sample.sampleMillis > latest.sampleMillis)
            latest = sample;
    }
    if (!latest)
        throw new Error("CO-OPS water level missing");
    latest.qualityLabel = latest.quality === "p" ? "PRELIMINARY"
        : latest.quality === "v" ? "VERIFIED" : "QUALITY UNSPECIFIED";
    return latest;
}

function predictionKind(value) {
    const type = shortText(value, 8).toUpperCase();
    if (type === "HH") return {id:"HH", label:"HIGHER HIGH", high:true};
    if (type === "H") return {id:"H", label:"HIGH", high:true};
    if (type === "LL") return {id:"LL", label:"LOWER LOW", high:false};
    if (type === "L") return {id:"L", label:"LOW", high:false};
    return {id:type || "?", label:type || "PREDICTED", high:null};
}

function parsePredictions(root, nowMs, limit) {
    if (!root || typeof root !== "object" || Array.isArray(root) || root.error)
        throw new Error("Invalid CO-OPS tide-prediction response");
    const source = Array.isArray(root.predictions) ? root.predictions : [];
    const floor = isFinite(Number(nowMs)) && Number(nowMs) > 0
        ? Number(nowMs) - 60000 : 0;
    const rows = [];
    for (let i = 0; i < source.length; i++) {
        const row = source[i] || {};
        const value = finite(row.v);
        const millis = coopsUtcMillis(row.t);
        if (value === null || millis < floor)
            continue;
        const kind = predictionKind(
            row.type !== undefined ? row.type : row.ty
        );
        rows.push({
            time:shortText(row.t, 40),
            sampleMillis:millis,
            sampleUtc:utcLabel(millis),
            value:value,
            type:kind.id,
            label:kind.label,
            high:kind.high
        });
    }
    rows.sort(function(a, b) { return a.sampleMillis - b.sampleMillis; });
    const count = Math.max(1, Math.min(12, Math.floor(Number(limit) || 6)));
    return rows.slice(0, count);
}

function requestKey(latitudeRaw, longitudeRaw) {
    const latitude = finite(latitudeRaw);
    const longitude = finite(longitudeRaw);
    if (latitude === null || longitude === null
            || Math.abs(latitude) > 90 || Math.abs(longitude) > 180)
        return "";
    return latitude.toFixed(3) + "|" + longitude.toFixed(3);
}

function ymdUtc(millisRaw) {
    const millis = Number(millisRaw);
    if (!isFinite(millis) || millis <= 0)
        return "";
    const date = new Date(millis);
    return String(date.getUTCFullYear()).padStart(4, "0")
        + String(date.getUTCMonth() + 1).padStart(2, "0")
        + String(date.getUTCDate()).padStart(2, "0");
}

function predictionWindow(nowMs) {
    const now = Number(nowMs);
    if (!isFinite(now) || now <= 0)
        return {beginDate:"", endDate:""};
    const date = new Date(now);
    const start = Date.UTC(
        date.getUTCFullYear(), date.getUTCMonth(), date.getUTCDate()
    );
    return {
        beginDate:ymdUtc(start),
        endDate:ymdUtc(start + 2 * 86400000)
    };
}

function feetLabel(valueRaw) {
    const value = finite(valueRaw);
    return value === null ? "--" : value.toFixed(2) + " ft";
}
