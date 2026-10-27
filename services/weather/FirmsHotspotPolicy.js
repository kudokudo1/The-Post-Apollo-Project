.pragma library

function clean(value, limit) {
    return String(value === undefined || value === null ? "" : value)
        .trim().slice(0, limit);
}

function finite(value) {
    if (value === undefined || value === null || value === "")
        return null;
    const number = Number(value);
    return isFinite(number) ? number : null;
}

function configuredKey(raw) {
    const key = String(raw || "").trim();
    return /^[A-Za-z0-9_-]{8,128}$/.test(key) ? key : "";
}

function boundedArea(bounds, maxLongitudeSpan, maxLatitudeSpan) {
    if (!bounds || !bounds.valid)
        return {valid: false, reason: "MAP VIEW UNAVAILABLE", bbox: ""};

    const west = finite(bounds.west);
    const south = finite(bounds.south);
    const east = finite(bounds.east);
    const north = finite(bounds.north);
    if (west === null || south === null || east === null || north === null
            || west < -180 || east > 180 || south < -90 || north > 90
            || !(west < east) || !(south < north)) {
        return {valid: false, reason: "MAP BOUNDS INVALID", bbox: ""};
    }

    const lonSpan = east - west;
    const latSpan = north - south;
    const lonLimit = Number(maxLongitudeSpan);
    const latLimit = Number(maxLatitudeSpan);
    if (!isFinite(lonLimit) || !isFinite(latLimit)
            || lonLimit <= 0 || latLimit <= 0)
        return {valid: false, reason: "REQUEST LIMIT INVALID", bbox: ""};

    if (lonSpan > lonLimit + 1e-9 || latSpan > latLimit + 1e-9) {
        return {
            valid: false,
            reason: "ZOOM IN // VIEW TOO WIDE",
            bbox: "",
            longitudeSpan: lonSpan,
            latitudeSpan: latSpan
        };
    }

    return {
        valid: true,
        reason: "",
        bbox: [west, south, east, north]
            .map(function(value) { return Number(value).toFixed(4); })
            .join(","),
        west: west,
        south: south,
        east: east,
        north: north,
        longitudeSpan: lonSpan,
        latitudeSpan: latSpan
    };
}

function splitCsvLine(line) {
    const result = [];
    let value = "";
    let quoted = false;
    for (let i = 0; i < line.length; i++) {
        const ch = line[i];
        if (quoted) {
            if (ch === '"') {
                if (i + 1 < line.length && line[i + 1] === '"') {
                    value += '"';
                    i++;
                } else {
                    quoted = false;
                }
            } else {
                value += ch;
            }
        } else if (ch === '"') {
            quoted = true;
        } else if (ch === ",") {
            result.push(value);
            value = "";
        } else {
            value += ch;
        }
    }
    result.push(value);
    return result;
}

function confidenceLabel(raw) {
    switch (String(raw || "").trim().toLowerCase()) {
    case "h": return "HIGH";
    case "n": return "NOMINAL";
    case "l": return "LOW";
    default: return clean(raw, 24).toUpperCase() || "UNKNOWN";
    }
}

function acquiredUtc(dateRaw, timeRaw) {
    const date = String(dateRaw || "").trim();
    let time = String(timeRaw || "").trim();
    if (!/^\d{4}-\d{2}-\d{2}$/.test(date) || !/^\d{1,4}$/.test(time))
        return "";
    time = time.padStart(4, "0");
    const hh = Number(time.slice(0, 2));
    const mm = Number(time.slice(2, 4));
    if (!isFinite(hh) || !isFinite(mm) || hh > 23 || mm > 59)
        return "";
    return date + " " + time.slice(0, 2) + ":" + time.slice(2) + "Z";
}

function parseViirsCsv(raw, limit) {
    const text = String(raw || "").replace(/^\uFEFF/, "").trim();
    if (!text)
        return [];

    const lines = text.split(/\r?\n/).filter(function(line) {
        return line.trim().length > 0;
    });
    if (lines.length < 1)
        return [];

    const header = splitCsvLine(lines[0]).map(function(value) {
        return String(value || "").trim().toLowerCase();
    });
    const index = {};
    for (let i = 0; i < header.length; i++)
        index[header[i]] = i;

    for (const required of ["latitude", "longitude", "acq_date", "acq_time"]) {
        if (index[required] === undefined)
            throw new Error("Invalid FIRMS VIIRS CSV");
    }

    const requested = Number(limit);
    const maximum = isFinite(requested) && requested > 0
                  ? Math.min(2000, Math.floor(requested)) : 800;
    const rows = [];
    const seen = {};

    function field(values, name) {
        const at = index[name];
        return at === undefined ? "" : values[at];
    }

    for (let i = 1; i < lines.length && rows.length < maximum; i++) {
        const values = splitCsvLine(lines[i]);
        const latitude = finite(field(values, "latitude"));
        const longitude = finite(field(values, "longitude"));
        if (latitude === null || longitude === null
                || Math.abs(latitude) > 90 || Math.abs(longitude) > 180)
            continue;

        const date = clean(field(values, "acq_date"), 16);
        const time = clean(field(values, "acq_time"), 8);
        const acquired = acquiredUtc(date, time);
        if (!acquired)
            continue;

        const satellite = clean(field(values, "satellite"), 24);
        const confidence = clean(field(values, "confidence"), 24);
        const dedupe = [
            latitude.toFixed(5), longitude.toFixed(5),
            acquired, satellite
        ].join("|");
        if (seen[dedupe])
            continue;
        seen[dedupe] = true;

        const brightness = finite(field(values, "bright_ti4"));
        const frp = finite(field(values, "frp"));
        rows.push({
            id: dedupe,
            title: "VIIRS HOTSPOT",
            latitude: latitude,
            longitude: longitude,
            coordinates: latitude.toFixed(4) + ", " + longitude.toFixed(4),
            acquiredUtc: acquired,
            brightnessK: brightness === null ? -1 : brightness,
            frpMw: frp === null ? -1 : frp,
            confidenceCode: confidence,
            confidenceLabel: confidenceLabel(confidence),
            satellite: satellite || "UNKNOWN",
            instrument: clean(field(values, "instrument"), 24) || "VIIRS",
            dayNight: clean(field(values, "daynight"), 8).toUpperCase() || "UNKNOWN",
            version: clean(field(values, "version"), 32)
        });
    }
    return rows;
}
