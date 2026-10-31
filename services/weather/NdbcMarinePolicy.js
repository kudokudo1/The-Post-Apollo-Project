.pragma library

function finite(value) {
    if (value === undefined || value === null)
        return null;
    const text = String(value).trim();
    if (!text || text === "MM" || text === "N/A" || text === "-")
        return null;
    const number = Number(text);
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
    const a = finite(latA);
    const b = finite(lonA);
    const c = finite(latB);
    const d = finite(lonB);
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

function utcLabel(millisRaw) {
    const millis = Number(millisRaw);
    if (!isFinite(millis) || millis <= 0)
        return "--";
    const iso = new Date(millis).toISOString();
    return iso.slice(0, 10) + " " + iso.slice(11, 16) + "Z";
}

function parseHeader(line) {
    const text = String(line || "").trim();
    if (text.indexOf("#STN") !== 0)
        return [];
    return text.slice(1).trim().split(/\s+/);
}

function rowObject(header, tokens) {
    const out = {};
    for (let i = 0; i < header.length && i < tokens.length; i++)
        out[header[i]] = tokens[i];
    return out;
}

function observationMillis(row) {
    const year = finite(row.YYYY);
    const month = finite(row.MM);
    const day = finite(row.DD);
    const hour = finite(row.hh);
    const minute = finite(row.mm);
    if (year === null || month === null || day === null
            || hour === null || minute === null)
        return -1;
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

function parseLatest(text) {
    const lines = String(text || "").split(/\r?\n/);
    let header = [];
    const rows = [];

    for (let i = 0; i < lines.length; i++) {
        const raw = String(lines[i] || "").trim();
        if (!raw)
            continue;
        if (raw.indexOf("#STN") === 0) {
            header = parseHeader(raw);
            continue;
        }
        if (raw[0] === "#")
            continue;
        if (header.length === 0)
            continue;

        const source = rowObject(header, raw.split(/\s+/));
        const stationId = shortText(source.STN, 16);
        const latitude = finite(source.LAT);
        const longitude = finite(source.LON);
        const sampleMillis = observationMillis(source);
        if (!stationId || latitude === null || longitude === null
                || Math.abs(latitude) > 90 || Math.abs(longitude) > 180
                || sampleMillis < 0)
            continue;

        rows.push({
            stationId:stationId,
            latitude:latitude,
            longitude:longitude,
            sampleMillis:sampleMillis,
            sampleUtc:utcLabel(sampleMillis),
            windDirection:finite(source.WDIR),
            windSpeedMs:finite(source.WSPD),
            gustMs:finite(source.GST),
            waveHeightM:finite(source.WVHT),
            dominantPeriodS:finite(source.DPD),
            averagePeriodS:finite(source.APD),
            meanWaveDirection:finite(source.MWD),
            pressureHpa:finite(source.PRES),
            pressureTendencyHpa:finite(source.PTDY),
            airTempC:finite(source.ATMP),
            waterTempC:finite(source.WTMP),
            dewpointC:finite(source.DEWP),
            visibilityNm:finite(source.VIS),
            tideFt:finite(source.TIDE)
        });
    }

    if (header.length === 0)
        throw new Error("NDBC latest-observation header missing");
    if (rows.length === 0)
        throw new Error("NDBC latest-observation data missing");
    return rows;
}

function nearest(rows, latitudeRaw, longitudeRaw) {
    const latitude = finite(latitudeRaw);
    const longitude = finite(longitudeRaw);
    if (!Array.isArray(rows)
            || latitude === null || longitude === null
            || Math.abs(latitude) > 90 || Math.abs(longitude) > 180)
        return null;

    let best = null;
    for (let i = 0; i < rows.length; i++) {
        const row = rows[i];
        const distance = distanceKm(
            latitude, longitude, row.latitude, row.longitude
        );
        if (distance < 0)
            continue;
        if (!best || distance < best.distanceKm) {
            best = Object.assign({}, row, {distanceKm:distance});
        }
    }
    return best;
}

function requestKey(latitudeRaw, longitudeRaw) {
    const latitude = finite(latitudeRaw);
    const longitude = finite(longitudeRaw);
    if (latitude === null || longitude === null
            || Math.abs(latitude) > 90 || Math.abs(longitude) > 180)
        return "";
    return latitude.toFixed(3) + "|" + longitude.toFixed(3);
}

function celsiusToF(valueRaw) {
    const value = finite(valueRaw);
    return value === null ? null : value * 9 / 5 + 32;
}

function metersToFeet(valueRaw) {
    const value = finite(valueRaw);
    return value === null ? null : value * 3.28084;
}

function metersPerSecondToMph(valueRaw) {
    const value = finite(valueRaw);
    return value === null ? null : value * 2.236936;
}

function numericLabel(valueRaw, digits, suffix) {
    const value = finite(valueRaw);
    return value === null ? "--"
        : value.toFixed(Math.max(0, Number(digits) || 0))
          + String(suffix || "");
}
